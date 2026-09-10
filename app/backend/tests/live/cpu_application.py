"""Explicit live CPU test: ASGI application routes, PostgreSQL, files and model TCP.

Run this file explicitly with RUN_POSTGRES_INTEGRATION=1 and VOICEUP_CPU_LIVE=1.
The caller owns a newly migrated *_test database, the isolated CPU service and
the temporary audio/evidence directory; this file never launches a service or
changes the application's configured database, model URL, or runtime mode.
"""

import hashlib
import json
import math
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.domain.models.speaker_identity import SpeakerProfile, SpeakerSample
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.speaker_inference import HttpEmbeddingAdapter
from app.main import app
from app.services.speaker_worker import SpeakerWorker
from tests.integration.test_speaker_pilot import PERMISSIONS, Pilot

pytestmark = pytest.mark.integration


@pytest.fixture
async def cpu_pilot(postgres_database_url: str, tmp_path: Path) -> AsyncIterator[Pilot]:
    if os.environ.get("VOICEUP_CPU_LIVE") != "1":
        pytest.fail("Explicit VOICEUP_CPU_LIVE=1 is required; no fixture model is available here")
    inference_url = os.environ["VOICEUP_CPU_LIVE_INFERENCE_URL"]
    if not inference_url.startswith("http://voiceup-cpu-live-") or not inference_url.endswith(
        ":8090"
    ):
        pytest.fail("The caller must provide an isolated voiceup-cpu-live-* model service")
    key = os.environ["VOICEUP_CPU_LIVE_INFERENCE_KEY"]
    if len(key.encode()) < 32:
        pytest.fail("A process-provided ephemeral inference key is required")
    engine = create_async_engine(postgres_database_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    settings = get_settings().model_copy(
        update={
            "audio_storage_path": tmp_path / "owned",
            "inference_url": inference_url,
            "inference_key": SecretStr(key),
        }
    )
    async with sessions() as session, session.begin():
        suffix = uuid4().hex
        tenant = Tenant(code=f"cpu-live-{suffix}", name="CPU live fixture")
        session.add(tenant)
        await session.flush()
        user = User(
            home_tenant_id=tenant.tenant_id,
            username=f"cpu-live-{suffix}",
            email=f"{suffix}@example.invalid",
            display_name="CPU live fixture",
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

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        async with AsyncClient(trust_env=False) as inference_client:
            ready = await inference_client.get(f"{inference_url}/ready", timeout=15)
            assert ready.status_code == 200
            assert ready.json()["device"] == "cpu"
            assert ready.json()["model_revision"] == MODEL_REVISION
            provider = HttpEmbeddingAdapter(settings, inference_client)
            worker = SpeakerWorker(sessions, AudioStorage(settings), provider, settings)
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url=f"http://test{settings.api_prefix}",
                headers={
                    "Authorization": f"Bearer {token}",
                    settings.tenant_header: tenant.public_id,
                },
            ) as client:
                # Pilot is only the existing public-route helper; its fixture provider is never
                # constructed. The worker and helper both retain this actual HTTP adapter.
                yield Pilot(client, sessions, worker, provider, settings, tenant, user)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        await engine.dispose()


async def profile_state(pilot: Pilot) -> tuple[str, int, float]:
    """Compare persistence without exporting voice vectors or database identities."""
    async with pilot.sessions() as session:
        profile = await session.scalar(
            select(SpeakerProfile).where(SpeakerProfile.tenant_id == pilot.tenant.tenant_id)
        )
        assert profile is not None
        samples = await session.scalar(
            select(func.count())
            .select_from(SpeakerSample)
            .where(SpeakerSample.tenant_id == pilot.tenant.tenant_id)
        )
        assert samples is not None
        vector = [float(value) for value in profile.embedding]
        assert len(vector) == 192
        norm = math.sqrt(math.fsum(value * value for value in vector))
        state = {
            "name": profile.name,
            "embedding": vector,
            "samples": samples,
            "sample_count": profile.sample_count,
            "source_sha256": profile.source_sha256,
            "model_id": profile.model_id,
            "model_revision": profile.model_revision,
        }
        digest = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
        return digest, samples, norm


async def test_cpu_enrollment_and_identification_preserve_persistent_profile(
    cpu_pilot: Pilot,
) -> None:
    sample = Path(os.environ["VOICEUP_CPU_LIVE_AUDIO"])
    evidence_path = Path(os.environ["VOICEUP_CPU_LIVE_EVIDENCE"])
    data = sample.read_bytes()
    assert data[:4] == b"RIFF"
    assert isinstance(cpu_pilot.provider, HttpEmbeddingAdapter)
    assert cpu_pilot.worker.embedding is cpu_pilot.provider
    empty = await cpu_pilot.client.get("/speaker-profiles")
    assert empty.status_code == 200 and empty.json()["total"] == 0

    first_source = await cpu_pilot.upload(data=data)
    enrollment_key = str(uuid4())
    enrollment_job = await cpu_pilot.submit(
        first_source["public_id"], name="CPU fixture person", key=enrollment_key
    )
    started = time.perf_counter()
    enrolled = await cpu_pilot.terminal(enrollment_job)
    enrollment_seconds = time.perf_counter() - started
    assert enrolled["status"] == "succeeded", enrolled.get("error")
    assert enrolled["result"]["decision"] == "enrolled"
    assert enrolled["result"]["device"] == "cpu"
    assert enrolled["result"]["model_id"] == MODEL_ID
    assert enrolled["result"]["model_revision"] == MODEL_REVISION
    assert enrolled["result"]["speech_seconds"] >= 10
    assert enrolled["result"]["windows_count"] >= 2
    profile_id = enrolled["result"]["profile_public_id"]
    before_response = await cpu_pilot.client.get("/speaker-profiles")
    assert before_response.status_code == 200
    before = before_response.json()
    assert before["total"] == 1 and before["items"][0]["sample_count"] == 1
    assert not {"embedding", "storage_key", "tenant_id"} & before["items"][0].keys()
    persisted_before = await profile_state(cpu_pilot)
    assert persisted_before[1] == 1 and abs(persisted_before[2] - 1) < 1e-5

    # A completed enrollment retry must not add another profile, sample or model operation.
    replayed = await cpu_pilot.submit(
        first_source["public_id"], name="CPU fixture person", key=enrollment_key
    )
    assert replayed["public_id"] == enrollment_job["public_id"]
    assert replayed["status"] == "succeeded"

    second_source = await cpu_pilot.upload(data=data)
    identification_job = await cpu_pilot.submit(
        second_source["public_id"], purpose="identify", name=None
    )
    started = time.perf_counter()
    identified = await cpu_pilot.terminal(identification_job)
    identification_seconds = time.perf_counter() - started
    assert identified["status"] == "succeeded", identified.get("error")
    assert identified["result"]["device"] == "cpu"
    assert identified["result"]["decision"] == "recognized"
    assert identified["result"]["profile_public_id"] == profile_id
    after_response = await cpu_pilot.client.get("/speaker-profiles")
    assert after_response.status_code == 200 and after_response.json() == before
    persisted_after = await profile_state(cpu_pilot)
    assert persisted_after == persisted_before
    assert not await cpu_pilot.worker.process_once()

    evidence = {
        "schema_version": 1,
        "status": "passed",
        "test_count": 1,
        "application_transport": "httpx-ASGITransport-in-process",
        "model_transport": "real-HTTP-TCP-to-isolated-Linux-CPU-container",
        "model_provider": "HttpEmbeddingAdapter",
        "worker": "SpeakerWorker.process_once",
        "device": "cpu",
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": 192,
        "audio_sha256": hashlib.sha256(data).hexdigest(),
        "audio_bytes": len(data),
        "same_audio_reused": True,
        "enrollment": {
            "decision": enrolled["result"]["decision"],
            "seconds": round(enrollment_seconds, 3),
            "speech_seconds": enrolled["result"]["speech_seconds"],
            "windows_count": enrolled["result"]["windows_count"],
        },
        "identification": {
            "decision": identified["result"]["decision"],
            "seconds": round(identification_seconds, 3),
            "same_profile": identified["result"]["profile_public_id"] == profile_id,
        },
        "persistent_profile_unchanged": persisted_after == persisted_before,
        "profile_total": after_response.json()["total"],
        "sample_count": persisted_after[1],
        "enrollment_retry_reused_job": True,
        "accuracy_claim": False,
        "macos_observed": False,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
