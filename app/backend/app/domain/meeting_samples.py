"""Immutable provenance for bounded packed audio and verified 16 kHz frame ranges."""

from dataclasses import dataclass

from app.domain.meeting import MAX_SOURCE_SECONDS

FrameRanges = tuple[tuple[int, int], ...]
PROVIDER_SAMPLE_RATE = 16000
MAX_SAMPLE_SECONDS = 60


def _source_bounds(sample_rate: int, source_frames: int) -> None:
    if (
        type(sample_rate) is not int
        or not 8000 <= sample_rate <= 192000
        or type(source_frames) is not int
        or not 0 < source_frames <= MAX_SOURCE_SECONDS * sample_rate
    ):
        raise ValueError("invalid_sample_source_bounds")


def _checked_ranges(ranges: FrameRanges, limit: int) -> None:
    if type(ranges) is not tuple:
        raise ValueError("mutable_sample_ranges")
    previous = 0
    for interval in ranges:
        if (
            type(interval) is not tuple
            or len(interval) != 2
            or type(interval[0]) is not int
            or type(interval[1]) is not int
        ):
            raise ValueError("invalid_sample_frame_interval")
        start, end = interval
        if not previous <= start < end <= limit:
            raise ValueError("invalid_sample_frame_interval")
        previous = end


def select_source_ranges(ranges: FrameRanges, source_frames: int, sample_rate: int) -> FrameRanges:
    """Select the chronological first sixty seconds of canonical source evidence."""
    _source_bounds(sample_rate, source_frames)
    _checked_ranges(ranges, source_frames)
    selected: list[tuple[int, int]] = []
    remaining = MAX_SAMPLE_SECONDS * sample_rate
    for start, end in ranges:
        count = min(end - start, remaining)
        selected.append((start, start + count))
        remaining -= count
        if not remaining:
            break
    return tuple(selected)


@dataclass(frozen=True, slots=True)
class SourceFrameManifest:
    sample_rate: int
    source_frames: int
    source_ranges: FrameRanges

    def __post_init__(self) -> None:
        _source_bounds(self.sample_rate, self.source_frames)
        _checked_ranges(self.source_ranges, self.source_frames)
        if not 0 < self.frames <= MAX_SAMPLE_SECONDS * self.sample_rate:
            raise ValueError("invalid_packed_sample_duration")

    @property
    def frames(self) -> int:
        return sum(end - start for start, end in self.source_ranges)

    @property
    def seconds(self) -> float:
        return self.frames / self.sample_rate


def _append(ranges: list[tuple[int, int]], start: int, end: int) -> None:
    if start >= end:
        return
    if ranges and start == ranges[-1][1]:
        ranges[-1] = (ranges[-1][0], end)
    else:
        ranges.append((start, end))


def map_provider_ranges(manifest: SourceFrameManifest, ranges: FrameRanges) -> FrameRanges:
    """Map verified 16 kHz integer frames inward through packed original-source joins."""
    provider_frames = (
        manifest.frames * PROVIDER_SAMPLE_RATE + manifest.sample_rate - 1
    ) // manifest.sample_rate
    _checked_ranges(ranges, provider_frames)
    # Adjacent verified regions form one continuous interval before conversion;
    # independently rounding their shared boundary would create an artificial gap.
    verified: list[tuple[int, int]] = []
    for start, end in ranges:
        _append(verified, start, end)
    result: list[tuple[int, int]] = []
    for start, end in verified:
        first = (start * manifest.sample_rate + PROVIDER_SAMPLE_RATE - 1) // PROVIDER_SAMPLE_RATE
        last = min(manifest.frames, end * manifest.sample_rate // PROVIDER_SAMPLE_RATE)
        packed_offset = 0
        for source_start, source_end in manifest.source_ranges:
            packed_end = packed_offset + source_end - source_start
            left, right = max(first, packed_offset), min(last, packed_end)
            if left < right:
                _append(
                    result,
                    source_start + left - packed_offset,
                    source_start + right - packed_offset,
                )
            packed_offset = packed_end
            if packed_offset >= last:
                break
    return tuple(result)
