"""Source-bound, versioned meeting quality; the pilot enrollment route stays separate."""

import base64
import binascii
import hashlib
import io
import math
from typing import Literal, Protocol, Self

import numpy as np
import soundfile as sf
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from voiceup.identity import normalize_embedding

from .audio import decode_audio
from .config import Settings
from .errors import InferenceError
from .evidence import _usable
from .meeting_coherence import has_secondary_voice
from .meeting_models import DIARIZATION_ID, DIARIZATION_REVISION
from .model_bundle import MODEL_ID, MODEL_REVISION
from .models import ModelHandles

QUALITY_VERSION = "meeting-natural-context-v1"
MAX_MEMORY_JSON_BYTES = 36 * 1024 * 1024
MAX_MEMORY_WAV_BYTES = 60 * 192000 * 2 + 44


class VoiceMemoryModels(Protocol):
    def voice_embedding(self, samples: np.ndarray) -> np.ndarray: ...


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class FrameRange(Record):
    start: int = Field(ge=0, le=60 * 192000)
    end: int = Field(gt=0, le=60 * 192000)

    @model_validator(mode="after")
    def positive(self) -> Self:
        if self.end <= self.start:
            raise ValueError("invalid_frame_range")
        return self


class Context(FrameRange):
    voiced_ranges: list[FrameRange] = Field(min_length=1, max_length=256)


class Tracking(Record):
    embedding: list[float] = Field(min_length=256, max_length=256)
    dimensions: Literal[256]
    component: Literal["embedding"]
    model_id: Literal["pyannote/speaker-diarization-community-1"]
    model_revision: Literal["3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"]

    @model_validator(mode="after")
    def unit(self) -> Self:
        if not math.isclose(sum(x * x for x in self.embedding), 1, abs_tol=1e-4):
            raise ValueError("invalid_tracking_vector")
        return self


class MemoryRequest(Record):
    audio_base64: str = Field(min_length=1, max_length=MAX_MEMORY_JSON_BYTES)
    sample_rate: int = Field(ge=8000, le=192000)
    contexts: list[Context] = Field(min_length=1, max_length=20)
    target: Tracking
    competitors: list[Tracking] = Field(max_length=999)


def _wav(pcm: np.ndarray, rate: int) -> bytes:
    stream = io.BytesIO()
    sf.write(stream, pcm, rate, format="WAV", subtype="PCM_16")
    return stream.getvalue()


def _mask_ranges(mask: np.ndarray) -> list[dict]:
    changes = np.diff(np.pad(mask.astype(np.int8), (1, 1)))
    return [
        {"start": int(a), "end": int(b)}
        for a, b in zip(
            np.flatnonzero(changes == 1), np.flatnonzero(changes == -1), strict=True
        )
    ]


def _starts(first: int, last: int, length: int, step: int) -> list[int]:
    starts = list(range(first, last - length + 1, step))
    if starts and starts[-1] + length < last:
        starts.append(last - length)
    return starts


