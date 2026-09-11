"""Source-owned words preserve short speakers and expose simultaneous speech."""

import pytest

from app.domain.meeting_timeline import SpeechTurn, SpeechWord, align_words, stitch_words


def test_context_words_are_owned_once_and_short_speaker_is_retained() -> None:
    turns = [SpeechTurn(58, 63, 1), SpeechTurn(63, 64, 2)]
    words = [
        SpeechWord(59, 59.8, " First", 0.9),
        SpeechWord(59.8, 60.2, " boundary", 0.9),
        SpeechWord(63, 64, " Hi.", 0.9),
    ]
    left = align_words(words, turns, turns, 0, 60)
    right = align_words(words, turns, turns, 60, 120)
    assert [row.text for row in left] == ["First"]
    assert [(row.text, row.speaker, row.uncertain) for row in right] == [
        ("boundary", 1, False),
        ("Hi.", 2, False),
    ]


def test_overlap_stays_visible_even_when_exclusive_turn_picks_one_speaker() -> None:
    rows = align_words(
        [SpeechWord(1, 2, " hello", 0.9)],
        [SpeechTurn(0, 3, 1), SpeechTurn(1, 2, 2)],
        [SpeechTurn(0, 3, 1)],
        0,
        60,
    )
    assert len(rows) == 1
    assert (rows[0].speaker, rows[0].overlap, rows[0].uncertain) == (1, True, True)


def test_stretched_word_spanning_sequential_voices_keeps_text_without_claiming_identity() -> None:
    turns = [SpeechTurn(0, 0.8, 1), SpeechTurn(1, 9.5, 2), SpeechTurn(10, 12.66, 3)]
    rows = align_words([SpeechWord(0, 12.66, " and", 0.85)], turns, turns, 0, 60)
    assert len(rows) == 1
    assert (rows[0].text, rows[0].speaker, rows[0].overlap, rows[0].uncertain) == (
        "and",
        None,
        False,
        True,
    )


def test_dominant_short_boundary_word_retains_its_supported_identity() -> None:
    turns = [SpeechTurn(0, 0.91, 1), SpeechTurn(0.91, 1, 2)]
    rows = align_words([SpeechWord(0, 1, " word", 0.9)], turns, turns, 0, 60)
    assert rows[0].speaker == 1 and rows[0].uncertain is False


def test_exclusive_minor_voice_cannot_override_regular_sequential_dominance() -> None:
    turns = [SpeechTurn(0, 0.91, 1), SpeechTurn(0.91, 1, 2)]
    rows = align_words([SpeechWord(0, 1, " word", 0.9)], turns, [turns[1]], 0, 60)
    assert rows[0].speaker == 1 and rows[0].uncertain is False


@pytest.mark.parametrize("share,expected", [(0.8, 1), (0.799, None)])
def test_sequential_identity_requires_at_least_eighty_percent_support(
    share: float, expected: int | None
) -> None:
    turns = [SpeechTurn(0, share, 1), SpeechTurn(share, 1, 2)]
    rows = align_words([SpeechWord(0, 1, " word", 0.9)], turns, turns, 0, 60)
    assert rows[0].speaker == expected and rows[0].uncertain is (expected is None)


def test_grouping_cannot_bridge_untranscribed_competing_speech() -> None:
    turns = [SpeechTurn(0, 0.2, 1), SpeechTurn(0.3, 0.6, 2), SpeechTurn(0.8, 1, 1)]
    rows = align_words(
        [SpeechWord(0, 0.2, " first", 0.9), SpeechWord(0.8, 1, " second", 0.9)],
        turns,
        turns,
        0,
        60,
    )
    assert [(row.start, row.end, row.text) for row in rows] == [
        (0, 0.2, "first"),
        (0.8, 1, "second"),
    ]


def test_absent_speech_does_not_produce_hallucinated_words() -> None:
    assert align_words([SpeechWord(1, 2, " invented", 0.9)], [], [], 0, 60) == []


def test_exclusive_supported_unaligned_word_is_retained_without_assigning_identity() -> None:
    rows = align_words(
        [SpeechWord(1.1, 1.4, " uncertain", 0.9)],
        [SpeechTurn(0, 1, 1)],
        [SpeechTurn(0, 2, 1)],
        0,
        60,
    )
    assert len(rows) == 1
    assert (rows[0].text, rows[0].speaker, rows[0].overlap, rows[0].uncertain) == (
        "uncertain",
        None,
        False,
        True,
    )


@pytest.mark.parametrize("probability", [0.49, 0.9])
def test_speech_elsewhere_does_not_admit_words_in_an_unsupported_gap(probability: float) -> None:
    assert (
        align_words(
            [SpeechWord(4, 5, " unsupported", probability)],
            [SpeechTurn(0, 1, 1)],
            [SpeechTurn(0, 1, 1)],
            0,
            60,
        )
        == []
    )


def test_low_probability_unaligned_word_is_not_rescued_by_exclusive_output() -> None:
    assert (
        align_words(
            [SpeechWord(1.1, 1.4, " uncertain", 0.49)],
            [SpeechTurn(0, 1, 1)],
            [SpeechTurn(0, 2, 1)],
            0,
            60,
        )
        == []
    )


def test_unaligned_fallback_does_not_invent_an_exclusive_only_speaker() -> None:
    assert (
        align_words(
            [SpeechWord(1.1, 1.4, " unsupported", 0.9)],
            [SpeechTurn(0, 1, 1)],
            [SpeechTurn(0, 2, 2)],
            0,
            60,
        )
        == []
    )


