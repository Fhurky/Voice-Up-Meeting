"""Installed model selection preserves identity and exposes bounded assistant text."""

import asyncio
import json
from dataclasses import asdict

import httpx
import pytest

from app.core.config import get_settings
from app.infrastructure import ollama_correction as adapter_module
from app.services import transcript_correction_ports as ports
from app.services.speaker_ports import SpeakerError

MODEL = "qwen3.5:27b"
DIGEST = "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
CONTEXT = ports.CorrectionContext("Yeni sürüyü yükledik.", ("Yazılım hazır.",), (), "tr")


def settings():
    return get_settings().model_copy(
        update={
            "text_review_enabled": True,
            "text_review_url": "http://ollama:11434",
            "text_review_model": MODEL,
            "text_review_model_digest": DIGEST,
        }
    )


def entry(name=MODEL, digest=DIGEST, **extra):
    return {"name": name, "model": name, "digest": digest, "size": 17420432728, **extra}


def show(**extra):
    return {
        "capabilities": ["completion", "thinking", "tools"],
        "template": "private-template",
        "model_info": {"private": "not-returned"},
        **extra,
    }


def completion(name=MODEL, text='{"edits":[]}', **extra):
    return {
        "model": name,
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": text},
        **extra,
    }


def selection(name=MODEL, digest=DIGEST):
    return ports.ModelSelection(name, digest)


