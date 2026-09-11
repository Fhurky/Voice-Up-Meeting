"""Resultant accumulation preserves evidence weight without changing identity thresholds."""

import math
from itertools import permutations

import pytest

from app.domain.meeting_centroid import ABSENT_RESULTANT, advance_centroid
from app.domain.meeting_identity import AcousticCandidate, choose_acoustic_track
from app.domain.speaker_identity import MatchPolicy


def vector(angle: float, dimensions: int) -> list[float]:
    radians = math.radians(angle)
    return [math.cos(radians), math.sin(radians)] + [0.0] * (dimensions - 2)


@pytest.mark.parametrize("dimensions", [192, 256])
def test_every_order_retains_the_true_weighted_sum_and_same_decision(dimensions: int) -> None:
    observations = [(0, 2.0), (35, 7.0), (70, 5.0)]
    expected = [
        math.fsum(vector(angle, dimensions)[index] * weight for angle, weight in observations)
        for index in range(dimensions)
    ]
    expected_norm = math.sqrt(math.fsum(value * value for value in expected))
    for order in permutations(observations):
        previous, state, seconds = None, ABSENT_RESULTANT, 0.0
        for angle, weight in order:
            result = advance_centroid(
                previous, seconds, vector(angle, dimensions), weight, state, dimensions=dimensions
            )
            previous = result.embedding
            assert result.state is not None
            state = result.state.to_record()
            seconds += weight
        assert previous == pytest.approx([value / expected_norm for value in expected], abs=1e-12)
        assert result.state.weight == 14
        assert result.state.norm == pytest.approx(expected_norm, abs=1e-12)
        assert result.state.origin == "source_resultant"

    decisions = []
    for angles in ((0, 35, 70), (70, 35, 0)):
        previous, state, seconds = None, ABSENT_RESULTANT, 0.0
        for angle in angles:
            result = advance_centroid(
                previous, seconds, vector(angle, dimensions), 10, state, dimensions=dimensions
            )
            previous = result.embedding
            state = result.state.to_record()
            seconds += 10
        assert previous is not None
        decisions.append(
            choose_acoustic_track(
                vector(92, dimensions),
                [AcousticCandidate(1, previous)],
                set(),
                MatchPolicy(),
                dimensions=dimensions,
            )
        )
    assert decisions == [(None, "below_match_threshold")] * 2


def test_absent_vectors_never_inflate_the_population_weight() -> None:
    result = advance_centroid(None, 20, vector(0, 192), 5)
    assert result.state.weight == result.state.norm == 5
    absent = advance_centroid(result.embedding, 25, None, 10, result.state.to_record())
    assert absent == result
    next_result = advance_centroid(
        absent.embedding, 35, vector(35, 192), 7, absent.state.to_record()
    )
    assert next_result.state.weight == 12


@pytest.mark.parametrize("dimensions", [192, 256])
def test_legacy_centroid_is_an_explicit_fixed_seed_and_stays_legacy(dimensions: int) -> None:
    original = vector(20, dimensions)
    unchanged = advance_centroid(original, 20, vector(40, dimensions), 0, dimensions=dimensions)
    assert unchanged.embedding == original and unchanged.state is None
    result = advance_centroid(original, 20, vector(40, dimensions), 10, dimensions=dimensions)
    assert result.state.weight == 30
    assert result.state.origin == "legacy_centroid_seed"
    again = advance_centroid(
        result.embedding,
        30,
        vector(30, dimensions),
        10,
        result.state.to_record(),
        dimensions=dimensions,
    )
    assert again.state.origin == "legacy_centroid_seed"
    assert again.state.weight == 40


def test_zero_update_preserves_float32_vector_and_state_exactly() -> None:
    original = [0.7071067690849304, 0.7071067690849304] + [0.0] * 190
    state = {"version": 1, "weight": 20.0, "norm": 19.0, "origin": "source_resultant"}
    result = advance_centroid(original, 20, vector(80, 192), 0, state)
    assert result.embedding == original
    assert result.state.to_record() == state


@pytest.mark.parametrize(
    "record",
    [
        None,
        {},
        {"version": 2},
        {"version": True, "weight": 20, "norm": 20, "origin": "source_resultant"},
        {"version": 1, "weight": 20, "norm": 20, "origin": "unknown"},
        {"version": 1, "weight": 20, "norm": 20, "origin": []},
        {"version": 1, "weight": 10**1000, "norm": 20, "origin": "source_resultant"},
        {"version": 1, "weight": 20, "norm": 20, "origin": "source_resultant", "extra": 1},
        *[
            {"version": 1, "weight": 20, "norm": 20, "origin": "source_resultant", key: value}
            for key in ("weight", "norm")
            for value in (0, -1, True, "20", float("nan"), float("inf"), 21)
        ],
    ],
)
def test_malformed_present_state_fails_even_without_new_weight(record: object) -> None:
    with pytest.raises(ValueError, match="invalid_meeting_resultant"):
        advance_centroid(vector(0, 192), 20, None, 0, record)


def test_resultant_without_vector_and_zero_weight_legacy_fail_closed() -> None:
    record = {"version": 1, "weight": 20, "norm": 20, "origin": "source_resultant"}
    with pytest.raises(ValueError, match="invalid_meeting_resultant"):
        advance_centroid(None, 20, vector(0, 192), 10, record)
    with pytest.raises(ValueError, match="invalid_meeting_resultant"):
        advance_centroid(vector(0, 192), 0, vector(20, 192), 10)


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_source_weight_does_not_reset_the_centroid(value: float) -> None:
    with pytest.raises(ValueError):
        advance_centroid(None, 0, vector(0, 192), value)
    with pytest.raises(ValueError):
        advance_centroid(None, value, vector(0, 192), 1)


def test_exact_cancellation_is_rejected_instead_of_inventing_a_center() -> None:
    result = advance_centroid(None, 0, vector(0, 192), 10)
    with pytest.raises(ValueError):
        advance_centroid(result.embedding, 10, vector(180, 192), 10, result.state.to_record())
