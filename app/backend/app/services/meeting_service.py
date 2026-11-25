"""Uploaded meeting lifecycle, tenant mutation boundaries and public projections."""

import asyncio
import hashlib
import json
import logging
import math
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.request_context import RequestContext
from app.domain.meeting import (
    CAPTURE_CHAIN_START,
    CAPTURE_CHANNELS,
    CAPTURE_FRAME_BYTES,
    CAPTURE_HEADER_BYTES,
    CAPTURE_IDLE_SECONDS,
    CAPTURE_PART_MAX_SECONDS,
    CHANNEL_NAMES,
    CORE_SECONDS,
    UPLOAD_PART_BYTES,
    capture_frames,
    capture_max_frames,
    capture_wav_header,
    meeting_tracks,
    next_capture_chain,
    window_core_seconds,
)
from app.domain.meeting_timeline import SpeechTurn, union_turns
from app.domain.models.meeting import (
    Meeting,
    MeetingParticipant,
    MeetingQuestion,
    MeetingSpeaker,
    MeetingUploadPart,
)
from app.infrastructure.meeting_audio import PREVIEW_MAX_SECONDS, MeetingAudioStorage
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.infrastructure.repositories.transcript_revision_repository import (
    TranscriptRevisionRepository,
)
from app.schemas.meeting import (
    MeetingCaptureAck,
    MeetingCaptureComplete,
    MeetingCaptureCreate,
    MeetingCreate,
    MeetingOptions,
    MeetingPage,
    MeetingResponse,
    MeetingSpeakerPage,
    MeetingSpeakerRename,
    MeetingSpeakerResponse,
    MeetingSpeakerTurnPage,
    MeetingSpeakerTurnResponse,
    MeetingTranscriptPage,
    MeetingTranscriptResponse,
    MeetingUploadManifest,
    MeetingUploadPartResponse,
)
from app.services.speaker_ports import SpeakerError
from app.services.transcript_suggestions import saved_correction_response

capture_logger = logging.getLogger("app.meeting_capture")


