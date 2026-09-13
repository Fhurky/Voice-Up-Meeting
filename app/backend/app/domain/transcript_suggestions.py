"""Visible model proposals, exact source mapping, and explicit user approval eligibility."""

import json
import unicodedata
from dataclasses import dataclass, replace
from typing import Any, Literal

from app.domain.transcript_correction import MAX_TARGET_CHARACTERS, ProposedEdit, validate_edits

SUGGESTION_POLICY: Literal["tr-context-words-v2"] = "tr-context-words-v2"
MAX_MODEL_OUTPUT_CHARACTERS = 8192
ProposalAssessment = Literal["checked", "review_required", "unmapped"]
ProposalReason = Literal[
    "semantic_review",
    "source_not_found",
    "ambiguous_source",
    "overlapping_edits",
    "unsupported_characters",
]
SuggestionStatus = Literal["unchanged", "suggested", "unmapped", "invalid_output"]


@dataclass(frozen=True, slots=True)
class SuggestionProposal:
    original: str
    replacement: str
    start_char: int | None
    end_char: int | None
    assessment: ProposalAssessment
    reason: ProposalReason | None


@dataclass(frozen=True, slots=True)
class SuggestionProjection:
    suggested_text: str
    proposals: tuple[SuggestionProposal, ...]
    status: SuggestionStatus
    saveable: bool


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _nonfinite(_value: str) -> None:
    raise ValueError("nonfinite_json")


def _proposal(text: str, original: str, replacement: str) -> SuggestionProposal:
    reason: ProposalReason | None = None
    start = text.find(original)
    if any(unicodedata.category(character).startswith("C") for character in original + replacement):
        reason = "unsupported_characters"
    elif start < 0:
        reason = "source_not_found"
    elif text.find(original, start + 1) >= 0:
        reason = "ambiguous_source"
    if reason is not None:
        return SuggestionProposal(original, replacement, None, None, "unmapped", reason)
    checked = original == replacement or bool(
        validate_edits(text, [ProposedEdit(original, replacement)]).edits
    )
    return SuggestionProposal(
        original,
        replacement,
        start,
        start + len(original),
        "checked" if checked else "review_required",
        None if checked else "semantic_review",
    )


def project_model_output(
    original_text: str, model_output: str, *, truncated: bool = False
) -> SuggestionProjection:
    """Keep semantic warnings visible; only structural ambiguity prevents source-bound saving."""
    invalid = SuggestionProjection(original_text, (), "invalid_output", False)
    if (
        not 1 <= len(original_text) <= MAX_TARGET_CHARACTERS
        or len(model_output) > MAX_MODEL_OUTPUT_CHARACTERS
    ):
        return invalid
    try:
        document = json.loads(
            model_output, object_pairs_hook=_unique_object, parse_constant=_nonfinite
        )
    except (ValueError, UnicodeError, RecursionError):
        return invalid
    if (
        not isinstance(document, dict)
        or set(document) != {"edits"}
        or not isinstance(document["edits"], list)
        or len(document["edits"]) > 3
    ):
        return invalid
    proposals = []
    for edit in document["edits"]:
        if (
            not isinstance(edit, dict)
            or set(edit) != {"original", "replacement"}
            or any(
                not isinstance(value, str) or not 1 <= len(value) <= 64 for value in edit.values()
            )
        ):
            return invalid
        proposals.append(_proposal(original_text, edit["original"], edit["replacement"]))
    mapped = [
        proposal
        for proposal in proposals
        if proposal.start_char is not None and proposal.end_char is not None
    ]
    conflicting = {
        index
        for index, proposal in enumerate(proposals)
        if proposal.start_char is not None
        and proposal.end_char is not None
        and any(
            other is not proposal
            and other.start_char is not None
            and other.end_char is not None
            and max(proposal.start_char, other.start_char) < min(proposal.end_char, other.end_char)
            for other in mapped
        )
    }
    proposals = [
        (
            replace(
                proposal,
                start_char=None,
                end_char=None,
                assessment="unmapped",
                reason="overlapping_edits",
            )
            if index in conflicting
            else proposal
        )
        for index, proposal in enumerate(proposals)
    ]
    suggested = original_text
    for proposal in sorted(
        proposals,
        key=lambda value: value.start_char if value.start_char is not None else -1,
        reverse=True,
    ):
        if proposal.start_char is not None and proposal.end_char is not None:
            suggested = (
                suggested[: proposal.start_char]
                + proposal.replacement
                + suggested[proposal.end_char :]
            )
    unmapped = any(proposal.assessment == "unmapped" for proposal in proposals)
    status: SuggestionStatus = (
        "invalid_output"
        if truncated
        else "unmapped" if unmapped else "suggested" if suggested != original_text else "unchanged"
    )
    return SuggestionProjection(suggested, tuple(proposals), status, status == "suggested")
