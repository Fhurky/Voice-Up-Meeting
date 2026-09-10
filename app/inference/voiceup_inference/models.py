"""Local-only loaders extend the reference adapters without their network paths."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from voiceup.backends import SileroVAD, SpeechBrainEmbedder

from .errors import InferenceError
from .model_bundle import verify_bundle

if TYPE_CHECKING:
    from .config import RuntimeProfile, Settings

RUNTIME_REQUIREMENTS: dict[RuntimeProfile, tuple[str, str]] = {
    "x86_64-cu128": ("x86_64", "12.8"),
    "aarch64-cu129": ("aarch64", "12.9"),
}
CPU_RUNTIME_REQUIREMENTS: dict[RuntimeProfile, str] = {
    "x86_64-cpu": "x86_64",
    "aarch64-cpu": "aarch64",
}


def require_cpu(torch: Any, device: str, runtime_profile: RuntimeProfile) -> None:
    expected_arch = CPU_RUNTIME_REQUIREMENTS.get(runtime_profile)
    machine = platform.machine().lower()
    architecture = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    if (
        device != "cpu"
        or expected_arch is None
        or platform.system() != "Linux"
        or architecture != expected_arch
        or str(torch.__version__) != "2.8.0+cpu"
        or torch.version.cuda is not None
    ):
        raise InferenceError(
            "cpu_runtime_mismatch",
            "Expected matching Linux architecture and PyTorch 2.8.0 CPU build",
            503,
        )
    try:
        # Read back a CPU kernel result; a version string alone cannot establish execution.
        probe = torch.ones(1, device="cpu") + 1
        if probe.device.type != "cpu" or probe.item() != 2.0:
            raise InferenceError("cpu_unavailable", "CPU execution could not be established", 503)
    except (RuntimeError, ValueError, TypeError):
        raise InferenceError(
            "cpu_unavailable", "CPU execution could not be established", 503
        ) from None


def require_cuda(torch: Any, device: str, runtime_profile: RuntimeProfile = "x86_64-cu128") -> None:
    if not torch.cuda.is_available():
        raise InferenceError("cuda_unavailable", "CUDA device is unavailable", 503)
    expected_arch, expected_cuda = RUNTIME_REQUIREMENTS[runtime_profile]
    machine = platform.machine().lower()
    architecture = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    if architecture != expected_arch:
        raise InferenceError(
            "cuda_runtime_mismatch", f"Runtime profile requires {expected_arch} architecture", 503
        )
    index = int(device.split(":")[1])
    if index >= torch.cuda.device_count():
        raise InferenceError("cuda_unavailable", "Configured CUDA device is unavailable", 503)
    if torch.version.cuda != expected_cuda or torch.__version__.split("+")[0] != "2.8.0":
        raise InferenceError(
            "cuda_runtime_mismatch", f"Expected PyTorch 2.8.0 with CUDA {expected_cuda}", 503
        )
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

    if settings.device == "cpu":
        require_cpu(torch, settings.device, settings.runtime_profile)
    else:
        require_cuda(torch, settings.device, settings.runtime_profile)
    embedder = OfflineECAPA(settings.model_dir / "ecapa", device=settings.device)
    vad = OfflineSilero(settings.model_dir / "silero" / "silero_vad.jit", settings.device)
    # Warmup checks model loading on the explicit device. This synthetic input is
    # operational readiness evidence only, never speaker recognition accuracy.
    embedder.encode(np.zeros(3 * 16000, dtype=np.float32))
    vad.speech_spans(np.zeros(16000, dtype=np.float32))
    metrics = None
    if settings.device != "cpu":
        torch.cuda.synchronize(int(settings.device.split(":")[1]))
        metrics = CudaMetrics(torch, settings.device)
    return ModelHandles(embedder, vad, metrics)
