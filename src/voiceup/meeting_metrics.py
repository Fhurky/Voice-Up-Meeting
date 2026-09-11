"""Bounded speaker-permutation transcription scoring, independent of model output selection.

This is corpus cpWER, not persistent identity accuracy, DER or word timestamp
accuracy. Every input word participates, including an explicit unassigned stream.
"""

from __future__ import annotations

import unicodedata

NORMALIZATION = "unicode-words-v1"
MAX_STREAMS = 200
MAX_TEXT_CHARACTERS = 2_000_000
MAX_WORDS = 50_000
MAX_EDIT_CELLS = 50_000_000


def _normalize_text(text: str) -> str:
    if not isinstance(text, str) or len(text) > MAX_TEXT_CHARACTERS:
        raise ValueError("invalid_transcript_text")
    text = unicodedata.normalize("NFKC", text).casefold().translate({0x2018: "'", 0x2019: "'"})
    if len(text) > MAX_TEXT_CHARACTERS:
        raise ValueError("transcript_text_limit")
    return text


def tokenize(text: str) -> list[str]:
    """NFKC/casefold; retain letters, numbers, marks and interior apostrophes."""
    return _tokenize_normalized(_normalize_text(text))


def _tokenize_normalized(text: str) -> list[str]:
    word_character = [unicodedata.category(character)[0] in "LNM" for character in text]
    normalized = []
    for index, character in enumerate(text):
        interior_apostrophe = (
            character == "'"
            and index > 0
            and index + 1 < len(text)
            and word_character[index - 1]
            and word_character[index + 1]
        )
        normalized.append(character if word_character[index] or interior_apostrophe else " ")
    return "".join(normalized).split()


def _streams(value: dict, *, reference: bool) -> list[tuple[str | None, list[str]]]:
    if not isinstance(value, dict) or len(value) > MAX_STREAMS:
        raise ValueError("invalid_transcript_streams")
    total_characters = 0
    for key, text in value.items():
        if key is None and not reference:
            pass
        elif not isinstance(key, str) or not key.strip() or len(key) > 128:
            raise ValueError("invalid_speaker_id")
        if not isinstance(text, str):
            raise ValueError("invalid_transcript_text")
        total_characters += len(text)
    if total_characters > MAX_TEXT_CHARACTERS:
        raise ValueError("transcript_text_limit")
    normalized = []
    normalized_characters = 0
    for key in sorted(value, key=lambda key: (key is None, key)):
        text = _normalize_text(value[key])
        normalized_characters += len(text)
        if normalized_characters > MAX_TEXT_CHARACTERS:
            raise ValueError("transcript_text_limit")
        normalized.append((key, text))
    return [(key, _tokenize_normalized(text)) for key, text in normalized]


