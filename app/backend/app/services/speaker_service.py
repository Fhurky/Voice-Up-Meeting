"""Speaker pilot orchestration, public serialization and mutation boundaries."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from app.core.config import Settings
from app.core.request_context import RequestContext
from app.domain.models.speaker_identity import Recording, SpeakerJob, SpeakerProfile
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.audio_storage import AudioStorage, UploadSource
from app.infrastructure.repositories.speaker_repository import SpeakerRepository
from app.schemas.speaker_identity import (
    JobError,
    RecordingResponse,
    SpeakerJobCreate,
    SpeakerJobPage,
    SpeakerJobResponse,
    SpeakerProfilePage,
    SpeakerProfileResponse,
    SpeakerResult,
)
from app.services.speaker_ports import SpeakerError

ERROR_MESSAGES = {
    "invalid_audio": "The audio file cannot be decoded safely.",
    "unsupported_audio": "Only WAV and FLAC audio files are supported.",
    "audio_limit": "The audio exceeds the configured size or duration limit.",
    "not_found": "The requested resource is unavailable.",
    "idempotency_conflict": "This retry key was already used with different content.",
    "recording_expired": "The uploaded audio expired; upload it again with a new key.",
    "recording_in_use": "An active profile sample or job still uses this recording.",
    "sample_limit": "A profile can contain at most 20 verified samples.",
    "forbidden": "The required permission is missing.",
    "insufficient_speech": "The recording contains insufficient usable speech.",
    "inconsistent_audio": "The speech windows are not sufficiently consistent.",
    "clipped_audio": "The recording is too heavily clipped.",
    "target_mismatch": "This sample does not safely match the selected profile.",
    "profile_unavailable": "The target profile is no longer available.",
    "model_mismatch": "The embedding model contract does not match this population.",
    "inference_unavailable": "The local inference service is unavailable.",
    "job_timeout": "The inference time limit was exceeded.",
    "worker_interrupted": "The worker lease expired after the allowed attempts.",
    "recording_unavailable": "The source audio is no longer available.",
    "validation_error": "The request contains invalid fields.",
}


def error_message(code: str) -> str:
    return ERROR_MESSAGES.get(code, "The operation could not be completed.")


def profile_response(profile: SpeakerProfile) -> SpeakerProfileResponse:
    return SpeakerProfileResponse(
        public_id=profile.public_id,
        name=profile.name,
        sample_count=profile.sample_count,
        model_id=profile.model_id,
        model_revision=profile.model_revision,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def recording_response(recording: Recording) -> RecordingResponse:
    return RecordingResponse(
        public_id=recording.public_id,
        sha256=recording.sha256,
        size_bytes=recording.size_bytes,
        format=cast(Literal["WAV", "FLAC"], recording.format),
        duration_seconds=recording.duration_seconds,
        created_at=recording.created_at,
    )


class SpeakerService:
    def __init__(
        self, repository: SpeakerRepository, storage: AudioStorage, settings: Settings
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.settings = settings

    async def upload(
        self,
        context: RequestContext,
        key: str,
        source: UploadSource,
        filename: str | None,
    ) -> RecordingResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        # File validation precedes idempotency comparison so a key never admits an invalid source.
        stored = await self.storage.receive(source, filename)
        keep_file = False
        try:
            await self.repository.lock_tenant(tenant_id)
            existing = await self.repository.recording_by_key(tenant_id, key)
            now = datetime.now(UTC)
            if existing is not None and existing.idempotency_expires_at <= now:
                existing.idempotency_key = None
                await self.repository.session.flush()
                existing = None
            if existing is not None:
                if existing.sha256 != stored.sha256:
                    raise SpeakerError("idempotency_conflict", 409)
                if (
                    existing.is_deleted
                    or existing.file_removed_at is not None
                    or (
                        existing.expires_at <= now
                        and not await self.repository.recording_in_use(
                            tenant_id, existing.recording_id
                        )
                    )
                ):
                    raise SpeakerError("recording_expired", 410)
                return recording_response(existing)
            recording = Recording(
                tenant_id=tenant_id,
                storage_key=stored.key,
                sha256=stored.sha256,
                size_bytes=stored.size_bytes,
                format=stored.format,
                duration_seconds=stored.duration_seconds,
                idempotency_key=key,
                idempotency_expires_at=now + timedelta(days=self.settings.job_retention_days),
                expires_at=now + timedelta(hours=self.settings.audio_retention_hours),
                created_by=actor_id,
                updated_by=actor_id,
            )
            self.repository.session.add(recording)
            await self.repository.session.flush()
            result = recording_response(recording)
            # Explicit commit makes a failed DB write remove the new file before the response.
            await self.repository.session.commit()
            keep_file = True
            return result
        finally:
            if not keep_file:
                await self.storage.remove(stored.key)

    async def start_job(
        self, context: RequestContext, key: str, body: SpeakerJobCreate
    ) -> SpeakerJobResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        if body.purpose == "enroll" and not context.has_permission("speaker_profiles:write"):
            raise SpeakerError("forbidden", 403)
        await self.repository.lock_tenant(tenant_id)
        source = await self.repository.recording(
            tenant_id, str(body.recording_public_id), active=False
        )
        if source is None:
            raise SpeakerError("not_found", 404)
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "sha256": source.sha256,
                    "purpose": body.purpose,
                    "model_id": MODEL_ID,
                    "model_revision": MODEL_REVISION,
                    "profile": (str(body.profile_public_id) if body.profile_public_id else None),
                    "name": body.name,
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        existing = await self.repository.job_by_key(tenant_id, body.purpose, key)
        if existing is not None:
            if existing[0].fingerprint != fingerprint:
                raise SpeakerError("idempotency_conflict", 409)
            return await self.job_response(*existing)
        if (
            source.is_deleted
            or source.file_removed_at is not None
            or (
                source.expires_at <= datetime.now(UTC)
                and not await self.repository.recording_in_use(tenant_id, source.recording_id)
            )
        ):
            raise SpeakerError("recording_expired", 410)
        target = None
        if body.profile_public_id is not None:
            target = await self.repository.profile(tenant_id, str(body.profile_public_id))
            if target is None:
                raise SpeakerError("not_found", 404)
            if target.model_id != MODEL_ID or target.model_revision != MODEL_REVISION:
                raise SpeakerError("model_mismatch", 409)
            if target.sample_count >= 20:
                raise SpeakerError("sample_limit", 409)
        job = SpeakerJob(
            tenant_id=tenant_id,
            recording_id=source.recording_id,
            target_profile_id=target.speaker_profile_id if target else None,
            requested_name=body.name,
            purpose=body.purpose,
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            idempotency_key=key,
            fingerprint=fingerprint,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.repository.session.add(job)
        await self.repository.session.flush()
        return await self.job_response(job, source)

    async def job_response(self, job: SpeakerJob, recording: Recording) -> SpeakerJobResponse:
        result = SpeakerResult.model_validate(job.result) if job.result else None
        if result and result.profile_public_id:
            profile = await self.repository.profile(job.tenant_id, result.profile_public_id)
            result.profile_deleted = profile is None
            result.profile_name = profile.name if profile else None
        return SpeakerJobResponse(
            public_id=job.public_id,
            purpose=cast(Literal["enroll", "identify"], job.purpose),
            status=cast(Literal["queued", "running", "succeeded", "failed"], job.status),
            recording_public_id=recording.public_id,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            attempt_count=job.attempt_count,
            result=result,
            error=(
                JobError(code=job.error_code, message=error_message(job.error_code))
                if job.error_code
                else None
            ),
        )

    async def get_job(self, context: RequestContext, public_id: str) -> SpeakerJobResponse:
        tenant_id, _ = await self.repository.actor(context)
        record = await self.repository.job(tenant_id, public_id)
        if record is None:
            raise SpeakerError("not_found", 404)
        return await self.job_response(*record)

    async def list_jobs(self, context: RequestContext, offset: int, limit: int) -> SpeakerJobPage:
        tenant_id, _ = await self.repository.actor(context)
        jobs, total = await self.repository.jobs(tenant_id, offset, limit)
        return SpeakerJobPage(
            items=[await self.job_response(*job) for job in jobs],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def list_profiles(
        self, context: RequestContext, offset: int, limit: int
    ) -> SpeakerProfilePage:
        tenant_id, _ = await self.repository.actor(context)
        profiles, total = await self.repository.profiles(tenant_id, offset, limit)
        return SpeakerProfilePage(
            items=[profile_response(profile) for profile in profiles],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def rename_profile(
        self, context: RequestContext, public_id: str, name: str
    ) -> SpeakerProfileResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        profile = await self.repository.profile(tenant_id, public_id)
        if profile is None:
            raise SpeakerError("not_found", 404)
        profile.name = name
        profile.updated_by = actor_id
        await self.repository.session.flush()
        await self.repository.session.refresh(profile)
        return profile_response(profile)

    async def delete_profile(self, context: RequestContext, public_id: str) -> None:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        profile = await self.repository.profile(tenant_id, public_id)
        if profile is None:
            raise SpeakerError("not_found", 404)
        now = datetime.now(UTC)
        profile.is_deleted, profile.deleted_at, profile.deleted_by = True, now, actor_id
        profile.updated_by = actor_id
        samples = await self.repository.samples(tenant_id, profile.speaker_profile_id)
        for sample in samples:
            sample.is_deleted, sample.deleted_at, sample.deleted_by = (
                True,
                now,
                actor_id,
            )
            sample.updated_by = actor_id
        await self.repository.session.flush()
        sources = await self.repository.recordings_by_ids(
            tenant_id, {sample.recording_id for sample in samples}
        )
        for recording in sources:
            recording.expires_at = now

    async def delete_recording(self, context: RequestContext, public_id: str) -> None:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        recording = await self.repository.recording(tenant_id, public_id)
        if recording is None:
            raise SpeakerError("not_found", 404)
        if await self.repository.recording_in_use(tenant_id, recording.recording_id):
            raise SpeakerError("recording_in_use", 409)
        now = datetime.now(UTC)
        recording.is_deleted, recording.deleted_at, recording.deleted_by = (
            True,
            now,
            actor_id,
        )
        recording.updated_by = actor_id
        recording.expires_at = now
