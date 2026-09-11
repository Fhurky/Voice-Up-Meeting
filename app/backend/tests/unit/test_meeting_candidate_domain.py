"""Candidate construction follows acoustic identity mapping and preserves source barriers."""

from app.domain.meeting_candidates import CandidateTurn, build_candidate_contexts


def test_two_short_native_labels_form_one_context_after_acoustic_mapping() -> None:
    result = build_candidate_contexts(
        [CandidateTurn(0, 17, 1, "a"), CandidateTurn(18, 35, 1, "b")],
        [(0, 17), (18, 35)],
        1,
        10,
        0,
        35,
    )
    assert len(result) == 1
    assert result[0].start == 0 and result[0].end == 35
    assert result[0].voiced_ranges == ((0, 17), (18, 32))


def test_different_acoustic_people_do_not_bridge() -> None:
    assert (
        build_candidate_contexts(
            [CandidateTurn(0, 17, 1, "a"), CandidateTurn(18, 35, 2, "b")],
            [(0, 17), (18, 35)],
            1,
            10,
            0,
            35,
        )
        == []
    )


def test_competing_speech_and_original_native_overlap_are_hard_barriers() -> None:
    assert (
        build_candidate_contexts(
            [
                CandidateTurn(0, 17, 1, "a"),
                CandidateTurn(18, 35, 1, "b"),
                CandidateTurn(17, 18, 2, "c"),
            ],
            [(0, 35)],
            1,
            10,
            0,
            35,
        )
        == []
    )
    assert (
        build_candidate_contexts(
            [CandidateTurn(0, 18, 1, "a"), CandidateTurn(17, 35, 1, "b")],
            [(0, 35)],
            1,
            10,
            0,
            35,
        )
        == []
    )


def test_vad_silence_never_becomes_counted_voice() -> None:
    result = build_candidate_contexts(
        [CandidateTurn(0, 80, 1, "a")],
        [(5, 15), (60, 70)],
        1,
        10,
        0,
        80,
    )
    assert result[0].voiced_ranges == ((5, 15), (60, 70))
