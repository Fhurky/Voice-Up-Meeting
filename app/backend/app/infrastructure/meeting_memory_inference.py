"""Bounded JSON transport for the independent meeting-memory quality adapter."""

import base64
import hashlib
import io
import json

import httpx
import soundfile as sf  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.core.config import Settings
from app.services.meeting_memory_ports import MeetingMemoryResult, MemoryContext
from app.services.meeting_ports import MeetingTracking
from app.services.speaker_ports import SpeakerError


class HttpMeetingMemoryAdapter:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    async def verify(
        self,
        audio: bytes,
        *,
        contexts: list[MemoryContext],
        target: MeetingTracking,
        competitors: list[MeetingTracking],
        job_public_id: str,
        tenant_public_id: str,
    ) -> MeetingMemoryResult:
        if self.settings.inference_key is None:
            raise SpeakerError("inference_unavailable", 503)
        try:
            info = sf.info(io.BytesIO(audio))
            if (
                len(audio) > 60 * 192000 * 2 + 4096
                or info.format != "WAV"
                or info.subtype != "PCM_16"
                or info.channels != 1
                or not 8000 <= info.samplerate <= 192000
                or not 0 < info.frames <= 60 * info.samplerate
                or not 1 <= len(contexts) <= 20
                or len(competitors) > 999
            ):
                raise ValueError("invalid_memory_input")
            previous = 0
            for context in contexts:
                if (
                    context.start < previous
                    or context.end > info.frames
                    or not 3 * info.samplerate <= context.end - context.start <= 8 * info.samplerate
                ):
                    raise ValueError("invalid_memory_context")
                previous = context.end
        except (ValueError, RuntimeError, sf.LibsndfileError):
            raise SpeakerError("invalid_audio", 422) from None
        body = json.dumps(
            {
                "audio_base64": base64.b64encode(audio).decode("ascii"),
                "sample_rate": info.samplerate,
                "contexts": [context.model_dump(mode="json") for context in contexts],
                "target": target.model_dump(mode="json"),
                "competitors": [row.model_dump(mode="json") for row in competitors],
            },
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        if len(body) > 36 * 1024 * 1024:
            raise SpeakerError("audio_limit", 413)
        try:
            async with self.client.stream(
                "POST",
                httpx.URL(self.settings.inference_url).join("/v1/meeting-memory"),
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept-Encoding": "identity",
                    "X-Inference-Key": self.settings.inference_key.get_secret_value(),
                    "X-Job-Id": job_public_id,
                    "X-Tenant-Id": tenant_public_id,
                },
                timeout=self.settings.meeting_chunk_timeout_seconds,
            ) as response:
                if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                    raise SpeakerError("model_mismatch", 502)
                limit = 128 * 1024
                declared = response.headers.get("Content-Length")
                if declared is not None and (
                    len(declared) > 12 or not declared.isdecimal() or int(declared) > limit
                ):
                    raise SpeakerError("model_mismatch", 502)
                if response.is_stream_consumed:
                    raw = response.content
                else:
                    buffer = bytearray()
                    async for chunk in response.aiter_raw(chunk_size=65536):
                        if len(buffer) + len(chunk) > limit:
                            raise SpeakerError("model_mismatch", 502)
                        buffer.extend(chunk)
                    raw = bytes(buffer)
                if len(raw) > limit:
                    raise SpeakerError("model_mismatch", 502)
                status = response.status_code
        except httpx.TimeoutException:
            raise SpeakerError("job_timeout", 503) from None
        except httpx.HTTPError:
            raise SpeakerError("inference_unavailable", 503) from None
        if status != 200:
            try:
                code = json.loads(raw)["detail"]["code"]
            except (ValueError, TypeError, KeyError):
                code = None
            if status == 503 and code == "inference_busy":
                raise SpeakerError("inference_busy", 503)
            if (
                status in {400, 413, 415, 422}
                and isinstance(code, str)
                and code
                in {
                    "invalid_audio",
                    "audio_limit",
                    "unsupported_audio",
                    "clipped_audio",
                }
            ):
                raise SpeakerError(code, status)
            raise SpeakerError("inference_unavailable", 503)
        try:
            result = MeetingMemoryResult.model_validate_json(raw)
            if (
                result.input_sha256 != hashlib.sha256(audio).hexdigest()
                or result.input_frames != info.frames
                or result.sample_rate != info.samplerate
                or any(index >= len(contexts) for index in result.accepted_context_indices)
            ):
                raise ValueError("memory_source_mismatch")
        except (ValueError, ValidationError):
            raise SpeakerError("model_mismatch", 502) from None
        return result
