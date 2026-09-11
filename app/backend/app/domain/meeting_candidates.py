"""Construct unqualified natural contexts after acoustic mapping in original source frames."""

from collections import defaultdict
from dataclasses import dataclass

from app.domain.meeting import clean_union


@dataclass(frozen=True, slots=True)
class CandidateTurn:
    start: int
    end: int
    speaker: int
    native_label: str


@dataclass(frozen=True, slots=True)
class CandidateContext:
    start: int
    end: int
    voiced_ranges: tuple[tuple[int, int], ...]


def native_overlap_ranges(turns: list[CandidateTurn]) -> list[tuple[int, int]]:
    events: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for turn in turns:
        events[turn.start].append((turn.native_label, 1))
        events[turn.end].append((turn.native_label, -1))
    active: dict[str, int] = {}
    previous = 0
    overlaps = []
    for position, changes in sorted(events.items()):
        if len(active) > 1 and position > previous:
            overlaps.append((previous, position))
        for label, delta in changes:
            count = active.get(label, 0) + delta
            if count:
                active[label] = count
            else:
                active.pop(label, None)
        previous = position
    return clean_union(overlaps, [], 0, previous)


def build_candidate_contexts(
    turns: list[CandidateTurn],
    speech: list[tuple[int, int]],
    speaker: int,
    sample_rate: int,
    core_start: int,
    core_end: int,
    *,
    native_overlap: list[tuple[int, int]] | None = None,
) -> list[CandidateContext]:
    if sample_rate <= 0 or core_start < 0 or core_end < core_start:
        raise ValueError("invalid_candidate_source")
    limit = max(core_end, max((turn.end for turn in turns), default=0))
    competing = [(turn.start, turn.end) for turn in turns if turn.speaker != speaker]
    barriers = competing + (
        native_overlap if native_overlap is not None else native_overlap_ranges(turns)
    )
    own = clean_union(
        [(turn.start, turn.end) for turn in turns if turn.speaker == speaker],
        barriers,
        0,
        limit,
    )
    components: list[tuple[int, int]] = []
    for start, end in own:
        if (
            components
            and start - components[-1][1] <= sample_rate
            and not any(
                max(components[-1][1], left) < min(start, right) for left, right in barriers
            )
        ):
            components[-1] = (components[-1][0], end)
        else:
            components.append((start, end))
    voiced = clean_union(
        [(max(a, c), min(b, d)) for a, b in own for c, d in speech if max(a, c) < min(b, d)],
        [],
        0,
        limit,
    )
    result = []
    tail_guard = (sample_rate + 3) // 4
    for start, end in components:
        first = start
        while end - first >= 3 * sample_rate:
            last = min(end, first + 8 * sample_rate)
            begin, finish = max(core_start, first), min(core_end, last)
            if finish - begin >= 3 * sample_rate:
                kept = clean_union(voiced, [], begin, min(finish, end - tail_guard))
                if kept:
                    result.append(CandidateContext(begin, finish, tuple(kept)))
            first = last
    return result
