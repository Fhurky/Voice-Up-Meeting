"""Durable claim, fenced completion and bounded retry for speaker jobs."""

import asyncio
import hashlib
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.domain.models.speaker_identity import SpeakerProfile, SpeakerSample
from app.domain.speaker_identity import (
    MODEL_ID,
    MODEL_REVISION,
    MatchPolicy,
    decide,
    normalize,
)
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.repositories.speaker_repository import SpeakerRepository
from app.schemas.speaker_identity import MatchPolicyResponse, SpeakerResult
from app.services.speaker_ports import EmbeddingPort, EmbeddingResult, SpeakerError

logger = logging.getLogger("app.speaker_worker")


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    job_id: int
    public_id: str
    tenant_id: int
    tenant_public_id: str
    token: int
    purpose: Literal["enroll", "identify"]
    storage_key: str | None


class SpeakerWorker:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        storage: AudioStorage,
        embedding: EmbeddingPort,
        settings: Settings,
    ) -> None:
        self.sessions = sessions
        self.storage = storage
        self.embedding = embedding
        self.settings = settings
        self.policy = MatchPolicy(
            settings.speaker_match_threshold,
            settings.speaker_new_threshold,
            settings.speaker_match_margin,
        )

    async def claim(self) -> ClaimedJob | None:
        async with self.sessions() as session, session.begin():
            repository = SpeakerRepository(session)
            now = datetime.now(UTC)
            job = await repository.claim(now)
            if job is None:
                return None
            if job.attempt_count >= 2:
                job.status = "failed"
                job.error_code = "worker_interrupted"
                job.finished_at = now
                job.lease_expires_at = None
                return None
            job.attempt_count += 1
            job.claim_token += 1
            job.status = "running"
            job.started_at = job.started_at or now
            job.error_code = None
            job.lease_expires_at = now + timedelta(seconds=self.settings.job_timeout_seconds + 30)
            source = await repository.source_for_job(job)
            return ClaimedJob(
                job.speaker_job_id,
                job.public_id,
                job.tenant_id,
                source[1] if source else "",
                job.claim_token,
                cast(Literal["enroll", "identify"], job.purpose),
                source[0].storage_key if source else None,
            )

    async def process_once(self) -> bool:
        claim = await self.claim()
        if claim is None:
            return False
        started = time.monotonic()
        code = "succeeded"
        device = "unavailable"
        speech_seconds = 0.0
        try:
            if claim.storage_key is None:
                raise SpeakerError("recording_unavailable", 410)
            async with asyncio.timeout(self.settings.job_timeout_seconds):
                audio = await self.storage.read(claim.storage_key)
                result = await self.embedding.embed(
                    audio,
                    purpose=claim.purpose,
                    job_public_id=claim.public_id,
                    tenant_public_id=claim.tenant_public_id,
                )
            device, speech_seconds = result.device, result.speech_seconds
            if not await self.complete(claim, result):
                code = "stale_claim"
        except TimeoutError:
            code = "job_timeout"
            await self.fail(claim, code, retryable=True)
        except SpeakerError as exc:
            code = exc.code
            await self.fail(claim, code, retryable=code in {"inference_unavailable", "job_timeout"})
        except (SQLAlchemyError, OSError, ValueError):
            # Keep payloads, file paths and nearest-neighbor data out of logs and errors.
            code = "inference_unavailable"
            await self.fail(claim, code, retryable=True)
        logger.info(
            "speaker_job_attempt",
            extra={
                "structured_fields": {
                    "job_public_id": claim.public_id,
                    "state": code,
                    "duration_seconds": round(time.monotonic() - started, 4),
                    "speech_seconds": speech_seconds,
                    "device": device,
                    "model_revision": MODEL_REVISION,
                }
            },
        )
        return True

    async def complete(self, claim: ClaimedJob, result: EmbeddingResult) -> bool:
        if result.model_id != MODEL_ID or result.model_revision != MODEL_REVISION:
            raise SpeakerError("model_mismatch", 502)
        try:
            vector = normalize(result.embedding)
        except ValueError as exc:
            raise SpeakerError("model_mismatch", 502) from exc
        if (
            claim.purpose == "enroll"
            and (result.speech_seconds < 10 - 1e-6 or result.windows_count < 2)
        ) or result.speech_seconds < 3 - 1e-6:
            raise SpeakerError("insufficient_speech", 422)
        async with self.sessions() as session, session.begin():
            repository = SpeakerRepository(session)
            await repository.lock_tenant(claim.tenant_id)
            job = await repository.fenced_job(claim.job_id, claim.token, datetime.now(UTC))
            if job is None:
                return False
            source = await repository.source_for_job(job)
            if source is None:
                raise SpeakerError("recording_unavailable", 410)
            recording = source[0]
            if job.model_id != result.model_id or job.model_revision != result.model_revision:
                raise SpeakerError("model_mismatch", 502)
            ranked = await repository.ranked(job.tenant_id, vector)
            scores = [score for _, score in ranked]
            decision = decide(scores, self.policy)
            profile: SpeakerProfile | None = None
            output_decision: Literal["enrolled", "recognized", "unknown", "ambiguous"] = (
                decision.decision
            )
            reason = decision.reason
            if job.purpose == "enroll":
                if job.target_profile_id is not None:
                    profile = await repository.profile_by_id(job.tenant_id, job.target_profile_id)
                    if profile is None:
                        raise SpeakerError("profile_unavailable", 409)
                    if profile.model_id != MODEL_ID or profile.model_revision != MODEL_REVISION:
                        raise SpeakerError("model_mismatch", 409)
                    if profile.sample_count >= 20:
                        raise SpeakerError("sample_limit", 409)
                    if (
                        decision.decision != "recognized"
                        or ranked[0][0].speaker_profile_id != profile.speaker_profile_id
                    ):
                        raise SpeakerError("target_mismatch", 409)
                else:
                    profile = SpeakerProfile(
                        tenant_id=job.tenant_id,
                        name=job.requested_name or "",
                        sample_count=1,
                        model_id=MODEL_ID,
                        model_revision=MODEL_REVISION,
                        embedding=vector,
                        source_sha256=recording.sha256,
                        created_by=job.created_by,
                        updated_by=job.created_by,
                    )
                    session.add(profile)
                    await session.flush()
                existing = await repository.samples(job.tenant_id, profile.speaker_profile_id)
                if len(existing) >= 20:
                    raise SpeakerError("sample_limit", 409)
                if any(
                    item.model_id != MODEL_ID or item.model_revision != MODEL_REVISION
                    for item in existing
                ):
                    raise SpeakerError("model_mismatch", 409)
                vectors = [list(item.embedding) for item in existing] + [vector]
                profile.embedding = normalize(
                    [sum(float(v[index]) for v in vectors) / len(vectors) for index in range(192)]
                )
                profile.sample_count = len(vectors)
                hashes = sorted([item.source_sha256 for item in existing] + [recording.sha256])
                profile.source_sha256 = hashlib.sha256("\n".join(hashes).encode()).hexdigest()
                profile.updated_by = job.created_by
                session.add(
                    SpeakerSample(
                        tenant_id=job.tenant_id,
                        speaker_profile_id=profile.speaker_profile_id,
                        recording_id=recording.recording_id,
                        speaker_job_id=job.speaker_job_id,
                        embedding=vector,
                        model_id=MODEL_ID,
                        model_revision=MODEL_REVISION,
                        source_sha256=recording.sha256,
                        speech_seconds=result.speech_seconds,
                        windows_count=result.windows_count,
                        created_by=job.created_by,
                        updated_by=job.created_by,
                    )
                )
                output_decision, reason = "enrolled", "enrolled"
            elif decision.decision == "recognized":
                profile = ranked[0][0]
            output = SpeakerResult(
                decision=output_decision,
                profile_public_id=profile.public_id if profile else None,
                profile_name=profile.name if profile else None,
                similarity=scores[0] if scores else None,
                runner_up_similarity=scores[1] if len(scores) > 1 else None,
                speech_seconds=result.speech_seconds,
                windows_count=result.windows_count,
                model_id=result.model_id,
                model_revision=result.model_revision,
                device=result.device,
                reason=reason,
                policy=MatchPolicyResponse(**asdict(self.policy)),
            )
            job.result = output.model_dump(mode="json")
            job.status = "succeeded"
            job.error_code = None
            job.finished_at = datetime.now(UTC)
            job.lease_expires_at = None
            return True

    async def fail(self, claim: ClaimedJob, code: str, *, retryable: bool) -> bool:
        async with self.sessions() as session, session.begin():
            repository = SpeakerRepository(session)
            job = await repository.fenced_job(claim.job_id, claim.token, datetime.now(UTC))
            if job is None:
                return False
            job.error_code = code
            job.lease_expires_at = None
            if retryable and job.attempt_count < 2:
                job.status = "queued"
            else:
                job.status = "failed"
                job.finished_at = datetime.now(UTC)
            return True

    async def cleanup(self) -> int:
        now = datetime.now(UTC)
        count = 0
        async with self.sessions() as session, session.begin():
            repository = SpeakerRepository(session)
            rows = await repository.expired_recordings(now)
            for recording in sorted(rows, key=lambda row: row.tenant_id):
                await repository.lock_tenant(recording.tenant_id)
                if await repository.recording_in_use(recording.tenant_id, recording.recording_id):
                    continue
                await self.storage.remove(recording.storage_key)
                recording.is_deleted = True
                recording.deleted_at = recording.deleted_at or now
                recording.file_removed_at = now
                count += 1
            await repository.expire_job_results(
                now - timedelta(days=self.settings.job_retention_days)
            )
            await repository.release_expired_upload_keys(now)
            known = await repository.known_storage_keys()
        # Crashes between writing a complete file and committing its metadata leave owned orphans.
        cutoff = now.timestamp() - self.settings.audio_retention_hours * 3600
        if self.storage.root.exists():
            for path in self.storage.root.glob("*.audio"):
                if path.name not in known and path.stat().st_mtime < cutoff:
                    await self.storage.remove(path.name)
                    count += 1
        return count
