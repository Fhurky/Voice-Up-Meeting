"""Typed, source-bounded application boundary for the local meeting provider."""

import math
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.speaker_identity import PreprocessingVersion


class MeetingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class MeetingRange(MeetingRecord):
    start: float = Field(ge=0, le=310)
    end: float = Field(gt=0, le=310)

    @model_validator(mode="after")
    def positive_interval(self) -> Self:
        if self.end <= self.start:
            raise ValueError("invalid_meeting_interval")
        return self


class MeetingTurn(MeetingRange):
    speaker: str = Field(min_length=1, max_length=128)


class MeetingWord(MeetingRange):
    word: str = Field(max_length=4096)
    probability: float = Field(ge=0, le=1)


class MeetingSegment(MeetingRange):
    text: str = Field(max_length=32768)


class MeetingTracking(MeetingRecord):
    embedding: list[float] = Field(min_length=256, max_length=256)
    model_id: Literal["pyannote/speaker-diarization-community-1"]
    model_revision: Literal["3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"]
    component: Literal["embedding"]
    dimensions: Literal[256]

    @model_validator(mode="after")
    def normalized_tracking(self) -> Self:
        norm = math.sqrt(sum(value * value for value in self.embedding))
        if not math.isclose(norm, 1.0, rel_tol=0, abs_tol=1e-4):
            raise ValueError("invalid_meeting_tracking_norm")
        return self


class MeetingCandidateContext(MeetingRange):
    voiced_ranges: list[MeetingRange] = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def natural_source(self) -> Self:
        if not 3 - 1e-6 <= self.end - self.start <= 8 + 1e-6:
            raise ValueError("invalid_candidate_context_duration")
        previous = self.start
        for interval in self.voiced_ranges:
            if interval.start < previous or interval.end > self.end:
                raise ValueError("invalid_candidate_voiced_subset")
            previous = interval.end
        return self


class MeetingTrack(MeetingRecord):
    speaker: str = Field(min_length=1, max_length=128)
    status: Literal["usable", "insufficient_speech", "inconsistent_audio"]
    embedding: list[float] | None = Field(min_length=192, max_length=192)
    dimensions: Literal[192]
    validated_ranges: list[MeetingRange] = Field(max_length=4096)
    validated_seconds: float = Field(ge=0, le=310)
    used_seconds: float = Field(ge=0, le=310)
    windows_count: int = Field(ge=0, le=20)
    min_pair_similarity: float | None = Field(ge=-1.000001, le=1.000001)
    preprocessing_version: PreprocessingVersion
    tracking: MeetingTracking | None = None
    candidate_contexts: list[MeetingCandidateContext] | None = Field(default=None, max_length=104)

    @model_validator(mode="after")
    def consistent_evidence(self) -> Self:
        if self.windows_count:
            if (
                not 3 * self.windows_count - 1e-6
                <= self.used_seconds
                <= 8 * self.windows_count + 1e-6
            ):
                raise ValueError("invalid_meeting_window_duration")
        elif self.used_seconds != 0:
            raise ValueError("invalid_meeting_window_duration")
        if self.status != "usable":
            if self.embedding is not None or self.validated_ranges or self.validated_seconds != 0:
                raise ValueError("invalid_meeting_abstention")
            return self
        if (
            self.embedding is None
            or self.used_seconds < 3 - 1e-6
            or self.windows_count < 1
            or self.min_pair_similarity is None
            or self.min_pair_similarity < 0.55
            or not self.validated_ranges
        ):
            raise ValueError("invalid_meeting_voice_evidence")
        norm = math.sqrt(sum(value * value for value in self.embedding))
        if not math.isclose(norm, 1.0, rel_tol=0, abs_tol=1e-4):
            raise ValueError("invalid_meeting_embedding_norm")
        previous = -1.0
        for interval in self.validated_ranges:
            if interval.start < previous:
                raise ValueError("duplicated_meeting_evidence")
            previous = interval.end
        total = sum(interval.end - interval.start for interval in self.validated_ranges)
        if abs(total - self.validated_seconds) > 1e-6 or self.used_seconds > total + 1e-6:
            raise ValueError("invalid_meeting_evidence_duration")
        return self


class DiarizationIdentity(MeetingRecord):
    model_id: Literal["pyannote/speaker-diarization-community-1"]
    revision: Literal["3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"]
    recipe: Literal["community-vbx-fa015-v1"] | None = None


