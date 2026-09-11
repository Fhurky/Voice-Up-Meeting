"""Tenant-scoped PostgreSQL meeting queries and worker lease fencing."""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_context import RequestContext
from app.domain.models.meeting import (
    Meeting,
    MeetingChunk,
    MeetingSpeaker,
    MeetingTranscript,
    MeetingUploadPart,
)
from app.domain.models.role import SUPER_ADMIN_ROLE
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.infrastructure.repositories.speaker_repository import SpeakerRepository
from app.infrastructure.repositories.user_repository import UserRepository


class MeetingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.speaker_repository = SpeakerRepository(session)

    async def actor(self, context: RequestContext) -> tuple[int, int]:
        return await self.speaker_repository.actor(context)

    async def lock_tenant(self, tenant_id: int) -> None:
        await self.speaker_repository.lock_tenant(tenant_id)

    async def current_owner_allowed(self, meeting: Meeting) -> bool:
        if not await self.tenant_public_id(meeting.tenant_id):
            return False
        user = await self.session.scalar(
            select(User).where(
                User.user_id == meeting.created_by,
                User.is_active.is_(True),
                User.is_deleted.is_(False),
            )
        )
        if user is None:
            return False
        try:
            authorization = await UserRepository(self.session).authorization_for(user)
        except LookupError:
            return False
        if SUPER_ADMIN_ROLE in authorization.roles:
            return True
        required = {"meeting_analysis:run"}
        if meeting.auto_enroll:
            required.add("speaker_profiles:write")
        return user.home_tenant_id == meeting.tenant_id and required.issubset(
            authorization.permissions
        )

    async def meeting(
        self, tenant_id: int, public_id: str, *, active: bool = True
    ) -> Meeting | None:
        query = select(Meeting).where(
            Meeting.tenant_id == tenant_id, Meeting.public_id == public_id
        )
        if active:
            query = query.where(Meeting.is_deleted.is_(False))
        return (await self.session.scalars(query)).one_or_none()

    async def by_key(self, tenant_id: int, key: str) -> Meeting | None:
        return (
            await self.session.scalars(
                select(Meeting).where(
                    Meeting.tenant_id == tenant_id, Meeting.idempotency_key == key
                )
            )
        ).one_or_none()

    async def list_meetings(
        self, tenant_id: int, offset: int, limit: int
    ) -> tuple[list[Meeting], int]:
        filters = (Meeting.tenant_id == tenant_id, Meeting.is_deleted.is_(False))
        total = await self.session.scalar(select(func.count()).select_from(Meeting).where(*filters))
        rows = await self.session.scalars(
            select(Meeting)
            .where(*filters)
            .order_by(Meeting.created_at.desc(), Meeting.meeting_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(rows), int(total or 0)

    async def upload_parts(self, tenant_id: int, meeting_id: int) -> list[MeetingUploadPart]:
        return list(
            await self.session.scalars(
                select(MeetingUploadPart)
                .where(
                    MeetingUploadPart.tenant_id == tenant_id,
                    MeetingUploadPart.meeting_id == meeting_id,
                    MeetingUploadPart.is_deleted.is_(False),
                )
                .order_by(MeetingUploadPart.index)
                .limit(512)
            )
        )

    async def upload_part(
        self, tenant_id: int, meeting_id: int, index: int
    ) -> MeetingUploadPart | None:
        return (
            await self.session.scalars(
                select(MeetingUploadPart).where(
                    MeetingUploadPart.tenant_id == tenant_id,
                    MeetingUploadPart.meeting_id == meeting_id,
                    MeetingUploadPart.index == index,
                    MeetingUploadPart.is_deleted.is_(False),
                )
            )
        ).one_or_none()

    async def retained_bytes(self, tenant_id: int) -> int:
        # Reserve expected bytes even during upload and until removed, including soft deletes.
        result = await self.session.scalar(
            select(func.coalesce(func.sum(Meeting.size_bytes), 0)).where(
                Meeting.tenant_id == tenant_id, Meeting.source_removed_at.is_(None)
            )
        )
        return int(result or 0)

    async def active_upload_count(self, tenant_id: int) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Meeting)
            .where(
                Meeting.tenant_id == tenant_id,
                Meeting.status == "uploading",
                Meeting.is_deleted.is_(False),
                Meeting.source_removed_at.is_(None),
            )
        )
        return int(result or 0)

    async def chunks(self, tenant_id: int, meeting_id: int) -> list[MeetingChunk]:
        return list(
            await self.session.scalars(
                select(MeetingChunk)
                .where(
                    MeetingChunk.tenant_id == tenant_id,
                    MeetingChunk.meeting_id == meeting_id,
                    MeetingChunk.is_deleted.is_(False),
                )
                .order_by(MeetingChunk.index)
                .limit(240)
            )
        )

    async def chunk(self, tenant_id: int, meeting_id: int, index: int) -> MeetingChunk | None:
        return (
            await self.session.scalars(
                select(MeetingChunk).where(
                    MeetingChunk.tenant_id == tenant_id,
                    MeetingChunk.meeting_id == meeting_id,
                    MeetingChunk.index == index,
                    MeetingChunk.is_deleted.is_(False),
                )
            )
        ).one_or_none()

    async def speakers(
        self, tenant_id: int, meeting_id: int, offset: int, limit: int
    ) -> tuple[list[MeetingSpeaker], int]:
        filters = (
            MeetingSpeaker.tenant_id == tenant_id,
            MeetingSpeaker.meeting_id == meeting_id,
            MeetingSpeaker.is_deleted.is_(False),
        )
        total = await self.session.scalar(
            select(func.count()).select_from(MeetingSpeaker).where(*filters)
        )
        rows = await self.session.scalars(
            select(MeetingSpeaker)
            .where(*filters)
            .order_by(MeetingSpeaker.ordinal)
            .offset(offset)
            .limit(limit)
        )
        return list(rows), int(total or 0)

    async def speaker(
        self, tenant_id: int, meeting_id: int, public_id: str
    ) -> MeetingSpeaker | None:
        return (
            await self.session.scalars(
                select(MeetingSpeaker).where(
                    MeetingSpeaker.tenant_id == tenant_id,
                    MeetingSpeaker.meeting_id == meeting_id,
                    MeetingSpeaker.public_id == public_id,
                    MeetingSpeaker.is_deleted.is_(False),
                )
            )
        ).one_or_none()

    async def speaker_by_id(
        self, tenant_id: int, meeting_id: int, speaker_id: int
    ) -> MeetingSpeaker | None:
        return (
            await self.session.scalars(
                select(MeetingSpeaker).where(
                    MeetingSpeaker.tenant_id == tenant_id,
                    MeetingSpeaker.meeting_id == meeting_id,
                    MeetingSpeaker.meeting_speaker_id == speaker_id,
                    MeetingSpeaker.is_deleted.is_(False),
                )
            )
        ).one_or_none()

    async def transcript(
        self, tenant_id: int, meeting_id: int, offset: int, limit: int
    ) -> tuple[list[MeetingTranscript], int]:
        filters = (
            MeetingTranscript.tenant_id == tenant_id,
            MeetingTranscript.meeting_id == meeting_id,
            MeetingTranscript.is_deleted.is_(False),
        )
        total = await self.session.scalar(
            select(func.count()).select_from(MeetingTranscript).where(*filters)
        )
        rows = await self.session.scalars(
            select(MeetingTranscript)
            .where(*filters)
            .order_by(MeetingTranscript.ordinal)
            .offset(offset)
            .limit(limit)
        )
        return list(rows), int(total or 0)

    async def claim(self, now: datetime) -> Meeting | None:
        return (
            await self.session.scalars(
                select(Meeting)
                .where(
                    Meeting.is_deleted.is_(False),
                    Meeting.source_removed_at.is_(None),
                    or_(
                        Meeting.status == "queued",
                        and_(
                            Meeting.status.in_(["running", "finalizing"]),
                            Meeting.lease_expires_at <= now,
                        ),
                    ),
                )
                .order_by(
                    func.coalesce(Meeting.lease_expires_at, Meeting.created_at),
                    Meeting.meeting_id,
                )
                .with_for_update(skip_locked=True)
                .limit(1)
            )
        ).one_or_none()

    async def fenced(self, meeting_id: int, token: int, now: datetime) -> Meeting | None:
        return (
            await self.session.scalars(
                select(Meeting)
                .where(
                    Meeting.meeting_id == meeting_id,
                    Meeting.claim_token == token,
                    Meeting.status.in_(["running", "finalizing"]),
                    Meeting.lease_expires_at > now,
                    Meeting.is_deleted.is_(False),
                    Meeting.source_removed_at.is_(None),
                )
                .with_for_update()
            )
        ).one_or_none()

    async def tenant_public_id(self, tenant_id: int) -> str | None:
        public_id = await self.session.scalar(
            select(Tenant.public_id).where(
                Tenant.tenant_id == tenant_id,
                Tenant.is_deleted.is_(False),
                Tenant.is_active.is_(True),
            )
        )
        return str(public_id) if public_id is not None else None

    async def pending_speaker(self, tenant_id: int, meeting_id: int) -> MeetingSpeaker | None:
        return (
            await self.session.scalars(
                select(MeetingSpeaker)
                .where(
                    MeetingSpeaker.tenant_id == tenant_id,
                    MeetingSpeaker.meeting_id == meeting_id,
                    MeetingSpeaker.is_deleted.is_(False),
                    MeetingSpeaker.props["memory_completed"].as_boolean().is_distinct_from(True),
                )
                .order_by(MeetingSpeaker.ordinal)
                .limit(1)
            )
        ).one_or_none()

    async def next_transcript_ordinal(self, tenant_id: int, meeting_id: int) -> int:
        result = await self.session.scalar(
            select(func.max(MeetingTranscript.ordinal)).where(
                MeetingTranscript.tenant_id == tenant_id, MeetingTranscript.meeting_id == meeting_id
            )
        )
        return int(result) + 1 if result is not None else 0

    async def speaker_profile_assignments(
        self, tenant_id: int, meeting_id: int, profile_id: int
    ) -> list[MeetingSpeaker]:
        return list(
            await self.session.scalars(
                select(MeetingSpeaker).where(
                    MeetingSpeaker.tenant_id == tenant_id,
                    MeetingSpeaker.meeting_id == meeting_id,
                    MeetingSpeaker.profile_id == profile_id,
                    MeetingSpeaker.is_deleted.is_(False),
                )
            )
        )
