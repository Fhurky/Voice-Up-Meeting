"""Shared source snapshots for transient review and short user-approval transactions."""

import hashlib
import json
from dataclasses import dataclass

from app.core.request_context import RequestContext
from app.domain.models.meeting import MeetingTranscript
from app.domain.transcript_correction import MAX_CONTEXT_CHARACTERS, MAX_TARGET_CHARACTERS
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.services.speaker_ports import SpeakerError
from app.services.transcript_correction_ports import CorrectionContext


@dataclass(frozen=True, slots=True)
class ReviewSnapshot:
    transcript_public_id: str
    context: CorrectionContext
    fingerprint: str
    tenant_id: int
    actor_id: int
    meeting_id: int
    transcript_id: int


def _identity(
    row: MeetingTranscript,
) -> tuple[str, int, str, str, float, float, int | None, bool, bool]:
    return (
        row.public_id,
        row.ordinal,
        row.text,
        row.language,
        row.start,
        row.end,
        row.meeting_speaker_id,
        row.overlap,
        row.uncertain,
    )


class TranscriptSourceReader:
    def __init__(self, repository: MeetingRepository) -> None:
        self.repository = repository

    async def released(
        self, context: RequestContext, meeting_public_id: str, transcript_public_id: str
    ) -> ReviewSnapshot:
        try:
            return await self.read(context, meeting_public_id, transcript_public_id)
        finally:
            await self.repository.session.rollback()

    async def read(
        self, context: RequestContext, meeting_public_id: str, transcript_public_id: str
    ) -> ReviewSnapshot:
        tenant_id, actor_id = await self.repository.actor(context)
        meeting = await self.repository.meeting(tenant_id, meeting_public_id)
        if meeting is None:
            raise SpeakerError("not_found", 404)
        target = await self.repository.transcript_for_review(
            tenant_id, meeting.meeting_id, transcript_public_id
        )
        if target is None:
            raise SpeakerError("not_found", 404)
        if not await self.repository.current_reviewer_allowed(context, tenant_id, actor_id):
            raise SpeakerError("forbidden", 403)
        if meeting.status != "succeeded":
            raise SpeakerError("meeting_state_conflict", 409)
        if not 1 <= len(target.text) <= MAX_TARGET_CHARACTERS:
            raise SpeakerError("text_review_context_limit", 422)
        before = await self.repository.transcript_neighbors(
            tenant_id, meeting.meeting_id, target.ordinal, before=True
        )
        after = await self.repository.transcript_neighbors(
            tenant_id, meeting.meeting_id, target.ordinal, before=False
        )
        selected_before: list[MeetingTranscript] = []
        selected_after: list[MeetingTranscript] = []
        remaining = MAX_CONTEXT_CHARACTERS - len(target.text)
        closed = [False, False]
        for index in range(3):
            for side, source, selected in (
                (0, before, selected_before),
                (1, after, selected_after),
            ):
                if closed[side] or index >= len(source):
                    continue
                row = source[index]
                if len(row.text) > remaining:
                    closed[side] = True
                else:
                    selected.append(row)
                    remaining -= len(row.text)
        selected_before.reverse()
        source_context = CorrectionContext(
            target.text,
            tuple(row.text for row in selected_before),
            tuple(row.text for row in selected_after),
            target.language,
        )
        fingerprint = hashlib.sha256(
            json.dumps(
                [_identity(row) for row in [*selected_before, target, *selected_after]],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return ReviewSnapshot(
            target.public_id,
            source_context,
            fingerprint,
            tenant_id,
            actor_id,
            meeting.meeting_id,
            target.meeting_transcript_id,
        )
