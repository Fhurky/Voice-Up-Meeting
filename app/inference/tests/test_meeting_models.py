"""Meeting model identity and path checks use real bounded filesystem packages."""

import hashlib
import json

import pytest

from voiceup_inference.meeting_models import ASR_ID, ASR_REVISION, verify_meeting_bundle


@pytest.fixture
def bundle(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    contents = {"README.md": b"license", "config.json": b"{}", "model.bin": b"weights"}
    for name, data in contents.items():
        (model / name).write_bytes(data)
    document = {
        "schema_version": 1,
        "repository": ASR_ID,
        "revision": ASR_REVISION,
        "license": "mit",
        "files": [
            {
                "path": name,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in contents.items()
        ],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    return model, manifest, document


def check(model, manifest):
    verify_meeting_bundle(
        model, manifest, ASR_ID, ASR_REVISION, {"README.md", "config.json", "model.bin"}
    )


def test_complete_model_bundle_is_verified_without_writes(bundle):
    model, manifest, _ = bundle
    before = {p.name: p.read_bytes() for p in model.iterdir()}
    check(model, manifest)
    assert {p.name: p.read_bytes() for p in model.iterdir()} == before


@pytest.mark.parametrize(
    "change",
    ["revision", "repository", "path", "duplicate", "missing", "corrupt", "extra"],
)
def test_wrong_model_package_is_rejected(bundle, change):
    model, manifest, document = bundle
    if change in {"revision", "repository"}:
        document[change] = "untrusted"
    elif change == "path":
        document["files"][0]["path"] = "../outside"
    elif change == "duplicate":
        document["files"][1] = document["files"][0]
    elif change == "missing":
        (model / "config.json").unlink()
    elif change == "corrupt":
        (model / "model.bin").write_bytes(b"altered")
    else:
        (model / "extra.json").write_bytes(b"extra")
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="meeting_model_package_invalid"):
        check(model, manifest)


def test_unsupported_meeting_profile_fails_before_loading_optional_dependencies():
    from voiceup_inference.config import Settings
    from voiceup_inference.errors import InferenceError
    from voiceup_inference.meeting_models import LocalMeetingModels

    settings = Settings(
        internal_key="x" * 32, device="cpu", runtime_profile="x86_64-cpu"
    )
    with pytest.raises(InferenceError) as captured:
        LocalMeetingModels(settings)
    assert captured.value.code == "meeting_runtime_unsupported"


def test_local_constructor_applies_recorded_clustering_recipe(monkeypatch):
    from types import SimpleNamespace

    import faster_whisper
    from pyannote.audio import Pipeline

    from voiceup_inference import meeting_models
    from voiceup_inference.config import Settings
    from voiceup_inference.meeting_runtime import model_identity

    parameters = []

    class PipelineFixture:
        def instantiate(self, params):
            parameters.append(params)
            return self

    def load_pipeline(path, *, token):
        assert token is False
        return PipelineFixture()

    def load_whisper(
        path,
        *,
        device,
        device_index,
        compute_type,
        cpu_threads,
        num_workers,
        local_files_only,
    ):
        assert local_files_only is True and compute_type == "int8_float16"
        return SimpleNamespace(
            model=SimpleNamespace(unload_model=lambda *, to_cpu: None)
        )

    monkeypatch.setattr(meeting_models, "verify_meeting_bundle", lambda *args: None)
    monkeypatch.setattr(Pipeline, "from_pretrained", load_pipeline)
    monkeypatch.setattr(faster_whisper, "WhisperModel", load_whisper)
    meeting_models.LocalMeetingModels(
        Settings(internal_key="x" * 32, device="cuda:0", runtime_profile="x86_64-cu128")
    )
    assert parameters == [
        {
            "clustering": {"threshold": 0.6, "Fa": 0.15, "Fb": 0.8},
            "segmentation": {"min_duration_off": 0.0},
        }
    ]
    assert model_identity()["diarization"]["recipe"] == "community-vbx-fa015-v1"


def test_diarization_restores_the_existing_pilot_precision_flags(monkeypatch):
    from types import SimpleNamespace

    import numpy as np
    import torch

    from voiceup.audio import Audio
    from voiceup_inference.meeting_models import LocalMeetingModels

    monkeypatch.setattr(torch.backends.cuda.matmul, "allow_tf32", True)
    monkeypatch.setattr(torch.backends.cudnn, "allow_tf32", True)
    torch.set_float32_matmul_precision("medium")
    annotation = SimpleNamespace(
        itertracks=lambda *, yield_label: iter([]), labels=lambda: []
    )

    class PipelineFixture:
        def to(self, device):
            return self

        def __call__(self, audio, *, max_speakers=None, num_speakers=None):
            assert audio["waveform"].shape == (1, 16000)
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            return SimpleNamespace(
                speaker_diarization=annotation,
                exclusive_speaker_diarization=annotation,
                speaker_embeddings=np.zeros((0, 256), dtype=np.float64),
            )

    models = object.__new__(LocalMeetingModels)
    models._torch = torch
    models._device = torch.device("cpu")
    models._pipeline = PipelineFixture()
    assert (
        models.diarize(Audio(np.zeros(16000, dtype=np.float32)))["speaker_diarization"]
        == []
    )
    assert torch.backends.cuda.matmul.allow_tf32 is True
    assert torch.backends.cudnn.allow_tf32 is True
    assert torch.get_float32_matmul_precision() == "medium"


def native_tracking_fixture(embeddings, labels):
    from types import SimpleNamespace

    import torch

    from voiceup_inference.meeting_models import LocalMeetingModels

    annotation = SimpleNamespace(
        labels=lambda: labels,
        itertracks=lambda *, yield_label: iter(
            [
                (SimpleNamespace(start=0.0, end=1.0), index, label)
                for index, label in enumerate(labels)
            ]
        ),
    )

    class PipelineFixture:
        def to(self, device):
            return self

        def __call__(self, audio, *, max_speakers=None, num_speakers=None):
            return SimpleNamespace(
                speaker_diarization=annotation,
                exclusive_speaker_diarization=annotation,
                speaker_embeddings=embeddings,
            )

    models = object.__new__(LocalMeetingModels)
    models._torch = torch
    models._device = torch.device("cpu")
    models._pipeline = PipelineFixture()
    return models


def test_native_256_centroids_keep_label_order_and_normalize_independently():
    import numpy as np

    from voiceup.audio import Audio

    native = np.zeros((2, 256), dtype=np.float64)
    native[0, :2] = [3, 4]
    native[1, 1] = 2
    models = native_tracking_fixture(native, ["SPEAKER_02", "SPEAKER_00"])
    result = models.diarize(Audio(np.zeros(16000, dtype=np.float32)))
    assert result["speaker_embeddings"]["SPEAKER_02"] == pytest.approx(
        [0.6, 0.8] + [0.0] * 254
    )
    assert result["speaker_embeddings"]["SPEAKER_00"] == [0.0, 1.0] + [0.0] * 254
    assert native[0, :2].tolist() == [3, 4]


def test_native_zero_padding_has_no_tracking_vector_without_losing_the_turn():
    import numpy as np

    from voiceup.audio import Audio

    native = np.zeros((2, 256), dtype=np.float64)
    native[0, 0] = 3.3386496435549446
    result = native_tracking_fixture(native, ["SPEAKER_00", "SPEAKER_01"]).diarize(
        Audio(np.zeros(16000, dtype=np.float32))
    )
    assert len(result["speaker_diarization"]) == 2
    assert result["speaker_embeddings"]["SPEAKER_01"] is None
    assert result["speaker_embeddings"]["SPEAKER_00"] == [1.0] + [0.0] * 255


@pytest.mark.parametrize(
    "change", ["dimension", "nonfinite", "rows", "duplicate_labels"]
)
def test_invalid_native_tracking_centroid_cannot_be_used(change):
    import numpy as np

    from voiceup.audio import Audio

    native = np.zeros((2, 256), dtype=np.float64)
    native[:, 0] = 1
    labels = ["SPEAKER_00", "SPEAKER_01"]
    if change == "dimension":
        native = native[:, :192]
    elif change == "nonfinite":
        native[0, 0] = np.nan
    elif change == "rows":
        native = native[:1]
    else:
        labels[1] = labels[0]
    with pytest.raises(ValueError):
        native_tracking_fixture(native, labels).diarize(
            Audio(np.zeros(16000, dtype=np.float32))
        )
