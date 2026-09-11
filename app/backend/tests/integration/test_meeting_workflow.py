"""Uploaded meeting contracts through real HTTP, files, and tenant-qualified PostgreSQL."""

import hashlib
import io
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import soundfile as sf
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.domain.models.meeting import Meeting, MeetingSpeaker, MeetingTranscript
from app.domain.models.permission import Permission, RolePermission
from app.domain.models.role import Role, UserRole
from app.domain.models.speaker_identity import SpeakerProfile
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.main import app

pytestmark = pytest.mark.integration
PERMISSIONS = ["meeting_analysis:read", "meeting_analysis:run", "speaker_profiles:write"]


def source_bytes(seconds: float = 3) -> bytes:
    stream = io.BytesIO()
    sf.write(stream, [0.1] * round(seconds * 16000), 16000, format="WAV")
    return stream.getvalue()


@dataclass
class MeetingHarness:
    client: AsyncClient
    sessions: async_sessionmaker
    settings: Settings
    tenant: Tenant
    user: User

    def token(self, permissions: list[str], *, super_admin: bool = False) -> str:
        return create_access_token(
            subject=UUID(self.user.public_id),
            username=self.user.username,
            tenant_id=UUID(self.tenant.public_id),
            roles=[],
            permissions=permissions,
            is_super_admin=super_admin,
        )


@pytest.fixture
async def meeting_harness(
    postgres_database_url: str, tmp_path: Path
) -> AsyncIterator[MeetingHarness]:
    engine = create_async_engine(postgres_database_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    settings = get_settings().model_copy(update={"audio_storage_path": tmp_path / "owned"})
    async with sessions() as session, session.begin():
        suffix = uuid4().hex
        tenant = Tenant(code=f"meeting-{suffix}", name="Meeting test")
        session.add(tenant)
        await session.flush()
        user = User(
            home_tenant_id=tenant.tenant_id,
            username=f"meeting-{suffix}",
            email=f"{suffix}@example.invalid",
            display_name="Test",
            password_hash="disabled-test-credential",
        )
        session.add(user)
        await session.flush()
        role = Role(code=f"meeting-fixture-{suffix}", name="Meeting fixture")
        session.add(role)
        await session.flush()
        session.add(
            UserRole(user_id=user.user_id, role_id=role.role_id, tenant_id=tenant.tenant_id)
        )
        for permission in await session.scalars(
            select(Permission).where(Permission.code.in_(PERMISSIONS))
        ):
            session.add(
                RolePermission(role_id=role.role_id, permission_id=permission.permission_id)
            )

    async def database():
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_settings] = lambda: settings
    token = create_access_token(
        subject=UUID(user.public_id),
        username=user.username,
        tenant_id=UUID(tenant.public_id),
        roles=[],
        permissions=PERMISSIONS,
        is_super_admin=False,
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=f"http://test{settings.api_prefix}",
            headers={"Authorization": f"Bearer {token}", settings.tenant_header: tenant.public_id},
        ) as client:
            yield MeetingHarness(client, sessions, settings, tenant, user)
    finally:
        app.dependency_overrides.clear()
        async with sessions() as session, session.begin():
            await session.execute(
                update(Meeting)
                .where(
                    Meeting.tenant_id == tenant.tenant_id,
                )
                .values(
                    status="cancelled",
                    claim_token=Meeting.claim_token + 1,
                    lease_expires_at=None,
                    finished_at=datetime.now(UTC),
                    source_removed_at=datetime.now(UTC),
                    title="",
                    idempotency_key=None,
                )
            )
        await engine.dispose()


@pytest.fixture
async def meeting_client(meeting_harness: MeetingHarness) -> AsyncIterator[AsyncClient]:
    yield meeting_harness.client


async def create(client: AsyncClient, data: bytes, key: str | None = None, **kwargs) -> dict:
    response = await client.post(
        "/meetings",
        json={"title": "Meeting", "format": "WAV", "size_bytes": len(data), **kwargs},
        headers={"Idempotency-Key": key or str(uuid4())},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def upload(client: AsyncClient, meeting: dict, data: bytes, index: int = 0):
    return await client.put(
        f"/meetings/{meeting['public_id']}/upload-parts/{index}",
        content=data,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Chunk-SHA256": hashlib.sha256(data).hexdigest(),
        },
    )


