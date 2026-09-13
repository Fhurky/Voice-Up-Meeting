"""Private typed evidence bound to a server-produced source correction."""

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProofEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    start_char: int = Field(ge=0, le=1024, strict=True)
    end_char: int = Field(gt=0, le=1024, strict=True)
    original: str = Field(min_length=1, max_length=64)
    replacement: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        if self.start_char >= self.end_char:
            raise ValueError("invalid_edit_interval")
        return self


class CorrectionSaveProof(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    preview_id: UUID
    actor_public_id: UUID
    tenant_public_id: UUID
    meeting_public_id: UUID
    transcript_public_id: UUID
    source_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    context_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)
    edits: tuple[ProofEdit, ...] = Field(min_length=1, max_length=3)
    model_name: str = Field(min_length=1, max_length=200)
    model_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_version: Literal["tr-context-words-v2"]
    issued_at: int = Field(ge=0, strict=True)
    expires_at: int = Field(gt=0, strict=True)

    @model_validator(mode="after")
    def bounded_lifetime(self) -> Self:
        if self.expires_at - self.issued_at != 900:
            raise ValueError("invalid_receipt_lifetime")
        return self
