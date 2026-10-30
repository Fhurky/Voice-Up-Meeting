"""Cluster per-chunk speaker tracks into one meeting population after the last chunk."""

import heapq
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass

# Long tracks settle first so a short, noisy track cannot chain two voices together.
LONG_TRACK_SECONDS = 10.0
MINIMUM_TRACK_WEIGHT = 0.1

TrackKey = tuple[int, str]


@dataclass(frozen=True, slots=True)
class ReconciliationTrack:
    chunk: int
    label: str
    seconds: float
    embedding: tuple[float, ...] | None


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    clusters: dict[TrackKey, int]
    ambiguous: frozenset[int]


@dataclass(slots=True)
class _Node:
    members: set[int]
    conflicts: set[int]
    resultant: list[float] | None
    seconds: float
    generation: int = 0
    alive: bool = True


def _unit(vector: list[float] | tuple[float, ...]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise ValueError("invalid_reconciliation_vector")
    return [value / norm for value in vector]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _merge(nodes: list[_Node], threshold: float, eligible: Callable[[_Node], bool]) -> None:
    centroids = {
        index: _unit(node.resultant)
        for index, node in enumerate(nodes)
        if node.alive and node.resultant is not None
    }
    heap: list[tuple[float, int, int, int, int]] = []

    def push(left: int, right: int) -> None:
        first, second = min(left, right), max(left, right)
        a, b = nodes[first], nodes[second]
        if a.conflicts & b.members or not eligible(a) or not eligible(b):
            return
        score = _dot(centroids[first], centroids[second])
        if score >= threshold:
            heapq.heappush(heap, (-score, first, second, a.generation, b.generation))

    ordered = sorted(centroids)
    for position, left in enumerate(ordered):
        for right in ordered[position + 1 :]:
            push(left, right)
    while heap:
        _, first, second, first_generation, second_generation = heapq.heappop(heap)
        a, b = nodes[first], nodes[second]
        if (
            not (a.alive and b.alive)
            or a.generation != first_generation
            or b.generation != second_generation
        ):
            continue
        if a.resultant is None or b.resultant is None:
            raise ValueError("invalid_reconciliation_vector")
        a.members |= b.members
        a.conflicts |= b.conflicts
        a.seconds += b.seconds
        a.resultant = [x + y for x, y in zip(a.resultant, b.resultant, strict=True)]
        a.generation += 1
        b.alive = False
        centroids[first] = _unit(a.resultant)
        del centroids[second]
        for other in centroids:
            if other != first:
                push(first, other)


def reconcile_tracks(
    tracks: list[ReconciliationTrack],
    threshold: float,
    new_threshold: float,
    conflicts: Iterable[tuple[TrackKey, TrackKey]] = (),
) -> ReconciliationResult:
    """Conflicting tracks are provably different voices and never share a cluster.

    Numbering follows first appearance, so meeting speaker ordinals stay stable and readable.
    A stated speaker count never forces a merge: different voices stay different.
    """
    if not -1.0 <= threshold <= 1.0 or not -1.0 <= new_threshold <= 1.0:
        raise ValueError("invalid_reconciliation_threshold")
    ordered = sorted(enumerate(tracks), key=lambda item: (item[1].chunk, item[0]))
    tracks = [track for _, track in ordered]
    positions = {(track.chunk, track.label): index for index, track in enumerate(tracks)}
    if len(positions) != len(tracks):
        raise ValueError("duplicate_reconciliation_track")
    opposed: list[set[int]] = [set() for _ in tracks]
    for left, right in conflicts:
        opposed[positions[left]].add(positions[right])
        opposed[positions[right]].add(positions[left])
    vectors = [_unit(track.embedding) if track.embedding is not None else None for track in tracks]
    nodes = [
        _Node(
            {index},
            opposed[index],
            (
                [value * max(track.seconds, MINIMUM_TRACK_WEIGHT) for value in vector]
                if vector is not None
                else None
            ),
            track.seconds,
        )
        for index, (track, vector) in enumerate(zip(tracks, vectors, strict=True))
    ]
    _merge(nodes, threshold, lambda node: node.seconds >= LONG_TRACK_SECONDS)
    _merge(nodes, threshold, lambda node: True)
    survivors = sorted((node for node in nodes if node.alive), key=lambda node: min(node.members))
    clusters: dict[TrackKey, int] = {}
    ambiguous: set[int] = set()
    for number, node in enumerate(survivors):
        for member in node.members:
            clusters[(tracks[member].chunk, tracks[member].label)] = number
        if node.resultant is None or len(node.members) < 2:
            continue
        centroid = _unit(node.resultant)
        for member in node.members:
            vector = vectors[member]
            if (
                vector is not None
                and tracks[member].seconds >= LONG_TRACK_SECONDS
                and _dot(vector, centroid) < new_threshold
            ):
                ambiguous.add(number)
                break
    return ReconciliationResult(clusters, frozenset(ambiguous))
