"""Selected-model review and explicit, source-bound user approval of text versions."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.request_context import RequestContext
from app.domain.models.transcript_revision import MeetingTranscriptRevision
from app.domain.transcript_suggestions import (
    MAX_MODEL_OUTPUT_CHARACTERS,
    SUGGESTION_POLICY,
    project_model_output,
)
from app.infrastructure.correction_receipts import CorrectionReceiptSigner
from app.infrastructure.repositories.meeting_repository import MeetingRepository
from app.infrastructure.repositories.transcript_revision_repository import (
    TranscriptRevisionRepository,
)
from app.schemas.transcript_correction import TranscriptCorrectionEdit
from app.schemas.transcript_suggestions import (
    InstalledReviewModelResponse,
    ReviewModelList,
    SavedTranscriptCorrection,
    TranscriptCorrectionSelection,
    TranscriptCorrectionSuggestion,
    TranscriptSuggestionProposal,
)
from app.services.speaker_ports import SpeakerError
from app.services.transcript_correction_ports import ModelSelection, TranscriptSuggestionPort
from app.services.transcript_revision_ports import CorrectionSaveProof, ProofEdit
from app.services.transcript_source import ReviewSnapshot, TranscriptSourceReader


def saved_correction_response(row: MeetingTranscriptRevision) -> SavedTranscriptCorrection:
    return SavedTranscriptCorrection(
        public_id=UUID(row.public_id),
        revision=row.revision,
        corrected_text=row.corrected_text,
        source_text_sha256=row.source_text_sha256,
        edits=[TranscriptCorrectionEdit.model_validate(edit) for edit in row.edits],
        model_name=row.model_name,
        model_digest=row.model_digest,
        policy_version=SUGGESTION_POLICY,
        saved_at=row.created_at,
    )


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TranscriptSuggestionService:
    def __init__(
        self,
        repository: MeetingRepository,
        revisions: TranscriptRevisionRepository,
        model: TranscriptSuggestionPort,
        receipts: CorrectionReceiptSigner,
    ) -> None:
        self.repository, self.revisions, self.model, self.receipts = (
            repository,
            revisions,
            model,
            receipts,
        )
        self.source = TranscriptSourceReader(repository)

    @staticmethod
    def _require_permissions(context: RequestContext) -> None:
        if not context.has_permission("meeting_analysis:read") or not context.has_permission(
            "meeting_analysis:run"
        ):
            raise SpeakerError("forbidden", 403)

    async def _actor_allowed(self, context: RequestContext) -> None:
        try:
            tenant_id, actor_id = await self.repository.actor(context)
            if not await self.repository.current_reviewer_allowed(context, tenant_id, actor_id):
                raise SpeakerError("forbidden", 403)
        finally:
            await self.repository.session.rollback()

    async def models(self, context: RequestContext) -> ReviewModelList:
        self._require_permissions(context)
        try:
            async with asyncio.timeout(100):
                await self._actor_allowed(context)
                models = await self.model.list_models()
                await self._actor_allowed(context)
                return ReviewModelList(
                    items=[InstalledReviewModelResponse.model_validate(model) for model in models]
                )
        except TimeoutError:
            raise SpeakerError("text_review_timeout", 504) from None

    async def _snapshot(
        self, context: RequestContext, meeting_id: str, transcript_id: str
    ) -> tuple[ReviewSnapshot, int]:
        try:
            source = await self.source.read(context, meeting_id, transcript_id)
            revision = await self.revisions.number(
                source.tenant_id, source.meeting_id, source.transcript_id
            )
            return source, revision
        finally:
            await self.repository.session.rollback()

    async def suggest(
        self,
        context: RequestContext,
        meeting_id: str,
        transcript_id: str,
        selection: TranscriptCorrectionSelection,
    ) -> TranscriptCorrectionSuggestion:
        self._require_permissions(context)
        try:
            async with asyncio.timeout(100):
                source, expected_revision = await self._snapshot(context, meeting_id, transcript_id)
                result = await self.model.suggest(
                    source.context, ModelSelection(selection.model_name, selection.model_digest)
                )
                if (
                    result.model_name != selection.model_name
                    or result.model_digest != selection.model_digest
                ):
                    raise SpeakerError("text_review_model_mismatch", 503)
                try:
                    current, _ = await self._snapshot(context, meeting_id, transcript_id)
                except SpeakerError as exc:
                    if exc.code in {"meeting_state_conflict", "text_review_context_limit"}:
                        raise SpeakerError("transcript_changed", 409) from None
                    raise
                if current.fingerprint != source.fingerprint:
                    raise SpeakerError("transcript_changed", 409)
                model_output = result.model_output.encode("utf-8", "backslashreplace").decode(
                    "utf-8"
                )
                truncated = (
                    result.model_output_truncated or len(model_output) > MAX_MODEL_OUTPUT_CHARACTERS
                )
                model_output = model_output[:MAX_MODEL_OUTPUT_CHARACTERS]
                projection = project_model_output(
                    source.context.target_text, model_output, truncated=truncated
                )
                source_hash = _text_hash(source.context.target_text)
                save_token, expires_at = None, None
                if projection.saveable:
                    now = int(datetime.now(UTC).timestamp())
                    proof = CorrectionSaveProof(
                        preview_id=uuid4(),
                        actor_public_id=UUID(str(context.subject)),
                        tenant_public_id=UUID(str(context.tenant_id)),
                        meeting_public_id=UUID(meeting_id),
                        transcript_public_id=UUID(transcript_id),
                        source_text_sha256=source_hash,
                        context_sha256=source.fingerprint,
                        expected_revision=expected_revision,
                        edits=tuple(
                            ProofEdit(
                                start_char=proposal.start_char,
                                end_char=proposal.end_char,
                                original=proposal.original,
                                replacement=proposal.replacement,
                            )
                            for proposal in sorted(
                                projection.proposals,
                                key=lambda item: (
                                    item.start_char if item.start_char is not None else -1
                                ),
                            )
                            if proposal.start_char is not None and proposal.end_char is not None
                        ),
                        model_name=result.model_name,
                        model_digest=result.model_digest,
                        policy_version=SUGGESTION_POLICY,
                        issued_at=now,
                        expires_at=now + 900,
                    )
                    save_token = self.receipts.sign(proof)
                    expires_at = datetime.fromtimestamp(proof.expires_at, UTC)
                return TranscriptCorrectionSuggestion(
                    transcript_public_id=UUID(transcript_id),
                    source_text_sha256=source_hash,
                    original_text=source.context.target_text,
                    suggested_text=projection.suggested_text,
                    proposals=[
                        TranscriptSuggestionProposal(
                            original=proposal.original.encode("utf-8", "backslashreplace").decode(
                                "utf-8"
                            )[:64],
                            replacement=proposal.replacement.encode(
                                "utf-8", "backslashreplace"
                            ).decode("utf-8")[:64],
                            start_char=proposal.start_char,
                            end_char=proposal.end_char,
                            assessment=proposal.assessment,
                            reason=proposal.reason,
                        )
                        for proposal in projection.proposals
                    ],
                    model_output=model_output,
                    model_output_truncated=truncated,
                    status=projection.status,
                    model_name=result.model_name,
                    model_digest=result.model_digest,
                    policy_version=SUGGESTION_POLICY,
                    expected_revision=expected_revision,
                    save_token=save_token,
                    expires_at=expires_at,
                )
        except TimeoutError:
            raise SpeakerError("text_review_timeout", 504) from None

    async def save(
        self, context: RequestContext, meeting_id: str, transcript_id: str, token: str
    ) -> SavedTranscriptCorrection:
        self._require_permissions(context)
        proof = self.receipts.verify(token, now=datetime.now(UTC))
        if (
            str(proof.actor_public_id) != str(context.subject)
            or str(proof.tenant_public_id) != str(context.tenant_id)
            or str(proof.meeting_public_id) != meeting_id
            or str(proof.transcript_public_id) != transcript_id
        ):
            raise SpeakerError("invalid_correction_token", 422)
        tenant_id, _ = await self.repository.actor(context)
        await self.repository.lock_tenant(tenant_id)
        await self.revisions.lock_source(tenant_id, meeting_id, transcript_id)
        try:
            source = await self.source.read(context, meeting_id, transcript_id)
        except SpeakerError as exc:
            if exc.code in {"meeting_state_conflict", "text_review_context_limit"}:
                raise SpeakerError("transcript_changed", 409) from None
            raise
        if (
            proof.source_text_sha256 != _text_hash(source.context.target_text)
            or proof.context_sha256 != source.fingerprint
        ):
            raise SpeakerError("transcript_changed", 409)
        existing = await self.revisions.by_preview(
            source.tenant_id, source.meeting_id, source.transcript_id, str(proof.preview_id)
        )
        if existing is not None:
            return saved_correction_response(existing)
        if (
            await self.revisions.number(source.tenant_id, source.meeting_id, source.transcript_id)
            != proof.expected_revision
        ):
            raise SpeakerError("correction_conflict", 409)
        raw = json.dumps(
            {
                "edits": [
                    {"original": edit.original, "replacement": edit.replacement}
                    for edit in proof.edits
                ]
            },
            ensure_ascii=False,
        )
        projected = project_model_output(source.context.target_text, raw)
        if not projected.saveable or any(
            (proposal.start_char, proposal.end_char) != (edit.start_char, edit.end_char)
            for proposal, edit in zip(projected.proposals, proof.edits, strict=True)
        ):
            raise SpeakerError("invalid_correction_token", 422)
        revision = MeetingTranscriptRevision(
            tenant_id=source.tenant_id,
            meeting_id=source.meeting_id,
            meeting_transcript_id=source.transcript_id,
            revision=proof.expected_revision + 1,
            preview_id=str(proof.preview_id),
            source_text_sha256=proof.source_text_sha256,
            context_sha256=proof.context_sha256,
            corrected_text=projected.suggested_text,
            edits=[edit.model_dump() for edit in proof.edits],
            model_name=proof.model_name,
            model_digest=proof.model_digest,
            policy_version=proof.policy_version,
            created_by=source.actor_id,
            updated_by=source.actor_id,
        )
        await self.revisions.append(revision)
        return saved_correction_response(revision)
