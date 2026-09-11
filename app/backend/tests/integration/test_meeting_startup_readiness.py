"""Cold model startup cannot consume persisted meeting claims or retries."""

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.domain.models.meeting import Meeting
from app.infrastructure.meeting_inference import HttpMeetingAdapter
from app.scripts.speaker_worker import process_ready_meeting
from tests.integration import test_meeting_worker as fixtures

meeting_harness = fixtures.meeting_harness
pytestmark = pytest.mark.integration
SERVICE_KEY = "readiness-test-only-key-at-least-32-bytes"


def ready_payload():
    identity = fixtures.result(10).model_dump()["model_identity"]
    identity["diarization"]["recipe"] = "community-vbx-fa015-v1"
    return {
        "ready": True,
        "device": "cuda:0",
        "model_identity": identity,
    }


async def state(harness, public_id):
    async with harness.sessions() as session:
        row = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        return row.status, row.attempt_count, row.claim_token, row.next_chunk_index


@pytest.mark.parametrize("outage", ["connect", "503"])
async def test_queued_job_survives_model_startup_then_processes_when_ready(meeting_harness, outage):
    harness = meeting_harness
    public_id = await fixtures.queued(harness, seconds=10)
    available, requests = False, []

    def producer(request: httpx.Request):
        requests.append(request.url.path)
        assert request.headers["x-inference-key"] == SERVICE_KEY
        if request.url.path == "/meeting-ready":
            if not available:
                if outage == "connect":
                    raise httpx.ConnectError("service is starting", request=request)
                return httpx.Response(503, json={"detail": {"code": "meeting_model_not_ready"}})
            return httpx.Response(200, json=ready_payload())
        assert request.url.path == "/v1/meeting-chunks"
        return httpx.Response(200, json=fixtures.result(10).model_dump())

    async with httpx.AsyncClient(transport=httpx.MockTransport(producer)) as client:
        adapter = HttpMeetingAdapter(
            harness.settings.model_copy(update={"inference_key": SecretStr(SERVICE_KEY)}), client
        )
        worker = fixtures.worker(harness, adapter)
        assert await state(harness, public_id) == ("queued", 0, 0, 0)
        for _ in range(3):
            assert not await process_ready_meeting(adapter, worker)
        assert requests == ["/meeting-ready"] * 3
        assert await state(harness, public_id) == ("queued", 0, 0, 0)
        available = True
        assert await process_ready_meeting(adapter, worker)
        assert requests[-2:] == ["/meeting-ready", "/v1/meeting-chunks"]
        status, attempts, token, chunks = await state(harness, public_id)
        assert status == "finalizing" and attempts == 0 and token == 1 and chunks == 1


async def test_real_post_admission_model_failures_still_exhaust_bounded_retries(meeting_harness):
    harness = meeting_harness
    public_id = await fixtures.queued(harness, seconds=10)

    def producer(request: httpx.Request):
        if request.url.path == "/meeting-ready":
            return httpx.Response(200, json=ready_payload())
        assert request.url.path == "/v1/meeting-chunks"
        return httpx.Response(503, json={"detail": {"code": "meeting_inference_failed"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(producer)) as client:
        adapter = HttpMeetingAdapter(
            harness.settings.model_copy(update={"inference_key": SecretStr(SERVICE_KEY)}), client
        )
        worker = fixtures.worker(harness, adapter)
        assert await process_ready_meeting(adapter, worker)
        assert await state(harness, public_id) == ("running", 1, 1, 0)
        assert await process_ready_meeting(adapter, worker)
        assert await state(harness, public_id) == ("failed", 2, 2, 0)
        assert not await process_ready_meeting(adapter, worker)