async def test_upload_retry_complete_and_private_fields(meeting_client: AsyncClient) -> None:
    data, key = source_bytes(), str(uuid4())
    meeting = await create(meeting_client, data, key, participant_count=5, expected_speakers=3)
    assert meeting == await create(
        meeting_client, data, key, participant_count=5, expected_speakers=3
    )
    assert meeting["status"] == "uploading" and meeting["uploaded_bytes"] == 0
    assert not {"storage_key", "tenant_id", "embedding", "fingerprint"} & meeting.keys()
    path = f"/meetings/{meeting['public_id']}"
    assert (await meeting_client.post(path + "/complete")).status_code == 409
    ack = await upload(meeting_client, meeting, data)
    assert ack.status_code == 200, ack.text
    assert ack.json()["uploaded_bytes"] == len(data)
    assert (await upload(meeting_client, meeting, data)).json() == ack.json()
    changed = data[:-1] + bytes([data[-1] ^ 1])
    assert (await upload(meeting_client, meeting, changed)).status_code == 409
    completed = await meeting_client.post(path + "/complete")
    assert completed.status_code == 202, completed.text
    assert completed.json()["status"] == "queued"
    assert completed.json()["sha256"] == hashlib.sha256(data).hexdigest()
    assert (await meeting_client.post(path + "/complete")).json() == completed.json()
    transcript = (await meeting_client.get(path + "/transcript")).json()
    assert transcript["total"] == 0 and transcript["provisional"]


