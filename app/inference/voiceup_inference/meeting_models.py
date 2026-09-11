"""Pinned local meeting model identities and immutable bundle validation."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator, Set
from contextlib import contextmanager
from pathlib import Path
from threading import Lock, get_ident
from typing import TYPE_CHECKING

import numpy as np

from voiceup.identity import normalize_embedding

if TYPE_CHECKING:
    from voiceup.audio import Audio

    from .config import Settings
    from .meeting_memory import VoiceMemoryModels

DIARIZATION_ID = "pyannote/speaker-diarization-community-1"
DIARIZATION_REVISION = "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
DIARIZATION_RECIPE = "community-vbx-fa015-v1"
ASR_ID = "Systran/faster-whisper-large-v3"
ASR_REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
DIARIZATION_FILES = frozenset(
    {
        "README.md",
        "config.yaml",
        "embedding/README.md",
        "plda/README.md",
        "embedding/pytorch_model.bin",
        "plda/plda.npz",
        "plda/xvec_transform.npz",
        "segmentation/pytorch_model.bin",
    }
)
ASR_FILES = frozenset(
    {
        "README.md",
        "config.json",
        "model.bin",
        "preprocessor_config.json",
        "tokenizer.json",
        "vocabulary.json",
    }
)


def _checked_path(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("meeting_model_package_invalid")
    return path


def verify_meeting_bundle(
    directory: Path,
    manifest: Path,
    repository: str,
    revision: str,
    expected_paths: Set[str],
) -> None:
    directory, manifest = _checked_path(directory), _checked_path(manifest)
    if (
        not directory.is_dir()
        or not manifest.is_file()
        or manifest.stat().st_size > 65536
    ):
        raise ValueError("meeting_model_package_invalid")
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or type(document.get("schema_version")) is not int
        or document.get("schema_version") != 1
        or document.get("repository") != repository
        or document.get("revision") != revision
        or document.get("license") != ("mit" if repository == ASR_ID else "cc-by-4.0")
        or not isinstance(document.get("files"), list)
        or len(document["files"]) != len(expected_paths)
    ):
        raise ValueError("meeting_model_package_invalid")
    seen = set()
    for row in document["files"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"path", "size_bytes", "sha256"}
            or not isinstance(row["path"], str)
            or row["path"] not in expected_paths
            or row["path"] in seen
            or type(row["size_bytes"]) is not int
            or not 0 < row["size_bytes"] <= 4 * 1024**3
            or not isinstance(row["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
        ):
            raise ValueError("meeting_model_package_invalid")
        seen.add(row["path"])
        path = _checked_path(directory / row["path"])
        if not path.is_file() or path.stat().st_size != row["size_bytes"]:
            raise ValueError("meeting_model_package_invalid")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != row["sha256"]:
                raise ValueError("meeting_model_package_invalid")
    actual = set()
    for path in directory.rglob("*"):
        _checked_path(path)
        if not path.is_dir():
            actual.add(path.relative_to(directory).as_posix())
    if actual != seen:
        raise ValueError("meeting_model_package_invalid")


class _VoiceEmbeddingSession:
    """A thread-owned, expiring encoder; the request owns device cleanup."""

    def __init__(self, models: LocalMeetingModels):
        self._models = models
        self._owner = get_ident()
        self._active = True
        self._upload_attempted = False

    def voice_embedding(self, samples: np.ndarray) -> np.ndarray:
        if not self._active or self._owner != get_ident():
            raise RuntimeError("meeting_embedding_session_invalid")
        models = self._models
        torch = models._torch
        matmul_tf32 = torch.backends.cuda.matmul.allow_tf32
        matmul_precision = torch.get_float32_matmul_precision()
        cudnn_tf32 = torch.backends.cudnn.allow_tf32
        try:
            if not self._upload_attempted:
                self._upload_attempted = True
                models._pipeline.to(models._device)
            with torch.inference_mode():
                output = models._pipeline._embedding(
                    torch.from_numpy(samples.copy()).unsqueeze(0).unsqueeze(0)
                )
            if not isinstance(output, np.ndarray) or output.shape != (1, 256):
                raise ValueError("invalid_meeting_memory_embedding")
            return normalize_embedding(output[0], 256)
        finally:
            torch.backends.cuda.matmul.allow_tf32 = matmul_tf32
            torch.backends.cudnn.allow_tf32 = cudnn_tf32
            torch.set_float32_matmul_precision(matmul_precision)


class LocalMeetingModels:
    """Use local artifacts and release each large GPU model before the next one."""

    def __init__(self, settings: Settings):
        from .errors import InferenceError

        if settings.runtime_profile != "x86_64-cu128":
            raise InferenceError(
                "meeting_runtime_unsupported",
                "Meeting models require the verified CUDA runtime",
                503,
            )
        import torch
        from faster_whisper import WhisperModel
        from pyannote.audio import Pipeline

        verify_meeting_bundle(
            settings.meeting_diarization_dir,
            settings.meeting_diarization_manifest,
            DIARIZATION_ID,
            DIARIZATION_REVISION,
            DIARIZATION_FILES,
        )
        verify_meeting_bundle(
            settings.meeting_asr_dir,
            settings.meeting_asr_manifest,
            ASR_ID,
            ASR_REVISION,
            ASR_FILES,
        )
        self._torch = torch
        self._device = torch.device(settings.device)
        self._voice_embedding_slot = Lock()
        self._pipeline = Pipeline.from_pretrained(
            str(settings.meeting_diarization_dir), token=False
        )
        self._pipeline.instantiate(
            {
                "clustering": {"threshold": 0.6, "Fa": 0.15, "Fb": 0.8},
                "segmentation": {"min_duration_off": 0.0},
            }
        )
        self._asr = WhisperModel(
            str(settings.meeting_asr_dir),
            device="cuda",
            device_index=int(settings.device.split(":")[1]),
            compute_type="int8_float16",
            cpu_threads=4,
            num_workers=1,
            local_files_only=True,
        )
        self._asr.model.unload_model(to_cpu=True)

    def diarize(
        self,
        audio: Audio,
        *,
        max_speakers: int | None = None,
        num_speakers: int | None = None,
    ) -> dict:
        torch = self._torch
        matmul_tf32 = torch.backends.cuda.matmul.allow_tf32
        matmul_precision = torch.get_float32_matmul_precision()
        cudnn_tf32 = torch.backends.cudnn.allow_tf32
        counts = {
            key: value
            for key, value in {
                "max_speakers": max_speakers,
                "num_speakers": num_speakers,
            }.items()
            if value is not None
        }
        try:
            self._pipeline.to(self._device)
            output = self._pipeline(
                {
                    "waveform": torch.from_numpy(audio.samples.copy()).unsqueeze(0),
                    "sample_rate": audio.sample_rate,
                },
                **counts,
            )
            labels = output.speaker_diarization.labels()
            embeddings = output.speaker_embeddings
            if (
                not isinstance(labels, list)
                or len(labels) > 1000
                or any(
                    not isinstance(label, str) or not 0 < len(label.strip()) <= 128
                    for label in labels
                )
                or len(set(labels)) != len(labels)
                or not isinstance(embeddings, np.ndarray)
                or embeddings.shape != (len(labels), 256)
                or embeddings.dtype.kind != "f"
                or not np.isfinite(embeddings).all()
            ):
                raise ValueError("invalid_meeting_tracking_embeddings")
            result = {
                name: [
                    {
                        "start": float(segment.start),
                        "end": float(segment.end),
                        "speaker": str(label),
                    }
                    for segment, _, label in getattr(output, name).itertracks(
                        yield_label=True
                    )
                ]
                for name in ("speaker_diarization", "exclusive_speaker_diarization")
            }
            if {row["speaker"] for row in result["speaker_diarization"]} != set(labels):
                raise ValueError("invalid_meeting_tracking_labels")
            # Native rows are explicitly ordered by diarization.labels(); these
            # WeSpeaker centroids never enter the persistent ECAPA vector space.
            result["speaker_embeddings"] = {
                label: (
                    normalize_embedding(embeddings[index], 256).tolist()
                    if np.any(embeddings[index])
                    else None
                )
                for index, label in enumerate(labels)
            }
            return result
        finally:
            try:
                self._pipeline.to(torch.device("cpu"))
                torch.cuda.empty_cache()
            finally:
                torch.backends.cuda.matmul.allow_tf32 = matmul_tf32
                torch.backends.cudnn.allow_tf32 = cudnn_tf32
                torch.set_float32_matmul_precision(matmul_precision)

    def voice_embedding(self, samples: np.ndarray) -> np.ndarray:
        with self.voice_embedding_session() as encoder:
            return encoder.voice_embedding(samples)

    @contextmanager
    def voice_embedding_session(self) -> Iterator[VoiceMemoryModels]:
        """Keep sequential batch-one probes resident within the HTTP admission slot."""
        if not self._voice_embedding_slot.acquire(blocking=False):
            raise RuntimeError("meeting_embedding_session_busy")
        encoder = _VoiceEmbeddingSession(self)
        torch = self._torch
        matmul_tf32 = torch.backends.cuda.matmul.allow_tf32
        matmul_precision = torch.get_float32_matmul_precision()
        cudnn_tf32 = torch.backends.cudnn.allow_tf32
        try:
            yield encoder
        finally:
            encoder._active = False
            try:
                if encoder._upload_attempted:
                    self._pipeline.to(torch.device("cpu"))
                    torch.cuda.empty_cache()
            finally:
                try:
                    torch.backends.cuda.matmul.allow_tf32 = matmul_tf32
                    torch.backends.cudnn.allow_tf32 = cudnn_tf32
                    torch.set_float32_matmul_precision(matmul_precision)
                finally:
                    self._voice_embedding_slot.release()

    def transcribe(self, audio: Audio, language: str | None) -> dict:
        from dataclasses import asdict

        try:
            self._asr.model.load_model()
            segments, info = self._asr.transcribe(
                audio.samples,
                language=language,
                beam_size=5,
                word_timestamps=True,
                condition_on_previous_text=False,
                vad_filter=False,
            )
            return {
                "segments": [asdict(segment) for segment in segments],
                "language": info.language,
                "language_probability": float(info.language_probability),
            }
        finally:
            self._asr.model.unload_model(to_cpu=True)


def load_meeting_models(settings: Settings) -> LocalMeetingModels:
    return LocalMeetingModels(settings)