def verify_memory(
    payload: dict, models: VoiceMemoryModels, pilot: ModelHandles, settings: Settings
) -> dict:
    try:
        request = MemoryRequest.model_validate(payload)
        body = base64.b64decode(request.audio_base64, validate=True)
        if not body or len(body) > MAX_MEMORY_WAV_BYTES:
            raise ValueError("invalid_memory_bytes")
        with sf.SoundFile(io.BytesIO(body)) as source:
            rate, frames = source.samplerate, source.frames
            if (
                source.format != "WAV"
                or source.subtype != "PCM_16"
                or source.channels != 1
                or rate != request.sample_rate
                or not 0 < frames <= rate * 60
            ):
                raise ValueError("invalid_memory_audio")
            original = source.read(dtype="int16")
        previous = 0
        for context in request.contexts:
            if not (
                previous <= context.start < context.end <= frames
                and 3 * rate <= context.end - context.start <= 8 * rate
            ):
                raise ValueError("invalid_memory_context")
            previous = context.end
            cursor = context.start
            for span in context.voiced_ranges:
                if span.start < cursor or span.end > context.end:
                    raise ValueError("invalid_memory_voice")
                cursor = span.end
    except (
        ValidationError,
        ValueError,
        RuntimeError,
        binascii.Error,
        sf.LibsndfileError,
    ):
        raise InferenceError(
            "validation_error", "Invalid meeting memory request", 422
        ) from None

    result = {
        "input_sha256": hashlib.sha256(body).hexdigest(),
        "retained_sha256": None,
        "input_frames": frames,
        "sample_rate": rate,
        "quality_version": QUALITY_VERSION,
        "status": "insufficient_speech",
        "accepted_context_indices": [],
        "validated_ranges": [],
        "validated_seconds": 0.0,
        "windows_count": 0,
        "device": settings.device,
        "embedding192": None,
        "memory_embedding": None,
        "ecapa_model_id": MODEL_ID,
        "ecapa_model_revision": MODEL_REVISION,
    }
    try:
        audio = decode_audio(
            body, settings.model_copy(update={"max_duration_seconds": 60.0})
        )
    except InferenceError as exc:
        if exc.code == "clipped_audio":
            result["status"] = "clipped_audio"
            return result
        raise
    population = np.asarray(
        [request.target.embedding, *[x.embedding for x in request.competitors]],
        dtype=np.float64,
    )
    cache: dict[tuple[int, int], np.ndarray] = {}

    def encode(first: int, last: int) -> np.ndarray:
        key = (first, last)
        if key not in cache:
            cache[key] = normalize_embedding(
                models.voice_embedding(audio.samples[first:last]), 256
            )
        return cache[key]

    def scores(first: int, last: int) -> np.ndarray:
        return population @ encode(first, last)

    def supports(values: np.ndarray) -> bool:
        return bool(
            values[0] >= 0.55
            and (len(values) == 1 or values[0] - max(values[1:]) >= 0.1)
        )

    vad_mask = np.zeros(frames, dtype=bool)
    for start, end in pilot.vad.speech_spans(audio.samples, 16000):
        if not (
            math.isfinite(start)
            and math.isfinite(end)
            and 0 <= start < end <= audio.duration
        ):
            raise ValueError("invalid_memory_vad")
        vad_mask[math.ceil(start * rate) : min(frames, math.floor(end * rate))] = True
    retained = np.zeros(frames, dtype=bool)
    accepted = []
    seen = set()
    for index, context in enumerate(request.contexts):
        pcm_hash = hashlib.sha256(
            original[context.start : context.end].tobytes()
        ).hexdigest()
        if pcm_hash in seen:
            continue
        seen.add(pcm_hash)
        first = math.ceil(context.start * 16000 / rate)
        last = math.floor(context.end * 16000 / rate)
        samples = audio.samples[first:last]
        if not _usable(samples) or len(samples) < 48000:
            continue
        if not supports(scores(first, last)):
            result["status"] = "inconsistent_audio"
            continue
        if not all(
            supports(scores(start, start + 48000))
            for start in _starts(first, last, 48000, 48000)
        ):
            result["status"] = "inconsistent_audio"
            continue
        clean = np.zeros(frames, dtype=bool)
        for span in context.voiced_ranges:
            clean[span.start : span.end] = True
        clean &= vad_mask
        for start in _starts(first, last, 24000, 8000):
            values = scores(start, start + 24000)
            order = np.argsort(values)[::-1]
            if (
                len(order) > 1
                and order[0] != 0
                and values[order[0]] >= 0.45
                and values[order[0]] - values[order[1]] >= 0.1
            ):
                # Remove all possibly covered original frames; this is abstention,
                # never a lower-threshold assignment to the alternative person.
                clean[
                    math.floor(start * rate / 16000) : math.ceil(
                        (start + 24000) * rate / 16000
                    )
                ] = False
        if clean.any():
            retained |= clean
            accepted.append(index)
    seconds = int(retained.sum()) / rate
    if seconds < 3:
        return result
    retained_body = _wav(original[retained], rate)
    final_audio = decode_audio(
        retained_body, settings.model_copy(update={"max_duration_seconds": 60.0})
    )
    final_speech_spans = tuple(pilot.vad.speech_spans(final_audio.samples, 16000))
    if has_secondary_voice(
        final_audio.samples,
        models.voice_embedding,
        final_speech_spans,
    ) or has_secondary_voice(
        final_audio.samples,
        lambda window: pilot.embedder.encode(window, 16000),
        final_speech_spans,
        dimensions=192,
    ):
        result["status"] = "inconsistent_audio"
        return result
    vector192 = normalize_embedding(
        pilot.embedder.encode(final_audio.samples, 16000), 192
    )
    vector256 = normalize_embedding(models.voice_embedding(final_audio.samples), 256)
    result.update(
        {
            "status": "usable",
            "retained_sha256": hashlib.sha256(retained_body).hexdigest(),
            "accepted_context_indices": accepted,
            "validated_ranges": _mask_ranges(retained),
            "validated_seconds": seconds,
            "windows_count": len(accepted),
            "embedding192": vector192.tolist(),
            "memory_embedding": {
                "embedding": vector256.tolist(),
                "dimensions": 256,
                "component": "embedding",
                "model_id": DIARIZATION_ID,
                "model_revision": DIARIZATION_REVISION,
            },
        }
    )
    return result
