"""Public immutable lexical-review result; original audio coordinates are not replaced."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TranscriptCorrectionEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    start_char: int = Field(ge=0, le=1024)
    end_char: int = Field(gt=0, le=1024)
    original: str = Field(min_length=1, max_length=64)
    replacement: str = Field(min_length=1, max_length=64)


class TranscriptCorrectionPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transcript_public_id: UUID
    source_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    original_text: str = Field(min_length=1, max_length=1024)
    suggested_text: str = Field(min_length=1, max_length=1216)
    status: Literal["unchanged", "suggested", "rejected"]
    edits: list[TranscriptCorrectionEdit] = Field(max_length=3)
    rejected_count: int = Field(ge=0, le=3)
    model_name: str = Field(min_length=1, max_length=200)
    model_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_version: Literal["tr-context-words-v1"]
