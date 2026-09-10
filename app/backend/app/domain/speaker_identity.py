"""Pure speaker identity decisions, independent of models and persistence."""

import math
from dataclasses import dataclass
from typing import Literal

MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
MODEL_REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"
DIMENSIONS = 192
PreprocessingVersion = Literal["vad-windows-v1", "vad-packed-fallback-v1"]


def normalize_name(value: str) -> str:
    return " ".join(value.split())


def normalize(vector: list[float]) -> list[float]:
    if len(vector) != DIMENSIONS or not all(math.isfinite(v) for v in vector):
        raise ValueError("Invalid embedding dimensions or non-finite values")
    norm = math.sqrt(sum(v * v for v in vector))
    if norm < 1e-12:
        raise ValueError("Zero embedding")
    return [v / norm for v in vector]


@dataclass(frozen=True, slots=True)
class MatchPolicy:
    match_threshold: float = 0.55
    new_threshold: float = 0.45
    margin: float = 0.10


@dataclass(frozen=True, slots=True)
class MatchDecision:
    decision: Literal["recognized", "unknown", "ambiguous"]
    reason: str


def decide(scores: list[float], policy: MatchPolicy) -> MatchDecision:
    if not scores:
        return MatchDecision("unknown", "no_profiles")
    if scores[0] < policy.new_threshold:
        return MatchDecision("unknown", "below_new_threshold")
    if scores[0] < policy.match_threshold:
        return MatchDecision("ambiguous", "below_match_threshold")
    if len(scores) > 1 and scores[0] - scores[1] < policy.margin:
        return MatchDecision("ambiguous", "insufficient_margin")
    return MatchDecision("recognized", "matched")
