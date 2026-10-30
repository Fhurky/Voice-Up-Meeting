"""Meeting-end clustering merges one voice across chunks and never merges within a chunk."""

import math

import pytest

from app.domain.meeting_reconciliation import ReconciliationTrack, reconcile_tracks

THRESHOLD, NEW_THRESHOLD = 0.6, 0.45


def voice(angle: float) -> tuple[float, ...]:
    return (math.cos(angle), math.sin(angle)) + (0.0,) * 254


def track(
    chunk: int, label: str, angle: float | None, seconds: float = 60.0
) -> ReconciliationTrack:
    return ReconciliationTrack(chunk, label, seconds, None if angle is None else voice(angle))


def clusters(tracks: list[ReconciliationTrack], conflicts=()) -> dict[tuple[int, str], int]:
    return reconcile_tracks(tracks, THRESHOLD, NEW_THRESHOLD, conflicts).clusters


def test_one_voice_across_three_chunks_becomes_one_speaker() -> None:
    tracks = [track(0, "A", 0.0), track(1, "A", 0.1), track(2, "B", 0.2)]
    assert clusters(tracks) == {(0, "A"): 0, (1, "A"): 0, (2, "B"): 0}


def test_a_duplicate_does_not_block_the_next_chunk_from_joining() -> None:
    # The shipped margin rule opened a new speaker whenever two near-identical candidates existed.
    tracks = [track(0, "A", 0.0), track(1, "A", 0.02), track(2, "A", 0.01), track(3, "A", 0.03)]
    assert set(clusters(tracks).values()) == {0}


def test_different_voices_stay_apart() -> None:
    tracks = [
        track(0, "A", 0.0),
        track(0, "B", math.pi / 2),
        track(1, "A", 0.05),
        track(1, "B", 1.5),
    ]
    assert clusters(tracks) == {(0, "A"): 0, (0, "B"): 1, (1, "A"): 0, (1, "B"): 1}


def test_one_voice_split_inside_a_chunk_merges_unless_the_tracks_conflict() -> None:
    tracks = [track(0, "A", 0.0), track(0, "B", 0.0)]
    assert clusters(tracks) == {(0, "A"): 0, (0, "B"): 0}
    conflict = [((0, "A"), (0, "B"))]
    assert clusters(tracks, conflict) == {(0, "A"): 0, (0, "B"): 1}


def test_transitive_merges_keep_a_conflict_apart() -> None:
    tracks = [track(0, "A", 0.0), track(0, "B", 0.02), track(1, "A", 0.01), track(2, "A", 0.015)]
    result = clusters(tracks, [((0, "A"), (0, "B"))])
    assert result[(0, "A")] != result[(0, "B")]
    assert len(set(result.values())) == 2


def test_a_conflict_is_kept_when_each_side_grows_first() -> None:
    tracks = [
        track(0, "A", 0.0),
        track(1, "A", 0.01),
        track(1, "B", 0.02),
        track(2, "A", 0.03),
    ]
    result = clusters(tracks, [((1, "A"), (1, "B"))])
    assert result[(1, "A")] != result[(1, "B")]
    assert len(set(result.values())) == 2


def test_a_short_track_between_two_voices_does_not_chain_them() -> None:
    bridge = 0.5
    tracks = [track(0, "A", 0.0), track(1, "A", 1.0), track(2, "A", bridge, seconds=1.0)]
    result = reconcile_tracks(tracks, 0.8, NEW_THRESHOLD).clusters
    assert result[(0, "A")] != result[(1, "A")]


def test_track_without_a_vector_stays_alone() -> None:
    assert clusters([track(0, "A", 0.0), track(1, "A", None), track(2, "A", 0.0)]) == {
        (0, "A"): 0,
        (1, "A"): 1,
        (2, "A"): 0,
    }


def test_numbering_follows_first_appearance_and_is_deterministic() -> None:
    tracks = [track(0, "B", 1.5), track(0, "A", 0.0), track(1, "C", 0.01), track(1, "D", 1.51)]
    first = reconcile_tracks(tracks, THRESHOLD, NEW_THRESHOLD)
    assert first == reconcile_tracks(list(tracks), THRESHOLD, NEW_THRESHOLD)
    assert first.clusters == {(0, "B"): 0, (0, "A"): 1, (1, "C"): 1, (1, "D"): 0}


def test_cluster_with_an_outlying_long_member_is_ambiguous() -> None:
    # Average linkage can absorb a long member that no longer resembles the final centroid.
    tracks = [
        track(0, "A", 0.0, seconds=300.0),
        track(1, "A", 0.3, seconds=300.0),
        track(2, "A", 0.75, seconds=20.0),
    ]
    result = reconcile_tracks(tracks, 0.65, 0.9)
    assert set(result.clusters.values()) == {0}
    assert result.ambiguous == frozenset({0})


def test_short_members_and_single_tracks_do_not_mark_a_cluster_ambiguous() -> None:
    tracks = [
        track(0, "A", 0.0),
        track(1, "A", 0.01),
        track(2, "A", 0.6, seconds=2.0),
        track(0, "B", 2.0),
    ]
    result = reconcile_tracks(tracks, THRESHOLD, 0.9)
    assert result.clusters[(2, "A")] == result.clusters[(0, "A")]
    assert result.ambiguous == frozenset()


def test_empty_input_invalid_threshold_and_duplicate_track() -> None:
    assert reconcile_tracks([], THRESHOLD, NEW_THRESHOLD).clusters == {}
    with pytest.raises(ValueError, match="duplicate_reconciliation_track"):
        reconcile_tracks([track(0, "A", 0.0), track(0, "A", 0.1)], THRESHOLD, NEW_THRESHOLD)
    with pytest.raises(ValueError, match="invalid_reconciliation_threshold"):
        reconcile_tracks([track(0, "A", 0.0)], 1.5, NEW_THRESHOLD)
