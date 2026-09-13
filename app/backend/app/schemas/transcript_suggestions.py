"""Selected-model proposals and explicit user-approved transcript version contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.transcript_suggestions import ProposalAssessment, ProposalReason, SuggestionStatus
from app.schemas.transcript_correction import TranscriptCorrectionEdit


class InstalledReviewModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    name: str = Field(min_length=1, max_length=200)
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0)
    selectable: bool
    unavailable_reason: (
        Literal[
            "remote_model",
            "not_language_model",
            "model_changed",
            "default_changed",
            "metadata_unavailable",
        ]
        | None
    )
    is_default: bool


class ReviewModelList(BaseModel):
    items: list[InstalledReviewModelResponse] = Field(max_length=100)


class TranscriptCorrectionSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_name: str = Field(min_length=1, max_length=200)
    model_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class TranscriptSuggestionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    original: str = Field(min_length=1, max_length=64)
    replacement: str = Field(min_length=1, max_length=64)
    start_char: int | None = Field(ge=0, le=1024)
    end_char: int | None = Field(gt=0, le=1024)
    assessment: ProposalAssessment
    reason: ProposalReason | None


class TranscriptCorrectionSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transcript_public_id: UUID
    source_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    original_text: str = Field(min_length=1, max_length=1024)
    suggested_text: str = Field(min_length=1, max_length=1216)
    proposals: list[TranscriptSuggestionProposal] = Field(max_length=3)
    model_output: str = Field(max_length=8192)
    model_output_truncated: bool
    status: SuggestionStatus
    model_name: str = Field(min_length=1, max_length=200)
    model_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_version: Literal["tr-context-words-v2"]
    expected_revision: int = Field(ge=0)
    save_token: str | None = Field(max_length=32768)
    expires_at: datetime | None


class TranscriptCorrectionSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    save_token: str = Field(min_length=1, max_length=32768)


class SavedTranscriptCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    public_id: UUID
    revision: int = Field(ge=1)
    corrected_text: str = Field(min_length=1, max_length=1216)
    source_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    edits: list[TranscriptCorrectionEdit] = Field(min_length=1, max_length=3)
    model_name: str = Field(min_length=1, max_length=200)
    model_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_version: Literal["tr-context-words-v2"]
    saved_at: datetime
