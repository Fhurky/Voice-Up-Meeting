"""Public uploaded-meeting contracts contain no source paths or biometric vectors."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.meeting import MAX_SOURCE_BYTES, UPLOAD_PART_BYTES
from app.domain.speaker_identity import normalize_name
from app.schemas.transcript_suggestions import SavedTranscriptCorrection

MeetingStatus = Literal[
    "uploading", "queued", "running", "finalizing", "succeeded", "failed", "cancelled"
]
MeetingDecision = Literal["profile_pending", "recognized", "enrolled", "ambiguous"]
MeetingLanguage = Literal["tr", "en", "auto"]
MAX_PARTICIPANTS = 50
MAX_SUBJECT_CHARACTERS = 500
MAX_QUESTIONS = 20
MAX_QUESTION_CHARACTERS = 500


class MeetingParticipantResponse(BaseModel):
    """A listed profile; the name is hidden once the profile is deleted."""

    profile_public_id: UUID
    name: str | None


class MeetingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    format: Literal["WAV", "FLAC"]
    size_bytes: int = Field(gt=0, le=MAX_SOURCE_BYTES, strict=True)
    language: MeetingLanguage = "tr"
    participant_count: int | None = Field(default=None, ge=1, le=1000, strict=True)
    expected_speakers: int | None = Field(default=None, ge=1, le=1000, strict=True)
    auto_enroll: bool = False
    participant_profile_ids: list[UUID] = Field(default_factory=list, max_length=MAX_PARTICIPANTS)
    subject: str | None = Field(default=None, max_length=MAX_SUBJECT_CHARACTERS)
    questions: list[str] = Field(default_factory=list, max_length=MAX_QUESTIONS)

    @field_validator("subject")
    @classmethod
    def subject_text(cls, value: str | None) -> str | None:
        return normalize_name(value) or None if value is not None else None

    @field_validator("questions")
    @classmethod
    def distinct_questions(cls, value: list[str]) -> list[str]:
        questions = [normalize_name(question) for question in value]
        if any(not 1 <= len(question) <= MAX_QUESTION_CHARACTERS for question in questions):
            raise ValueError("A question must contain between 1 and 500 characters")
        if len({question.casefold() for question in questions}) != len(questions):
            raise ValueError("Questions must be distinct")
        return questions

    @field_validator("participant_profile_ids")
    @classmethod
    def unique_participants(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Participants must be unique")
        # A canonical order keeps the idempotency fingerprint independent of selection order.
        return sorted(value, key=str)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = normalize_name(value)
        if not value:
            raise ValueError("A title is required")
        return value

    @model_validator(mode="after")
    def count_relationship(self) -> "MeetingCreate":
        if (
            self.participant_count is not None
            and self.expected_speakers is not None
            and self.expected_speakers > self.participant_count
        ):
            raise ValueError("Speaking count cannot exceed participant count")
        if (
            self.participant_count is not None
            and len(self.participant_profile_ids) > self.participant_count
        ):
            raise ValueError("Listed participants cannot exceed participant count")
        return self


class MeetingProcessingMode(BaseModel):
    processing_device: Literal["gpu", "cpu", "unknown"]


class MeetingProcessorState(BaseModel):
    device: Literal["gpu", "cpu"]
    gpu_available: bool
    cpu_available: bool
    switching: bool
    last_error: Literal["processor_switch_failed"] | None


class MeetingProcessorChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device: Literal["gpu", "cpu"]


class MeetingQuestionResponse(BaseModel):
    public_id: UUID
    text: str


class MeetingResponse(BaseModel):
    public_id: UUID
    title: str
    status: MeetingStatus
    format: Literal["WAV", "FLAC"]
    size_bytes: int
    uploaded_bytes: int
    upload_part_bytes: int = UPLOAD_PART_BYTES
    next_upload_index: int
    sha256: str | None
    duration_seconds: float | None
    processed_seconds: float
    completed_chunks: int
    total_chunks: int
    language: MeetingLanguage
    participant_count: int | None
    expected_speakers: int | None
    auto_enroll: bool
    participants: list[MeetingParticipantResponse]
    subject: str | None
    questions: list[MeetingQuestionResponse]
    observed_speakers: int
    count_mismatch: bool
    error_code: str | None
    source_available: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class MeetingPage(BaseModel):
    items: list[MeetingResponse]
    total: int
    offset: int
    limit: int


class MeetingUploadPartResponse(BaseModel):
    index: int
    size_bytes: int
    sha256: str


class MeetingUploadManifest(BaseModel):
    meeting_public_id: UUID
    parts: list[MeetingUploadPartResponse]
    uploaded_bytes: int
    next_index: int


class MeetingSpeakerResponse(BaseModel):
    public_id: UUID
    ordinal: int
    display_name: str | None
    profile_public_id: UUID | None
    profile_name: str | None
    profile_deleted: bool
    decision: MeetingDecision
    reason: str
    speech_seconds: float
    version: int
    profile_updated_at: datetime | None


class MeetingSpeakerPage(BaseModel):
    items: list[MeetingSpeakerResponse]
    total: int
    offset: int
    limit: int


class MeetingSpeakerRename(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    version: int = Field(ge=1, strict=True)
    profile_updated_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = normalize_name(value)
        if not value:
            raise ValueError("A name is required")
        return value


class MeetingTranscriptResponse(BaseModel):
    public_id: UUID
    ordinal: int
    speaker_public_id: UUID | None
    speaker_ordinal: int | None
    speaker_name: str | None
    profile_public_id: UUID | None
    source_participant_id: str | None = None
    start_seconds: float
    end_seconds: float
    text: str
    language: str
    overlap: bool
    uncertain: bool
    correction: SavedTranscriptCorrection | None = None


class MeetingTranscriptPage(BaseModel):
    items: list[MeetingTranscriptResponse]
    total: int
    offset: int
    limit: int
    provisional: bool


class MeetingSpeakerTurnResponse(BaseModel):
    """One attributed speech interval; a null speaker is speech not linked to a meeting speaker."""

    start_seconds: float
    end_seconds: float
    speaker_public_id: UUID | None


class MeetingSpeakerTurnPage(BaseModel):
    items: list[MeetingSpeakerTurnResponse]
    total: int
    offset: int
    limit: int
    provisional: bool
