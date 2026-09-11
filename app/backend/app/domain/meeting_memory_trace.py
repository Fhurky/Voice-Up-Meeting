"""Bounded, identity-free provenance for private meeting-memory comparisons."""

import math
import re
from dataclasses import asdict

from app.domain.speaker_identity import (
    MEETING_MODEL_ID,
    MEETING_MODEL_REVISION,
    MEETING_PREPROCESSING_VERSION,
    MODEL_ID,
    MODEL_REVISION,
    MatchPolicy,
    PreprocessingVersion,
    decide,
)


def _population(
    scores: list[float],
    policy: MatchPolicy,
    model_id: str,
    model_revision: str,
    preprocessing_version: str | None,
) -> dict[str, object]:
    if (
        len(scores) > 2
        or any(
            isinstance(score, bool) or not math.isfinite(score) or not -1 <= score <= 1
            for score in scores
        )
        or scores != sorted(scores, reverse=True)
    ):
        raise ValueError("invalid_memory_match_trace")
    decision = decide(scores, policy)
    return {
        "model_id": model_id,
        "model_revision": model_revision,
        "preprocessing_version": preprocessing_version,
        "scores": list(scores),
        "decision": decision.decision,
        "reason": decision.reason,
    }


def build_memory_match_trace(
    ecapa_scores: list[float],
    community_scores: list[float] | None,
    *,
    policy: MatchPolicy,
    evidence_sha256: str,
    preprocessing_version: PreprocessingVersion | None,
    winner_agreement: bool | None,
) -> dict[str, object]:
    if not re.fullmatch(r"[0-9a-f]{64}", evidence_sha256):
        raise ValueError("invalid_memory_match_trace")
    has_both_candidates = bool(ecapa_scores and community_scores)
    if (has_both_candidates and type(winner_agreement) is not bool) or (
        not has_both_candidates and winner_agreement is not None
    ):
        raise ValueError("invalid_memory_match_trace")
    return {
        "version": 1,
        "evidence_sha256": evidence_sha256,
        "policy": asdict(policy),
        "ecapa192": _population(
            ecapa_scores, policy, MODEL_ID, MODEL_REVISION, preprocessing_version
        ),
        "community256": (
            _population(
                community_scores,
                policy,
                MEETING_MODEL_ID,
                MEETING_MODEL_REVISION,
                MEETING_PREPROCESSING_VERSION,
            )
            if community_scores is not None
            else None
        ),
        "winner_agreement": winner_agreement,
    }
