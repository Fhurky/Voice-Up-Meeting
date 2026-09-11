"""Source-time ownership and unique clean evidence for uploaded meetings."""

import math

UPLOAD_PART_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024 * 1024
MAX_SOURCE_SECONDS = 4 * 3600
CORE_SECONDS = 300
CONTEXT_SECONDS = 5
AUTO_ENROLL_SECONDS = 20


def window_core_seconds(props: dict[str, object]) -> int:
    """Historical checkpoints predate the explicit per-meeting window policy."""
    value = props.get("window_core_seconds", 60)
    if type(value) is not int or value not in {60, CORE_SECONDS}:
        raise ValueError("Invalid core duration")
    return value


def analysis_windows(
    duration: float, *, core_seconds: int = CORE_SECONDS
) -> list[tuple[int, float, float, float, float]]:
    if not math.isfinite(duration) or not 0 < duration <= MAX_SOURCE_SECONDS:
        raise ValueError("Invalid source duration")
    if type(core_seconds) is not int or core_seconds not in {60, CORE_SECONDS}:
        raise ValueError("Invalid core duration")
    return [
        (
            index,
            max(0.0, index * core_seconds - CONTEXT_SECONDS),
            float(index * core_seconds),
            min(duration, (index + 1) * core_seconds),
            min(duration, (index + 1) * core_seconds + CONTEXT_SECONDS),
        )
        for index in range(math.ceil(duration / core_seconds))
    ]


def clean_union(
    ranges: list[tuple[int, int]],
    excluded: list[tuple[int, int]],
    start: int,
    end: int,
) -> list[tuple[int, int]]:
    """Union integer sample ranges, intersect ownership, then subtract all overlap."""
    if start < 0 or end < start:
        raise ValueError("Invalid source bounds")
    for left, right in ranges + excluded:
        if not isinstance(left, int) or not isinstance(right, int) or left < 0 or right <= left:
            raise ValueError("Invalid sample interval")
    merged: list[tuple[int, int]] = []
    for left, right in sorted(ranges):
        left, right = max(start, left), min(end, right)
        if left >= right:
            continue
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    for left, right in sorted(excluded):
        result: list[tuple[int, int]] = []
        for begin, finish in merged:
            if right <= begin or left >= finish:
                result.append((begin, finish))
            else:
                if begin < left:
                    result.append((begin, left))
                if right < finish:
                    result.append((right, finish))
        merged = result
    return merged
