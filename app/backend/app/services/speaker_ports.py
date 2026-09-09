"""Typed application boundary for the internal embedding provider."""

from dataclasses import dataclass
from typing import Literal, Protocol


class SpeakerError(Exception):
    def __init__(self, code: str, status_code: int = 400) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    embedding: list[float]
    speech_seconds: float
    windows_count: int
    model_id: str
    model_revision: str
    device: str


class EmbeddingPort(Protocol):
    async def embed(
        self,
        audio: bytes,
        *,
        purpose: Literal["enroll", "identify"],
        job_public_id: str,
        tenant_public_id: str,
    ) -> EmbeddingResult: ...
