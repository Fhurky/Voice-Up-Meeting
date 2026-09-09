"""Real HTTP, files and PostgreSQL boundaries; fixture vectors are not model evidence."""

import io
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import pytest
import soundfile as sf
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.domain.models.speaker_identity import (
    Recording,
    SpeakerJob,
    SpeakerProfile,
    SpeakerSample,
)
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.repositories.speaker_repository import SpeakerRepository
from app.main import app
from app.services.speaker_ports import EmbeddingResult, SpeakerError
from app.services.speaker_worker import SpeakerWorker

pytestmark = pytest.mark.integration
PERMISSIONS = [
    "speaker_profiles:read",
    "speaker_profiles:write",
    "speaker_analysis:run",
    "speaker_analysis:read",
]


def audio_bytes(seconds: float = 12, value: float = 0.1) -> bytes:
    output = io.BytesIO()
    sf.write(output, [value] * int(16000 * seconds), 16000, format="WAV")
    return output.getvalue()


class FixtureEmbeddingProvider:
    def __init__(self) -> None:
        self.vector = [1.0] + [0.0] * 191
        self.error: SpeakerError | None = None
        self.calls = 0
        self.speech_seconds = 12.0
        self.windows_count = 2

    async def embed(
        self,
        audio: bytes,
        *,
        purpose: Literal["enroll", "identify"],
        job_public_id: str,
        tenant_public_id: str,
    ) -> EmbeddingResult:
        assert audio[:4] == b"RIFF"
        assert UUID(job_public_id) and UUID(tenant_public_id)
        assert purpose in {"enroll", "identify"}
        self.calls += 1
        if self.error:
            raise self.error
        return EmbeddingResult(
            self.vector,
            self.speech_seconds,
            self.windows_count,
            MODEL_ID,
            MODEL_REVISION,
            "fixture-vector",
        )


@pytest.fixture(scope="module")
def migrated_speaker_database(postgres_database_url: str) -> Iterator[None]:
    del postgres_database_url
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, "head")
    command.check(config)
    yield


@dataclass
class Pilot:
    client: AsyncClient
    sessions: async_sessionmaker[AsyncSession]
    worker: SpeakerWorker
    provider: FixtureEmbeddingProvider
    settings: Settings
    tenant: Tenant
    user: User

    async def upload(self, *, key: str | None = None, data: bytes | None = None) -> dict:
        response = await self.client.post(
            "/recordings",
            files={
                "file": (
                    "sample.wav",
                    data if data is not None else audio_bytes(),
                    "audio/wav",
                )
            },
            headers={"Idempotency-Key": key or str(uuid4())},
        )
        assert response.status_code == 201, response.text
        return response.json()

    async def submit(
        self,
        source: str,
        *,
        purpose: str = "enroll",
        name: str | None = "Person",
        target: str | None = None,
        key: str | None = None,
    ) -> dict:
        body = {"recording_public_id": source, "purpose": purpose}
        if name is not None:
            body["name"] = name
        if target is not None:
            body["profile_public_id"] = target
        response = await self.client.post(
            "/speaker-jobs", json=body, headers={"Idempotency-Key": key or str(uuid4())}
        )
        assert response.status_code == 202, response.text
        return response.json()

    async def terminal(self, job: dict) -> dict:
        assert await self.worker.process_once()
        response = await self.client.get(f"/speaker-jobs/{job['public_id']}")
        assert response.status_code == 200, response.text
        return response.json()

    async def enroll(self) -> tuple[dict, dict, dict]:
        source = await self.upload()
        job = await self.submit(source["public_id"])
        result = await self.terminal(job)
        assert result["status"] == "succeeded", result
        return source, job, result


