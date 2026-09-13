"""Conservative, source-bound lexical suggestions; never mutate acoustic evidence."""

import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

POLICY_VERSION: Literal["tr-context-words-v1"] = "tr-context-words-v1"
MAX_TARGET_CHARACTERS = 1024
MAX_CONTEXT_CHARACTERS = 4000
_WORDS = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_NUMBER_WORDS = frozenset(
    [
        "sıfır",
        "bir",
        "iki",
        "üç",
        "dört",
        "beş",
        "altı",
        "yedi",
        "sekiz",
        "dokuz",
        "on",
        "yirmi",
        "otuz",
        "kırk",
        "elli",
        "altmış",
        "yetmiş",
        "seksen",
        "doksan",
        "yüz",
        "bin",
        "milyon",
        "milyar",
        "trilyon",
        "yarım",
        "çeyrek",
        "ocak",
        "şubat",
        "mart",
        "nisan",
        "mayıs",
        "haziran",
        "temmuz",
        "ağustos",
        "eylül",
        "ekim",
        "kasım",
        "aralık",
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "hundred",
        "thousand",
        "million",
    ]
)
_NEGATIVE_WORDS = frozenset(
    ["değil", "yok", "hayır", "asla", "hiç", "hiçbir", "not", "no", "never", "without"]
)


@dataclass(frozen=True, slots=True)
class ProposedEdit:
    original: str
    replacement: str


@dataclass(frozen=True, slots=True)
class ValidatedEdit:
    start_char: int
    end_char: int
    original: str
    replacement: str


@dataclass(frozen=True, slots=True)
class CorrectionDecision:
    suggested_text: str
    status: Literal["unchanged", "suggested", "rejected"]
    edits: tuple[ValidatedEdit, ...]
    rejected_count: int


def _fold(value: str) -> str:
    return unicodedata.normalize("NFC", value).translate(str.maketrans("Iİ", "ıi")).casefold()


def _distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for index, character in enumerate(left, 1):
        current = [index]
        for other_index, other in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[other_index] + 1,
                    previous[other_index - 1] + (character != other),
                )
            )
        previous = current
    return previous[-1]


def _negation(value: str) -> tuple[str, ...]:
    """Conservative lexical/suffix heuristics, not a complete Turkish morphological parser."""
    values = [_fold(match.group()) for match in _WORDS.finditer(value)]
    return tuple(
        token
        for token in values
        if token in _NEGATIVE_WORDS
        or re.search(
            r"(?:ma|me)(?:dı|di|du|dü|mış|miş|muş|müş|yacak|yecek|z|sın|sin|malı|meli)", token
        )
        or re.search(r"(?:mıyor|miyor|muyor|müyor)", token)
    )


def _numbers(value: str) -> tuple[str, ...]:
    return tuple(
        token
        for match in _WORDS.finditer(value)
        if (token := _fold(match.group())) in _NUMBER_WORDS
        or any(char.isnumeric() for char in token)
    )


def _candidate(text: str, edit: ProposedEdit) -> ValidatedEdit | None:
    old, new = edit.original, edit.replacement
    if (
        not isinstance(old, str)
        or not isinstance(new, str)
        or not 1 <= len(old) <= 64
        or not 1 <= len(new) <= 64
        or old == new
        or old.strip() != old
        or new.strip() != new
        or any(unicodedata.category(char).startswith("C") for char in old + new)
        or any(char in "<>`{}[]" for char in new)
        or text.count(old) != 1
    ):
        return None
    start, end = text.index(old), text.index(old) + len(old)
    if (start and (text[start - 1].isalnum() or text[start - 1] in "_'’")) or (
        end < len(text) and (text[end].isalnum() or text[end] in "_'’")
    ):
        return None
    before, after = list(_WORDS.finditer(old)), list(_WORDS.finditer(new))
    if not 1 <= len(before) <= 3 or not 1 <= len(after) <= 3 or abs(len(before) - len(after)) > 1:
        return None
    if tuple(_fold(word.group()) for word in before) == tuple(
        _fold(word.group()) for word in after
    ):
        return None
    if _numbers(old) != _numbers(new) or _negation(old) != _negation(new):
        return None
    folded_old, folded_new = _fold(old), _fold(new)
    if any(
        value.replace(marker, "", 1) == other
        for value, other in ((folded_old, folded_new), (folded_new, folded_old))
        for marker in ("ma", "me")
    ):
        return None
    # Title case and acronyms are protected conservatively, including sentence-initial names.
    protected_before = tuple(word.group() for word in before if word.group()[0].isupper())
    protected_after = tuple(word.group() for word in after if word.group()[0].isupper())
    if protected_before != protected_after:
        return None
    if _distance(folded_old, folded_new) > min(
        8, max(2, math.ceil(max(len(old), len(new)) * 0.35))
    ):
        return None
    return ValidatedEdit(start, end, old, new)


def validate_edits(original_text: str, edits: Sequence[ProposedEdit]) -> CorrectionDecision:
    """Return only validated proposals; rejected model content never crosses this boundary."""
    if not 1 <= len(original_text) <= MAX_TARGET_CHARACTERS or len(edits) > 3:
        return CorrectionDecision(original_text, "rejected", (), len(edits))
    candidates = [
        candidate for edit in edits if (candidate := _candidate(original_text, edit)) is not None
    ]
    accepted = [
        edit
        for edit in candidates
        if not any(
            other is not edit
            and max(other.start_char, edit.start_char) < min(other.end_char, edit.end_char)
            for other in candidates
        )
    ]
    accepted.sort(key=lambda edit: edit.start_char)
    if (
        sum(
            max(len(_WORDS.findall(edit.original)), len(_WORDS.findall(edit.replacement)))
            for edit in accepted
        )
        > 3
    ):
        accepted = []
    suggested = original_text
    for edit in reversed(accepted):
        suggested = suggested[: edit.start_char] + edit.replacement + suggested[edit.end_char :]
    rejected = len(edits) - len(accepted)
    status: Literal["unchanged", "suggested", "rejected"] = (
        "suggested" if accepted else "rejected" if rejected else "unchanged"
    )
    return CorrectionDecision(suggested, status, tuple(accepted), rejected)
