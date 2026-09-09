"""Read-only, open-set speaker matching using cosine similarity.

Thresholds are configuration values, not calibrated probabilities. A speaker is
recognized only when both the absolute score and the gap to the next speaker
pass the policy. Enrollment remains an explicit operation in ``Registry``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

import numpy as np

if TYPE_CHECKING:
    from .registry import SpeakerProfile


def normalize_embedding(embedding: object, dimension: int | None = None) -> np.ndarray:
    """Return a normalized float64 copy of one finite, nonzero vector.

    Scaling before computing the norm also handles very large or very small
    finite input values without overflow or underflow.
    """
    if dimension is not None and (
        isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1
    ):
        raise ValueError("dimension must be a positive integer")
    try:
        raw = np.asarray(embedding)
        if np.iscomplexobj(raw):
            raise ValueError("embedding must contain real numbers")
        values = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("embedding must be a real numeric vector") from exc
    if values.ndim != 1 or values.size == 0:
        raise ValueError("embedding must be a nonempty one-dimensional vector")
    if dimension is not None and values.size != dimension:
        raise ValueError(f"embedding dimension {values.size} does not match expected {dimension}")
    if not np.all(np.isfinite(values)):
        raise ValueError("embedding must contain only finite values")
    scale = float(np.max(np.abs(values)))
    if scale == 0:
        raise ValueError("embedding must have nonzero norm")
    scaled = values / scale
    return scaled / np.linalg.norm(scaled)


@dataclass(frozen=True)
class MatchPolicy:
    """Provisional cosine thresholds; calibrate on held-out meeting audio."""

    match_threshold: float = 0.75
    new_threshold: float = 0.45
    min_margin: float = 0.10

    def __post_init__(self) -> None:
        values = (self.match_threshold, self.new_threshold, self.min_margin)
        try:
            valid = all(np.isfinite(value) for value in values)
            valid = valid and -1 <= self.new_threshold < self.match_threshold <= 1
            valid = valid and 0 <= self.min_margin <= 2
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise ValueError(
                "policy requires finite -1 <= new_threshold < match_threshold "
                "<= 1 and 0 <= min_margin <= 2"
            )


@dataclass(frozen=True)
class MatchDecision:
    status: str
    speaker_id: str | None
    score: float | None
    margin: float | None
    reason: str
    candidates: tuple[tuple[str, float], ...] = ()


def identify(
    embedding: object,
    profiles: Iterable[SpeakerProfile],
    policy: MatchPolicy | None = None,
) -> MatchDecision:
    """Compare to each speaker's normalized centroid without updating profiles.

    Each stored exemplar receives equal weight. A centroid reduces sensitivity
    to a single unusually similar exemplar; clean, varied enrollment examples
    remain essential. The runner-up is a different speaker, not another sample
    of the best speaker. With only one speaker there is no runner-up margin.
    """
    policy = policy if policy is not None else MatchPolicy()
    query = normalize_embedding(embedding)
    candidates: list[tuple[str, float]] = []
    seen: set[str] = set()
    for profile in profiles:
        if profile.speaker_id in seen:
            raise ValueError(f"duplicate speaker profile: {profile.speaker_id}")
        seen.add(profile.speaker_id)
        if not profile.embeddings:
            raise ValueError(f"speaker {profile.speaker_id} has no embeddings")
        examples = [normalize_embedding(example, int(query.size)) for example in profile.embeddings]
        try:
            centroid = normalize_embedding(np.mean(examples, axis=0), int(query.size))
        except ValueError as exc:
            raise ValueError(
                f"speaker {profile.speaker_id} has an unusable embedding centroid"
            ) from exc
        score = float(np.clip(np.dot(query, centroid), -1.0, 1.0))
        candidates.append((profile.speaker_id, score))
    candidates.sort(key=lambda candidate: (-candidate[1], candidate[0]))
    if not candidates:
        return MatchDecision("unknown", None, None, None, "empty_registry")

    best_id, best_score = candidates[0]
    margin = best_score - candidates[1][1] if len(candidates) > 1 else None
    top_candidates = tuple(candidates[:5])
    if best_score < policy.new_threshold:
        return MatchDecision(
            "unknown", None, best_score, margin, "below_new_threshold", top_candidates
        )
    if best_score < policy.match_threshold:
        return MatchDecision(
            "ambiguous", None, best_score, margin, "below_match_threshold", top_candidates
        )
    if margin is not None and margin < policy.min_margin:
        return MatchDecision(
            "ambiguous", None, best_score, margin, "insufficient_margin", top_candidates
        )
    return MatchDecision(
        "recognized", best_id, best_score, margin, "thresholds_passed", top_candidates
    )
