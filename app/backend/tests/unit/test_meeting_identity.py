"""Acoustic reconciliation never uses participant names or count targets as identity."""

import math

import pytest

from app.domain.meeting_identity import AcousticCandidate, choose_acoustic_track, merge_centroid
from app.domain.speaker_identity import MatchPolicy


def vector(index: int) -> list[float]:
    return [float(position == index) for position in range(192)]


def test_returning_chunk_keeps_track_and_new_voice_does_not() -> None:
    candidates = [AcousticCandidate(10, vector(0)), AcousticCandidate(11, vector(1))]
    assert choose_acoustic_track(vector(0), candidates, set(), MatchPolicy()) == (10, "matched")
    assert choose_acoustic_track(vector(2), candidates, set(), MatchPolicy()) == (
        None,
        "below_new_threshold",
    )


def test_ambiguous_voice_abstains_and_simultaneous_voices_cannot_merge() -> None:
    candidates = [AcousticCandidate(10, vector(0)), AcousticCandidate(11, vector(0))]
    assert choose_acoustic_track(vector(0), candidates, set(), MatchPolicy()) == (
        None,
        "insufficient_margin",
    )
    assert choose_acoustic_track(vector(0), candidates[:1], {10}, MatchPolicy()) == (
        None,
        "overlap_conflict",
    )


def test_missing_short_evidence_does_not_force_nearest_identity() -> None:
    assert choose_acoustic_track(
        None, [AcousticCandidate(10, vector(0))], set(), MatchPolicy()
    ) == (None, "insufficient_speech")


def test_centroid_uses_unique_owned_speech_weight_and_normalizes() -> None:
    result = merge_centroid(vector(0), 10, vector(1), 20)
    assert result[:2] == pytest.approx([1 / math.sqrt(5), 2 / math.sqrt(5)])
    assert sum(value * value for value in result) == pytest.approx(1)


def test_duplicate_context_does_not_change_centroid() -> None:
    assert merge_centroid(vector(0), 10, vector(1), 0) == vector(0)


def test_tracking_matches_within_its_own_population_and_keeps_overlap_exclusion() -> None:
    first, other = vector(0) + [0.0] * 64, vector(1) + [0.0] * 64
    candidates = [AcousticCandidate(10, first), AcousticCandidate(11, other)]
    assert choose_acoustic_track(first, candidates, set(), MatchPolicy(), dimensions=256) == (
        10,
        "matched",
    )
    assert choose_acoustic_track(first, candidates, {10}, MatchPolicy(), dimensions=256) == (
        None,
        "overlap_conflict",
    )
    centroid = merge_centroid(first, 10, other, 20, dimensions=256)
    assert len(centroid) == 256
    assert centroid[:2] == pytest.approx([1 / math.sqrt(5), 2 / math.sqrt(5)])


def test_tracking_and_profile_vectors_cannot_be_mixed_or_truncated() -> None:
    tracking = vector(0) + [0.0] * 64
    with pytest.raises(ValueError):
        choose_acoustic_track(
            tracking, [AcousticCandidate(10, vector(0))], set(), MatchPolicy(), dimensions=256
        )
    with pytest.raises(ValueError):
        choose_acoustic_track(tracking, [], set(), MatchPolicy())
    with pytest.raises(ValueError):
        merge_centroid(tracking, 10, vector(0), 20, dimensions=256)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 1e308])
def test_invalid_provider_vectors_cannot_match_or_create_zero_centroids(value: float) -> None:
    with pytest.raises(ValueError):
        choose_acoustic_track([value] * 192, [], set(), MatchPolicy())
    with pytest.raises(ValueError):
        merge_centroid([value] * 192, 1, vector(0), 2)


@pytest.mark.parametrize("seconds", [-1, float("nan"), float("inf")])
def test_invalid_evidence_duration_is_rejected(seconds: float) -> None:
    with pytest.raises(ValueError):
        merge_centroid(vector(0), seconds, vector(1), 1)
    with pytest.raises(ValueError):
        merge_centroid(vector(0), 1, vector(1), seconds)
