"""Conservative matching between meeting-local acoustic tracks."""

import math
from dataclasses import dataclass

from app.domain.speaker_identity import MatchPolicy, decide


def normalized_evidence(values: list[float], *, dimensions: int = 192) -> list[float]:
    if (
        dimensions not in {192, 256}
        or len(values) != dimensions
        or not all(math.isfinite(value) for value in values)
    ):
        raise ValueError("invalid_meeting_embedding")
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isfinite(norm) or norm < 1e-12:
        raise ValueError("invalid_meeting_embedding")
    result = [value / norm for value in values]
    if not math.isclose(sum(value * value for value in result), 1.0, abs_tol=1e-6):
        raise ValueError("invalid_meeting_embedding")
    return result


@dataclass(frozen=True, slots=True)
class AcousticCandidate:
    identity: int
    embedding: list[float]


def choose_acoustic_track(
    embedding: list[float] | None,
    candidates: list[AcousticCandidate],
    overlapping: set[int],
    policy: MatchPolicy,
    *,
    dimensions: int = 192,
) -> tuple[int | None, str]:
    if embedding is None:
        return None, "insufficient_speech"
    vector = normalized_evidence(embedding, dimensions=dimensions)
    ranked = sorted(
        [
            (
                candidate.identity,
                sum(
                    left * right
                    for left, right in zip(
                        vector,
                        normalized_evidence(candidate.embedding, dimensions=dimensions),
                        strict=True,
                    )
                ),
            )
            for candidate in candidates
        ],
        key=lambda item: (-item[1], item[0]),
    )
    decision = decide([score for _, score in ranked[:2]], policy)
    if decision.decision != "recognized":
        return None, decision.reason
    identity = ranked[0][0]
    if identity in overlapping:
        return None, "overlap_conflict"
    return identity, decision.reason


def merge_centroid(
    previous: list[float],
    previous_seconds: float,
    current: list[float],
    new_seconds: float,
    *,
    dimensions: int = 192,
) -> list[float]:
    if any(not math.isfinite(value) or value < 0 for value in (previous_seconds, new_seconds)):
        raise ValueError("invalid_meeting_evidence_duration")
    previous_vector = normalized_evidence(previous, dimensions=dimensions)
    current_vector = normalized_evidence(current, dimensions=dimensions)
    if new_seconds <= 0:
        return previous_vector
    if previous_seconds <= 0:
        return current_vector
    weight = new_seconds / (previous_seconds + new_seconds)
    return normalized_evidence(
        [
            left * (1 - weight) + right * weight
            for left, right in zip(previous_vector, current_vector, strict=True)
        ],
        dimensions=dimensions,
    )