def _distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, left in enumerate(reference, 1):
        current = [i]
        for j, right in enumerate(hypothesis, 1):
            current.append(min(previous[j] + 1, current[-1] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def _counts(reference: list[str], hypothesis: list[str]) -> tuple[int, int, int]:
    # Cells carry S/D/I counts; equal-cost paths prefer diagonal, deletion, insertion.
    previous = [(0, 0, j) for j in range(len(hypothesis) + 1)]
    for i, left in enumerate(reference, 1):
        current = [(0, i, 0)]
        for j, right in enumerate(hypothesis, 1):
            substitution, deletion, insertion = previous[j - 1]
            diagonal = (substitution + (left != right), deletion, insertion)
            substitution, deletion, insertion = previous[j]
            remove = (substitution, deletion + 1, insertion)
            substitution, deletion, insertion = current[-1]
            add = (substitution, deletion, insertion + 1)
            current.append(min((diagonal, remove, add), key=sum))
        previous = current
    return previous[-1]


def _assignment(cost: list[list[int]]) -> list[int]:
    """Exact square minimum-cost assignment with deterministic column tie-breaking."""
    size = len(cost)
    row_potential = [0] * (size + 1)
    column_potential = [0] * (size + 1)
    owner = [0] * (size + 1)
    predecessor = [0] * (size + 1)
    infinity = sum(max(row, default=0) for row in cost) + 1
    for row in range(1, size + 1):
        owner[0] = row
        column = 0
        slack = [infinity] * (size + 1)
        visited = [False] * (size + 1)
        while True:
            visited[column] = True
            current_row = owner[column]
            step, next_column = infinity, 0
            for candidate in range(1, size + 1):
                if visited[candidate]:
                    continue
                reduced = (
                    cost[current_row - 1][candidate - 1]
                    - row_potential[current_row]
                    - column_potential[candidate]
                )
                if reduced < slack[candidate]:
                    slack[candidate] = reduced
                    predecessor[candidate] = column
                if slack[candidate] < step:
                    step, next_column = slack[candidate], candidate
            for candidate in range(size + 1):
                if visited[candidate]:
                    row_potential[owner[candidate]] += step
                    column_potential[candidate] -= step
                else:
                    slack[candidate] -= step
            column = next_column
            if owner[column] == 0:
                break
        while column:
            previous_column = predecessor[column]
            owner[column] = owner[previous_column]
            column = previous_column
    result = [0] * size
    for column in range(1, size + 1):
        result[owner[column] - 1] = column - 1
    return result


def score_transcript(reference: dict[str, str], hypothesis: dict[str | None, str]) -> dict:
    """Score all streams after caller-provided chronological per-speaker concatenation.

    None is permitted only as the unassigned hypothesis speaker. Empty/missing streams
    have ordinary insertion/deletion costs. Undefined reference denominators return
    None. Input limits fail explicitly instead of truncating the evaluation population.
    """
    refs = _streams(reference, reference=True)
    hyps = _streams(hypothesis, reference=False)
    reference_words = sum(len(words) for _, words in refs)
    hypothesis_words = sum(len(words) for _, words in hyps)
    if max(reference_words, hypothesis_words) > MAX_WORDS:
        raise ValueError("transcript_word_limit")
    if reference_words * hypothesis_words > MAX_EDIT_CELLS:
        raise ValueError("edit_work_limit")
    unassigned_words = len(next((words for key, words in hyps if key is None), []))
    has_unassigned = any(key is None for key, _ in hyps)
    pair_costs = [[_distance(a, b) for _, b in hyps] for _, a in refs]

    def calculate(constrained: bool) -> dict:
        size = max(len(refs), len(hyps))
        if constrained and has_unassigned:
            size = max(len(refs), len(hyps) - 1) + 1
        forbidden = reference_words + hypothesis_words + 1
        matrix = []
        for row in range(size):
            values = []
            for column in range(size):
                if row >= len(refs):
                    value = len(hyps[column][1]) if column < len(hyps) else 0
                elif column >= len(hyps):
                    value = len(refs[row][1])
                elif constrained and hyps[column][0] is None:
                    value = forbidden
                else:
                    value = pair_costs[row][column]
                values.append(value)
            matrix.append(values)
        matches = _assignment(matrix)
        substitutions = deletions = insertions = 0
        alignment = []
        for row, column in enumerate(matches):
            ref = refs[row] if row < len(refs) else (None, [])
            hyp = hyps[column] if column < len(hyps) else (None, [])
            sub, delete, insert = _counts(ref[1], hyp[1])
            substitutions += sub
            deletions += delete
            insertions += insert
            if row < len(refs) or column < len(hyps):
                alignment.append(
                    {
                        "reference_speaker": ref[0],
                        "hypothesis_speaker": hyp[0],
                        "reference_is_dummy": row >= len(refs),
                        "hypothesis_is_dummy": column >= len(hyps),
                        "hypothesis_is_unassigned": column < len(hyps) and hyp[0] is None,
                        "errors": sub + delete + insert,
                    }
                )
        errors = substitutions + deletions + insertions
        return {
            "errors": errors,
            "substitutions": substitutions,
            "deletions": deletions,
            "insertions": insertions,
            "rate": errors / reference_words if reference_words else None,
            "assignment": alignment,
        }

    return {
        "normalization": NORMALIZATION,
        "counts": {
            "reference_speakers": len(refs),
            "hypothesis_speakers": len(hyps) - int(has_unassigned),
            "reference_words": reference_words,
            "hypothesis_words": hypothesis_words,
            "unassigned_words": unassigned_words,
        },
        "cpwer": calculate(False),
        "assigned_only": calculate(True),
        "unassigned_word_fraction": unassigned_words / hypothesis_words
        if hypothesis_words
        else None,
        "note": "Corpus cpWER permits label permutation; assigned_only forbids unassigned-to-person "
        "matches. Neither is persistent identity accuracy, DER or word timestamp accuracy.",
    }
