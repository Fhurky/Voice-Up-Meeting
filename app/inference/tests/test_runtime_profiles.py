"""Runtime admission doubles establish device contracts, not hardware compatibility."""

import platform
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from voiceup_inference import models
from voiceup_inference.config import Settings
from voiceup_inference.errors import InferenceError

KEY = "test-internal-key-at-least-32-characters"
PROFILES = [("x86_64-cu128", "x86_64", "12.8"), ("aarch64-cu129", "aarch64", "12.9")]
CPU_PROFILES = [("x86_64-cpu", "x86_64"), ("aarch64-cpu", "aarch64")]


class FixtureCuda:
    def __init__(self, available=True, count=1):
        self.available = available
        self.count = count
        self.selected = None
        self.synchronized = []

    def is_available(self):
        return self.available

    def device_count(self):
        return self.count

    def set_device(self, index):
        self.selected = index

    def synchronize(self, index):
        self.synchronized.append(index)


class FixtureTensor:
    def __init__(self, device_type):
        self.device = SimpleNamespace(type=device_type)
        self.added = False

    def __add__(self, value):
        assert value == 1
        self.added = True
        return self

    def item(self):
        assert self.added
        return 2.0


class FixtureTorch:
    def __init__(self, cuda_version, version="2.8.0", available=True, count=1, device_type="cuda"):
        self.cuda = FixtureCuda(available, count)
        self.version = SimpleNamespace(cuda=cuda_version)
        self.__version__ = version
        self.tensor = FixtureTensor(device_type)
        self.allocated_device = None

    def ones(self, size, *, device):
        assert size == 1
        self.allocated_device = device
        return self.tensor


def test_runtime_profile_remains_x86_by_default_and_spark_is_explicit(monkeypatch):
    monkeypatch.delenv("VOICEUP_INFERENCE_RUNTIME_PROFILE", raising=False)
    assert Settings(internal_key=KEY).runtime_profile == "x86_64-cu128"
    monkeypatch.setenv("VOICEUP_INFERENCE_RUNTIME_PROFILE", "aarch64-cu129")
    assert Settings(internal_key=KEY).runtime_profile == "aarch64-cu129"


@pytest.mark.parametrize("profile", ["auto", "cpu", "aarch64-cu128"])
def test_unknown_runtime_profiles_are_rejected(profile):
    with pytest.raises(ValueError):
        Settings(internal_key=KEY, runtime_profile=profile)


@pytest.mark.parametrize(
    "profile,machine,cuda_version",
    PROFILES + [("x86_64-cu128", "AMD64", "12.8"), ("aarch64-cu129", "arm64", "12.9")],
)
def test_matching_profile_requires_cuda_allocation_kernel_and_synchronization(
    monkeypatch, profile, machine, cuda_version
):
    monkeypatch.setattr(platform, "machine", lambda: machine)
    torch = FixtureTorch(cuda_version, version=f"2.8.0+cu{cuda_version.replace('.', '')}")
    models.require_cuda(torch, "cuda:0", profile)
    assert torch.cuda.selected == 0
    assert torch.allocated_device == "cuda:0"
    assert torch.tensor.added
    assert torch.cuda.synchronized == [0]


@pytest.mark.parametrize(
    "profile,machine,cuda_version",
    [("x86_64-cu128", "aarch64", "12.8"), ("aarch64-cu129", "x86_64", "12.9")]
    + [("x86_64-cu128", "", "12.8"), ("aarch64-cu129", "ppc64le", "12.9")],
)
def test_mismatched_or_unknown_architecture_never_allocates(
    monkeypatch, profile, machine, cuda_version
):
    monkeypatch.setattr(platform, "machine", lambda: machine)
    torch = FixtureTorch(cuda_version)
    with pytest.raises(InferenceError) as error:
        models.require_cuda(torch, "cuda:0", profile)
    assert error.value.code == "cuda_runtime_mismatch"
    assert error.value.status_code == 503
    assert torch.allocated_device is None


@pytest.mark.parametrize("profile,machine,cuda_version", PROFILES)
@pytest.mark.parametrize("mismatch", ["torch", "cuda", "cpu_build"])
def test_both_profiles_reject_other_torch_or_cuda_builds(
    monkeypatch, profile, machine, cuda_version, mismatch
):
    monkeypatch.setattr(platform, "machine", lambda: machine)
    torch = FixtureTorch(cuda_version)
    if mismatch == "torch":
        torch.__version__ = "2.8.1"
    elif mismatch == "cuda":
        torch.version.cuda = "12.9" if cuda_version == "12.8" else "12.8"
    else:
        torch.version.cuda = None
    with pytest.raises(InferenceError) as error:
        models.require_cuda(torch, "cuda:0", profile)
    assert error.value.code == "cuda_runtime_mismatch"
    assert torch.allocated_device is None


@pytest.mark.parametrize("profile,machine,cuda_version", PROFILES)
@pytest.mark.parametrize("failure", ["unavailable", "missing_index", "cpu_probe"])
def test_both_profiles_reject_missing_gpu_or_cpu_execution(
    monkeypatch, profile, machine, cuda_version, failure
):
    monkeypatch.setattr(platform, "machine", lambda: machine)
    torch = FixtureTorch(
        cuda_version,
        available=failure != "unavailable",
        device_type="cpu" if failure == "cpu_probe" else "cuda",
    )
    with pytest.raises(InferenceError) as error:
        models.require_cuda(torch, "cuda:1" if failure == "missing_index" else "cuda:0", profile)
    assert error.value.code == "cuda_unavailable"
    assert error.value.status_code == 503