@pytest.fixture
async def pilot(
    migrated_speaker_database: None, postgres_database_url: str, tmp_path: Path
) -> AsyncIterator[Pilot]:
    engine = create_async_engine(postgres_database_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    settings = get_settings().model_copy(update={"audio_storage_path": tmp_path / "owned"})
    async with sessions() as session, session.begin():
        suffix = uuid4().hex
        tenant = Tenant(code=f"pilot-{suffix}", name="Pilot")
        session.add(tenant)
        await session.flush()
        user = User(
            home_tenant_id=tenant.tenant_id,
            username=f"user-{suffix}",
            email=f"{suffix}@example.invalid",
            display_name="Pilot",
            password_hash="disabled-test-credential",
        )
        session.add(user)
        await session.flush()
    token = create_access_token(
        subject=UUID(user.public_id),
        username=user.username,
        tenant_id=UUID(tenant.public_id),
        roles=[],
        permissions=PERMISSIONS,
        is_super_admin=False,
    )

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    provider = FixtureEmbeddingProvider()
    worker = SpeakerWorker(sessions, AudioStorage(settings), provider, settings)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=f"http://test{settings.api_prefix}",
            headers={
                "Authorization": f"Bearer {token}",
                settings.tenant_header: tenant.public_id,
            },
        ) as client:
            yield Pilot(client, sessions, worker, provider, settings, tenant, user)
    finally:
        app.dependency_overrides.clear()
        # The gate owns and drops the whole uniquely named disposable test database.
        await engine.dispose()


@pytest.mark.parametrize(
    "purpose,seconds,windows", [("enroll", 10 - 5e-7, 2), ("identify", 3 - 5e-7, 1)]
)
async def test_worker_accepts_producer_duration_tolerance(
    pilot: Pilot, purpose: str, seconds: float, windows: int
) -> None:
    pilot.provider.speech_seconds = seconds
    pilot.provider.windows_count = windows
    recording = await pilot.upload()
    job = await pilot.submit(
        recording["public_id"], purpose=purpose, name="Person" if purpose == "enroll" else None
    )
    result = await pilot.terminal(job)
    assert result["status"] == "succeeded", result
    assert result["result"]["speech_seconds"] == seconds


async def test_persistent_enroll_identify_and_public_contract(pilot: Pilot) -> None:
    source, job, result = await pilot.enroll()
    profile_id = result["result"]["profile_public_id"]
    assert result["result"]["decision"] == "enrolled"
    assert result["attempt_count"] == 1
    profiles = (await pilot.client.get("/speaker-profiles")).json()
    assert profiles["total"] == 1
    assert profiles["items"][0]["sample_count"] == 1
    assert (
        not {"embedding", "tenant_id", "speaker_profile_id", "storage_key"}
        & profiles["items"][0].keys()
    )
    identified = await pilot.terminal(
        await pilot.submit(source["public_id"], purpose="identify", name=None)
    )
    assert identified["result"]["decision"] == "recognized"
    assert identified["result"]["profile_public_id"] == profile_id
    assert (await pilot.client.get("/speaker-profiles")).json()["items"][0]["sample_count"] == 1
    async with pilot.sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(SpeakerSample)
                .where(SpeakerSample.tenant_id == pilot.tenant.tenant_id)
            )
            == 1
        )
    assert (await pilot.client.get(f"/speaker-jobs/{job['public_id']}")).json()[
        "status"
    ] == "succeeded"


async def test_idempotency_uses_content_not_recording_identity(pilot: Pilot) -> None:
    upload_key, job_key = str(uuid4()), str(uuid4())
    source = await pilot.upload(key=upload_key)
    replay = await pilot.upload(key=upload_key)
    assert replay["public_id"] == source["public_id"]
    duplicate = await pilot.upload()
    job = await pilot.submit(source["public_id"], key=job_key, name="  Test   Person ")
    replay_job = await pilot.submit(duplicate["public_id"], key=job_key, name="Test Person")
    assert replay_job["public_id"] == job["public_id"]
    conflict = await pilot.client.post(
        "/speaker-jobs",
        json={
            "recording_public_id": source["public_id"],
            "purpose": "enroll",
            "name": "Different",
        },
        headers={"Idempotency-Key": job_key},
    )
    assert conflict.status_code == 409
    conflict_upload = await pilot.client.post(
        "/recordings",
        files={"file": ("sample.wav", audio_bytes(value=0.2))},
        headers={"Idempotency-Key": upload_key},
    )
    assert conflict_upload.status_code == 409
    await pilot.terminal(job)
    assert len(list(pilot.settings.audio_storage_path.glob("*.audio"))) == 2


