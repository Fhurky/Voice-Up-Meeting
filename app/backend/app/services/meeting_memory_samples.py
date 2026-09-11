"""Prepare and independently validate bounded natural-context source manifests."""

import hashlib
import io
from dataclasses import dataclass

import soundfile as sf  # type: ignore[import-untyped]

from app.domain.meeting import clean_union
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.services.meeting_memory_ports import MeetingMemoryResult, MemoryContext, MemoryFrameRange
from app.services.speaker_ports import SpeakerError


@dataclass(frozen=True, slots=True)
class ContextSample:
    data: bytes
    sample_rate: int
    source_contexts: list[MemoryContext]
    contexts: list[MemoryContext]
    context_hashes: list[str]


def prepare_context_sample(
    storage: MeetingAudioStorage, storage_key: str, source_contexts: list[MemoryContext], rate: int
) -> ContextSample:
    selected: list[MemoryContext] = []
    remaining, previous = 60 * rate, 0
    for context in source_contexts:
        size = context.end - context.start
        if context.start < previous or not 3 * rate <= size <= 8 * rate:
            raise SpeakerError("model_mismatch", 502)
        previous = context.end
        if size <= remaining and len(selected) < 20:
            selected.append(context)
            remaining -= size
    if not selected:
        raise SpeakerError("insufficient_speech", 422)
    sample = storage.sample_with_manifest(
        storage_key, [(item.start, item.end) for item in selected], rate
    )
    if sample.manifest.frames != sum(item.end - item.start for item in selected):
        raise SpeakerError("model_mismatch", 502)
    contexts, hashes, offset = [], [], 0
    with sf.SoundFile(io.BytesIO(sample.data)) as source:
        for context in selected:
            size = context.end - context.start
            source.seek(offset)
            pcm = source.read(size, dtype="int16").tobytes()
            hashes.append(hashlib.sha256(pcm).hexdigest())
            contexts.append(
                MemoryContext(
                    start=offset,
                    end=offset + size,
                    voiced_ranges=[
                        MemoryFrameRange(
                            start=offset + span.start - context.start,
                            end=offset + span.end - context.start,
                        )
                        for span in context.voiced_ranges
                    ],
                )
            )
            offset += size
    return ContextSample(sample.data, rate, selected, contexts, hashes)


def validate_context_result(
    sample: ContextSample, result: MeetingMemoryResult
) -> tuple[list[tuple[int, int]], int]:
    if (
        result.input_sha256 != hashlib.sha256(sample.data).hexdigest()
        or result.sample_rate != sample.sample_rate
        or result.input_frames != sum(item.end - item.start for item in sample.contexts)
        or any(index >= len(sample.contexts) for index in result.accepted_context_indices)
    ):
        raise SpeakerError("model_mismatch", 502)
    if result.status != "usable":
        return [], 0
    accepted = set(result.accepted_context_indices)
    used: set[int] = set()
    source_ranges: list[tuple[int, int]] = []
    for interval in result.validated_ranges:
        cursor = interval.start
        for index, (context, original) in enumerate(
            zip(sample.contexts, sample.source_contexts, strict=True)
        ):
            if index not in accepted:
                continue
            for voice in context.voiced_ranges:
                left, right = max(cursor, voice.start), min(interval.end, voice.end)
                if left < right:
                    if left != cursor:
                        raise SpeakerError("model_mismatch", 502)
                    source_ranges.append(
                        (
                            original.start + left - context.start,
                            original.start + right - context.start,
                        )
                    )
                    cursor = right
                    used.add(index)
            if cursor == interval.end:
                break
        if cursor != interval.end:
            raise SpeakerError("model_mismatch", 502)
    if used != accepted:
        raise SpeakerError("model_mismatch", 502)
    source_ranges = clean_union(
        source_ranges, [], 0, max(item.end for item in sample.source_contexts)
    )
    actual_frames = sum(end - start for start, end in source_ranges)
    if abs(actual_frames / sample.sample_rate - result.validated_seconds) > 1e-6:
        raise SpeakerError("model_mismatch", 502)
    independent = len({sample.context_hashes[index] for index in accepted})
    return source_ranges, independent