class MeetingVad(MeetingRecord):
    model_id: Literal["silero-vad"]
    model_version: Literal["6.2.1"]
    model_sha256: Literal["e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720"]
    ranges: list[MeetingRange] = Field(max_length=4096)

    @model_validator(mode="after")
    def ordered_speech(self) -> Self:
        previous = 0.0
        for interval in self.ranges:
            if interval.start < previous:
                raise ValueError("invalid_meeting_vad_order")
            previous = interval.end
        return self


class AsrIdentity(MeetingRecord):
    model_id: Literal["Systran/faster-whisper-large-v3"]
    revision: Literal["edaa852ec7e145841d8ffdb056a99866b5f0a478"]


class EmbeddingIdentity(MeetingRecord):
    model_id: Literal["speechbrain/spkrec-ecapa-voxceleb"]
    revision: Literal["0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"]
    dimensions: Literal[192]


class MeetingModelIdentity(MeetingRecord):
    diarization: DiarizationIdentity
    asr: AsrIdentity
    embedding: EmbeddingIdentity


class MeetingChunkResult(MeetingRecord):
    input_seconds: float = Field(gt=0, le=310)
    sample_rate: Literal[16000]
    turns: list[MeetingTurn] = Field(max_length=4096)
    exclusive_turns: list[MeetingTurn] = Field(max_length=4096)
    segments: list[MeetingSegment] = Field(max_length=4096)
    words: list[MeetingWord] = Field(max_length=16384)
    language: str | None = Field(min_length=2, max_length=3, pattern=r"^[a-z]+$")
    language_probability: float = Field(ge=0, le=1)
    tracks: list[MeetingTrack] = Field(max_length=1000)
    model_identity: MeetingModelIdentity
    vad: MeetingVad | None = None
    device: str = Field(pattern=r"^cuda:[0-9]+$", max_length=16)

    @model_validator(mode="after")
    def source_bound_evidence(self) -> Self:
        ranges: list[MeetingRange] = [
            *self.turns,
            *self.exclusive_turns,
            *self.segments,
            *self.words,
        ]
        ranges.extend(interval for track in self.tracks for interval in track.validated_ranges)
        if self.vad is not None:
            if self.model_identity.diarization.recipe != "community-vbx-fa015-v1":
                raise ValueError("meeting_candidate_recipe_missing")
            ranges.extend(self.vad.ranges)
        ranges.extend(
            context for track in self.tracks for context in track.candidate_contexts or []
        )
        if any(interval.end > self.input_seconds for interval in ranges):
            raise ValueError("meeting_source_bounds")
        labels = {turn.speaker for turn in self.turns}
        track_labels = {track.speaker for track in self.tracks}
        if len(track_labels) != len(self.tracks) or track_labels != labels:
            raise ValueError("meeting_track_mismatch")
        if any(turn.speaker not in labels for turn in self.exclusive_turns):
            raise ValueError("meeting_exclusive_label_mismatch")
        if self.language is None and (self.words or self.segments):
            raise ValueError("meeting_language_missing")
        for track in self.tracks:
            own = sorted(
                (turn.start, turn.end) for turn in self.turns if turn.speaker == track.speaker
            )
            others = [turn for turn in self.turns if turn.speaker != track.speaker]
            for context in track.candidate_contexts or []:
                if any(
                    max(context.start, turn.start) < min(context.end, turn.end) for turn in others
                ):
                    raise ValueError("meeting_candidate_context_overlap")
            verified_or_candidate = [*track.validated_ranges]
            verified_or_candidate.extend(
                interval
                for context in track.candidate_contexts or []
                for interval in context.voiced_ranges
            )
            for interval in verified_or_candidate:
                if any(
                    max(interval.start, turn.start) < min(interval.end, turn.end) for turn in others
                ):
                    raise ValueError("meeting_evidence_overlap")
                cursor = interval.start
                for start, end in own:
                    if start > cursor + 1e-6:
                        break
                    cursor = max(cursor, end)
                    if cursor >= interval.end - 1e-6:
                        break
                if cursor < interval.end - 1e-6:
                    raise ValueError("meeting_evidence_outside_track")
        return self


class MeetingAnalysisPort(Protocol):
    async def analyze(
        self,
        audio: bytes,
        *,
        job_public_id: str,
        tenant_public_id: str,
        language: str | None,
        max_speakers: int | None,
        num_speakers: int | None,
    ) -> MeetingChunkResult: ...
