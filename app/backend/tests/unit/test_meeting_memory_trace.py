"""Private score provenance does not replace or relax the matching policy."""

import json

import pytest

from app.domain.meeting_memory_trace import build_memory_match_trace
from app.domain.speaker_identity import (
    MEETING_MODEL_ID,
    MEETING_MODEL_REVISION,
    MODEL_ID,
    MODEL_REVISION,
    MatchPolicy,
)


def trace(ecapa, community, agreement=None, **overrides):
    return build_memory_match_trace(
        ecapa,
        community,
        policy=MatchPolicy(),
        evidence_sha256="a" * 64,
        preprocessing_version="meeting-natural-context-v1",
        winner_agreement=agreement,
        **overrides,
    )


def test_trace_keeps_each_population_reason_and_no_candidate_identity() -> None:
    actual = trace([0.51, 0.31], [0.2, 0.1], False)
    assert actual == {
        "version": 1,
        "evidence_sha256": "a" * 64,
        "policy": {"match_threshold": 0.55, "new_threshold": 0.45, "margin": 0.1},
        "ecapa192": {
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "preprocessing_version": "meeting-natural-context-v1",
            "scores": [0.51, 0.31],
            "decision": "ambiguous",
            "reason": "below_match_threshold",
        },
        "community256": {
            "model_id": MEETING_MODEL_ID,
            "model_revision": MEETING_MODEL_REVISION,
            "preprocessing_version": "meeting-natural-context-v1",
            "scores": [0.2, 0.1],
            "decision": "unknown",
            "reason": "below_new_threshold",
        },
        "winner_agreement": False,
    }
    assert len(json.dumps(actual)) < 1500


@pytest.mark.parametrize("community", [None, []])
def test_unqueried_legacy_population_is_distinct_from_an_empty_gallery(community) -> None:
    actual = trace([], community)
    assert actual["ecapa192"]["scores"] == []
    assert actual["ecapa192"]["reason"] == "no_profiles"
    assert actual["winner_agreement"] is None
    if community is None:
        assert actual["community256"] is None
    else:
        assert actual["community256"]["scores"] == []
        assert actual["community256"]["reason"] == "no_profiles"


@pytest.mark.parametrize(
    ("scores", "decision", "reason"),
    [
        ([0.44], "unknown", "below_new_threshold"),
        ([0.45], "ambiguous", "below_match_threshold"),
        ([0.55], "recognized", "matched"),
        ([0.7, 0.65], "ambiguous", "insufficient_margin"),
        ([0.7, 0.4], "recognized", "matched"),
    ],
)
def test_trace_records_existing_policy_boundaries(scores, decision, reason) -> None:
    actual = trace(scores, None)["ecapa192"]
    assert (actual["decision"], actual["reason"]) == (decision, reason)


@pytest.mark.parametrize(
    "scores", [[0.7, 0.6, 0.5], [float("nan")], [float("inf")], [True], [1.01], [-1.01], [0.1, 0.2]]
)
def test_unbounded_or_invalid_scores_are_not_recorded(scores) -> None:
    with pytest.raises(ValueError, match="invalid_memory_match_trace"):
        trace(scores, None)


@pytest.mark.parametrize(
    ("ecapa", "community", "agreement"),
    [([], [], False), ([0.5], None, True), ([0.5], [0.2], None), ([0.5], [0.2], 1)],
)
def test_agreement_is_nullable_only_when_top_candidates_are_unavailable(
    ecapa, community, agreement
) -> None:
    with pytest.raises(ValueError, match="invalid_memory_match_trace"):
        trace(ecapa, community, agreement)


def test_trace_copies_score_lists() -> None:
    values = [0.7, 0.4]
    actual = trace(values, None)
    values[0] = 0
    assert actual["ecapa192"]["scores"] == [0.7, 0.4]


def test_actual_policy_and_legacy_preprocessing_are_recorded() -> None:
    actual = build_memory_match_trace(
        [0.6],
        None,
        policy=MatchPolicy(0.7, 0.4, 0.2),
        evidence_sha256="b" * 64,
        preprocessing_version="vad-packed-fallback-v1",
        winner_agreement=None,
    )
    assert actual["policy"] == {"match_threshold": 0.7, "new_threshold": 0.4, "margin": 0.2}
    assert actual["ecapa192"]["reason"] == "below_match_threshold"
    assert actual["ecapa192"]["preprocessing_version"] == "vad-packed-fallback-v1"


def test_source_fingerprint_must_be_an_exact_digest() -> None:
    with pytest.raises(ValueError, match="invalid_memory_match_trace"):
        build_memory_match_trace(
            [],
            None,
            policy=MatchPolicy(),
            evidence_sha256="not-a-source-digest",
            preprocessing_version=None,
            winner_agreement=None,
        )
