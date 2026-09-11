"""Deterministic source-time ownership and acoustic attribution of transcript words."""

import math
import unicodedata
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class SpeechTurn:
    start: float
    end: float
    speaker: int


@dataclass(frozen=True, slots=True)
class SpeechWord:
    start: float
    end: float
    text: str
    probability: float
    uncertain: bool = False


@dataclass(frozen=True, slots=True)
class TranscriptLine:
    start: float
    end: float
    text: str
    speaker: int | None
    overlap: bool
    uncertain: bool


def _token(word: SpeechWord) -> str:
    value = word.text.strip().casefold()
    while value and unicodedata.category(value[0]).startswith("P"):
        value = value[1:]
    while value and unicodedata.category(value[-1]).startswith("P"):
        value = value[:-1]
    return value


def _midpoint(word: SpeechWord) -> float:
    return (word.start + word.end) / 2


def stitch_words(
    previous: list[SpeechWord], current: list[SpeechWord], boundary: float
) -> list[SpeechWord]:
    """Join two source-time observations at a neighboring-word anchor near the core edge.

    The caller delays the previous core's final five seconds. A unique mutual nearest
    match within one second needs an adjacent match in both observations. One anchored
    seam preserves real repeated words instead of deleting tokens independently.
    Without an anchor both observations remain explicitly uncertain; no exact boundary
    transcription claim can be made for that fallback.
    """
    if not math.isfinite(boundary) or boundary < 0:
        raise ValueError("invalid_stitch_boundary")
    for word in previous + current:
        if (
            not all(math.isfinite(value) for value in (word.start, word.end, word.probability))
            or not 0 <= word.start < word.end
            or not 0 <= word.probability <= 1
        ):
            raise ValueError("invalid_stitch_word")
    previous = sorted(previous, key=lambda word: (word.start, word.end))
    current = sorted(current, key=lambda word: (word.start, word.end))
    if not previous:
        return current
    if not current:
        return previous
    lower, upper = boundary - 5, boundary + 5
    earlier = [word for word in previous if _midpoint(word) < lower]
    later = [word for word in current if _midpoint(word) > upper]
    left = [word for word in previous if lower <= _midpoint(word) <= upper]
    right = [word for word in current if lower <= _midpoint(word) <= upper]
    if not left or not right:
        return sorted(earlier + left + right + later, key=lambda word: (word.start, word.end))

    def fallback() -> list[SpeechWord]:
        return sorted(
            earlier + [replace(word, uncertain=True) for word in left + right] + later,
            key=lambda word: (word.start, word.end),
        )

    # A pathological provider response cannot turn a ten-second join into an
    # unbounded quadratic comparison. Preserve its words as uncertain evidence.
    if max(len(left), len(right)) > 256:
        return fallback()
    left_tokens, right_tokens = [_token(word) for word in left], [_token(word) for word in right]
    distances = {
        (i, j): abs(_midpoint(before) - _midpoint(after))
        for i, before in enumerate(left)
        for j, after in enumerate(right)
        if left_tokens[i]
        and left_tokens[i] == right_tokens[j]
        and abs(_midpoint(before) - _midpoint(after)) <= 1
    }

    by_left: dict[int, list[tuple[float, int]]] = {}
    by_right: dict[int, list[tuple[float, int]]] = {}
    for (i, j), distance in distances.items():
        by_left.setdefault(i, []).append((distance, j))
        by_right.setdefault(j, []).append((distance, i))

    def unique_nearest(candidates: list[tuple[float, int]]) -> int | None:
        candidates = sorted(candidates)
        if not candidates or (len(candidates) > 1 and candidates[1][0] - candidates[0][0] <= 1e-6):
            return None
        return candidates[0][1]

    left_nearest = {i: unique_nearest(by_left.get(i, [])) for i in range(len(left))}
    right_nearest = {j: unique_nearest(by_right.get(j, [])) for j in range(len(right))}
    pairs = {(i, j) for i, j in left_nearest.items() if j is not None and right_nearest[j] == i}
    anchors = [
        (i, j)
        for i, j in pairs
        if ((i - 1, j - 1) in pairs or (i + 1, j + 1) in pairs)
        and (j + 1 == len(right) or left[i].start <= right[j + 1].start)
    ]
    if not anchors:
        return fallback()
    left_cut, right_cut = min(
        anchors,
        key=lambda pair: (
            abs((_midpoint(left[pair[0]]) + _midpoint(right[pair[1]])) / 2 - boundary),
            pair,
        ),
    )
    joined_left: list[SpeechWord] = []
    for i, word in enumerate(left[: left_cut + 1]):
        match = left_nearest[i]
        uncertain = match is None or (i, match) not in pairs or right[match].uncertain
        joined_left.append(replace(word, uncertain=word.uncertain or uncertain))
    joined_right: list[SpeechWord] = []
    for j, word in enumerate(right):
        if j <= right_cut:
            continue
        match = right_nearest[j]
        uncertain = match is None or (match, j) not in pairs or left[match].uncertain
        joined_right.append(replace(word, uncertain=word.uncertain or uncertain))
    return sorted(
        earlier + joined_left + joined_right + later, key=lambda word: (word.start, word.end)
    )


