"""Two-channel capture streamed during a meeting (PRD 037) through real HTTP, files and PostgreSQL."""

import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import numpy as np
import pytest
import soundfile as sf
from sqlalchemy import select, update

from app.domain.models.meeting import Meeting
from app.domain.models.tenant import Tenant
from tests.integration import test_meeting_workflow as workflow

meeting_harness = workflow.meeting_harness
pytestmark = pytest.mark.integration
RATE = 16000


def stereo_part(seconds: float, microphone: float, system: float) -> bytes:
    frames = round(seconds * RATE)
    samples = np.empty((frames, 2), dtype="<i2")
    samples[:, 0] = round(microphone * 32767)
    samples[:, 1] = round(system * 32767)
    return samples.tobytes()


def chain(parts: list[bytes]) -> str:
    value = bytes(32)
    for part in parts:
        value = hashlib.sha256(value + hashlib.sha256(part).digest()).digest()
    return value.hex()


async def create_capture(client, **kwargs) -> dict:
    response = await client.post(
        "/meetings/captures",
        json={"title": "Teams", "sample_rate": RATE, **kwargs},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def send(client, meeting: dict, start_frame: int, data: bytes, **headers):
    return await client.put(
        f"/meetings/{meeting['public_id']}/capture-frames/{start_frame}",
        content=data,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Chunk-SHA256": hashlib.sha256(data).hexdigest(),
            **headers,
        },
    )


def capture_events(caplog: pytest.LogCaptureFixture, name: str) -> list[dict]:
    return [
        record.structured_fields  # type: ignore[attr-defined]
        for record in caplog.records
        if record.getMessage() == name
    ]


async def test_capture_streams_parts_and_completes_with_the_chain(
    meeting_harness, caplog: pytest.LogCaptureFixture
) -> None:
    client = meeting_harness.client
    meeting = await create_capture(client, auto_enroll=False)
    assert meeting["status"] == "uploading" and meeting["capture_mode"] == "two_channel"
    assert meeting["captured_frames"] == 0 and meeting["capture_idle"] is False
    parts = [stereo_part(2, 0.1, 0.2), stereo_part(2, 0.3, 0.4), stereo_part(0.5, 0.0, 0.5)]
    start = 0
    for part in parts:
        response = await send(client, meeting, start, part)
        assert response.status_code == 200, response.text
        start += len(part) // 4
        assert response.json() == {"received_frames": start}
    # A retry after a lost acknowledgement is accepted without changing anything.
    retried = await send(client, meeting, 0, parts[0])
    assert retried.status_code == 200 and retried.json() == {"received_frames": start}
    path = f"/meetings/{meeting['public_id']}"
    progress = (await client.get(path)).json()
    assert progress["captured_frames"] == start and progress["captured_seconds"] == 4.5
    with caplog.at_level("INFO", logger="app.meeting_capture"):
        completed = await client.post(
            path + "/capture/complete", json={"frames": start, "chain_sha256": chain(parts)}
        )
    assert completed.status_code == 202, completed.text
    body = completed.json()
    assert body["status"] == "queued" and body["duration_seconds"] == 4.5
    async with meeting_harness.sessions() as session:
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
    stored = (
        meeting_harness.settings.audio_storage_path / "meetings" / row.storage_key
    ).read_bytes()
    assert hashlib.sha256(stored).hexdigest() == body["sha256"]
    assert stored[44:] == b"".join(parts) and row.size_bytes == len(stored)
    with sf.SoundFile(io.BytesIO(stored)) as source:
        assert (source.channels, source.samplerate, source.frames) == (2, RATE, start)
    assert row.channels == 2 and row.sample_rate == RATE
    events = capture_events(caplog, "meeting_capture")
    assert events == [{"outcome": "completed", "seconds": 4.5, "parts": 3, "duplicates": 1}]
    assert meeting["public_id"] not in json.dumps(events)
    # Completing again returns the queued meeting unchanged.
    again = await client.post(
        path + "/capture/complete", json={"frames": start, "chain_sha256": chain(parts)}
    )
    assert again.status_code == 202 and again.json()["sha256"] == body["sha256"]
    assert (await send(client, meeting, start, parts[0])).json()["detail"]["code"] == (
        "meeting_not_capturing"
    )


