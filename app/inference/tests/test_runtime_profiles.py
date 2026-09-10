"""Runtime admission tests use CUDA doubles; they establish no GPU compatibility."""

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
