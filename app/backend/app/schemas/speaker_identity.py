"""Public speaker pilot contracts. No vector or private file path is exposed."""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.speaker_identity import normalize_name


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpeakerJobCreate(StrictRequest):
    recording_public_id: UUID
    purpose: Literal["enroll", "identify"]
    name: str | None = Field(default=None, max_length=120)
    profile_public_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_name(value)
        if not normalized:
            raise ValueError("Name cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        count = int(self.name is not None) + int(self.profile_public_id is not None)
        if (self.purpose == "enroll" and count != 1) or (self.purpose == "identify" and count != 0):
            raise ValueError("Enrollment requires one target; identification forbids targets")
        return self


class SpeakerProfileRename(StrictRequest):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        normalized = normalize_name(value)
        if not normalized:
            raise ValueError("Name cannot be blank")
        return normalized


class RecordingResponse(BaseModel):
    public_id: str
    sha256: str
    size_bytes: int
    format: Literal["WAV", "FLAC"]
    duration_seconds: float
    created_at: datetime


class SpeakerProfileResponse(BaseModel):
    public_id: str
    name: str
    sample_count: int
    model_id: str
    model_revision: str
    created_at: datetime
    updated_at: datetime


class MatchPolicyResponse(BaseModel):
    match_threshold: float
    new_threshold: float
    margin: float


class SpeakerResult(BaseModel):
    decision: Literal["enrolled", "recognized", "unknown", "ambiguous"]
    profile_public_id: str | None = None
    profile_name: str | None = None
    profile_deleted: bool = False
    similarity: float | None = None
    runner_up_similarity: float | None = None
    speech_seconds: float
    windows_count: int
    model_id: str
    model_revision: str
    device: str
    reason: str
    policy: MatchPolicyResponse


class JobError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: JobError


class SpeakerJobResponse(BaseModel):
    public_id: str
    purpose: Literal["enroll", "identify"]
    status: Literal["queued", "running", "succeeded", "failed"]
    recording_public_id: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    result: SpeakerResult | None
    error: JobError | None


class SpeakerProfilePage(BaseModel):
    items: list[SpeakerProfileResponse]
    total: int
    offset: int
    limit: int


class SpeakerJobPage(BaseModel):
    items: list[SpeakerJobResponse]
    total: int
    offset: int
    limit: int
