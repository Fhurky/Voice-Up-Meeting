"""Bounded private model admission, independent of a claimed meeting job."""

import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import create_autospec

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import get_settings
from app.infrastructure import meeting_inference
from app.infrastructure.meeting_inference import HttpMeetingAdapter
from app.services.speaker_ports import SpeakerError

pytestmark = pytest.mark.unit


def readiness_payload():
    observed = json.loads(
        (Path(__file__).parents[1] / "fixtures/meeting_chunk_actual.json").read_text(
            encoding="utf-8"
        )
    )["payload"]
    observed["model_identity"]["diarization"]["recipe"] = "community-vbx-fa015-v1"
    return {
        "ready": True,
        "device": observed["device"],
        "model_identity": observed["model_identity"],
    }


def settings():
    return get_settings().model_copy(
        update={"inference_key": SecretStr("test-meeting-key-at-least-32-bytes")}
    )


async def test_private_readiness_validates_observed_models_and_sends_only_service_context():
    def producer(request: httpx.Request):
        assert request.method == "GET" and request.url.path == "/meeting-ready"
        assert not request.url.query and request.content == b""
        assert request.headers["x-inference-key"] == "test-meeting-key-at-least-32-bytes"
        assert request.headers["accept-encoding"] == "identity"
        assert "x-job-id" not in request.headers and "x-tenant-id" not in request.headers
        assert max(request.extensions["timeout"].values()) <= 5
        return httpx.Response(200, json=readiness_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(producer)) as client:
        assert await HttpMeetingAdapter(settings(), client).ready()


@pytest.mark.parametrize("failure", ["connect", "timeout", "proxy503", "loading503"])
async def test_transient_readiness_failure_does_not_admit_work(failure):
    def producer(request: httpx.Request):
        if failure == "connect":
            raise httpx.ConnectError("private service has not started", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("model is still starting", request=request)
        if failure == "loading503":
            return httpx.Response(503, json={"detail": {"code": "meeting_model_not_ready"}})
        return httpx.Response(503, content=b"proxy unavailable")

    async with httpx.AsyncClient(transport=httpx.MockTransport(producer)) as client:
        assert not await HttpMeetingAdapter(settings(), client).ready()


@pytest.mark.parametrize(
    "change", ["revision", "model", "false", "string", "device", "extra", "recipe_missing"]
)
async def test_wrong_readiness_contract_is_visible_as_model_error(change):
    payload = copy.deepcopy(readiness_payload())
    if change == "revision":
        payload["model_identity"]["diarization"]["revision"] = "0" * 40
    elif change == "model":
        payload["model_identity"]["asr"]["model_id"] = "other"
    elif change in {"false", "string"}:
        payload["ready"] = False if change == "false" else "true"
    elif change == "device":
        payload["device"] = "cpu"
    elif change == "recipe_missing":
        payload["model_identity"]["diarization"].pop("recipe")
    else:
        payload["unapproved"] = True
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(SpeakerError) as captured:
            await HttpMeetingAdapter(settings(), client).ready()
    assert captured.value.code == "model_mismatch"


@pytest.mark.parametrize(
    "status,code", [(401, "unauthorized"), (503, "model_load_failed"), (503, []), (503, {})]
)
async def test_permanent_readiness_errors_are_not_reported_as_transient_loading(status, code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, json={"detail": {"code": code}})
        )
    ) as client:
        with pytest.raises(SpeakerError) as captured:
            await HttpMeetingAdapter(settings(), client).ready()
    assert captured.value.code == "inference_unavailable"


@pytest.mark.parametrize(
    "headers,body",
    [
        ({"content-encoding": "gzip"}, b"{}"),
        ({"content-length": "16385"}, b"{}"),
        ({}, b" " * 16385),
    ],
    ids=["compressed", "declared_oversize", "actual_oversize"],
)
async def test_readiness_response_cannot_expand_the_small_admission_budget(headers, body):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, headers=headers, content=body))
    ) as client:
        with pytest.raises(SpeakerError) as captured:
            await HttpMeetingAdapter(settings(), client).ready()
    assert captured.value.code == "model_mismatch"


async def test_readiness_total_deadline_includes_streaming(monkeypatch):
    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.sleep(0.05)
            yield json.dumps(readiness_payload()).encode()

    monkeypatch.setattr(meeting_inference, "READINESS_TIMEOUT_SECONDS", 0.01, raising=False)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=SlowStream()))
    ) as client:
        assert not await HttpMeetingAdapter(settings(), client).ready()


async def test_production_loop_keeps_pilot_cleanup_and_heartbeat_during_loading(
    tmp_path, monkeypatch
):
    from app.scripts import speaker_worker

    pilot = create_autospec(speaker_worker.SpeakerWorker, instance=True)
    meeting = create_autospec(speaker_worker.MeetingWorker, instance=True)
    cleanup = create_autospec(speaker_worker.MeetingCleanup, instance=True)
    engine = create_autospec(type(speaker_worker.engine), instance=True)
    pilot.process_once.return_value = False
    current = settings()
    original_client = httpx.AsyncClient

    def client_factory(*, trust_env):
        assert trust_env is False
        return original_client(
            transport=httpx.MockTransport(lambda _: httpx.Response(503)), trust_env=False
        )

    async def stop_poll(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(speaker_worker, "get_settings", lambda: current)
    monkeypatch.setattr(speaker_worker, "SpeakerWorker", lambda *args: pilot)
    monkeypatch.setattr(speaker_worker, "MeetingWorker", lambda *args: meeting)
    monkeypatch.setattr(speaker_worker, "MeetingCleanup", lambda *args: cleanup)
    monkeypatch.setattr(speaker_worker.httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(speaker_worker.asyncio, "sleep", stop_poll)
    monkeypatch.setattr(speaker_worker, "engine", engine)
    heartbeat = tmp_path / "worker-health"
    monkeypatch.setattr(speaker_worker, "HEARTBEAT_PATH", heartbeat)
    with pytest.raises(asyncio.CancelledError):
        await speaker_worker.run()
    pilot.cleanup.assert_awaited_once()
    pilot.process_once.assert_awaited_once()
    cleanup.run.assert_awaited_once()
    meeting.process_once.assert_not_awaited()
    engine.dispose.assert_awaited_once()
    assert heartbeat.is_file()
