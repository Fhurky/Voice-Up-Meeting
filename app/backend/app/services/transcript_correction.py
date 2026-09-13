"""Short tenant-scoped snapshots around local inference; no source writes or durable suggestions."""

import asyncio
import hashlib
from uuid import UUID

from app.core.request_context import RequestContext
from app.domain.transcript_correction import (
    POLICY_VERSION,
    validate_edits,
)
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.schemas.transcript_correction import TranscriptCorrectionEdit, TranscriptCorrectionPreview
from app.services.speaker_ports import SpeakerError
from app.services.transcript_correction_ports import TranscriptCorrectionPort
from app.services.transcript_source import ReviewSnapshot, TranscriptSourceReader


class TranscriptCorrectionService:
    def __init__(self, repository: MeetingRepository, model: TranscriptCorrectionPort) -> None:
        self.repository, self.model = repository, model

    async def _snapshot(
        self, context: RequestContext, meeting_public_id: str, transcript_public_id: str
    ) -> ReviewSnapshot:
        return await TranscriptSourceReader(self.repository).released(
            context, meeting_public_id, transcript_public_id
        )

    async def preview(
        self, context: RequestContext, meeting_public_id: str, transcript_public_id: str
    ) -> TranscriptCorrectionPreview:
        if not context.has_permission("meeting_analysis:read") or not context.has_permission(
            "meeting_analysis:run"
        ):
            raise SpeakerError("forbidden", 403)
        try:
            async with asyncio.timeout(100.0):
                snapshot = await self._snapshot(context, meeting_public_id, transcript_public_id)
                result = await self.model.review(snapshot.context)
                try:
                    current = await self._snapshot(context, meeting_public_id, transcript_public_id)
                except SpeakerError as exc:
                    if exc.code in {"meeting_state_conflict", "text_review_context_limit"}:
                        raise SpeakerError("transcript_changed", 409) from None
                    raise
                if current.fingerprint != snapshot.fingerprint:
                    raise SpeakerError("transcript_changed", 409)
                decision = validate_edits(snapshot.context.target_text, result.edits)
                return TranscriptCorrectionPreview(
                    transcript_public_id=UUID(snapshot.transcript_public_id),
                    source_text_sha256=hashlib.sha256(
                        snapshot.context.target_text.encode("utf-8")
                    ).hexdigest(),
                    original_text=snapshot.context.target_text,
                    suggested_text=decision.suggested_text,
                    status=decision.status,
                    edits=[
                        TranscriptCorrectionEdit.model_validate(edit) for edit in decision.edits
                    ],
                    rejected_count=decision.rejected_count,
                    model_name=result.model_name,
                    model_digest=result.model_digest,
                    policy_version=POLICY_VERSION,
                )
        except TimeoutError:
            raise SpeakerError("text_review_timeout", 504) from None
