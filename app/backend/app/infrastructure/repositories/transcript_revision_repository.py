"""Same-tenant revision reads and short serialized approval writes."""

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.meeting import Meeting, MeetingTranscript
from app.domain.models.transcript_revision import MeetingTranscriptRevision


class TranscriptRevisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def number(self, tenant_id: int, meeting_id: int, transcript_id: int) -> int:
        value = await self.session.scalar(
            select(func.max(MeetingTranscriptRevision.revision)).where(
                MeetingTranscriptRevision.tenant_id == tenant_id,
                MeetingTranscriptRevision.meeting_id == meeting_id,
                MeetingTranscriptRevision.meeting_transcript_id == transcript_id,
            )
        )
        return int(value or 0)

    async def by_preview(
        self, tenant_id: int, meeting_id: int, transcript_id: int, preview_id: str
    ) -> MeetingTranscriptRevision | None:
        return (
            await self.session.scalars(
                select(MeetingTranscriptRevision).where(
                    MeetingTranscriptRevision.tenant_id == tenant_id,
                    MeetingTranscriptRevision.meeting_id == meeting_id,
                    MeetingTranscriptRevision.meeting_transcript_id == transcript_id,
                    MeetingTranscriptRevision.preview_id == preview_id,
                    MeetingTranscriptRevision.is_deleted.is_(False),
                )
            )
        ).one_or_none()

    async def lock_source(
        self, tenant_id: int, meeting_public_id: str, transcript_public_id: str
    ) -> None:
        meeting = await self.session.scalar(
            select(Meeting.meeting_id)
            .where(Meeting.tenant_id == tenant_id, Meeting.public_id == meeting_public_id)
            .with_for_update()
        )
        if meeting is not None:
            await self.session.scalar(
                select(MeetingTranscript.meeting_transcript_id)
                .where(
                    MeetingTranscript.tenant_id == tenant_id,
                    MeetingTranscript.meeting_id == meeting,
                    MeetingTranscript.public_id == transcript_public_id,
                )
                .with_for_update()
            )

    async def latest_for_sources(
        self, tenant_id: int, meeting_id: int, sources: dict[int, str]
    ) -> dict[int, MeetingTranscriptRevision]:
        if not sources:
            return {}
        rows = await self.session.scalars(
            select(MeetingTranscriptRevision)
            .where(
                MeetingTranscriptRevision.tenant_id == tenant_id,
                MeetingTranscriptRevision.meeting_id == meeting_id,
                MeetingTranscriptRevision.is_deleted.is_(False),
                tuple_(
                    MeetingTranscriptRevision.meeting_transcript_id,
                    MeetingTranscriptRevision.source_text_sha256,
                ).in_(list(sources.items())),
            )
            .distinct(MeetingTranscriptRevision.meeting_transcript_id)
            .order_by(
                MeetingTranscriptRevision.meeting_transcript_id,
                MeetingTranscriptRevision.revision.desc(),
            )
        )
        return {row.meeting_transcript_id: row for row in rows}

    async def append(self, row: MeetingTranscriptRevision) -> None:
        self.session.add(row)
        await self.session.flush()