async def test_catalog_returns_all_three_installed_models_without_private_metadata():
    models = [entry(), entry("qwen3.6:12B", "a" * 64), entry("qwen3.5:9b", "b" * 64)]

    def handle(request):
        return httpx.Response(
            200, json={"models": models} if request.url.path == "/api/tags" else show()
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await adapter_module.OllamaCorrectionAdapter(settings(), client).list_models()
    assert len(result) == 3
    assert {row.name for row in result} == {row["name"] for row in models}
    for row in result:
        assert set(asdict(row)) == {
            "name",
            "digest",
            "size_bytes",
            "selectable",
            "unavailable_reason",
            "is_default",
        }
        assert row.selectable and row.unavailable_reason is None
        assert row.is_default is (row.name == MODEL)


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("remote_tags", "remote_model"),
        ("remote_show", "remote_model"),
        ("embedding", "not_language_model"),
        ("capabilities", "not_language_model"),
        ("default", "default_changed"),
        ("unavailable", "metadata_unavailable"),
    ],
)
async def test_catalog_marks_unusable_records_without_exposing_show_metadata(fault, reason):
    model = entry(**({"remote_host": "https://private.invalid"} if fault == "remote_tags" else {}))
    if fault == "default":
        model["digest"] = "a" * 64

    def handle(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [model]})
        if fault == "unavailable":
            return httpx.Response(503)
        details = show()
        if fault == "remote_show":
            details["remote_model"] = "private-other"
        if fault == "embedding":
            details["capabilities"] = ["embedding"]
        if fault == "capabilities":
            details["capabilities"] = "completion"
        return httpx.Response(200, json=details)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        rows = await adapter_module.OllamaCorrectionAdapter(settings(), client).list_models()
    assert len(rows) == 1 and rows[0].selectable is False
    assert rows[0].unavailable_reason == reason
    if fault == "default":
        assert rows[0].is_default is False


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"edits":[],"edits":[]}',
        '{"edits":[{"original":"üç","replacement":"beş"}]}',
        "<script>alert('text-only')</script>",
    ],
)
async def test_selected_suggestion_preserves_every_assistant_content_without_inner_parsing(content):
    seen = []

    def handle(request):
        seen.append(request)
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [entry()]})
        return httpx.Response(
            200, json=show() if request.url.path == "/api/show" else completion(text=content)
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await adapter_module.OllamaCorrectionAdapter(settings(), client).suggest(
            CONTEXT, selection()
        )
    assert result.model_output == content and result.model_output_truncated is False
    body = json.loads(next(item.content for item in seen if item.url.path == "/api/chat"))
    assert body["model"] == MODEL and body["think"] is False and body["stream"] is False
    assert body["messages"][0]["content"] == adapter_module._SYSTEM_PROMPT
    assert body["format"] == adapter_module._FORMAT
    assert body["options"] == {"temperature": 0, "seed": 42, "num_predict": 512, "num_ctx": 8192}
    assert set(json.loads(body["messages"][1]["content"])) == {
        "language",
        "before",
        "target",
        "after",
    }
    assert result.model_name == MODEL and result.model_digest == DIGEST


@pytest.mark.parametrize("length,done_reason", [(8193, "stop"), (12, "length")])
async def test_selected_truncation_is_visible_and_measured_in_codepoints(length, done_reason):
    content = "😀" * length

    def handle(request):
        value = (
            {"models": [entry()]}
            if request.url.path == "/api/tags"
            else (
                show()
                if request.url.path == "/api/show"
                else completion(text=content, done_reason=done_reason)
            )
        )
        return httpx.Response(200, json=value)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await adapter_module.OllamaCorrectionAdapter(settings(), client).suggest(
            CONTEXT, selection()
        )
    assert result.model_output == content[:8192]
    assert result.model_output_truncated is True


async def test_concurrent_selected_models_do_not_mutate_cached_default_settings():
    models = [entry(), entry("qwen3.6:12B", "a" * 64), entry("qwen3.5:9b", "b" * 64)]
    config = settings()
    original = config.model_dump()

    async def handle(request):
        await asyncio.sleep(0)
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": models})
        if request.url.path == "/api/show":
            return httpx.Response(200, json=show())
        return httpx.Response(200, json=completion(name=json.loads(request.content)["model"]))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        adapter = adapter_module.OllamaCorrectionAdapter(config, client)
        rows = await asyncio.gather(
            *(adapter.suggest(CONTEXT, selection(row["name"], row["digest"])) for row in models)
        )
    assert [(row.model_name, row.model_digest) for row in rows] == [
        (row["name"], row["digest"]) for row in models
    ]
    assert config.model_dump() == original


@pytest.mark.parametrize(
    "fault", ["digest", "duplicate", "remote_show", "not_completion", "changed_default"]
)
async def test_unverified_selection_never_receives_private_source(fault):
    seen = []
    model = entry(digest="a" * 64) if fault in {"digest", "changed_default"} else entry()

    def handle(request):
        seen.append(request.url.path)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [model, model] if fault == "duplicate" else [model]}
            )
        return httpx.Response(
            200,
            json=show(
                **(
                    {"remote_origin": "private"}
                    if fault == "remote_show"
                    else {"capabilities": ["embedding"]}
                )
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_model_mismatch"):
            await adapter_module.OllamaCorrectionAdapter(settings(), client).suggest(
                CONTEXT, selection(digest="a" * 64 if fault == "changed_default" else DIGEST)
            )
    assert "/api/chat" not in seen


@pytest.mark.parametrize("fault", ["digest", "removed", "remote_show"])
async def test_post_inference_identity_and_capability_changes_discard_content(fault):
    generated = False

    def handle(request):
        nonlocal generated
        if request.url.path == "/api/chat":
            generated = True
            return httpx.Response(200, json=completion(text="never-expose"))
        if request.url.path == "/api/show":
            return httpx.Response(
                200,
                json=show(
                    **({"remote_model": "other"} if generated and fault == "remote_show" else {})
                ),
            )
        models = (
            []
            if generated and fault == "removed"
            else [entry(digest="a" * 64 if generated and fault == "digest" else DIGEST)]
        )
        return httpx.Response(200, json={"models": models})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_model_mismatch"):
            await adapter_module.OllamaCorrectionAdapter(settings(), client).suggest(
                CONTEXT, selection()
            )


@pytest.mark.parametrize(
    "change",
    [
        {"done": False},
        {"model": "wrong"},
        {"done_reason": "tool_calls"},
        {"message": {"role": "tool", "content": "raw"}},
        {
            "message": {
                "role": "assistant",
                "content": "raw",
                "tool_calls": [{"function": {"name": "no"}}],
            }
        },
    ],
)
async def test_untrusted_envelope_is_not_exposed_as_model_text(change):
    def handle(request):
        return httpx.Response(
            200,
            json=(
                {"models": [entry()]}
                if request.url.path == "/api/tags"
                else show() if request.url.path == "/api/show" else completion(**change)
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_invalid_response"):
            await adapter_module.OllamaCorrectionAdapter(settings(), client).suggest(
                CONTEXT, selection()
            )


async def test_catalog_is_bounded_uncached_and_limits_parallel_show_requests():
    active = maximum = show_count = 0
    models = [entry(f"local-{index:03}:latest", f"{index:064x}") for index in range(105)]

    async def handle(request):
        nonlocal active, maximum, show_count
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": models})
        show_count += 1
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.001)
        active -= 1
        return httpx.Response(200, json=show())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        adapter = adapter_module.OllamaCorrectionAdapter(settings(), client)
        assert len(await adapter.list_models()) == 100
        models[:] = [entry()]
        assert (await adapter.list_models())[0].name == MODEL
    assert show_count == 101 and maximum <= 4


@pytest.mark.parametrize("operation", ["list", "suggest"])
async def test_new_model_operations_have_a_total_deadline(monkeypatch, operation):
    async def handle(request):
        await asyncio.Event().wait()
        return httpx.Response(200, json={})

    monkeypatch.setattr(adapter_module, "MODEL_LIST_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(adapter_module, "REVIEW_TIMEOUT_SECONDS", 0.01)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        adapter = adapter_module.OllamaCorrectionAdapter(settings(), client)
        with pytest.raises(SpeakerError, match="text_review_timeout"):
            await asyncio.wait_for(
                (
                    adapter.list_models()
                    if operation == "list"
                    else adapter.suggest(CONTEXT, selection())
                ),
                timeout=1,
            )


@pytest.mark.parametrize("fault", ["name", "digest", "size", "model", "document"])
async def test_catalog_rejects_malformed_identity_instead_of_fabricating_metadata(fault):
    record = entry()
    if fault == "name":
        record["name"] = "private\nname"
    if fault == "digest":
        record["digest"] = "not-a-digest"
    if fault == "size":
        record["size"] = True
    if fault == "model":
        record["model"] = "different-alias"

    def handle(request):
        return httpx.Response(200, json={"models": None if fault == "document" else [record]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_invalid_response"):
            await adapter_module.OllamaCorrectionAdapter(settings(), client).list_models()


async def test_catalog_race_returns_visible_unavailable_identity():
    count = 0

    def handle(request):
        nonlocal count
        if request.url.path == "/api/show":
            return httpx.Response(200, json=show())
        count += 1
        return httpx.Response(200, json={"models": [entry()] if count == 1 else []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await adapter_module.OllamaCorrectionAdapter(settings(), client).list_models()
    assert len(result) == 1 and result[0].digest == DIGEST
    assert not result[0].selectable and result[0].unavailable_reason == "model_changed"


@pytest.mark.parametrize("operation", ["list", "suggest"])
async def test_disabled_new_operations_do_not_contact_ollama(operation):
    def handle(request):
        pytest.fail("Disabled operation must not contact the model server")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        adapter = adapter_module.OllamaCorrectionAdapter(
            settings().model_copy(update={"text_review_enabled": False}), client
        )
        with pytest.raises(SpeakerError, match="text_review_unavailable"):
            await (
                adapter.list_models()
                if operation == "list"
                else adapter.suggest(CONTEXT, selection())
            )


async def test_suggestion_validates_source_and_selection_before_contacting_ollama():
    def handle(request):
        pytest.fail("Invalid source or selection must not contact the model server")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        adapter = adapter_module.OllamaCorrectionAdapter(settings(), client)
        with pytest.raises(SpeakerError, match="text_review_context_limit"):
            await adapter.suggest(ports.CorrectionContext("x" * 1025, (), (), "tr"), selection())
        with pytest.raises(SpeakerError, match="text_review_model_mismatch"):
            await adapter.suggest(CONTEXT, selection("https://other.invalid/model"))


@pytest.mark.parametrize("fault", ["redirect", "large", "body"])
async def test_catalog_metadata_transport_is_bounded_without_leaking_provider_error(fault):
    def handle(request):
        if fault == "redirect":
            return httpx.Response(302, headers={"Location": "http://private.invalid/secret"})
        if fault == "large":
            return httpx.Response(
                200,
                headers={"Content-Type": "application/json", "Content-Length": "999999999"},
                content=b"{}",
            )
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            content=b"invalid-json-private-metadata",
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), follow_redirects=False
    ) as client:
        with pytest.raises(SpeakerError) as error:
            await adapter_module.OllamaCorrectionAdapter(settings(), client).list_models()
    assert "private" not in str(error.value)
