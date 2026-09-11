"""Retention orchestration for uploaded meetings, independent of enrolled short samples."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.repositories.meeting_cleanup_repository import (
    TERMINAL_STATUSES,
    MeetingCleanupRepository,
)


class MeetingCleanup:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        storage: MeetingAudioStorage,
        settings: Settings,
    ) -> None:
        self.sessions = sessions
        self.storage = storage
        self.settings = settings

    async def run(self) -> int:
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=self.settings.meeting_result_retention_days)
        async with self.sessions() as session:
            candidates = await MeetingCleanupRepository(session).candidates(now, cutoff)
        count = 0
        for tenant_id, meeting_id in candidates:
            async with self.sessions() as session, session.begin():
                repository = MeetingCleanupRepository(session)
                meeting = await repository.locked(tenant_id, meeting_id)
                if meeting is None:
                    continue
                changed = False
                # Selection can race with upload completion; the locked row is authoritative.
                if meeting.status == "uploading" and meeting.upload_expires_at <= now:
                    meeting.status = "failed"
                    meeting.error_code = "upload_expired"
                    meeting.finished_at = now
                    meeting.source_expires_at = now
                    meeting.claim_token += 1
                    meeting.lease_expires_at = None
                    changed = True
                if meeting.status not in TERMINAL_STATUSES:
                    continue
                if meeting.source_removed_at is None and meeting.source_expires_at <= now:
                    # Missing files are idempotent after an interrupted database commit.
                    await asyncio.to_thread(self.storage.remove, meeting.storage_key)
                    meeting.source_removed_at = now
                    meeting.updated_by = None
                    changed = True
                if meeting.is_deleted or (
                    meeting.finished_at is not None and meeting.finished_at <= cutoff
                ):
                    await repository.scrub_results(meeting, now)
                    changed = True
                count += int(changed)
        return count
