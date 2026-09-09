"""Synthetic vectors test decisions only; they do not measure voice accuracy."""

import numpy as np
import pytest

from voiceup.identity import MatchPolicy, identify, normalize_embedding
from voiceup.registry import SpeakerProfile


def profile(speaker_id, *examples):
    return SpeakerProfile(speaker_id, speaker_id, [np.array(v) for v in examples])


def test_empty_registry_is_unknown_but_still_validates_query():
    result = identify([1, 0], [])
    assert result.status == "unknown"
    assert result.speaker_id is None
    assert result.score is None
    assert result.reason == "empty_registry"
    with pytest.raises(ValueError, match="nonzero"):
        identify([0, 0], [])


def test_clear_match_uses_centroid_and_leaves_examples_unchanged():
    alice = profile("alice", [1.0, 0.1, 0.0], [1.0, -0.1, 0.0])
    bob = profile("bob", [0.0, 1.0, 0.0])
    originals = [value.copy() for value in alice.embeddings]
    decision = identify([1, 0, 0], [alice, bob])
    assert decision.status == "recognized"
    assert decision.speaker_id == "alice"
    assert decision.score == pytest.approx(1)
    assert decision.margin == pytest.approx(1)
    assert decision.candidates[0] == ("alice", pytest.approx(1))
    assert len(alice.embeddings) == 2
    for original, current in zip(originals, alice.embeddings):
        np.testing.assert_array_equal(current, original)


def test_one_registered_person_requires_absolute_threshold():
    profiles = [profile("alice", [1.0, 0.0])]
    assert identify([1, 0], profiles).status == "recognized"
    assert identify([1, 0], profiles).margin is None
    result = identify([0.6, 0.8], profiles)
    assert result.status == "ambiguous"
    assert result.speaker_id is None
    assert result.reason == "below_match_threshold"
    assert identify([0, 1], profiles).status == "unknown"


def test_near_tie_is_ambiguous_even_with_high_score():
    result = identify(
        [1, 0, 0],
        [profile("alice", [1, 0, 0]), profile("bob", [0.99, 0.1, 0])],
    )
    assert result.status == "ambiguous"
    assert result.speaker_id is None
    assert result.score > 0.99
    assert result.margin < 0.1
    assert result.reason == "insufficient_margin"


def test_low_score_is_unknown_and_does_not_assign_nearest_speaker():
    result = identify([0, 0, 1], [profile("alice", [1, 0, 0]), profile("bob", [0, 1, 0])])
    assert result.status == "unknown"
    assert result.speaker_id is None
    assert result.reason == "below_new_threshold"


def test_threshold_boundaries_are_explicit():
    profiles = [profile("alice", [1, 0])]
    policy = MatchPolicy(match_threshold=0.8, new_threshold=0.0, min_margin=0)
    # Equality at the new-speaker boundary remains ambiguous.
    assert identify([0, 1], profiles, policy).status == "ambiguous"
    assert identify([-1, 0], profiles, policy).status == "unknown"
    # Equality at the recognition boundary passes.
    assert identify([0.8, 0.6], profiles, policy).status == "recognized"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"match_threshold": float("nan")},
        {"new_threshold": float("inf")},
        {"min_margin": float("nan")},
        {"new_threshold": -1.01},
        {"match_threshold": 1.01},
        {"new_threshold": 0.75},
        {"new_threshold": 0.9},
        {"min_margin": -0.01},
        {"min_margin": 2.01},
        {"match_threshold": "0.9"},
    ],
)
def test_invalid_policy_rejected(kwargs):
    with pytest.raises(ValueError, match="policy"):
        MatchPolicy(**kwargs)


@pytest.mark.parametrize(
    "value", [[], [0, 0], [np.nan, 1], [np.inf, 0], [[1, 0]], [1 + 2j, 0], "hello"]
)
def test_invalid_embedding_rejected(value):
    with pytest.raises(ValueError):
        normalize_embedding(value)


def test_large_and_tiny_values_normalize_without_numerical_overflow():
    np.testing.assert_allclose(normalize_embedding([1e308, 1e308]), [2**-0.5] * 2)
    np.testing.assert_allclose(normalize_embedding([1e-308, 0]), [1, 0])


def test_dimension_mismatch_and_corrupt_profiles_rejected():
    with pytest.raises(ValueError, match="dimension"):
        identify([1, 0], [profile("alice", [1, 0, 0])])
    with pytest.raises(ValueError, match="no embeddings"):
        identify([1, 0], [profile("alice")])
    with pytest.raises(ValueError, match="centroid"):
        identify([1, 0], [profile("alice", [1, 0], [-1, 0])])
    with pytest.raises(ValueError, match="duplicate"):
        identify([1, 0], [profile("alice", [1, 0]), profile("alice", [1, 0])])


def test_sixty_four_profiles_are_distinguished_functionally():
    basis = np.eye(64)
    profiles = [profile(f"person-{i:02d}", vector) for i, vector in enumerate(basis)]
    for i, vector in enumerate(basis):
        result = identify(vector, profiles)
        assert result.status == "recognized"
        assert result.speaker_id == f"person-{i:02d}"
        assert len(result.candidates) == 5
