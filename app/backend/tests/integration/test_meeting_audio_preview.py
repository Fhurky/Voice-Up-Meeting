"""Preview routing, authorization, retention and immutability with real PostgreSQL/audio."""

import io
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import numpy as np
import pytest
import soundfile as sf
from sqlalchemy import inspect, select

from app.core.security import create_access_token
from app.domain.models.meeting import Meeting, MeetingSpeaker, MeetingTranscript
from app.domain.models.speaker_identity import SpeakerProfile
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.main import app
from tests.integration import test_meeting_workflow as workflow

meeting_harness = workflow.meeting_harness
pytestmark = pytest.mark.integration


async def sealed(harness, *, format="WAV"):
    output = io.BytesIO()
    sf.write(output, [[0.25, 0.75]] * 48000, 16000, format=format, subtype="PCM_16")
    data = output.getvalue()
    meeting = await workflow.create(harness.client, data, format=format, auto_enroll=False)
    assert (await workflow.upload(harness.client, meeting, data)).status_code == 200
    path = f"/meetings/{meeting['public_id']}"
    response = await harness.client.post(path + "/complete")
    assert response.status_code == 202, response.text
    return meeting, path


async def snapshot(harness):
    result = []
    async with harness.sessions() as session:
        for model in [Meeting, MeetingSpeaker, MeetingTranscript, SpeakerProfile]:
            for row in await session.scalars(
                select(model).where(model.tenant_id == harness.tenant.tenant_id)
            ):
                values = {column.key: getattr(row, column.key) for column in inspect(model).columns}
                result.append(
                    {
                        key: value.tolist() if isinstance(value, np.ndarray) else value
                        for key, value in values.items()
                    }
                )
    return result


@pytest.mark.parametrize("format", ["WAV", "FLAC"])
async def test_read_only_preview_has_binary_contract_and_does_not_mutate(meeting_harness, format):
    harness = meeting_harness
    meeting, path = await sealed(harness, format=format)
    await workflow.seed_named_track(harness, meeting["public_id"], persistent=True)
    before = await snapshot(harness)
    read_only = {"Authorization": "Bearer " + harness.token(["meeting_analysis:read"])}
    url = path + "/audio-preview?start_seconds=1&end_seconds=3"
    response = await harness.client.get(url, headers=read_only)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert int(response.headers["content-length"]) == len(response.content) <= 11520128
    samples, rate = sf.read(io.BytesIO(response.content))
    assert rate == 16000 and len(samples) == 32000 and (samples == 0.5).all()
    assert (await harness.client.get(url, headers=read_only)).content == response.content
    assert await snapshot(harness) == before
    operation = app.openapi()["paths"][
        harness.settings.api_prefix + "/meetings/{public_id}/audio-preview"
    ]["get"]
    assert operation["operationId"] == "meeting_audio_preview"
    assert set(operation["responses"]["200"]["content"]) == {"audio/wav"}
    assert operation["responses"]["200"]["content"]["audio/wav"]["schema"]["format"] == "binary"


@pytest.mark.parametrize(
    "query",
    [
        "",
        "start_seconds=0",
        "end_seconds=1",
        "start_seconds=-1&end_seconds=1",
        "start_seconds=1&end_seconds=1",
        "start_seconds=2&end_seconds=1",
        "start_seconds=0&end_seconds=31",
        "start_seconds=0&end_seconds=3.1",
        "start_seconds=nan&end_seconds=1",
        "start_seconds=0&end_seconds=inf",
        "start_seconds=text&end_seconds=1",
        "start_seconds=0&end_seconds=0.000001",
    ],
)
async def test_preview_rejects_invalid_ranges_with_safe_error(meeting_harness, query):
    _, path = await sealed(meeting_harness)
    response = await meeting_harness.client.get(path + "/audio-preview?" + query)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "invalid_audio_range"