@pytest.mark.parametrize("profile,machine,cuda_version", PROFILES)
def test_cpu_device_is_rejected_for_every_profile(profile, machine, cuda_version):
    with pytest.raises(ValueError):
        Settings(internal_key=KEY, runtime_profile=profile, device="cpu")


@pytest.mark.parametrize("profile,machine,cuda_version", PROFILES)
def test_model_loader_applies_selected_profile_before_loading_both_models(
    monkeypatch, tmp_path, profile, machine, cuda_version
):
    monkeypatch.setattr(platform, "machine", lambda: machine)
    torch = FixtureTorch(cuda_version)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr(models, "verify_bundle", lambda directory: None)

    class FixtureEmbedder:
        def __init__(self, cache_dir, device):
            assert torch.tensor.added
            self.device = device

        def encode(self, samples):
            assert samples.shape == (48000,)
            return np.zeros(192)

    class FixtureVad:
        def __init__(self, jit_path, device):
            assert torch.tensor.added
            self.device = device

        def speech_spans(self, samples):
            assert samples.shape == (16000,)
            return []

    monkeypatch.setattr(models, "OfflineECAPA", FixtureEmbedder)
    monkeypatch.setattr(models, "OfflineSilero", FixtureVad)
    handles = models.load_models(
        Settings(internal_key=KEY, model_dir=tmp_path, runtime_profile=profile)
    )
    assert handles.embedder.device == handles.vad.device == "cuda:0"
    assert torch.cuda.synchronized == [0, 0]


@pytest.mark.parametrize("profile,machine", CPU_PROFILES)
def test_cpu_requires_explicit_matching_device_and_profile(profile, machine):
    assert Settings(internal_key=KEY, runtime_profile=profile, device="cpu").device == "cpu"
    with pytest.raises(ValueError):
        Settings(internal_key=KEY, runtime_profile=profile)


@pytest.mark.parametrize("profile,machine", CPU_PROFILES)
def test_cpu_profile_checks_build_architecture_and_executes_cpu_kernel(
    monkeypatch, profile, machine
):
    monkeypatch.setattr(platform, "machine", lambda: machine)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    torch = FixtureTorch(None, version="2.8.0+cpu", device_type="cpu")
    torch.cuda = object()  # Any attempted CUDA operation is an observable failure.
    models.require_cpu(torch, "cpu", profile)
    assert torch.allocated_device == "cpu"
    assert torch.tensor.added


@pytest.mark.parametrize("profile,machine", CPU_PROFILES)
@pytest.mark.parametrize(
    "mismatch", ["architecture", "platform", "version", "suffix", "cuda_build"]
)
def test_cpu_profile_rejects_incompatible_runtime_before_allocation(
    monkeypatch, profile, machine, mismatch
):
    monkeypatch.setattr(
        platform, "machine", lambda: "ppc64le" if mismatch == "architecture" else machine
    )
    monkeypatch.setattr(platform, "system", lambda: "Darwin" if mismatch == "platform" else "Linux")
    torch = FixtureTorch(None, version="2.8.0+cpu", device_type="cpu")
    torch.cuda = object()
    if mismatch == "version":
        torch.__version__ = "2.8.1+cpu"
    elif mismatch == "suffix":
        torch.__version__ = "2.8.0"
    elif mismatch == "cuda_build":
        torch.version.cuda = "12.8"
    with pytest.raises(InferenceError) as error:
        models.require_cpu(torch, "cpu", profile)
    assert error.value.code == "cpu_runtime_mismatch"
    assert error.value.status_code == 503
    assert torch.allocated_device is None


@pytest.mark.parametrize("failure", ["wrong_device", "wrong_value", "kernel_failure"])
def test_cpu_probe_must_complete_with_cpu_result(monkeypatch, failure):
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    torch = FixtureTorch(None, version="2.8.0+cpu", device_type="cpu")
    if failure == "wrong_device":
        torch.tensor.device.type = "cuda"
    elif failure == "wrong_value":
        torch.tensor.item = lambda: float("nan")
    else:

        def unavailable(size, *, device):
            raise RuntimeError("private-native-error-path")

        torch.ones = unavailable
    with pytest.raises(InferenceError) as error:
        models.require_cpu(torch, "cpu", "x86_64-cpu")
    assert error.value.code == "cpu_unavailable"
    assert "private-native-error-path" not in str(error.value)


@pytest.mark.parametrize("profile,machine", CPU_PROFILES)
def test_cpu_loader_warms_both_models_without_cuda_metrics(monkeypatch, tmp_path, profile, machine):
    monkeypatch.setattr(platform, "machine", lambda: machine)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    torch = FixtureTorch(None, version="2.8.0+cpu", device_type="cpu")
    torch.cuda = object()
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr(models, "verify_bundle", lambda directory: None)

    class CpuEmbedder:
        def __init__(self, cache_dir, device):
            assert cache_dir == tmp_path / "ecapa" and device == "cpu"
            assert torch.tensor.added
            self.warmed = False

        def encode(self, samples, sample_rate=16000):
            assert samples.shape == (48000,) and sample_rate == 16000
            self.warmed = True
            return np.ones(192)

    class CpuVad:
        def __init__(self, jit_path, device):
            assert jit_path == tmp_path / "silero" / "silero_vad.jit" and device == "cpu"
            self.warmed = False

        def speech_spans(self, samples, sample_rate=16000):
            assert samples.shape == (16000,) and sample_rate == 16000
            self.warmed = True
            return []

    monkeypatch.setattr(models, "OfflineECAPA", CpuEmbedder)
    monkeypatch.setattr(models, "OfflineSilero", CpuVad)
    handles = models.load_models(
        Settings(internal_key=KEY, model_dir=tmp_path, runtime_profile=profile, device="cpu")
    )
    assert handles.embedder.warmed and handles.vad.warmed
    assert handles.metrics is None