async def test_wrong_person_append_and_unknown_never_change_profile(
    pilot: Pilot,
) -> None:
    source, _, enrolled = await pilot.enroll()
    profile_id = enrolled["result"]["profile_public_id"]
    pilot.provider.vector = [0.0, 1.0] + [0.0] * 190
    failed = await pilot.terminal(
        await pilot.submit(source["public_id"], name=None, target=profile_id)
    )
    assert failed["status"] == "failed"
    assert failed["error"]["code"] == "target_mismatch"
    unknown = await pilot.terminal(
        await pilot.submit(source["public_id"], purpose="identify", name=None)
    )
    assert unknown["result"]["decision"] == "unknown"
    assert unknown["result"]["profile_public_id"] is None
    profiles = (await pilot.client.get("/speaker-profiles")).json()
    assert profiles["total"] == 1 and profiles["items"][0]["sample_count"] == 1


async def test_append_mean_and_explicit_sample_limit(pilot: Pilot) -> None:
    source, _, enrolled = await pilot.enroll()
    profile_id = enrolled["result"]["profile_public_id"]
    second = await pilot.terminal(
        await pilot.submit(source["public_id"], name=None, target=profile_id)
    )
    assert second["status"] == "succeeded"
    assert (await pilot.client.get("/speaker-profiles")).json()["items"][0]["sample_count"] == 2
    async with pilot.sessions() as session, session.begin():
        profile = await session.scalar(
            select(SpeakerProfile).where(SpeakerProfile.public_id == profile_id)
        )
        profile.sample_count = 20
    response = await pilot.client.post(
        "/speaker-jobs",
        json={
            "recording_public_id": source["public_id"],
            "purpose": "enroll",
            "profile_public_id": profile_id,
        },
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 409 and response.json()["detail"]["code"] == "sample_limit"


async def test_delete_race_fences_enrollment_and_redacts_history(pilot: Pilot) -> None:
    source, _, enrolled = await pilot.enroll()
    profile_id = enrolled["result"]["profile_public_id"]
    job = await pilot.submit(source["public_id"], name=None, target=profile_id)
    claim = await pilot.worker.claim()
    assert claim is not None
    assert (await pilot.client.delete(f"/speaker-profiles/{profile_id}")).status_code == 204
    result = await pilot.provider.embed(
        audio_bytes(),
        purpose="enroll",
        job_public_id=claim.public_id,
        tenant_public_id=claim.tenant_public_id,
    )
    with pytest.raises(SpeakerError, match="profile_unavailable"):
        await pilot.worker.complete(claim, result)
    await pilot.worker.fail(claim, "profile_unavailable", retryable=False)
    assert (await pilot.client.get("/speaker-profiles")).json()["total"] == 0
    history = (await pilot.client.get(f"/speaker-jobs/{enrolled['public_id']}")).json()["result"]
    assert history["profile_deleted"] and history["profile_name"] is None
    assert (await pilot.client.get(f"/speaker-jobs/{job['public_id']}")).json()[
        "status"
    ] == "failed"


async def test_stale_worker_cannot_duplicate_enrollment(pilot: Pilot) -> None:
    source = await pilot.upload()
    job = await pilot.submit(source["public_id"])
    first = await pilot.worker.claim()
    assert first is not None
    async with pilot.sessions() as session, session.begin():
        row = await session.get(SpeakerJob, first.job_id)
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    second = await pilot.worker.claim()
    assert second is not None and second.token > first.token
    embedding = await pilot.provider.embed(
        audio_bytes(),
        purpose="enroll",
        job_public_id=first.public_id,
        tenant_public_id=first.tenant_public_id,
    )
    assert await pilot.worker.complete(first, embedding) is False
    assert await pilot.worker.complete(second, embedding) is True
    assert await pilot.worker.complete(second, embedding) is False
    state = (await pilot.client.get(f"/speaker-jobs/{job['public_id']}")).json()
    assert state["status"] == "succeeded" and state["attempt_count"] == 2
    assert (await pilot.client.get("/speaker-profiles")).json()["total"] == 1


async def test_retry_budget_and_quality_errors_are_terminal(pilot: Pilot) -> None:
    source = await pilot.upload()
    pilot.provider.error = SpeakerError("inference_unavailable", 503)
    job = await pilot.submit(source["public_id"])
    first = await pilot.terminal(job)
    assert first["status"] == "queued"
    second = await pilot.terminal(job)
    assert second["status"] == "failed" and second["attempt_count"] == 2
    pilot.provider.error = SpeakerError("insufficient_speech", 422)
    failed = await pilot.terminal(await pilot.submit(source["public_id"]))
    assert failed["status"] == "failed" and failed["attempt_count"] == 1
    assert (await pilot.client.get("/speaker-profiles")).json()["total"] == 0


async def test_source_retention_and_delete_reference_guard(pilot: Pilot) -> None:
    source, _, enrolled = await pilot.enroll()
    assert (await pilot.client.delete(f"/recordings/{source['public_id']}")).status_code == 409
    async with pilot.sessions() as session, session.begin():
        recording = await session.scalar(
            select(Recording).where(Recording.public_id == source["public_id"])
        )
        recording.expires_at = datetime.now(UTC) - timedelta(hours=25)
    await pilot.worker.cleanup()
    assert len(list(pilot.settings.audio_storage_path.glob("*.audio"))) == 1
    await pilot.client.delete(f"/speaker-profiles/{enrolled['result']['profile_public_id']}")
    await pilot.worker.cleanup()
    assert len(list(pilot.settings.audio_storage_path.glob("*.audio"))) == 0
    expired = await pilot.client.post(
        "/speaker-jobs",
        json={"recording_public_id": source["public_id"], "purpose": "identify"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert expired.status_code == 410


async def test_tenant_scope_exact_ranking_and_migrated_vector_shape(
    pilot: Pilot,
) -> None:
    source, _, enrolled = await pilot.enroll()
    async with pilot.sessions() as session, session.begin():
        other = Tenant(code=f"other-{uuid4().hex}", name="Other")
        session.add(other)
        await session.flush()
        for index in range(30):
            session.add(
                SpeakerProfile(
                    tenant_id=pilot.tenant.tenant_id,
                    name=f"Distractor {index}",
                    sample_count=1,
                    model_id=MODEL_ID,
                    model_revision=MODEL_REVISION,
                    embedding=[0.0, 1.0] + [0.0] * 190,
                    source_sha256="0" * 64,
                )
            )
        session.add(
            SpeakerProfile(
                tenant_id=other.tenant_id,
                name="Other tenant",
                sample_count=1,
                model_id=MODEL_ID,
                model_revision=MODEL_REVISION,
                embedding=[1.0] + [0.0] * 191,
                source_sha256="0" * 64,
            )
        )
        session.add(
            SpeakerProfile(
                tenant_id=pilot.tenant.tenant_id,
                name="Other model",
                sample_count=1,
                model_id=MODEL_ID,
                model_revision="different-version",
                embedding=[1.0] + [0.0] * 191,
                source_sha256="0" * 64,
            )
        )
    async with pilot.sessions() as session:
        ranked = await SpeakerRepository(session).ranked(
            pilot.tenant.tenant_id, [1.0] + [0.0] * 191
        )
        assert ranked[0][0].public_id == enrolled["result"]["profile_public_id"]
        assert ranked[1][1] == pytest.approx(0.0)
        version = await session.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname='vector'")
        )
        assert tuple(map(int, version.split("."))) >= (0, 8, 5)
        assert (
            await session.scalar(
                text(
                    "SELECT format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid='speaker_sample'::regclass AND attname='embedding'"
                )
            )
            == "vector(192)"
        )
        columns = set(
            (
                await session.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name='speaker_job'"
                    )
                )
            ).scalars()
        )
        assert {
            "props",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "is_deleted",
            "deleted_at",
            "deleted_by",
        } <= columns
        assert Base.metadata.tables["speaker_job"].comment
    switched_token = create_access_token(
        subject=UUID(pilot.user.public_id),
        username=pilot.user.username,
        tenant_id=UUID(pilot.tenant.public_id),
        roles=[],
        permissions=[],
        is_super_admin=True,
    )
    foreign_headers = {
        "Authorization": f"Bearer {switched_token}",
        pilot.settings.tenant_header: other.public_id,
    }
    assert (
        await pilot.client.get(f"/speaker-jobs/{enrolled['public_id']}", headers=foreign_headers)
    ).status_code == 404
    assert (
        await pilot.client.patch(
            f"/speaker-profiles/{enrolled['result']['profile_public_id']}",
            json={"name": "No"},
            headers=foreign_headers,
        )
    ).status_code == 404
    assert (
        await pilot.client.delete(f"/recordings/{source['public_id']}", headers=foreign_headers)
    ).status_code == 404