class MeetingService:
    def __init__(
        self,
        repository: MeetingRepository,
        storage: MeetingAudioStorage,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.settings = settings

    async def required(self, tenant_id: int, public_id: str) -> Meeting:
        meeting = await self.repository.meeting(tenant_id, public_id)
        if meeting is None:
            raise SpeakerError("not_found", 404)
        return meeting

    async def response(self, meeting: Meeting) -> MeetingResponse:
        _, observed = await self.repository.speakers(meeting.tenant_id, meeting.meeting_id, 0, 1)
        mismatch = meeting.status == "succeeded" and (
            (meeting.expected_speakers is not None and observed != meeting.expected_speakers)
            or (meeting.participant_count is not None and observed > meeting.participant_count)
        )
        return MeetingResponse.model_validate(
            {
                "public_id": meeting.public_id,
                "title": meeting.title,
                "status": meeting.status,
                "format": meeting.format,
                "size_bytes": meeting.size_bytes,
                "uploaded_bytes": meeting.uploaded_bytes,
                "next_upload_index": math.ceil(meeting.uploaded_bytes / UPLOAD_PART_BYTES),
                "sha256": meeting.source_sha256,
                "duration_seconds": meeting.duration_seconds,
                "processed_seconds": meeting.processed_seconds,
                "completed_chunks": meeting.next_chunk_index,
                "total_chunks": (
                    math.ceil(meeting.duration_seconds / window_core_seconds(meeting.props))
                    * len(meeting_tracks(meeting.capture_mode))
                    if meeting.duration_seconds
                    else 0
                ),
                "language": meeting.language,
                "participant_count": meeting.participant_count,
                "expected_speakers": meeting.expected_speakers,
                "auto_enroll": meeting.auto_enroll,
                "participants": [
                    {
                        "profile_public_id": profile.public_id,
                        "name": None if profile.is_deleted else profile.name,
                    }
                    for profile in await self.repository.participants(
                        meeting.tenant_id, meeting.meeting_id
                    )
                ],
                "subject": meeting.subject,
                "questions": [
                    {"public_id": question.public_id, "text": question.text}
                    for question in await self.repository.questions(
                        meeting.tenant_id, meeting.meeting_id
                    )
                ],
                "observed_speakers": observed,
                "count_mismatch": mismatch,
                "error_code": meeting.error_code,
                "source_available": meeting.source_sha256 is not None
                and meeting.source_removed_at is None,
                "created_at": meeting.created_at,
                "started_at": meeting.started_at,
                "finished_at": meeting.finished_at,
                **self.capture_fields(meeting),
            }
        )

    @staticmethod
    def capture_fields(meeting: Meeting) -> dict[str, object]:
        if meeting.capture_mode != "two_channel" or not meeting.sample_rate:
            return {
                "capture_mode": meeting.capture_mode,
                "captured_frames": None,
                "captured_seconds": None,
                "capture_idle": False,
            }
        frames = capture_frames(meeting.uploaded_bytes)
        last = meeting.capture_part_at or meeting.created_at
        return {
            "capture_mode": meeting.capture_mode,
            "captured_frames": frames,
            "captured_seconds": frames / meeting.sample_rate,
            "capture_idle": meeting.status == "uploading"
            and last is not None
            and datetime.now(UTC) - last >= timedelta(seconds=CAPTURE_IDLE_SECONDS),
        }

    async def create(
        self, context: RequestContext, key: str, body: MeetingCreate
    ) -> MeetingResponse:
        return await self._create(
            context,
            key,
            body,
            body.model_dump(mode="json"),
            size_bytes=body.size_bytes,
            fields={"format": body.format},
        )

    async def create_capture(
        self, context: RequestContext, key: str, body: MeetingCaptureCreate
    ) -> MeetingResponse:
        # The final size is unknown while the meeting runs; the source limit is reserved until sealing.
        reserved = (
            CAPTURE_HEADER_BYTES
            + capture_max_frames(
                body.sample_rate, self.settings.meeting_max_seconds, self.settings.meeting_max_bytes
            )
            * CAPTURE_FRAME_BYTES
        )
        return await self._create(
            context,
            key,
            body,
            {"capture_mode": "two_channel", **body.model_dump(mode="json")},
            size_bytes=reserved,
            fields={
                "format": "WAV",
                "sample_rate": body.sample_rate,
                "channels": CAPTURE_CHANNELS,
                "capture_mode": "two_channel",
                "capture_chain": CAPTURE_CHAIN_START,
            },
        )

    async def _create(
        self,
        context: RequestContext,
        key: str,
        body: MeetingOptions,
        canonical: dict[str, object],
        *,
        size_bytes: int,
        fields: dict[str, object],
    ) -> MeetingResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        if body.auto_enroll and not context.has_permission("speaker_profiles:write"):
            raise SpeakerError("forbidden", 403)
        if body.participant_profile_ids and not context.has_permission("speaker_profiles:read"):
            raise SpeakerError("forbidden", 403)
        if size_bytes > self.settings.meeting_max_bytes:
            raise SpeakerError("audio_limit", 413)
        fingerprint = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        await self.repository.lock_tenant(tenant_id)
        existing = await self.repository.by_key(tenant_id, key)
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise SpeakerError("idempotency_conflict", 409)
            if existing.is_deleted:
                raise SpeakerError("recording_expired", 410)
            return await self.response(existing)
        if (
            await self.repository.active_upload_count(tenant_id)
            >= self.settings.meeting_active_uploads
        ):
            raise SpeakerError("upload_limit", 409)
        if (
            await self.repository.retained_bytes(tenant_id) + size_bytes
            > self.settings.meeting_tenant_max_bytes
        ):
            raise SpeakerError("storage_limit", 413)
        listed = [str(value) for value in body.participant_profile_ids]
        participants = await self.repository.active_profiles_by_public_id(tenant_id, listed)
        if len(participants) != len(listed):
            raise SpeakerError("participant_not_found", 404)
        now = datetime.now(UTC)
        meeting = Meeting(
            tenant_id=tenant_id,
            title=body.title,
            size_bytes=size_bytes,
            uploaded_bytes=0,
            storage_key=f"{uuid4().hex}.meeting",
            status="uploading",
            language=body.language,
            # A list holds only saved people; unsaved attendees make its length no count bound.
            participant_count=body.participant_count,
            expected_speakers=body.expected_speakers,
            subject=body.subject,
            auto_enroll=body.auto_enroll,
            props={"window_core_seconds": CORE_SECONDS},
            idempotency_key=key,
            fingerprint=fingerprint,
            source_expires_at=now + timedelta(days=self.settings.meeting_source_retention_days),
            upload_expires_at=now + timedelta(hours=self.settings.meeting_upload_retention_hours),
            created_by=actor_id,
            updated_by=actor_id,
            **fields,
        )
        self.repository.session.add(meeting)
        await self.repository.session.flush()
        self.repository.session.add_all(
            MeetingParticipant(
                tenant_id=tenant_id,
                meeting_id=meeting.meeting_id,
                speaker_profile_id=profile.speaker_profile_id,
                created_by=actor_id,
                updated_by=actor_id,
            )
            for profile in participants
        )
        self.repository.session.add_all(
            MeetingQuestion(
                tenant_id=tenant_id,
                meeting_id=meeting.meeting_id,
                ordinal=ordinal,
                text=question,
                created_by=actor_id,
                updated_by=actor_id,
            )
            for ordinal, question in enumerate(body.questions)
        )
        await self.repository.session.flush()
        return await self.response(meeting)

    async def get(self, context: RequestContext, public_id: str) -> MeetingResponse:
        tenant_id, _ = await self.repository.actor(context)
        return await self.response(await self.required(tenant_id, public_id))

    async def audio_preview(
        self, context: RequestContext, public_id: str, start_seconds: float, end_seconds: float
    ) -> bytes:
        if not context.has_permission("meeting_analysis:read"):
            raise SpeakerError("forbidden", 403)
        tenant_id, _ = await self.repository.actor(context)
        meeting = await self.required(tenant_id, public_id)
        if meeting.status == "uploading":
            raise SpeakerError("meeting_state_conflict", 409)
        if (
            meeting.source_removed_at is not None
            or meeting.source_expires_at is None
            or meeting.source_expires_at <= datetime.now(UTC)
        ):
            raise SpeakerError("recording_unavailable", 410)
        if (
            meeting.source_sha256 is None
            or meeting.duration_seconds is None
            or meeting.sample_rate is None
            or meeting.channels is None
            or meeting.uploaded_bytes != meeting.size_bytes
        ):
            raise SpeakerError("meeting_state_conflict", 409)
        if (
            not all(math.isfinite(value) for value in (start_seconds, end_seconds))
            or start_seconds < 0
            or not 0 < end_seconds - start_seconds <= PREVIEW_MAX_SECONDS
            or end_seconds > meeting.duration_seconds
        ):
            raise SpeakerError("invalid_audio_range", 422)
        return await asyncio.to_thread(
            self.storage.preview,
            meeting.storage_key,
            start_seconds,
            end_seconds,
            expected_bytes=meeting.size_bytes,
            expected_format=meeting.format,
            sample_rate=meeting.sample_rate,
            channels=meeting.channels,
            duration_seconds=meeting.duration_seconds,
        )

    async def list(self, context: RequestContext, offset: int, limit: int) -> MeetingPage:
        tenant_id, _ = await self.repository.actor(context)
        rows, total = await self.repository.list_meetings(tenant_id, offset, limit)
        return MeetingPage(
            items=[await self.response(row) for row in rows],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def manifest(self, context: RequestContext, public_id: str) -> MeetingUploadManifest:
        tenant_id, _ = await self.repository.actor(context)
        meeting = await self.required(tenant_id, public_id)
        return await self.manifest_response(meeting)

    async def manifest_response(self, meeting: Meeting) -> MeetingUploadManifest:
        rows = await self.repository.upload_parts(meeting.tenant_id, meeting.meeting_id)
        return MeetingUploadManifest(
            meeting_public_id=UUID(meeting.public_id),
            parts=[
                MeetingUploadPartResponse(
                    index=row.index, size_bytes=row.size_bytes, sha256=row.sha256
                )
                for row in rows
            ],
            uploaded_bytes=meeting.uploaded_bytes,
            next_index=len(rows),
        )

    async def append(
        self,
        context: RequestContext,
        public_id: str,
        index: int,
        data: bytes,
        sha256: str,
    ) -> MeetingUploadManifest:
        tenant_id, actor_id = await self.repository.actor(context)
        if hashlib.sha256(data).hexdigest() != sha256:
            raise SpeakerError("chunk_hash_mismatch", 409)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        if meeting.status != "uploading" or meeting.capture_mode != "file":
            raise SpeakerError("meeting_state_conflict", 409)
        if meeting.upload_expires_at <= datetime.now(UTC):
            raise SpeakerError("recording_expired", 410)
        previous = await self.repository.upload_part(tenant_id, meeting.meeting_id, index)
        if previous is not None:
            if previous.sha256 != sha256 or previous.size_bytes != len(data):
                raise SpeakerError("idempotency_conflict", 409)
            return await self.manifest_response(meeting)
        expected_index = math.ceil(meeting.uploaded_bytes / UPLOAD_PART_BYTES)
        expected_size = min(UPLOAD_PART_BYTES, meeting.size_bytes - meeting.uploaded_bytes)
        if index != expected_index or not expected_size or len(data) != expected_size:
            raise SpeakerError("upload_order_conflict", 409)
        await asyncio.to_thread(
            self.storage.append,
            meeting.storage_key,
            meeting.uploaded_bytes,
            data,
            sha256,
        )
        self.repository.session.add(
            MeetingUploadPart(
                tenant_id=tenant_id,
                meeting_id=meeting.meeting_id,
                index=index,
                size_bytes=len(data),
                sha256=sha256,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
        meeting.uploaded_bytes += len(data)
        meeting.updated_by = actor_id
        await self.repository.session.flush()
        return await self.manifest_response(meeting)

    async def complete(self, context: RequestContext, public_id: str) -> MeetingResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        if meeting.auto_enroll and not context.has_permission("speaker_profiles:write"):
            raise SpeakerError("forbidden", 403)
        if meeting.status in {"queued", "running", "finalizing", "succeeded"}:
            return await self.response(meeting)
        if meeting.status != "uploading" or meeting.capture_mode != "file":
            raise SpeakerError("meeting_state_conflict", 409)
        if meeting.upload_expires_at <= datetime.now(UTC):
            raise SpeakerError("recording_expired", 410)
        if meeting.uploaded_bytes != meeting.size_bytes:
            raise SpeakerError("upload_incomplete", 409)
        await self.queue_source(meeting, actor_id)
        return await self.response(meeting)

    async def queue_source(self, meeting: Meeting, actor_id: int) -> None:
        info = await asyncio.to_thread(
            self.storage.validate,
            meeting.storage_key,
            meeting.size_bytes,
            meeting.format,
        )
        if info.duration_seconds > self.settings.meeting_max_seconds:
            raise SpeakerError("audio_limit", 413)
        meeting.source_sha256 = info.sha256
        meeting.duration_seconds = info.duration_seconds
        meeting.sample_rate = info.sample_rate
        meeting.channels = info.channels
        meeting.status = "queued"
        meeting.updated_by = actor_id
        await self.repository.session.flush()

    async def capture_append(
        self,
        context: RequestContext,
        public_id: str,
        start_frame: int,
        data: bytes,
        sha256: str,
    ) -> MeetingCaptureAck:
        tenant_id, actor_id = await self.repository.actor(context)
        if hashlib.sha256(data).hexdigest() != sha256:
            raise SpeakerError("chunk_hash_mismatch", 409)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        if meeting.capture_mode != "two_channel" or meeting.status != "uploading":
            raise SpeakerError("meeting_not_capturing", 409)
        if meeting.upload_expires_at <= datetime.now(UTC):
            raise SpeakerError("recording_expired", 410)
        rate = meeting.sample_rate or 0
        if not data or len(data) % CAPTURE_FRAME_BYTES:
            raise SpeakerError("capture_part_unaligned", 422)
        frames = len(data) // CAPTURE_FRAME_BYTES
        if frames > rate * CAPTURE_PART_MAX_SECONDS:
            raise SpeakerError("audio_limit", 413)
        received = capture_frames(meeting.uploaded_bytes)
        counts = dict(meeting.props.get("capture", {}))
        if start_frame == received:
            limit = capture_max_frames(
                rate, self.settings.meeting_max_seconds, self.settings.meeting_max_bytes
            )
            if received + frames > limit:
                raise SpeakerError("audio_limit", 413)
            # The first part also writes the header space that sealing fills in.
            payload = data if received else bytes(CAPTURE_HEADER_BYTES) + data
            offset = meeting.uploaded_bytes if received else 0
            await asyncio.to_thread(
                self.storage.append,
                meeting.storage_key,
                offset,
                payload,
                hashlib.sha256(payload).hexdigest(),
            )
            meeting.uploaded_bytes = offset + len(payload)
            meeting.capture_chain = next_capture_chain(
                meeting.capture_chain or CAPTURE_CHAIN_START, sha256
            )
            meeting.capture_part_at = datetime.now(UTC)
            counts["parts"] = int(counts.get("parts", 0)) + 1
        elif start_frame + frames <= received:
            # A retried part whose acknowledgement was lost: the stored bytes must be identical.
            stored = await asyncio.to_thread(
                self.storage.read_range,
                meeting.storage_key,
                CAPTURE_HEADER_BYTES + start_frame * CAPTURE_FRAME_BYTES,
                len(data),
            )
            if hashlib.sha256(stored).hexdigest() != sha256:
                raise SpeakerError("capture_conflict", 409)
            counts["duplicates"] = int(counts.get("duplicates", 0)) + 1
        else:
            capture_logger.info(
                "meeting_capture_gap",
                extra={"structured_fields": {"missing_frames": start_frame - received}},
            )
            raise SpeakerError("capture_gap", 409)
        meeting.props = {**meeting.props, "capture": counts}
        meeting.updated_by = actor_id
        await self.repository.session.flush()
        return MeetingCaptureAck(received_frames=capture_frames(meeting.uploaded_bytes))

    async def capture_complete(
        self, context: RequestContext, public_id: str, body: MeetingCaptureComplete
    ) -> MeetingResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        if meeting.auto_enroll and not context.has_permission("speaker_profiles:write"):
            raise SpeakerError("forbidden", 403)
        if meeting.capture_mode != "two_channel":
            raise SpeakerError("meeting_state_conflict", 409)
        if meeting.status in {"queued", "running", "finalizing", "succeeded"}:
            return await self.response(meeting)
        if meeting.status != "uploading":
            raise SpeakerError("meeting_state_conflict", 409)
        if meeting.upload_expires_at <= datetime.now(UTC):
            raise SpeakerError("recording_expired", 410)
        if capture_frames(meeting.uploaded_bytes) != body.frames:
            raise SpeakerError("capture_incomplete", 409)
        if meeting.capture_chain != body.chain_sha256:
            raise SpeakerError("capture_chain_mismatch", 422)
        await self.seal_capture(meeting, actor_id, "completed")
        return await self.response(meeting)

    async def capture_seal(self, context: RequestContext, public_id: str) -> MeetingResponse:
        """Processes what arrived from a recording whose browser stopped sending."""
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        if meeting.auto_enroll and not context.has_permission("speaker_profiles:write"):
            raise SpeakerError("forbidden", 403)
        if meeting.capture_mode != "two_channel":
            raise SpeakerError("meeting_state_conflict", 409)
        if meeting.status in {"queued", "running", "finalizing", "succeeded"}:
            return await self.response(meeting)
        if meeting.status != "uploading":
            raise SpeakerError("meeting_state_conflict", 409)
        if meeting.upload_expires_at <= datetime.now(UTC):
            raise SpeakerError("recording_expired", 410)
        if not capture_frames(meeting.uploaded_bytes):
            raise SpeakerError("capture_empty", 409)
        if not self.capture_fields(meeting)["capture_idle"]:
            raise SpeakerError("capture_active", 409)
        await self.seal_capture(meeting, actor_id, "sealed")
        return await self.response(meeting)

    async def seal_capture(self, meeting: Meeting, actor_id: int, outcome: str) -> None:
        frames = capture_frames(meeting.uploaded_bytes)
        await asyncio.to_thread(
            self.storage.write_header,
            meeting.storage_key,
            capture_wav_header(meeting.sample_rate or 0, frames),
        )
        meeting.size_bytes = meeting.uploaded_bytes
        await self.queue_source(meeting, actor_id)
        counts = meeting.props.get("capture", {})
        capture_logger.info(
            "meeting_capture",
            extra={
                "structured_fields": {
                    "outcome": outcome,
                    "seconds": round(frames / (meeting.sample_rate or 1), 3),
                    "parts": int(counts.get("parts", 0)),
                    "duplicates": int(counts.get("duplicates", 0)),
                }
            },
        )

    async def cancel(self, context: RequestContext, public_id: str) -> MeetingResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        if meeting.status == "succeeded":
            raise SpeakerError("meeting_state_conflict", 409)
        if meeting.status != "cancelled":
            self.cancel_row(meeting, actor_id)
            await self.repository.session.flush()
        return await self.response(meeting)

    def cancel_row(self, meeting: Meeting, actor_id: int) -> None:
        now = datetime.now(UTC)
        meeting.status = "cancelled"
        meeting.claim_token += 1
        meeting.lease_expires_at = None
        meeting.finished_at = now
        meeting.source_expires_at = now + timedelta(
            days=self.settings.meeting_source_retention_days
        )
        meeting.updated_by = actor_id

    async def retry(self, context: RequestContext, public_id: str) -> MeetingResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        if meeting.auto_enroll and not context.has_permission("speaker_profiles:write"):
            raise SpeakerError("forbidden", 403)
        if meeting.status in {"queued", "running", "finalizing", "succeeded"}:
            return await self.response(meeting)
        if meeting.status != "failed":
            raise SpeakerError("meeting_state_conflict", 409)
        if meeting.source_removed_at is not None or meeting.source_sha256 is None:
            raise SpeakerError("recording_unavailable", 410)
        if meeting.source_expires_at is not None and meeting.source_expires_at <= datetime.now(UTC):
            raise SpeakerError("recording_expired", 410)
        meeting.status = "queued"
        meeting.claim_token += 1
        meeting.attempt_count = 0
        meeting.lease_expires_at = None
        meeting.finished_at = None
        meeting.error_code = None
        meeting.updated_by = actor_id
        await self.repository.session.flush()
        return await self.response(meeting)

    async def delete(self, context: RequestContext, public_id: str) -> None:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        self.cancel_row(meeting, actor_id)
        now = datetime.now(UTC)
        meeting.is_deleted, meeting.deleted_at, meeting.deleted_by = True, now, actor_id
        meeting.source_expires_at = now
        await self.repository.session.flush()

    async def speaker_response(self, row: MeetingSpeaker) -> MeetingSpeakerResponse:
        profile = (
            await self.repository.speaker_repository.profile_by_id(row.tenant_id, row.profile_id)
            if row.profile_id is not None
            else None
        )
        return MeetingSpeakerResponse.model_validate(
            {
                "public_id": row.public_id,
                "ordinal": row.ordinal,
                "channel": CHANNEL_NAMES[row.channel] if row.channel is not None else None,
                "display_name": row.display_name,
                "profile_public_id": profile.public_id if profile else None,
                "profile_name": profile.name if profile else None,
                "profile_deleted": row.profile_id is not None and profile is None,
                "decision": row.decision,
                "reason": row.reason or "insufficient_speech",
                "speech_seconds": row.speech_seconds,
                "version": row.version,
                "profile_updated_at": profile.updated_at if profile else None,
            }
        )

    async def speakers(
        self, context: RequestContext, public_id: str, offset: int, limit: int
    ) -> MeetingSpeakerPage:
        tenant_id, _ = await self.repository.actor(context)
        meeting = await self.required(tenant_id, public_id)
        rows, total = await self.repository.speakers(tenant_id, meeting.meeting_id, offset, limit)
        return MeetingSpeakerPage(
            items=[await self.speaker_response(row) for row in rows],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def rename(
        self,
        context: RequestContext,
        public_id: str,
        speaker_public_id: str,
        body: MeetingSpeakerRename,
    ) -> MeetingSpeakerResponse:
        tenant_id, actor_id = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        meeting = await self.required(tenant_id, public_id)
        row = await self.repository.speaker(tenant_id, meeting.meeting_id, speaker_public_id)
        if row is None:
            raise SpeakerError("not_found", 404)
        # Speakers are rebuilt at meeting end; a name given earlier would have no stable owner.
        if meeting.status != "succeeded":
            raise SpeakerError("meeting_not_ready", 409)
        if row.version != body.version:
            raise SpeakerError("name_conflict", 409)
        profile = (
            await self.repository.speaker_repository.profile_by_id(tenant_id, row.profile_id)
            if row.profile_id is not None
            else None
        )
        if profile is not None:
            if not context.has_permission("speaker_profiles:write"):
                raise SpeakerError("forbidden", 403)
            if body.profile_updated_at != profile.updated_at:
                raise SpeakerError("name_conflict", 409)
            profile.name, profile.updated_by = body.name, actor_id
        row.display_name, row.updated_by = body.name, actor_id
        row.version += 1
        await self.repository.session.flush()
        if profile is not None:
            await self.repository.session.refresh(profile)
        return await self.speaker_response(row)

    async def transcript(
        self, context: RequestContext, public_id: str, offset: int, limit: int
    ) -> MeetingTranscriptPage:
        tenant_id, _ = await self.repository.actor(context)
        meeting = await self.required(tenant_id, public_id)
        rows, total = await self.repository.transcript(tenant_id, meeting.meeting_id, offset, limit)
        corrections = await TranscriptRevisionRepository(
            self.repository.session
        ).latest_for_sources(
            tenant_id,
            meeting.meeting_id,
            {
                row.meeting_transcript_id: hashlib.sha256(row.text.encode("utf-8")).hexdigest()
                for row in rows
            },
        )
        speakers: dict[int, MeetingSpeakerResponse] = {}
        output: list[MeetingTranscriptResponse] = []
        for row in rows:
            speaker = None
            if row.meeting_speaker_id is not None:
                if row.meeting_speaker_id not in speakers:
                    found = await self.repository.speaker_by_id(
                        tenant_id, meeting.meeting_id, row.meeting_speaker_id
                    )
                    if found is not None:
                        speakers[row.meeting_speaker_id] = await self.speaker_response(found)
                speaker = speakers.get(row.meeting_speaker_id)
            output.append(
                MeetingTranscriptResponse.model_validate(
                    {
                        "public_id": row.public_id,
                        "ordinal": row.ordinal,
                        "speaker_public_id": speaker.public_id if speaker else None,
                        "speaker_ordinal": speaker.ordinal if speaker else None,
                        "speaker_name": (
                            (speaker.profile_name or speaker.display_name) if speaker else None
                        ),
                        "profile_public_id": (speaker.profile_public_id if speaker else None),
                        "start_seconds": row.start,
                        "end_seconds": row.end,
                        "text": row.text,
                        "language": row.language,
                        "overlap": row.overlap,
                        "uncertain": row.uncertain,
                        "correction": (
                            saved_correction_response(corrections[row.meeting_transcript_id])
                            if row.meeting_transcript_id in corrections
                            else None
                        ),
                    }
                )
            )
        return MeetingTranscriptPage(
            items=output,
            total=total,
            offset=offset,
            limit=limit,
            provisional=meeting.status != "succeeded",
        )

    async def speaker_turns(
        self, context: RequestContext, public_id: str, offset: int, limit: int
    ) -> MeetingSpeakerTurnPage:
        tenant_id, _ = await self.repository.actor(context)
        meeting = await self.required(tenant_id, public_id)
        chunks = await self.repository.chunk_speaker_turns(tenant_id, meeting.meeting_id)
        if any(not isinstance(turns, list) for turns in chunks):
            raise SpeakerError("speaker_turns_unavailable", 409)
        speakers = await self.repository.speaker_public_ids(tenant_id, meeting.meeting_id)
        turns = union_turns(
            [
                SpeechTurn(float(turn["start"]), float(turn["end"]), int(turn["speaker"]))
                for chunk in chunks
                for turn in chunk
            ]
        )
        return MeetingSpeakerTurnPage(
            items=[
                MeetingSpeakerTurnResponse(
                    start_seconds=turn.start,
                    end_seconds=turn.end,
                    speaker_public_id=(
                        UUID(speakers[turn.speaker]) if turn.speaker in speakers else None
                    ),
                )
                for turn in turns[offset : offset + limit]
            ],
            total=len(turns),
            offset=offset,
            limit=limit,
            provisional=meeting.status != "succeeded",
        )