def _intersection(start: float, end: float, turn: SpeechTurn) -> float:
    return max(0.0, min(end, turn.end) - max(start, turn.start))


def _scores(word: SpeechWord, turns: list[SpeechTurn]) -> dict[int, float]:
    ranges: dict[int, list[tuple[float, float]]] = {}
    for turn in turns:
        start, end = max(word.start, turn.start), min(word.end, turn.end)
        if start < end:
            ranges.setdefault(turn.speaker, []).append((start, end))
    scores: dict[int, float] = {}
    for speaker, intervals in ranges.items():
        end, seconds = -1.0, 0.0
        for start, finish in sorted(intervals):
            seconds += max(0, finish - max(start, end))
            end = max(end, finish)
        scores[speaker] = seconds
    return scores


def _overlap(word: SpeechWord, turns: list[SpeechTurn]) -> bool:
    latest_end, latest_speaker = -1.0, -1
    for turn in sorted(turns, key=lambda value: (value.start, value.end)):
        start, end = max(word.start, turn.start), min(word.end, turn.end)
        if start >= end:
            continue
        if start < latest_end and turn.speaker != latest_speaker:
            return True
        if end > latest_end:
            latest_end, latest_speaker = end, turn.speaker
    return False


def align_words(
    words: list[SpeechWord],
    turns: list[SpeechTurn],
    exclusive: list[SpeechTurn],
    core_start: float,
    core_end: float,
) -> list[TranscriptLine]:
    """Midpoints own words; regular turns retain uncertainty hidden by exclusive output."""
    result: list[TranscriptLine] = []
    regular_speakers = {turn.speaker for turn in turns}
    observed_exclusive = [turn for turn in exclusive if turn.speaker in regular_speakers]
    for word in sorted(words, key=lambda value: (value.start, value.end)):
        midpoint = (word.start + word.end) / 2
        if not core_start <= midpoint < core_end or not word.text.strip():
            continue
        active = [turn for turn in turns if _intersection(word.start, word.end, turn)]
        scores = _scores(word, active)
        if not scores:
            # Confidence alone cannot turn an unsupported gap into speech. A
            # second observed speech interval may retain text, never identity.
            if word.probability < 0.5 or not _scores(word, observed_exclusive):
                continue
            speaker, overlap, uncertain = None, False, True
        else:
            overlap = _overlap(word, active)
            preferred = {
                key: value for key, value in _scores(word, exclusive).items() if key in scores
            }
            supported = (preferred or scores) if overlap else scores
            ranked = sorted(supported.items(), key=lambda value: (-value[1], value[0]))
            tie = len(ranked) > 1 and abs(ranked[0][1] - ranked[1][1]) < 1e-6
            sequential_ambiguity = (
                not overlap
                and len(scores) > 1
                and max(scores.values()) < 0.8 * sum(scores.values())
            )
            speaker = None if tie or sequential_ambiguity else ranked[0][0]
            uncertain = (
                overlap or tie or sequential_ambiguity or word.probability < 0.5 or word.uncertain
            )
        text = word.text.strip()
        if result:
            previous = result[-1]
            if (
                (previous.speaker, previous.overlap, previous.uncertain)
                == (speaker, overlap, uncertain)
                and 0 <= word.start - previous.end <= 1.5
                and len(previous.text) + len(text) < 500
                and not any(
                    turn.speaker != speaker and _intersection(previous.end, word.start, turn)
                    for turn in turns
                )
            ):
                # Whisper carries the original separating space on each word.
                separator = " " if word.text[:1].isspace() else ""
                result[-1] = TranscriptLine(
                    previous.start,
                    word.end,
                    previous.text + separator + text,
                    speaker,
                    overlap,
                    uncertain,
                )
                continue
        result.append(TranscriptLine(word.start, word.end, text, speaker, overlap, uncertain))
    return result
