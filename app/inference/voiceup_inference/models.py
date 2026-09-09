"""Local-only loaders extend the reference adapters without their network paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from voiceup.backends import SileroVAD, SpeechBrainEmbedder

from .errors import InferenceError
from .model_bundle import verify_bundle

if TYPE_CHECKING:
    from .config import Settings


def require_cuda(torch: Any, device: str) -> None:
    if not torch.cuda.is_available():
        raise InferenceError("cuda_unavailable", "CUDA device is unavailable", 503)
    index = int(device.split(":")[1])
    if index >= torch.cuda.device_count():
        raise InferenceError("cuda_unavailable", "Configured CUDA device is unavailable", 503)
    if torch.version.cuda != "12.8" or torch.__version__.split("+")[0] != "2.8.0":
        raise InferenceError("cuda_runtime_mismatch", "Expected PyTorch 2.8.0 with CUDA 12.8", 503)
    torch.cuda.set_device(index)
    # A CUDA allocation and kernel establish more than driver enumeration.
    probe = torch.ones(1, device=device) + 1
    torch.cuda.synchronize(index)
    if probe.device.type != "cuda":
        raise InferenceError("cuda_unavailable", "CUDA execution could not be established", 503)


class OfflineECAPA(SpeechBrainEmbedder):
    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from speechbrain.inference.classifiers import EncoderClassifier
        from speechbrain.utils.fetching import FetchConfig, LocalStrategy

        # Every file is pre-verified by the loader. Source and all pretrainer paths
        # are local; savedir=None avoids writing or copying into the read-only mount.
        self._model = EncoderClassifier.from_hparams(
            source=str(self.cache_dir),
            savedir=None,
            overrides={"pretrained_path": str(self.cache_dir)},
            run_opts={"device": self.device},
            local_strategy=LocalStrategy.NO_LINK,
            fetch_config=FetchConfig(allow_network=False, allow_updates=False),
        )
        self._torch = torch


class OfflineSilero(SileroVAD):
    def __init__(self, jit_path: Path, device: str):
        super().__init__(device=device)
        self.jit_path = jit_path

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from silero_vad import get_speech_timestamps

        self._model = torch.jit.load(str(self.jit_path), map_location=self.device).eval()
        self._timestamps = get_speech_timestamps
        self._torch = torch


@dataclass
class CudaMetrics:
    torch: Any
    device: str

    def begin(self) -> None:
        self.torch.cuda.synchronize(self.device)
        self.torch.cuda.reset_peak_memory_stats(self.device)

    def finish(self) -> dict:
        self.torch.cuda.synchronize(self.device)
        return {
            "gpu_peak_allocated_bytes": int(self.torch.cuda.max_memory_allocated(self.device)),
            "gpu_peak_reserved_bytes": int(self.torch.cuda.max_memory_reserved(self.device)),
            "gpu_memory_scope": "pytorch_process_including_resident_models",
        }


@dataclass
class ModelHandles:
    embedder: Any
    vad: Any
    metrics: CudaMetrics | None = None


def load_models(settings: Settings) -> ModelHandles:
    verify_bundle(settings.model_dir)
    import torch

    require_cuda(torch, settings.device)
    embedder = OfflineECAPA(settings.model_dir / "ecapa", device=settings.device)
    vad = OfflineSilero(settings.model_dir / "silero" / "silero_vad.jit", settings.device)
    # Warmup checks model loading and both CUDA paths. This synthetic input is
    # operational readiness evidence only, never speaker recognition accuracy.
    embedder.encode(np.zeros(3 * 16000, dtype=np.float32))
    vad.speech_spans(np.zeros(16000, dtype=np.float32))
    torch.cuda.synchronize(int(settings.device.split(":")[1]))
    return ModelHandles(embedder, vad, CudaMetrics(torch, settings.device))