async def test_preview_requires_jwt_read_permission_and_ordinary_tenant(meeting_harness):
    harness = meeting_harness
    _, path = await sealed(harness)
    url = path + "/audio-preview?start_seconds=0&end_seconds=1"
    assert (await harness.client.get(url, headers={"Authorization": ""})).status_code == 401
    run_only = {"Authorization": "Bearer " + harness.token(["meeting_analysis:run"])}
    assert (await harness.client.get(url, headers=run_only)).status_code == 403
    async with harness.sessions() as session, session.begin():
        suffix = uuid4().hex
        tenant = Tenant(code=f"preview-{suffix}", name="Other")
        session.add(tenant)
        await session.flush()
        user = User(
            home_tenant_id=tenant.tenant_id,
            username=f"preview-{suffix}",
            email=f"{suffix}@example.invalid",
            display_name="Other",
            password_hash="disabled-test-credential",
        )
        session.add(user)
        await session.flush()
    token = create_access_token(
        subject=UUID(user.public_id),
        username=user.username,
        tenant_id=UUID(tenant.public_id),
        roles=[],
        permissions=["meeting_analysis:read"],
        is_super_admin=False,
    )
    foreign = {"Authorization": "Bearer " + token, harness.settings.tenant_header: tenant.public_id}
    assert (await harness.client.get(url, headers=foreign)).status_code == 404
    unknown = f"/meetings/{uuid4()}/audio-preview?start_seconds=0&end_seconds=1"
    assert (await harness.client.get(unknown)).status_code == 404


@pytest.mark.parametrize(
    "state,code,status",
    [
        ("uploading", "meeting_state_conflict", 409),
        ("expired", "recording_unavailable", 410),
        ("removed", "recording_unavailable", 410),
        ("missing", "recording_unavailable", 410),
        ("deleted", "not_found", 404),
    ],
)
async def test_preview_retention_and_sealing_are_independent_of_cleanup(
    meeting_harness, state, code, status
):
    harness = meeting_harness
    meeting, path = await sealed(harness)
    if state == "uploading":
        meeting = await workflow.create(harness.client, workflow.source_bytes(), auto_enroll=False)
        path = f"/meetings/{meeting['public_id']}"
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        if state == "expired":
            row.source_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        elif state == "removed":
            row.source_removed_at = datetime.now(UTC)
        elif state == "deleted":
            row.is_deleted, row.deleted_at, row.deleted_by = (
                True,
                datetime.now(UTC),
                harness.user.user_id,
            )
        elif state == "missing":
            (harness.settings.audio_storage_path / "meetings" / row.storage_key).unlink()
    response = await harness.client.get(path + "/audio-preview?start_seconds=0&end_seconds=1")
    assert response.status_code == status, response.text
    assert response.json()["detail"]["code"] == code
    if state == "expired":
        assert (await harness.client.get(path + "/transcript")).status_code == 200
        assert (await harness.client.get(path + "/speakers")).status_code == 200


async def test_preview_source_failure_does_not_leak_storage_details(meeting_harness):
    harness = meeting_harness
    meeting, path = await sealed(harness)
    async with harness.sessions() as session:
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        source_path = harness.settings.audio_storage_path / "meetings" / row.storage_key
    source_path.write_bytes(b"damaged")
    response = await harness.client.get(path + "/audio-preview?start_seconds=0&end_seconds=1")
    assert response.status_code == 410, response.text
    assert response.json()["detail"]["code"] == "recording_unavailable"
    assert row.storage_key not in response.text and str(source_path) not in response.text


async def test_unsealed_cancelled_upload_is_a_state_conflict(meeting_harness):
    harness = meeting_harness
    meeting = await workflow.create(harness.client, workflow.source_bytes(), auto_enroll=False)
    path = f"/meetings/{meeting['public_id']}"
    assert (await harness.client.post(path + "/cancel")).status_code == 200
    response = await harness.client.get(path + "/audio-preview?start_seconds=0&end_seconds=1")
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "meeting_state_conflict"
