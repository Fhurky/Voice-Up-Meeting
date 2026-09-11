"""Source-weighted sufficient statistics for private meeting centroids."""

import math
from dataclasses import dataclass
from typing import Literal, cast

from app.domain.meeting_identity import merge_centroid, normalized_evidence

ABSENT_RESULTANT = object()
Origin = Literal["source_resultant", "legacy_centroid_seed"]


def positive_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError("invalid_meeting_resultant")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError("invalid_meeting_resultant") from exc
    if not math.isfinite(number):
        raise ValueError("invalid_meeting_resultant")
    return number


def exceeds(value: float, maximum: float) -> bool:
    return value > maximum and not math.isclose(value, maximum, rel_tol=1e-6, abs_tol=1e-9)


@dataclass(frozen=True, slots=True)
class CentroidState:
    weight: float
    norm: float
    origin: Origin

    @classmethod
    def from_record(cls, record: object, available_seconds: float) -> "CentroidState":
        if (
            not isinstance(record, dict)
            or set(record) != {"version", "weight", "norm", "origin"}
            or type(record["version"]) is not int
            or record["version"] != 1
            or not isinstance(record["origin"], str)
            or record["origin"] not in {"source_resultant", "legacy_centroid_seed"}
        ):
            raise ValueError("invalid_meeting_resultant")
        weight, norm = positive_number(record["weight"]), positive_number(record["norm"])
        if exceeds(norm, weight) or exceeds(weight, available_seconds):
            raise ValueError("invalid_meeting_resultant")
        return cls(weight, norm, cast(Origin, record["origin"]))

    def to_record(self) -> dict[str, object]:
        return {"version": 1, "weight": self.weight, "norm": self.norm, "origin": self.origin}


@dataclass(frozen=True, slots=True)
class CentroidUpdate:
    embedding: list[float] | None
    state: CentroidState | None


def advance_centroid(
    previous: list[float] | None,
    previous_seconds: float,
    current: list[float] | None,
    new_seconds: float,
    recorded_state: object = ABSENT_RESULTANT,
    *,
    dimensions: int = 192,
) -> CentroidUpdate:
    if dimensions not in {192, 256}:
        raise ValueError("invalid_meeting_embedding")
    if any(not math.isfinite(value) or value < 0 for value in (previous_seconds, new_seconds)):
        raise ValueError("invalid_meeting_evidence_duration")
    old_vector = (
        normalized_evidence(previous, dimensions=dimensions) if previous is not None else None
    )
    new_vector = (
        normalized_evidence(current, dimensions=dimensions) if current is not None else None
    )
    state = None
    if recorded_state is not ABSENT_RESULTANT:
        state = CentroidState.from_record(recorded_state, previous_seconds)
        if old_vector is None:
            raise ValueError("invalid_meeting_resultant")
    # Validate present state, but preserve the exact stored float32 vector and
    # do not materialize legacy metadata when there is no contributing audio.
    if new_seconds == 0 or new_vector is None:
        return CentroidUpdate(previous, state)
    if old_vector is None:
        return CentroidUpdate(
            new_vector, CentroidState(new_seconds, new_seconds, "source_resultant")
        )
    legacy_seed = state is None
    if state is None:
        weight = positive_number(previous_seconds)
        state = CentroidState(weight, weight, "legacy_centroid_seed")
    weighted = [
        math.fsum((old * state.norm, new * new_seconds))
        for old, new in zip(old_vector, new_vector, strict=True)
    ]
    norm = math.sqrt(math.fsum(value * value for value in weighted))
    weight = state.weight + new_seconds
    if not math.isfinite(weight) or not math.isfinite(norm) or norm < 1e-12:
        raise ValueError("invalid_meeting_resultant")
    embedding = (
        merge_centroid(old_vector, state.weight, new_vector, new_seconds, dimensions=dimensions)
        if legacy_seed
        else normalized_evidence(weighted, dimensions=dimensions)
    )
    return CentroidUpdate(embedding, CentroidState(weight, norm, state.origin))
