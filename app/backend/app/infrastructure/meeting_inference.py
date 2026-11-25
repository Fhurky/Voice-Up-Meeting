"""Bounded private HTTP adapter; only validated evidence crosses into the application."""

import asyncio
import io
import json
import math
import re
from collections.abc import AsyncIterable
from typing import Any

import httpx
import soundfile as sf  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.core.config import Settings
from app.services.meeting_ports import (
    MeetingChunkResult,
    MeetingModelIdentity,
    MeetingRecordingResult,
)
from app.services.speaker_ports import SpeakerError

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = 120 * 1024 * 1024
# Whole-recording turns: tens of thousands of rows for a four-hour meeting.
MAX_RECORDING_RESPONSE_BYTES = 64 * 1024 * 1024
MAX_TURN_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_READINESS_BYTES = 16 * 1024
READINESS_TIMEOUT_SECONDS = 5.0


class HttpMeetingAdapter:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    async def processor(self) -> dict[str, Any]:
        return await self._processor_request("GET")

    async def switch_processor(self, device: str) -> dict[str, Any]:
        return await self._processor_request("POST", {"device": device})

    async def _processor_request(
        self, method: str, body: dict[str, str] | None = None
    ) -> dict[str, Any]:
        if self.settings.inference_key is None:
            raise SpeakerError("inference_unavailable", 503)
        try:
            response = await self.client.request(
                method,
                httpx.URL(self.settings.inference_url).join("/v1/meeting-processor"),
                json=body,
                headers={"X-Inference-Key": self.settings.inference_key.get_secret_value()},
                timeout=READINESS_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError:
            raise SpeakerError("inference_unavailable", 503) from None
        try:
            document = response.json()
        except ValueError:
            document = None
        if response.status_code not in {200, 202}:
            detail = document.get("detail") if isinstance(document, dict) else None
            code = detail.get("code") if isinstance(detail, dict) else None
            if code in {"inference_busy", "processor_unavailable"}:
                raise SpeakerError(code, 409)
            raise SpeakerError("inference_unavailable", 503)
        if (
            not isinstance(document, dict)
            or set(document)
            != {"device", "gpu_available", "cpu_available", "switching", "last_error"}
            or not isinstance(document["device"], str)
            or re.fullmatch(r"cpu|cuda:[0-9]{1,11}", document["device"]) is None
            or any(
                type(document[key]) is not bool
                for key in ("gpu_available", "cpu_available", "switching")
            )
            or document["last_error"] not in {None, "processor_switch_failed"}
        ):
            raise SpeakerError("model_mismatch", 502)
        return {**document, "device": "cpu" if document["device"] == "cpu" else "gpu"}

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
                or re.fullmatch(r"cpu|cuda:[0-9]{1,11}", document["device"]) is None
            ):
                raise ValueError("invalid_meeting_readiness")
            identity = MeetingModelIdentity.model_validate(document["model_identity"])
            if identity.diarization.recipe != "community-vbx-fa015-v1":
                raise ValueError("meeting_readiness_recipe_missing")
        except (ValueError, ValidationError):
            raise SpeakerError("model_mismatch", 502) from None
        return True

    def _job_headers(self, job_public_id: str, tenant_public_id: str) -> dict[str, str]:
        if self.settings.inference_key is None:
            raise SpeakerError("inference_unavailable", 503)
        return {
            "Accept-Encoding": "identity",
            "X-Inference-Key": self.settings.inference_key.get_secret_value(),
            "X-Job-Id": job_public_id,
            "X-Tenant-Id": tenant_public_id,
        }

    async def _send(
        self,
        path: str,
        *,
        params: dict[str, str | int],
        content: bytes | AsyncIterable[bytes],
        headers: dict[str, str],
        limit: int,
    ) -> bytes:
        """POST one bounded request; only the documented provider errors keep their codes."""
        try:
            async with self.client.stream(
                "POST",
                httpx.URL(self.settings.inference_url).join(path),
                params=params,
                content=content,
                headers=headers,
                timeout=self.settings.meeting_chunk_timeout_seconds,
            ) as response:
                if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                    raise SpeakerError("model_mismatch", 502)
                declared = response.headers.get("Content-Length")
                if declared is not None and (
                    len(declared) > 12 or not declared.isdecimal() or int(declared) > limit
                ):
                    raise SpeakerError("model_mismatch", 502)
                if response.is_stream_consumed:
                    body = response.content
                    if len(body) > limit:
                        raise SpeakerError("model_mismatch", 502)
                else:
                    buffer = bytearray()
                    async for chunk in response.aiter_raw(chunk_size=65536):
                        if len(buffer) + len(chunk) > limit:
                            raise SpeakerError("model_mismatch", 502)
                        buffer.extend(chunk)
                    body = bytes(buffer)
                status = response.status_code
        except httpx.TimeoutException:
            raise SpeakerError("job_timeout", 503) from None
        except httpx.HTTPError:
            raise SpeakerError("inference_unavailable", 503) from None
        if status != 200:
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
        return body

    @staticmethod
    def _chunk_info(audio: bytes) -> Any:
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
        return info

    @staticmethod
    def _chunk_result(body: bytes, info: Any) -> MeetingChunkResult:
        try:
            result = MeetingChunkResult.model_validate_json(body)
            # Resampling can add at most one 16 kHz sample to a fractional source frame.
            expected = math.ceil(info.frames * 16000 / info.samplerate) / 16000
            if abs(result.input_seconds - expected) > 1e-8:
                raise ValueError("meeting_source_duration_mismatch")
        except (ValueError, ValidationError):
            raise SpeakerError("model_mismatch", 502) from None
        return result

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
        headers = self._job_headers(job_public_id, tenant_public_id)
        info = self._chunk_info(audio)
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
        body = await self._send(
            "/v1/meeting-chunks",
            params=params,
            content=audio,
            headers={**headers, "Content-Type": "audio/wav"},
            limit=MAX_RESPONSE_BYTES,
        )
        return self._chunk_result(body, info)

    async def diarize_recording(
        self,
        blocks: AsyncIterable[bytes],
        *,
        sample_rate: int,
        size_bytes: int,
        job_public_id: str,
        tenant_public_id: str,
        max_speakers: int | None,
    ) -> MeetingRecordingResult:
        headers = self._job_headers(job_public_id, tenant_public_id)
        if (
            not 8000 <= sample_rate <= 192000
            or size_bytes <= 0
            or size_bytes % 2
            or (max_speakers is not None and not 1 <= max_speakers <= 1000)
        ):
            raise SpeakerError("validation_error", 422)
        body = await self._send(
            "/v1/meeting-recording",
            params={"max_speakers": max_speakers} if max_speakers is not None else {},
            content=blocks,
            headers={
                **headers,
                "Content-Type": "application/octet-stream",
                "Content-Length": str(size_bytes),
                "X-Sample-Rate": str(sample_rate),
            },
            limit=MAX_RECORDING_RESPONSE_BYTES,
        )
        try:
            result = MeetingRecordingResult.model_validate_json(body)
            expected = math.ceil(size_bytes // 2 * 16000 / sample_rate) / 16000
            if abs(result.input_seconds - expected) > 1e-6:
                raise ValueError("meeting_source_duration_mismatch")
        except (ValueError, ValidationError):
            raise SpeakerError("model_mismatch", 502) from None
        return result

    async def analyze_attributed(
        self,
        audio: bytes,
        turns: dict[str, list[dict[str, float | str]]],
        *,
        job_public_id: str,
        tenant_public_id: str,
        language: str | None,
    ) -> MeetingChunkResult:
        headers = self._job_headers(job_public_id, tenant_public_id)
        info = self._chunk_info(audio)
        document = json.dumps(turns, separators=(",", ":"), allow_nan=False).encode()
        if language not in {None, "en", "tr"} or len(document) > MAX_TURN_DOCUMENT_BYTES:
            raise SpeakerError("validation_error", 422)
        body = await self._send(
            "/v1/meeting-chunks/attributed",
            params={"language": language} if language is not None else {},
            content=document + audio,
            headers={
                **headers,
                "Content-Type": "application/octet-stream",
                "X-Turns-Bytes": str(len(document)),
            },
            limit=MAX_RESPONSE_BYTES,
        )
        result = self._chunk_result(body, info)
        labels = {str(row["speaker"]) for row in turns["turns"]}
        if (
            result.model_identity.diarization.recipe != "community-default-whole-v1"
            or not {track.speaker for track in result.tracks} <= labels
            or not {turn.speaker for turn in result.turns} <= labels
        ):
            raise SpeakerError("model_mismatch", 502)
        return result
