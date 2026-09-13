"""Ollama protocol and bounded transport checks use the observed local response shape."""

import asyncio
import json

import httpx
import pytest

from app.core.config import get_settings
from app.infrastructure.ollama_correction import OllamaCorrectionAdapter
from app.services.speaker_ports import SpeakerError
from app.services.transcript_correction_ports import CorrectionContext

DIGEST = "7653528ba5cba4dd8e19da24aaddc7f4d0b5ecd93571c0825dfd4137958ec06e"
MODEL = "qwen3.5:27b"
CONTEXT = CorrectionContext(
    "Yeni sürüyü sunucuya yükledik.", ("Yazılım sürümünü hazırladık.",), (), "tr"
)


def settings():
    return get_settings().model_copy(
        update={
            "text_review_enabled": True,
            "text_review_url": "http://ollama:11434",
            "text_review_model": MODEL,
            "text_review_model_digest": DIGEST,
        }
    )


def tags(**extra):
    return {
        "models": [
            {
                "name": MODEL,
                "model": MODEL,
                "digest": DIGEST,
                "details": {
                    "family": "qwen35",
                    "parameter_size": "27.8B",
                    "quantization_level": "Q4_K_M",
                },
                **extra,
            }
        ]
    }


def chat(content='{"edits":[{"original":"sürüyü","replacement":"sürümü"}]}', **extra):
    return {
        "model": MODEL,
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        **extra,
    }


async def test_protocol_pins_before_and_after_and_never_sends_identifiers():
    seen = []

    def handle(request):
        seen.append(request)
        return httpx.Response(200, json=chat() if request.url.path == "/api/chat" else tags())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), trust_env=False, follow_redirects=False
    ) as client:
        result = await OllamaCorrectionAdapter(settings(), client).review(CONTEXT)
    assert [request.url.path for request in seen] == ["/api/tags", "/api/chat", "/api/tags"]
    body = json.loads(seen[1].content)
    assert set(body) == {"model", "messages", "format", "stream", "think", "options", "keep_alive"}
    assert body["stream"] is False and body["think"] is False
    assert body["keep_alive"] == 0
    assert body["options"]["temperature"] == 0 and body["options"]["num_predict"] == 512
    assert body["format"]["additionalProperties"] is False
    source = json.loads(body["messages"][1]["content"])
    assert set(source) == {"language", "before", "target", "after"}
    assert source["target"] == CONTEXT.target_text
    assert result.edits[0].replacement == "sürümü"
    assert result.model_name == MODEL and result.model_digest == DIGEST


@pytest.mark.parametrize(
    "extra",
    [{"digest": "a" * 64}, {"remote_host": "https://example.invalid"}, {"remote_model": MODEL}],
)
async def test_changed_or_remote_model_never_receives_private_text(extra):
    seen = []

    def handle(request):
        seen.append(request.url.path)
        return httpx.Response(200, json=tags(**extra))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_model_mismatch"):
            await OllamaCorrectionAdapter(settings(), client).review(CONTEXT)
    assert seen == ["/api/tags"]


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "{}",
        '{"edits":[],"text":"extra"}',
        '{"edits":[],"edits":[]}',
        '{"edits":[{"original":"x","replacement":"y","confidence":1}]}',
        '{"edits":[{"original":"x","replacement":""}]}',
        '{"edits":[],"metadata":NaN}',
    ],
)
async def test_invalid_model_shape_is_safe_error(content):
    def handle(request):
        return httpx.Response(
            200, json=chat(content) if request.url.path == "/api/chat" else tags()
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_invalid_response"):
            await OllamaCorrectionAdapter(settings(), client).review(CONTEXT)


async def test_mid_call_digest_change_discards_valid_suggestion():
    count = 0

    def handle(request):
        nonlocal count
        count += 1
        return httpx.Response(
            200, json=chat() if count == 2 else tags(**({"digest": "a" * 64} if count == 3 else {}))
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_model_mismatch"):
            await OllamaCorrectionAdapter(settings(), client).review(CONTEXT)


@pytest.mark.parametrize(
    "status,headers,content",
    [
        (302, {"location": "http://elsewhere/api/chat"}, b""),
        (200, {"content-length": "9999999999"}, b"{}"),
        (200, {"content-type": "text/html"}, b"<html>private</html>"),
        (200, {"content-encoding": "gzip"}, b"private"),
    ],
)
async def test_transport_limits_redirects_and_encodings(status, headers, content):
    def handle(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=tags())
        return httpx.Response(status, headers=headers, content=content)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), follow_redirects=False
    ) as client:
        with pytest.raises(SpeakerError):
            await OllamaCorrectionAdapter(settings(), client).review(CONTEXT)


async def test_timeout_and_disabled_mode_keep_safe_codes():
    def handle(request):
        raise httpx.ReadTimeout("private host diagnostics")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_timeout"):
            await OllamaCorrectionAdapter(settings(), client).review(CONTEXT)
        config = settings().model_copy(update={"text_review_enabled": False})
        with pytest.raises(SpeakerError, match="text_review_unavailable"):
            await OllamaCorrectionAdapter(config, client).review(CONTEXT)


@pytest.mark.parametrize(
    "extra",
    [
        {"done": False},
        {"done_reason": "length"},
        {"model": "other-model"},
        {
            "message": {
                "role": "assistant",
                "content": '{"edits":[]}',
                "tool_calls": [{"function": {"name": "untrusted"}}],
            }
        },
    ],
)
async def test_incomplete_or_tool_using_completion_is_never_exposed(extra):
    def handle(request):
        return httpx.Response(
            200, json=chat(**extra) if request.url.path == "/api/chat" else tags()
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_invalid_response"):
            await OllamaCorrectionAdapter(settings(), client).review(CONTEXT)


async def test_streaming_body_is_bounded_even_without_content_length():
    class LargeStream(httpx.AsyncByteStream):
        count = 0
        closed = False

        async def __aiter__(self):
            for _ in range(100):
                self.count += 1
                yield b"x" * 16384

        async def aclose(self):
            self.closed = True

    stream = LargeStream()

    def handle(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=tags())
        return httpx.Response(200, headers={"Content-Type": "application/json"}, stream=stream)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_invalid_response"):
            await OllamaCorrectionAdapter(settings(), client).review(CONTEXT)
    assert stream.closed and stream.count == 5


async def test_total_deadline_cancels_stalled_stream_and_closes_connection(monkeypatch):
    import app.infrastructure.ollama_correction as adapter_module

    class StalledStream(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            await asyncio.Event().wait()
            yield b"unreachable"

        async def aclose(self):
            self.closed = True

    stream = StalledStream()

    def handle(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=tags())
        return httpx.Response(200, headers={"Content-Type": "application/json"}, stream=stream)

    monkeypatch.setattr(adapter_module, "REVIEW_TIMEOUT_SECONDS", 0.01)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SpeakerError, match="text_review_timeout"):
            await asyncio.wait_for(
                OllamaCorrectionAdapter(settings(), client).review(CONTEXT), timeout=1
            )
    assert stream.closed
