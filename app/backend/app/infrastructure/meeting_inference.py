"""Bounded private HTTP adapter; only validated evidence crosses into the application."""

import asyncio
import io
import json
import math
import re

import httpx
import soundfile as sf  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.core.config import Settings
from app.services.meeting_ports import MeetingChunkResult, MeetingModelIdentity
from app.services.speaker_ports import SpeakerError

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = 120 * 1024 * 1024
MAX_READINESS_BYTES = 16 * 1024
READINESS_TIMEOUT_SECONDS = 5.0


class HttpMeetingAdapter:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    async def ready(self) -> bool:
        """Probe model admission without claiming a tenant job or spending a retry."""
        if self.settings.inference_key is None:
            raise SpeakerError("inference_unavailable", 503)
        try:
            async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
                async with self.client.stream(
                    "GET",
                    httpx.URL(self.settings.inference_url).join("/meeting-ready"),
                    headers={
                        "Accept-Encoding": "identity",
                        "X-Inference-Key": self.settings.inference_key.get_secret_value(),
                    },
                    timeout=READINESS_TIMEOUT_SECONDS,
                ) as response:
                    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                        raise SpeakerError("model_mismatch", 502)
                    declared = response.headers.get("Content-Length")
                    if declared is not None and (
                        len(declared) > 12
                        or not declared.isdecimal()
                        or int(declared) > MAX_READINESS_BYTES
                    ):
                        raise SpeakerError("model_mismatch", 502)
                    if response.is_stream_consumed:
                        body = response.content
                        if len(body) > MAX_READINESS_BYTES:
                            raise SpeakerError("model_mismatch", 502)
                    else:
                        buffer = bytearray()
                        async for chunk in response.aiter_raw(chunk_size=4096):
                            if len(buffer) + len(chunk) > MAX_READINESS_BYTES:
                                raise SpeakerError("model_mismatch", 502)
                            buffer.extend(chunk)
                        body = bytes(buffer)
                    status = response.status_code
        except httpx.DecodingError:
            raise SpeakerError("model_mismatch", 502) from None
        except (TimeoutError, httpx.HTTPError):
            return False
        try:
            document = json.loads(body)
        except (ValueError, RecursionError):
            document = None
        if status == 503:
            detail = document.get("detail") if isinstance(document, dict) else None
            code = detail.get("code") if isinstance(detail, dict) else None
            if code is None or (
                isinstance(code, str)
                and code in {"model_not_ready", "meeting_model_not_ready", "inference_busy"}
            ):
                return False
            raise SpeakerError("inference_unavailable", 503)
        if status != 200:
            raise SpeakerError("inference_unavailable", 503)
        try:
            if (
                not isinstance(document, dict)
                or set(document) != {"ready", "device", "model_identity"}
                or document["ready"] is not True
                or not isinstance(document["device"], str)
                or re.fullmatch(r"cuda:[0-9]{1,11}", document["device"]) is None
            ):
                raise ValueError("invalid_meeting_readiness")
            identity = MeetingModelIdentity.model_validate(document["model_identity"])
            if identity.diarization.recipe != "community-vbx-fa015-v1":
                raise ValueError("meeting_readiness_recipe_missing")
        except (ValueError, ValidationError):
            raise SpeakerError("model_mismatch", 502) from None
        return True

    async def analyze(
        self,
        audio: bytes,
        *,
        job_public_id: str,
        tenant_public_id: str,
        language: str | None,
        max_speakers: int | None,
        num_speakers: int | None,
    ) -> MeetingChunkResult:
        if self.settings.inference_key is None:
            raise SpeakerError("inference_unavailable", 503)
        if not audio or len(audio) > MAX_REQUEST_BYTES:
            raise SpeakerError("audio_limit", 413)
        try:
            info = sf.info(io.BytesIO(audio))
            if (
                info.format != "WAV"
                or info.subtype != "PCM_16"
                or info.channels != 1
                or not 8000 <= info.samplerate <= 192000
                or not 0 < info.duration <= 310
            ):
                raise ValueError("invalid_chunk")
        except (ValueError, RuntimeError, sf.LibsndfileError):
            raise SpeakerError("invalid_audio", 422) from None
        if (
            language not in {None, "en", "tr"}
            or any(
                value is not None and (type(value) is not int or not 1 <= value <= 1000)
                for value in (max_speakers, num_speakers)
            )
            or (
                max_speakers is not None
                and num_speakers is not None
                and num_speakers > max_speakers
            )
        ):
            raise SpeakerError("validation_error", 422)
        params: dict[str, str | int] = {}
        if language is not None:
            params["language"] = language
        if max_speakers is not None:
            params["max_speakers"] = max_speakers
        if num_speakers is not None:
            params["num_speakers"] = num_speakers
        try:
            async with self.client.stream(
                "POST",
                httpx.URL(self.settings.inference_url).join("/v1/meeting-chunks"),
                params=params,
                content=audio,
                headers={
                    "Content-Type": "audio/wav",
                    "Accept-Encoding": "identity",
                    "X-Inference-Key": self.settings.inference_key.get_secret_value(),
                    "X-Job-Id": job_public_id,
                    "X-Tenant-Id": tenant_public_id,
                },
                timeout=self.settings.meeting_chunk_timeout_seconds,
            ) as response:
                if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                    raise SpeakerError("model_mismatch", 502)
                declared = response.headers.get("Content-Length")
                if declared is not None and (
                    len(declared) > 12
                    or not declared.isdecimal()
                    or int(declared) > MAX_RESPONSE_BYTES
                ):
                    raise SpeakerError("model_mismatch", 502)
                if response.is_stream_consumed:
                    body = response.content
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise SpeakerError("model_mismatch", 502)
                else:
                    buffer = bytearray()
                    async for chunk in response.aiter_raw(chunk_size=65536):
                        if len(buffer) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise SpeakerError("model_mismatch", 502)
                        buffer.extend(chunk)
                    body = bytes(buffer)
                status = response.status_code
        except httpx.TimeoutException:
            raise SpeakerError("job_timeout", 503) from None
        except httpx.HTTPError:
            raise SpeakerError("inference_unavailable", 503) from None
        if status != 200:
            import json

            try:
                error = json.loads(body)
                code = error["detail"]["code"]
            except (ValueError, TypeError, KeyError):
                code = None
            if status == 503 and code == "inference_busy":
                raise SpeakerError("inference_busy", 503)
            allowed = {
                "invalid_audio",
                "audio_limit",
                "unsupported_audio",
                "clipped_audio",
            }
            if status in {400, 413, 415, 422} and isinstance(code, str) and code in allowed:
                raise SpeakerError(code, status)
            raise SpeakerError("inference_unavailable", 503)
        try:
            result = MeetingChunkResult.model_validate_json(body)
            # Resampling can add at most one 16 kHz sample to a fractional source frame.
            expected = math.ceil(info.frames * 16000 / info.samplerate) / 16000
            if abs(result.input_seconds - expected) > 1e-8:
                raise ValueError("meeting_source_duration_mismatch")
        except (ValueError, ValidationError):
            raise SpeakerError("model_mismatch", 502) from None
        return result
