"""Lazy local inference adapters; importing this module downloads no models.

Audio enters each adapter as finite, mono float PCM at 16 kHz. Voice activity
and diarization describe a recording; ECAPA vectors are the input to persistent
speaker identification, not speaker names or calibrated identity probabilities.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any

import numpy as np


def _disable_telemetry() -> None:
    # Preserve an explicit operator choice while making local use private by default.
    os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def _device(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"cpu|cuda(?::\d+)?|mps", value):
        raise ValueError("device must be cpu, cuda, cuda:<index>, or mps")
    return value


def _audio(samples: np.ndarray, sample_rate: int, *, min_samples: int = 1) -> np.ndarray:
    if isinstance(sample_rate, bool) or sample_rate != 16000:
        raise ValueError("Audio must have a sample rate of 16000 Hz")
    array = np.asarray(samples)
    if array.ndim != 1:
        raise ValueError("Audio must be a one-dimensional mono array")
    if array.size < min_samples:
        raise ValueError(f"Audio must contain at least {min_samples / 16000:g} seconds")
    if array.dtype.kind != "f":
        raise ValueError("Audio must be floating-point PCM; decode integer PCM first")
    if not np.isfinite(array).all():
        raise ValueError("Audio must contain only finite samples")
    if np.max(np.abs(array)) > 1.0:
        raise ValueError("Audio PCM samples must be within [-1, 1]")
    # Copy to writable contiguous memory: torch must not alias read-only input.
    return np.array(array, dtype=np.float32, order="C", copy=True)


class SpeechBrainEmbedder:
    """192-dimensional ECAPA-TDNN embeddings from an immutable model revision."""

    repository = "speechbrain/spkrec-ecapa-voxceleb"
    revision = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"
    model_id = f"{repository}@{revision}"
    dimension = 192

    def __init__(self, cache_dir: Path | str = "models/ecapa", device: str = "cpu") -> None:
        self.cache_dir = Path(cache_dir)
        self.device = _device(device)
        self._model: Any = None
        self._torch: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        _disable_telemetry()
        try:
            import torch
            from speechbrain.inference.classifiers import EncoderClassifier
            from speechbrain.utils.fetching import FetchConfig, LocalStrategy
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "ECAPA dependencies are unavailable. Run `uv sync --extra ml` "
                "to install the supported PyTorch and SpeechBrain versions."
            ) from exc

        # Revision-specific directories prevent an old cached hyperparams file from
        # overriding a newly pinned revision. COPY avoids Windows symlink privileges.
        self._model = EncoderClassifier.from_hparams(
            source=self.repository,
            savedir=str(self.cache_dir / self.revision),
            run_opts={"device": self.device},
            local_strategy=LocalStrategy.COPY,
            fetch_config=FetchConfig(revision=self.revision),
        )
        self._torch = torch

    def encode(self, samples: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        audio = _audio(samples, sample_rate, min_samples=16000)
        self._load()
        waveform = self._torch.from_numpy(audio).unsqueeze(0).to(self.device)
        with self._torch.inference_mode():
            output = self._model.encode_batch(waveform, normalize=False)
        vector = np.asarray(output.detach().cpu().numpy(), dtype=np.float32).reshape(-1)
        if vector.size != self.dimension or not np.isfinite(vector).all():
            raise RuntimeError("ECAPA returned an invalid 192-dimensional speaker embedding")
        norm = float(np.linalg.norm(vector.astype(np.float64)))
        if not np.isfinite(norm) or norm <= 1e-12:
            raise RuntimeError("ECAPA returned a zero or invalid speaker embedding")
        return (vector / norm).astype(np.float32)


class SileroVAD:
    """Speech intervals from the model bundled in the installed silero-vad package."""

    def __init__(self, device: str = "cpu") -> None:
        self.device = _device(device)
        self._model: Any = None
        self._timestamps: Any = None
        self._torch: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        _disable_telemetry()
        try:
            import torch
            from silero_vad import get_speech_timestamps, load_silero_vad
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "Silero VAD dependencies are unavailable. Run `uv sync --extra ml`."
            ) from exc
        self._model = load_silero_vad(onnx=False).to(self.device)
        self._timestamps = get_speech_timestamps
        self._torch = torch

    def speech_spans(
        self, samples: np.ndarray, sample_rate: int = 16000
    ) -> list[tuple[float, float]]:
        audio = _audio(samples, sample_rate)
        self._load()
        waveform = self._torch.from_numpy(audio).to(self.device)
        with self._torch.inference_mode():
            # Sample indices avoid Silero's default 0.1-second output rounding.
            spans = self._timestamps(
                waveform, self._model, sampling_rate=sample_rate, return_seconds=False
            )
        result = []
        for span in spans:
            start, end = float(span["start"]), float(span["end"])
            if not np.isfinite([start, end]).all() or not 0 <= start < end <= audio.size:
                raise RuntimeError("Silero VAD returned an invalid speech interval")
            result.append((start / sample_rate, end / sample_rate))
        return result


class PyannoteDiarizer:
    """Community-1 local speaker turns, preserving simultaneous speech tracks."""

    model_id = "pyannote/speaker-diarization-community-1"
    revision = "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"

    def __init__(self, device: str = "cpu", token: str | None = None) -> None:
        self.device = _device(device)
        if token is not None and (not isinstance(token, str) or not token.strip()):
            raise ValueError("token must be a nonempty string or None")
        self._token = token
        self._pipeline: Any = None
        self._torch: Any = None

    def _load(self) -> None:
        if self._pipeline is not None:
            return
        _disable_telemetry()
        try:
            import torch
            from pyannote.audio import Pipeline
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "Diarization dependencies are unavailable. "
                "Run `uv sync --extra ml --extra diarization`."
            ) from exc
        try:
            pipeline = Pipeline.from_pretrained(
                self.model_id,
                revision=self.revision,
                token=self._token or os.environ.get("HF_TOKEN"),
            )
        except Exception:
            # Do not relay hub exceptions: request diagnostics may contain tokens.
            raise RuntimeError(
                "Could not load Community-1. Accept the model conditions at "
                "https://huggingface.co/pyannote/speaker-diarization-community-1 "
                "and set HF_TOKEN to an access token with model read access. "
                "Also check network access and the installed diarization dependencies."
            ) from None
        if pipeline is None:
            raise RuntimeError("Community-1 was not loaded; check model access and HF_TOKEN")
        pipeline.to(torch.device(self.device))
        self._pipeline = pipeline
        self._torch = torch

    def diarize(
        self,
        samples: np.ndarray,
        sample_rate: int = 16000,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> list[tuple[float, float, str]]:
        audio = _audio(samples, sample_rate)
        counts = {
            "num_speakers": num_speakers,
            "min_speakers": min_speakers,
            "max_speakers": max_speakers,
        }
        for name, value in counts.items():
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
            ):
                raise ValueError(f"{name} must be a positive integer")
        if min_speakers is not None and max_speakers is not None and min_speakers > max_speakers:
            raise ValueError("min_speakers must not exceed max_speakers")
        if num_speakers is not None:
            if min_speakers is not None and num_speakers < min_speakers:
                raise ValueError("num_speakers must not be below min_speakers")
            if max_speakers is not None and num_speakers > max_speakers:
                raise ValueError("num_speakers must not exceed max_speakers")
        self._load()
        # Pyannote owns device placement; its in-memory input contract uses [C,T].
        waveform = self._torch.from_numpy(audio).unsqueeze(0)
        with self._torch.inference_mode():
            output = self._pipeline(
                {"waveform": waveform, "sample_rate": sample_rate},
                **{name: value for name, value in counts.items() if value is not None},
            )
        if not hasattr(output, "speaker_diarization"):
            raise RuntimeError(
                "Unexpected pyannote output; install the supported version with "
                "`uv sync --extra ml --extra diarization`."
            )
        turns = []
        duration = audio.size / sample_rate
        for segment, _, label in output.speaker_diarization.itertracks(yield_label=True):
            start, end = float(segment.start), float(segment.end)
            if not np.isfinite([start, end]).all() or not start < end:
                raise RuntimeError("Pyannote returned an invalid speaker interval")
            # Model padding can extend turns beyond the actual source samples.
            start, end = max(0.0, start), min(duration, end)
            if start < end:
                turns.append((start, end, str(label)))
        return turns