def test_ambiguous_tie_is_unassigned_and_low_probability_is_visible() -> None:
    rows = align_words(
        [SpeechWord(1, 2, " uncertain", 0.2)], [SpeechTurn(0, 3, 1), SpeechTurn(0, 3, 2)], [], 0, 60
    )
    assert rows[0].speaker is None and rows[0].uncertain and rows[0].overlap


def test_ordered_words_group_without_duplicating_whitespace_or_crossing_speakers() -> None:
    rows = align_words(
        [
            SpeechWord(1, 1.2, " Hello", 0.9),
            SpeechWord(1.3, 1.8, " world.", 0.9),
            SpeechWord(3, 4, " Yes.", 0.9),
        ],
        [SpeechTurn(0, 2, 1), SpeechTurn(3, 4, 2)],
        [],
        0,
        60,
    )
    assert [(row.start, row.end, row.text, row.speaker) for row in rows] == [
        (1, 1.8, "Hello world.", 1),
        (3, 4, "Yes.", 2),
    ]


@pytest.mark.parametrize("previous_shift,current_shift", [(-0.1, 0.1), (0.1, -0.1)])
def test_independent_window_jitter_neither_duplicates_nor_loses_boundary_word(
    previous_shift: float, current_shift: float
) -> None:
    def words(shift: float) -> list[SpeechWord]:
        return [
            SpeechWord(58.5 + shift, 59.0 + shift, " Hello", 0.9),
            SpeechWord(59.8 + shift, 60.2 + shift, " boundary", 0.9),
            SpeechWord(60.5 + shift, 61.0 + shift, " world.", 0.9),
        ]

    result = stitch_words(words(previous_shift), words(current_shift), 60)
    assert [word.text.strip() for word in result] == ["Hello", "boundary", "world."]
    assert not any(word.uncertain for word in result)


def test_source_anchored_stitch_preserves_real_repeated_words() -> None:
    previous = [SpeechWord(59 + i * 0.4, 59.3 + i * 0.4, " yes", 0.9) for i in range(3)]
    current = [SpeechWord(row.start + 0.1, row.end + 0.1, row.text, 0.9) for row in previous]
    result = stitch_words(previous, current, 60)
    assert [word.text.strip() for word in result] == ["yes", "yes", "yes"]
    assert not any(word.uncertain for word in result)


def test_isolated_similar_word_is_not_silently_deleted_without_neighbor_anchor() -> None:
    result = stitch_words(
        [SpeechWord(59.7, 60.1, " yes", 0.9)],
        [SpeechWord(59.8, 60.2, " yes", 0.9)],
        60,
    )
    assert len(result) == 2 and all(word.uncertain for word in result)


def test_conflicting_words_remain_observable_in_uncertain_fallback() -> None:
    result = stitch_words(
        [SpeechWord(59.7, 60.1, " first", 0.9)],
        [SpeechWord(59.8, 60.2, " second", 0.9)],
        60,
    )
    assert {row.text.strip() for row in result} == {"first", "second"}
    assert all(word.uncertain for word in result)
    lines = align_words(result, [SpeechTurn(55, 65, 1)], [], 55, 65)
    assert lines and all(line.uncertain for line in lines)


def test_disjoint_context_is_not_matched_by_text_alone() -> None:
    previous = [SpeechWord(56, 56.3, " hello", 0.9), SpeechWord(56.4, 56.7, " again", 0.9)]
    current = [SpeechWord(63, 63.3, " hello", 0.9), SpeechWord(63.4, 63.7, " again", 0.9)]
    result = stitch_words(previous, current, 60)
    assert len(result) == 4


def test_anchored_join_preserves_outer_source_words_and_original_tokens() -> None:
    result = stitch_words(
        [
            SpeechWord(50, 51, " earlier", 0.9),
            SpeechWord(59, 59.5, " Hello,", 0.9),
            SpeechWord(60, 60.5, " world!", 0.9),
            SpeechWord(68, 69, " stale", 0.9),
        ],
        [
            SpeechWord(51, 52, " stale", 0.9),
            SpeechWord(59.1, 59.6, " hello", 0.9),
            SpeechWord(60.1, 60.6, " world", 0.9),
            SpeechWord(70, 71, " later", 0.9),
        ],
        60,
    )
    assert [word.text.strip() for word in result] == ["earlier", "Hello,", "world!", "later"]


def test_existing_uncertainty_survives_an_anchored_join() -> None:
    previous = [SpeechWord(59, 59.5, " first", 0.9, True), SpeechWord(60, 60.5, " second", 0.9)]
    current = [SpeechWord(59.1, 59.6, " first", 0.9), SpeechWord(60.1, 60.6, " second", 0.9)]
    assert stitch_words(previous, current, 60)[0].uncertain


def test_dense_context_has_bounded_matching_and_preserves_all_uncertain_observations() -> None:
    previous = [SpeechWord(59 + i / 1000, 59.1 + i / 1000, " a", 0.9) for i in range(257)]
    result = stitch_words(previous, previous, 60)
    assert len(result) == 514 and all(word.uncertain for word in result)


@pytest.mark.parametrize("boundary", [float("nan"), float("inf"), -1])
def test_invalid_stitch_boundary_is_rejected(boundary: float) -> None:
    with pytest.raises(ValueError):
        stitch_words([], [], boundary)


def test_duplicate_context_turns_do_not_double_weight_one_speaker() -> None:
    result = align_words(
        [SpeechWord(0, 2, " word", 0.9)],
        [SpeechTurn(0, 1, 1), SpeechTurn(0, 1, 1), SpeechTurn(0, 1.5, 2)],
        [],
        0,
        60,
    )
    assert result[0].speaker == 2 and result[0].overlap and result[0].uncertain
