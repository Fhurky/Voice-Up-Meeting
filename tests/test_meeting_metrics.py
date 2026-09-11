"""Speaker transcription errors retain missing, extra and unassigned words."""

from itertools import permutations

import pytest

from voiceup.meeting_metrics import score_transcript, tokenize


def test_normalization_retains_unicode_words_and_does_not_expand_numbers():
    assert tokenize("İZMİR, çağrı! Don't—stop; 25 ﬁles. l’amour") == [
        "i\u0307zmi\u0307r",
        "çağrı",
        "don't",
        "stop",
        "25",
        "files",
        "l'amour",
    ]


def test_correct_words_with_permuted_speaker_labels_have_no_error():
    result = score_transcript(
        {"a": "hello there", "b": "good day"}, {"x": "good day", "y": "hello there"}
    )
    assert result["cpwer"]["errors"] == 0
    assert result["cpwer"]["rate"] == 0
    assert result["counts"]["reference_words"] == 4


def test_substitution_deletion_and_insertion_counts():
    result = score_transcript({"a": "a b c d"}, {"x": "a x c d extra"})
    assert result["cpwer"]["substitutions"] == 1
    assert result["cpwer"]["insertions"] == 1
    assert result["cpwer"]["deletions"] == 0
    assert result["cpwer"]["rate"] == 0.5
    assert score_transcript({"a": "a b c"}, {})["cpwer"]["deletions"] == 3


def test_extra_and_missing_speakers_are_not_dropped():
    extra = score_transcript({"a": "hello"}, {"x": "hello", "y": "unwanted words"})
    assert extra["cpwer"]["insertions"] == 2
    assert extra["cpwer"]["rate"] == 2
    missing = score_transcript({"a": "hello", "b": "missing words"}, {"x": "hello"})
    assert missing["cpwer"]["deletions"] == 2
    assert missing["cpwer"]["rate"] == 2 / 3


def test_unassigned_stream_is_included_and_separately_penalized():
    result = score_transcript({"a": "hello there"}, {None: "hello there"})
    assert result["cpwer"]["errors"] == 0
    assert result["assigned_only"]["deletions"] == 2
    assert result["assigned_only"]["insertions"] == 2
    assert result["assigned_only"]["rate"] == 2
    assert result["counts"]["unassigned_words"] == 2
    assert result["unassigned_word_fraction"] == 1


def test_split_stream_is_an_error_even_when_every_word_exists():
    result = score_transcript({"a": "one two three four"}, {"x": "one two", "y": "three four"})
    assert result["cpwer"]["errors"] == 4


def test_empty_reference_is_undefined_not_a_perfect_score():
    result = score_transcript({}, {"x": "unexpected words"})
    assert result["cpwer"]["insertions"] == 2
    assert result["cpwer"]["rate"] is None
    assert score_transcript({}, {})["cpwer"]["rate"] is None


def test_fifty_speakers_use_exact_assignment():
    reference = {f"r{i:02}": f"unique{i} unique{i} unique{i}" for i in range(50)}
    hypothesis = {f"h{49 - i:02}": text for i, text in enumerate(reference.values())}
    assert score_transcript(reference, hypothesis)["cpwer"]["errors"] == 0


def _independent_distance(a, b):
    # Deliberately simple full matrix is an independent small-case oracle.
    grid = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        grid[i][0] = i
    for j in range(len(b) + 1):
        grid[0][j] = j
    for i, left in enumerate(a, 1):
        for j, right in enumerate(b, 1):
            grid[i][j] = min(
                grid[i - 1][j] + 1, grid[i][j - 1] + 1, grid[i - 1][j - 1] + (left != right)
            )
    return grid[-1][-1]


@pytest.mark.parametrize(
    "reference,hypothesis",
    [
        ({"a": "a b", "b": "c", "c": "d e"}, {"x": "d", "y": "a x", "z": "c e"}),
        ({"a": "a b", "b": "c"}, {"x": "a", "y": "b", "z": "c"}),
        ({"a": "a b", "b": "c", "c": "d e"}, {"x": "c", "y": "a d"}),
        ({"a": "same", "b": "same"}, {"x": "same", "y": "same"}),
    ],
)
def test_assignment_matches_exhaustive_independent_oracle(reference, hypothesis):
    size = max(len(reference), len(hypothesis))
    refs = [value.split() for value in reference.values()] + [[]] * (size - len(reference))
    hyps = [value.split() for value in hypothesis.values()] + [[]] * (size - len(hypothesis))
    expected = min(
        sum(_independent_distance(a, hyps[j]) for a, j in zip(refs, order))
        for order in permutations(range(size))
    )
    result = score_transcript(reference, hypothesis)
    assert result["cpwer"]["errors"] == expected
    assert result == score_transcript(
        dict(reversed(list(reference.items()))), dict(reversed(list(hypothesis.items())))
    )


@pytest.mark.parametrize(
    "reference,hypothesis",
    [
        ({None: "text"}, {}),
        ({"": "text"}, {}),
        ({"a": None}, {}),
        ({"a": "text"}, {1: "text"}),
        ([], {}),
        ({}, {"x": 4}),
        ({"x" * 129: "word"}, {}),
        ({str(i): "a" for i in range(201)}, {}),
    ],
)
def test_malformed_or_unbounded_inputs_fail(reference, hypothesis):
    with pytest.raises(ValueError):
        score_transcript(reference, hypothesis)


def test_edit_work_limit_fails_instead_of_silently_truncating():
    with pytest.raises(ValueError, match="edit_work_limit"):
        score_transcript({"a": "word " * 8000}, {"x": "word " * 8000})


def test_normalization_expansion_obeys_character_limit(monkeypatch):
    monkeypatch.setattr("voiceup.meeting_metrics.MAX_TEXT_CHARACTERS", 10)
    # One presentation-form character expands to eighteen NFKC characters.
    with pytest.raises(ValueError, match="transcript_text_limit"):
        tokenize("\ufdfa")


@pytest.mark.parametrize("reference_side", [True, False])
def test_normalization_expansion_is_bounded_across_streams(monkeypatch, reference_side):
    monkeypatch.setattr("voiceup.meeting_metrics.MAX_TEXT_CHARACTERS", 20)
    streams = {"a": "\ufdfa", "b": "\ufdfa"}
    with pytest.raises(ValueError, match="transcript_text_limit"):
        score_transcript(streams if reference_side else {}, {} if reference_side else streams)