async def test_invalid_files_and_missing_grants_reject_before_mutation(
    pilot: Pilot,
) -> None:
    for filename, content, expected in [
        ("fake.wav", b"not audio", 415),
        ("file.txt", b"text", 415),
        ("empty.wav", b"RIFF0000WAVE", 400),
        ("long.wav", audio_bytes(121), 413),
    ]:
        response = await pilot.client.post(
            "/recordings",
            files={"file": (filename, content)},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == expected, response.text
    token = create_access_token(
        subject=UUID(pilot.user.public_id),
        username=pilot.user.username,
        tenant_id=UUID(pilot.tenant.public_id),
        roles=[],
        permissions=[],
        is_super_admin=False,
    )
    denied = await pilot.client.get(
        "/speaker-profiles", headers={"Authorization": f"Bearer {token}"}
    )
    assert denied.status_code == 403 and denied.json()["detail"]["code"] == "forbidden"
    unauthenticated = await pilot.client.get("/speaker-profiles", headers={"Authorization": ""})
    assert unauthenticated.status_code == 401
    assert not list(pilot.settings.audio_storage_path.glob("*.audio"))


async def test_retention_batch_skips_more_than_one_hundred_referenced_sources(pilot: Pilot) -> None:
    now = datetime.now(UTC)
    async with pilot.sessions() as session, session.begin():
        active_jobs = []
        for index in range(101):
            recording = Recording(
                tenant_id=pilot.tenant.tenant_id,
                storage_key=f"{uuid4().hex}.audio",
                sha256="0" * 64,
                size_bytes=100,
                format="WAV",
                duration_seconds=10,
                idempotency_expires_at=now + timedelta(days=7),
                expires_at=now - timedelta(days=2),
            )
            session.add(recording)
            await session.flush()
            if index < 100:
                job = SpeakerJob(
                    tenant_id=pilot.tenant.tenant_id,
                    recording_id=recording.recording_id,
                    purpose="identify",
                    status="running",
                    model_id=MODEL_ID,
                    model_revision=MODEL_REVISION,
                    fingerprint="0" * 64,
                    lease_expires_at=now + timedelta(hours=1),
                )
                session.add(job)
                active_jobs.append(job)
            else:
                orphan_id = recording.recording_id
        await session.flush()
        candidates = await SpeakerRepository(session).expired_recordings(now)
        assert orphan_id in {item.recording_id for item in candidates}
        for job in active_jobs:
            job.status = "failed"
            job.finished_at = now


async def test_expired_upload_retry_and_job_result_retention(pilot: Pilot) -> None:
    key = str(uuid4())
    source = await pilot.upload(key=key)
    identified = await pilot.terminal(
        await pilot.submit(source["public_id"], purpose="identify", name=None)
    )
    async with pilot.sessions() as session, session.begin():
        recording = await session.scalar(
            select(Recording).where(Recording.public_id == source["public_id"])
        )
        recording.expires_at = datetime.now(UTC) - timedelta(hours=25)
        job = await session.scalar(
            select(SpeakerJob).where(SpeakerJob.public_id == identified["public_id"])
        )
        job.finished_at = datetime.now(UTC) - timedelta(days=8)
    await pilot.worker.cleanup()
    expired = await pilot.client.post(
        "/recordings",
        files={"file": ("sample.wav", audio_bytes())},
        headers={"Idempotency-Key": key},
    )
    assert expired.status_code == 410
    assert (await pilot.client.get(f"/speaker-jobs/{identified['public_id']}")).status_code == 404
    async with pilot.sessions() as session:
        job = await session.scalar(
            select(SpeakerJob).where(SpeakerJob.public_id == identified["public_id"])
        )
        assert job.result is None and job.idempotency_key is None
