"""Bounded retention selection and tenant-qualified meeting payload redaction."""

from datetime import datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.meeting import (
    Meeting,
    MeetingChunk,
    MeetingSpeaker,
    MeetingTranscript,
    MeetingUploadPart,
)
from app.infrastructure.repositories.speaker_repository import SpeakerRepository

TERMINAL_STATUSES = ("succeeded", "failed", "cancelled")


class MeetingCleanupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.speaker_repository = SpeakerRepository(session)

    async def candidates(self, now: datetime, cutoff: datetime) -> list[tuple[int, int]]:
        expired_upload = and_(Meeting.status == "uploading", Meeting.upload_expires_at <= now)
        expired_source = and_(Meeting.source_removed_at.is_(None), Meeting.source_expires_at <= now)
        expired_results = and_(Meeting.is_deleted.is_(False), Meeting.finished_at <= cutoff)
        deleted_results = and_(
            Meeting.is_deleted.is_(True),
            or_(Meeting.title != "", Meeting.idempotency_key.is_not(None)),
        )
        # Filter active work before LIMIT: hundreds of protected sources cannot starve cleanup.
        rows = await self.session.execute(
            select(Meeting.tenant_id, Meeting.meeting_id)
            .where(
                or_(
                    expired_upload,
                    and_(
                        Meeting.status.in_(TERMINAL_STATUSES),
                        or_(expired_source, expired_results, deleted_results),
                    ),
                )
            )
            .order_by(Meeting.source_expires_at, Meeting.meeting_id)
            .limit(100)
        )
        return [(int(tenant), int(meeting)) for tenant, meeting in rows]

    async def locked(self, tenant_id: int, meeting_id: int) -> Meeting | None:
        await self.speaker_repository.lock_tenant(tenant_id)
        return (
            await self.session.scalars(
                select(Meeting)
                .where(
                    Meeting.tenant_id == tenant_id,
                    Meeting.meeting_id == meeting_id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).one_or_none()

    async def scrub_results(self, meeting: Meeting, now: datetime) -> None:
        lifecycle = {
            "is_deleted": True,
            "deleted_at": now,
            "updated_at": now,
            "updated_by": None,
            "props": {},
        }
        for model, payload in (
            (MeetingTranscript, {"text": "", "meeting_speaker_id": None}),
            (MeetingChunk, {"result": {}}),
            (MeetingUploadPart, {"sha256": ""}),
            (
                MeetingSpeaker,
                {
                    "display_name": None,
                    "embedding": None,
                    "tracking_embedding": None,
                    "tracking_model_id": None,
                    "tracking_model_revision": None,
                    "clean_ranges": [],
                    "profile_id": None,
                    "enrollment_job_id": None,
                    "model_id": None,
                    "model_revision": None,
                    "source_sha256": None,
                    "reason": None,
                    "speech_seconds": 0,
                    "decision": "profile_pending",
                    "version": MeetingSpeaker.version + 1,
                },
            ),
        ):
            await self.session.execute(
                update(model)
                .where(
                    model.tenant_id == meeting.tenant_id,
                    model.meeting_id == meeting.meeting_id,
                )
                .values(**lifecycle, **payload)
            )
        meeting.is_deleted = True
        meeting.deleted_at = meeting.deleted_at or now
        meeting.updated_at = now
        meeting.updated_by = None
        meeting.title = ""
        meeting.idempotency_key = None
        meeting.source_sha256 = None
        meeting.error_code = None
        meeting.props = {}
