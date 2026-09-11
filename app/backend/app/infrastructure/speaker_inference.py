"""Strict HTTP adapter; the web service never imports a speech model."""

from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.domain.speaker_identity import (
    MODEL_ID,
    MODEL_REVISION,
    normalize,
)
from app.services.speaker_ports import EmbeddingResult, SpeakerError


class InferenceQuality(BaseModel):
    preprocessing_version: Literal["vad-windows-v1", "vad-packed-fallback-v1"] | None = None


class InferenceResponse(BaseModel):
    embedding: list[float] = Field(min_length=192, max_length=192)
    speech_seconds: float = Field(gt=0, le=120, allow_inf_nan=False)
    windows_count: int = Field(ge=1, le=20)
    model_id: Literal["speechbrain/spkrec-ecapa-voxceleb"]
    model_revision: Literal["0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"]
    dimensions: Literal[192]
    device: str = Field(min_length=1, max_length=64, pattern=r"^(cpu|cuda:[0-9]+)$")
    quality: InferenceQuality | None = None


class HttpEmbeddingAdapter:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    async def embed(
        self,
        audio: bytes,
        *,
        purpose: Literal["enroll", "identify"],
        job_public_id: str,
        tenant_public_id: str,
    ) -> EmbeddingResult:
        if self.settings.inference_key is None:
            raise SpeakerError("inference_unavailable", 503)
        try:
            response = await self.client.post(
                httpx.URL(self.settings.inference_url).join("/v1/embeddings"),
                params={"purpose": purpose},
                content=audio,
                headers={
                    "Content-Type": "application/octet-stream",
                    "X-Inference-Key": self.settings.inference_key.get_secret_value(),
                    "X-Job-Id": job_public_id,
                    "X-Tenant-Id": tenant_public_id,
                },
                timeout=self.settings.job_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise SpeakerError("job_timeout", 503) from exc
        except httpx.HTTPError as exc:
            raise SpeakerError("inference_unavailable", 503) from exc
        if response.status_code in {400, 413, 415, 422}:
            try:
                code = response.json()["detail"]["code"]
            except (ValueError, KeyError, TypeError):
                code = "invalid_audio"
            allowed = {
                "insufficient_speech",
                "inconsistent_audio",
                "clipped_audio",
                "invalid_audio",
                "audio_limit",
                "unsupported_audio",
            }
            raise SpeakerError(code if code in allowed else "invalid_audio", response.status_code)
        if response.status_code != 200:
            raise SpeakerError("inference_unavailable", 503)
        try:
            payload = InferenceResponse.model_validate(response.json())
            vector = normalize(payload.embedding)
        except (ValueError, ValidationError) as exc:
            raise SpeakerError("model_mismatch", 502) from exc
        if (
            purpose == "enroll"
            and (payload.speech_seconds < 10 - 1e-6 or payload.windows_count < 2)
        ) or payload.speech_seconds < 3 - 1e-6:
            raise SpeakerError("insufficient_speech", 422)
        return EmbeddingResult(
            vector,
            payload.speech_seconds,
            payload.windows_count,
            MODEL_ID,
            MODEL_REVISION,
            payload.device,
            preprocessing_version=(
                payload.quality.preprocessing_version if payload.quality is not None else None
            ),
        )