async def test_count_settings_are_semantic_idempotency_and_not_fifty_quota(
    meeting_client: AsyncClient,
) -> None:
    key, data = str(uuid4()), source_bytes()
    await create(meeting_client, data, key, participant_count=200, expected_speakers=100)
    changed = await meeting_client.post(
        "/meetings",
        json={
            "title": "Meeting",
            "format": "WAV",
            "size_bytes": len(data),
            "participant_count": 200,
            "expected_speakers": 99,
        },
        headers={"Idempotency-Key": key},
    )
    assert changed.status_code == 409
    for value in (-1, 0, 2.5, True):
        response = await meeting_client.post(
            "/meetings",
            json={"title": "Bad", "format": "WAV", "size_bytes": 100, "participant_count": value},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == 422
    response = await meeting_client.post(
        "/meetings",
        json={
            "title": "Bad",
            "format": "WAV",
            "size_bytes": 100,
            "participant_count": 4,
            "expected_speakers": 5,
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422


async def test_cancel_fences_upload_and_delete_hides_meeting(meeting_client: AsyncClient) -> None:
    data = source_bytes()
    meeting = await create(meeting_client, data)
    path = f"/meetings/{meeting['public_id']}"
    assert (await meeting_client.post(path + "/cancel")).json()["status"] == "cancelled"
    assert (await upload(meeting_client, meeting, data)).status_code == 409
    assert (await meeting_client.delete(path)).status_code == 204
    assert (await meeting_client.get(path)).status_code == 404


async def test_upload_limits_and_order_do_not_mutate_manifest(meeting_client: AsyncClient) -> None:
    data = source_bytes()
    meeting = await create(meeting_client, data)
    assert (await upload(meeting_client, meeting, data, 1)).status_code == 409
    assert (await upload(meeting_client, meeting, data[:20])).status_code == 409
    path = f"/meetings/{meeting['public_id']}/upload-parts"
    assert (await meeting_client.get(path)).json()["parts"] == []
    bad = await meeting_client.put(
        path + "/0",
        content=data,
        headers={"Content-Type": "application/octet-stream", "X-Chunk-SHA256": "0" * 64},
    )
    assert bad.status_code == 409
    assert (await meeting_client.get(path)).json()["parts"] == []


async def test_permissions_and_tenant_do_not_leak_or_mutate(
    meeting_harness: MeetingHarness,
) -> None:
    harness, data = meeting_harness, source_bytes()
    client = harness.client
    meeting = await create(client, data)
    path = f"/meetings/{meeting['public_id']}"
    denied = {"Authorization": "Bearer " + harness.token([])}
    assert (await client.get(path, headers=denied)).status_code == 403
    assert (await client.post(path + "/cancel", headers=denied)).status_code == 403
    run_only = {
        "Authorization": "Bearer " + harness.token(["meeting_analysis:run"]),
        "Idempotency-Key": str(uuid4()),
    }
    body = {"title": "No write", "format": "WAV", "size_bytes": len(data)}
    assert (await client.post("/meetings", json=body, headers=run_only)).status_code == 403
    body["auto_enroll"] = False
    assert (await client.post("/meetings", json=body, headers=run_only)).status_code == 201
    async with harness.sessions() as session, session.begin():
        other = Tenant(code=f"foreign-{uuid4().hex}", name="Other")
        session.add(other)
        await session.flush()
    foreign = {
        "Authorization": "Bearer " + harness.token([], super_admin=True),
        harness.settings.tenant_header: other.public_id,
    }
    for suffix in ("", "/upload-parts", "/speakers", "/transcript"):
        assert (await client.get(path + suffix, headers=foreign)).status_code == 404
    assert (await client.post(path + "/cancel", headers=foreign)).status_code == 404
    assert (await client.get(path)).json()["status"] == "uploading"


async def seed_named_track(
    harness: MeetingHarness, public_id: str, *, persistent: bool
) -> tuple[str, str | None]:
    async with harness.sessions() as session, session.begin():
        meeting = await session.scalar(select(Meeting).where(Meeting.public_id == public_id))
        profile = None
        if persistent:
            profile = SpeakerProfile(
                tenant_id=harness.tenant.tenant_id,
                name="Original",
                sample_count=1,
                model_id=MODEL_ID,
                model_revision=MODEL_REVISION,
                embedding=[1.0] + [0.0] * 191,
                source_sha256="a" * 64,
            )
            session.add(profile)
            await session.flush()
        track = MeetingSpeaker(
            tenant_id=harness.tenant.tenant_id,
            meeting_id=meeting.meeting_id,
            ordinal=0,
            profile_id=profile.speaker_profile_id if profile else None,
            decision="recognized" if profile else "profile_pending",
            reason="matched" if profile else "insufficient_speech",
            speech_seconds=3,
        )
        session.add(track)
        await session.flush()
        session.add(
            MeetingTranscript(
                tenant_id=harness.tenant.tenant_id,
                meeting_id=meeting.meeting_id,
                meeting_speaker_id=track.meeting_speaker_id,
                ordinal=0,
                start=0,
                end=1,
                text="A short utterance",
                language="en",
                uncertain=False,
                overlap=False,
            )
        )
        return track.public_id, profile.public_id if profile else None


@pytest.mark.parametrize("persistent", [False, True])
async def test_naming_is_versioned_and_does_not_create_or_reembed(
    meeting_harness: MeetingHarness, persistent: bool
) -> None:
    harness = meeting_harness
    meeting = await create(harness.client, source_bytes())
    track_id, profile_id = await seed_named_track(
        harness, meeting["public_id"], persistent=persistent
    )
    path = f"/meetings/{meeting['public_id']}"
    track = (await harness.client.get(path + "/speakers")).json()["items"][0]
    body = {
        "name": "  New   name ",
        "version": track["version"],
        "profile_updated_at": track["profile_updated_at"],
    }
    renamed = await harness.client.patch(path + f"/speakers/{track_id}", json=body)
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["display_name"] == "New name"
    assert (
        renamed.json()["public_id"] == track_id
        and renamed.json()["profile_public_id"] == profile_id
    )
    assert renamed.json()["decision"] == track["decision"]
    assert (
        await harness.client.patch(path + f"/speakers/{track_id}", json=body)
    ).status_code == 409
    transcript = (await harness.client.get(path + "/transcript")).json()["items"][0]
    assert transcript["speaker_ordinal"] == 0
    assert transcript["speaker_name"] == "New name" and transcript["text"] == "A short utterance"
    async with harness.sessions() as session:
        profiles = list(
            await session.scalars(
                select(SpeakerProfile).where(SpeakerProfile.tenant_id == harness.tenant.tenant_id)
            )
        )
        assert len(profiles) == int(persistent)
        if persistent:
            assert (
                profiles[0].sample_count == 1 and list(profiles[0].embedding) == [1.0] + [0.0] * 191
            )


async def test_expired_upload_cannot_continue(meeting_harness: MeetingHarness) -> None:
    harness, data = meeting_harness, source_bytes()
    meeting = await create(harness.client, data)
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        row.upload_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (await upload(harness.client, meeting, data)).status_code == 410


async def test_failed_meeting_with_expired_source_cannot_retry(
    meeting_harness: MeetingHarness,
) -> None:
    harness, data = meeting_harness, source_bytes()
    meeting = await create(harness.client, data)
    assert (await upload(harness.client, meeting, data)).status_code == 200
    path = f"/meetings/{meeting['public_id']}"
    assert (await harness.client.post(path + "/complete")).status_code == 202
    async with harness.sessions() as session, session.begin():
        row = await session.scalar(select(Meeting).where(Meeting.public_id == meeting["public_id"]))
        row.status = "failed"
        row.source_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (await harness.client.post(path + "/retry")).status_code == 410
