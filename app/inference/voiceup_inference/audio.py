"""Bound libsndfile decoding before allocation and reuse reference audio semantics."""

from io import BytesIO
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from voiceup.audio import Audio

from .config import Settings
from .errors import InferenceError


def decode_audio(
    payload: bytes,
    settings: Settings,
    *,
    max_decoded_samples: int = 24_000_000,
    require_mono_pcm16_wav: bool = False,
) -> Audio:
    if not payload:
        raise InferenceError("invalid_audio", "Audio file is empty", 400)
    if len(payload) > settings.max_upload_bytes:
        raise InferenceError("audio_limit", "Audio exceeds the upload size limit", 413)
    wav = (
        len(payload) >= 12
        and payload[:4] in (b"RIFF", b"RF64")
        and payload[8:12] == b"WAVE"
    )
    if not wav and not payload.startswith(b"fLaC"):
        raise InferenceError(
            "unsupported_audio", "Only WAV and FLAC audio are supported", 415
        )
    try:
        with sf.SoundFile(BytesIO(payload)) as source:
            if require_mono_pcm16_wav and (
                source.format != "WAV"
                or source.subtype != "PCM_16"
                or source.channels != 1
            ):
                raise InferenceError(
                    "unsupported_audio", "Meeting chunks require mono PCM16 WAV", 415
                )
            if source.format not in {"WAV", "WAVEX", "RF64", "FLAC"}:
                raise InferenceError(
                    "unsupported_audio", "Only WAV and FLAC audio are supported", 415
                )
            rate, frames, channels = source.samplerate, source.frames, source.channels
            if rate < 8000 or rate > 192000 or not 1 <= channels <= 8 or frames <= 0:
                raise InferenceError(
                    "invalid_audio", "Unsupported audio dimensions", 400
                )
            # Bound the float allocation before decoding. The pilot permits
            # 24 million samples; the separately bounded meeting port supplies its limit.
            if (
                frames / rate > settings.max_duration_seconds
                or frames * channels > max_decoded_samples
            ):
                raise InferenceError(
                    "audio_limit", "Audio exceeds the duration or decode limit", 413
                )
            samples = source.read(frames=frames + 1, dtype="float32", always_2d=True)
    except InferenceError:
        raise
    except (sf.LibsndfileError, RuntimeError, ValueError, OverflowError):
        raise InferenceError(
            "invalid_audio", "Audio file cannot be decoded", 400
        ) from None
    if (
        len(samples) != frames
        or not np.isfinite(samples).all()
        or np.max(np.abs(samples)) > 1
    ):
        raise InferenceError("invalid_audio", "Audio contains invalid PCM samples", 400)
    # Inspect channels before averaging so stereo cancellation cannot hide clipping.
    if float(np.mean(np.abs(samples) >= 0.999)) > 0.05:
        raise InferenceError("clipped_audio", "Audio is heavily clipped")
    mono = samples.mean(axis=1, dtype=np.float32)
    if rate != 16000:
        factor = gcd(rate, 16000)
        mono = resample_poly(mono, 16000 // factor, rate // factor)
    # Polyphase resampling can overshoot at sharp edges. Reject excessive overshoot
    # rather than passing out-of-range values to the reference embedding adapter.
    if np.max(np.abs(mono)) > 1.05:
        raise InferenceError("clipped_audio", "Audio has excessive full-scale peaks")
    return Audio(np.ascontiguousarray(np.clip(mono, -1, 1), dtype=np.float32))
