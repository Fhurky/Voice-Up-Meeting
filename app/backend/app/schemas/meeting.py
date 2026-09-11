"""Public uploaded-meeting contracts contain no source paths or biometric vectors."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.meeting import MAX_SOURCE_BYTES, UPLOAD_PART_BYTES
from app.domain.speaker_identity import normalize_name

MeetingStatus = Literal[
    "uploading", "queued", "running", "finalizing", "succeeded", "failed", "cancelled"
]
MeetingDecision = Literal["profile_pending", "recognized", "enrolled", "ambiguous"]
MeetingLanguage = Literal["tr", "en", "auto"]


class MeetingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    format: Literal["WAV", "FLAC"]
    size_bytes: int = Field(gt=0, le=MAX_SOURCE_BYTES, strict=True)
    language: MeetingLanguage = "tr"
    participant_count: int | None = Field(default=None, ge=1, le=1000, strict=True)
    expected_speakers: int | None = Field(default=None, ge=1, le=1000, strict=True)
    auto_enroll: bool = True

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
        return self


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


class MeetingTranscriptPage(BaseModel):
    items: list[MeetingTranscriptResponse]
    total: int
    offset: int
    limit: int
    provisional: bool