async def test_capture_rejects_gaps_conflicts_and_bad_parts(
    meeting_harness, caplog: pytest.LogCaptureFixture
) -> None:
    client = meeting_harness.client
    meeting = await create_capture(client, auto_enroll=False)
    first = stereo_part(2, 0.1, 0.1)
    assert (await send(client, meeting, 0, first)).status_code == 200
    with caplog.at_level("INFO", logger="app.meeting_capture"):
        gap = await send(client, meeting, RATE * 4, first)
    assert gap.status_code == 409 and gap.json()["detail"]["code"] == "capture_gap"
    assert capture_events(caplog, "meeting_capture_gap") == [{"missing_frames": RATE * 2}]
    changed = stereo_part(2, 0.1, 0.2)
    conflict = await send(client, meeting, 0, changed)
    assert conflict.status_code == 409 and conflict.json()["detail"]["code"] == "capture_conflict"
    unaligned = await send(client, meeting, RATE * 2, b"\x00" * 6)
    assert unaligned.status_code == 422
    assert unaligned.json()["detail"]["code"] == "capture_part_unaligned"
    too_long = await send(client, meeting, RATE * 2, stereo_part(4.5, 0, 0))
    assert too_long.status_code == 413
    wrong_hash = await send(client, meeting, RATE * 2, first, **{"X-Chunk-SHA256": "0" * 64})
    assert wrong_hash.status_code == 409
    assert wrong_hash.json()["detail"]["code"] == "chunk_hash_mismatch"
    path = f"/meetings/{meeting['public_id']}"
    assert (await client.post(path + "/complete")).status_code == 409
    upload = await workflow.upload(client, meeting, first)
    assert upload.status_code == 409
    incomplete = await client.post(
        path + "/capture/complete", json={"frames": RATE * 3, "chain_sha256": chain([first])}
    )
    assert incomplete.status_code == 409
    assert incomplete.json()["detail"]["code"] == "capture_incomplete"
    mismatch = await client.post(
        path + "/capture/complete", json={"frames": RATE * 2, "chain_sha256": chain([changed])}
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"]["code"] == "capture_chain_mismatch"
    assert (await client.get(path)).json()["captured_frames"] == RATE * 2
    file_meeting = await workflow.create(client, workflow.source_bytes(), auto_enroll=False)
    not_capturing = await send(client, file_meeting, 0, first)
    assert not_capturing.status_code == 409
    assert not_capturing.json()["detail"]["code"] == "meeting_not_capturing"


async def test_an_idle_capture_can_be_processed_as_received(
    meeting_harness, caplog: pytest.LogCaptureFixture
) -> None:
    harness = meeting_harness
    client = harness.client
    empty = await create_capture(client, auto_enroll=False)
    empty_seal = await client.post(f"/meetings/{empty['public_id']}/capture/seal")
    assert empty_seal.status_code == 409 and empty_seal.json()["detail"]["code"] == "capture_empty"
    meeting = await create_capture(client, auto_enroll=False)
    part = stereo_part(2, 0.2, 0.3)
    assert (await send(client, meeting, 0, part)).status_code == 200
    path = f"/meetings/{meeting['public_id']}"
    active = await client.post(path + "/capture/seal")
    assert active.status_code == 409 and active.json()["detail"]["code"] == "capture_active"
    async with harness.sessions() as session, session.begin():
        await session.execute(
            update(Meeting)
            .where(Meeting.public_id == meeting["public_id"])
            .values(capture_part_at=datetime.now(UTC) - timedelta(minutes=3))
        )
    assert (await client.get(path)).json()["capture_idle"] is True
    with caplog.at_level("INFO", logger="app.meeting_capture"):
        sealed = await client.post(path + "/capture/seal")
    assert sealed.status_code == 202, sealed.text
    assert sealed.json()["status"] == "queued" and sealed.json()["duration_seconds"] == 2
    assert sealed.json()["capture_idle"] is False
    assert capture_events(caplog, "meeting_capture") == [
        {"outcome": "sealed", "seconds": 2.0, "parts": 1, "duplicates": 0}
    ]


async def test_capture_permissions_and_tenant_isolation(meeting_harness) -> None:
    harness = meeting_harness
    client = harness.client
    meeting = await create_capture(client, auto_enroll=False)
    path = f"/meetings/{meeting['public_id']}"
    part = stereo_part(2, 0.1, 0.1)
    read_only = {"Authorization": "Bearer " + harness.token(["meeting_analysis:read"])}
    assert (await send(client, meeting, 0, part, **read_only)).status_code == 403
    assert (await client.post(path + "/capture/seal", headers=read_only)).status_code == 403
    create_denied = await client.post(
        "/meetings/captures",
        json={"title": "Teams", "sample_rate": RATE},
        headers={**read_only, "Idempotency-Key": str(uuid4())},
    )
    assert create_denied.status_code == 403
    run_only = {
        "Authorization": "Bearer " + harness.token(["meeting_analysis:run"]),
        "Idempotency-Key": str(uuid4()),
    }
    enroll_denied = await client.post(
        "/meetings/captures",
        json={"title": "Teams", "sample_rate": RATE, "auto_enroll": True},
        headers=run_only,
    )
    assert enroll_denied.status_code == 403
    async with harness.sessions() as session, session.begin():
        other = Tenant(code=f"foreign-{uuid4().hex}", name="Other")
        session.add(other)
        await session.flush()
    foreign = {
        "Authorization": "Bearer " + harness.token([], super_admin=True),
        harness.settings.tenant_header: other.public_id,
    }
    assert (await send(client, meeting, 0, part, **foreign)).status_code == 404
    assert (await client.post(path + "/capture/seal", headers=foreign)).status_code == 404
    foreign_complete = await client.post(
        path + "/capture/complete",
        json={"frames": RATE * 2, "chain_sha256": chain([part])},
        headers=foreign,
    )
    assert foreign_complete.status_code == 404
    assert (await client.get(path)).json()["captured_frames"] == 0


async def test_capture_validation_and_idempotent_creation(meeting_harness) -> None:
    client = meeting_harness.client
    key = str(uuid4())
    body = {"title": "Teams", "sample_rate": RATE, "auto_enroll": False}
    first = await client.post("/meetings/captures", json=body, headers={"Idempotency-Key": key})
    again = await client.post("/meetings/captures", json=body, headers={"Idempotency-Key": key})
    assert first.status_code == again.status_code == 201
    assert first.json()["public_id"] == again.json()["public_id"]
    changed = await client.post(
        "/meetings/captures", json={**body, "sample_rate": 48000}, headers={"Idempotency-Key": key}
    )
    assert changed.status_code == 409
    for rate in (7999, 192001):
        invalid = await client.post(
            "/meetings/captures",
            json={**body, "sample_rate": rate},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert invalid.status_code == 422
    # The reserved source size covers four hours of 16 kHz two-channel audio.
    assert first.json()["size_bytes"] == 44 + RATE * 14400 * 4
