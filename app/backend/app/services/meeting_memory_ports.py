"""Versioned meeting-only quality evidence in native submitted PCM frame coordinates."""

import math
from typing import Literal, Protocol, Self

from pydantic import Field, model_validator

from app.services.meeting_ports import MeetingRecord, MeetingTracking

MEMORY_MODEL_ID = "pyannote/speaker-diarization-community-1"
MEMORY_MODEL_REVISION = "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
MEMORY_QUALITY_VERSION = "meeting-natural-context-v1"


class MemoryFrameRange(MeetingRecord):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("invalid_memory_frame_range")
        return self


class MemoryContext(MemoryFrameRange):
    voiced_ranges: list[MemoryFrameRange] = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def voiced_subset(self) -> Self:
        previous = self.start
        for interval in self.voiced_ranges:
            if interval.start < previous or interval.end > self.end:
                raise ValueError("invalid_memory_context_voice")
            previous = interval.end
        return self


class MeetingMemoryResult(MeetingRecord):
    ecapa_model_id: Literal["speechbrain/spkrec-ecapa-voxceleb"]
    ecapa_model_revision: Literal["0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"]
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retained_sha256: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    input_frames: int = Field(gt=0, le=60 * 192000)
    sample_rate: int = Field(ge=8000, le=192000)
    quality_version: Literal["meeting-natural-context-v1"]
    status: Literal["usable", "insufficient_speech", "inconsistent_audio", "clipped_audio"]
    accepted_context_indices: list[int] = Field(max_length=20)
    validated_ranges: list[MemoryFrameRange] = Field(max_length=4096)
    validated_seconds: float = Field(ge=0, le=60)
    windows_count: int = Field(ge=0, le=20)
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$", max_length=16)
    embedding192: list[float] | None = Field(min_length=192, max_length=192)
    memory_embedding: MeetingTracking | None

    @model_validator(mode="after")
    def valid_evidence(self) -> Self:
        if self.input_frames > self.sample_rate * 60:
            raise ValueError("invalid_memory_input_duration")
        if self.status != "usable":
            if (
                self.retained_sha256 is not None
                or self.embedding192 is not None
                or self.memory_embedding is not None
                or self.validated_ranges
                or self.accepted_context_indices
                or self.validated_seconds != 0
                or self.windows_count != 0
            ):
                raise ValueError("rejected_memory_evidence")
            return self
        if (
            self.retained_sha256 is None
            or self.embedding192 is None
            or self.memory_embedding is None
            or not self.accepted_context_indices
            or not self.validated_ranges
            or not 3 - 1e-6 <= self.validated_seconds <= 60
            or not 1 <= self.windows_count <= 20
        ):
            raise ValueError("missing_memory_evidence")
        if (
            len(set(self.accepted_context_indices)) != len(self.accepted_context_indices)
            or any(index < 0 or index >= 20 for index in self.accepted_context_indices)
            or not math.isclose(
                sum(value * value for value in self.embedding192), 1.0, abs_tol=1e-4
            )
        ):
            raise ValueError("invalid_memory_embedding_or_contexts")
        previous, frames = 0, 0
        for interval in self.validated_ranges:
            if interval.start < previous or interval.end > self.input_frames:
                raise ValueError("invalid_memory_validated_frames")
            previous = interval.end
            frames += interval.end - interval.start
        if abs(frames / self.sample_rate - self.validated_seconds) > 1e-6:
            raise ValueError("invalid_memory_validated_duration")
        return self


class MeetingMemoryPort(Protocol):
    async def verify(
        self,
        audio: bytes,
        *,
        contexts: list[MemoryContext],
        target: MeetingTracking,
        competitors: list[MeetingTracking],
        job_public_id: str,
        tenant_public_id: str,
    ) -> MeetingMemoryResult: ...
