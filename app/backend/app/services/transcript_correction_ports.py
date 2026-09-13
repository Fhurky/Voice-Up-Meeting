"""Typed local language-model boundary for immutable transcript review."""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.domain.transcript_correction import ProposedEdit


@dataclass(frozen=True, slots=True)
class CorrectionContext:
    target_text: str
    before: tuple[str, ...]
    after: tuple[str, ...]
    language: str


@dataclass(frozen=True, slots=True)
class OllamaCorrectionResult:
    edits: tuple[ProposedEdit, ...]
    model_name: str
    model_digest: str


class TranscriptCorrectionPort(Protocol):
    async def review(self, context: CorrectionContext) -> OllamaCorrectionResult: ...


ModelUnavailableReason = Literal[
    "remote_model",
    "not_language_model",
    "model_changed",
    "default_changed",
    "metadata_unavailable",
]


@dataclass(frozen=True, slots=True)
class ModelSelection:
    name: str
    digest: str


@dataclass(frozen=True, slots=True)
class InstalledReviewModel:
    name: str
    digest: str
    size_bytes: int
    selectable: bool
    unavailable_reason: ModelUnavailableReason | None
    is_default: bool


@dataclass(frozen=True, slots=True)
class ModelSuggestionResult:
    model_output: str
    model_output_truncated: bool
    model_name: str
    model_digest: str


class TranscriptSuggestionPort(Protocol):
    async def list_models(self) -> tuple[InstalledReviewModel, ...]: ...

    async def suggest(
        self, context: CorrectionContext, selection: ModelSelection
    ) -> ModelSuggestionResult: ...
