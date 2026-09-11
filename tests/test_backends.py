"""Adapter contracts with local doubles: these tests never download model files."""

from contextlib import nullcontext
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from voiceup.audio import Turn, validate_turns
from voiceup.backends import PyannoteDiarizer, SileroVAD, SpeechBrainEmbedder


class Tensor:
    def __init__(self, values):
        self.values = np.asarray(values)

    def unsqueeze(self, axis):
        return Tensor(np.expand_dims(self.values, axis))

    def to(self, device):
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.values


@pytest.fixture
def fake_torch(monkeypatch):
    module = ModuleType("torch")
    module.from_numpy = Mock(side_effect=Tensor)
    module.inference_mode = Mock(side_effect=nullcontext)
    module.device = Mock(side_effect=lambda value: value)
    monkeypatch.setitem(sys.modules, "torch", module)
    return module


def module_with(monkeypatch, name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


@pytest.fixture
def samples():
    return np.full(16000, 0.01, dtype=np.float32)


def test_construction_is_lazy(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "torch", None)
    cache = tmp_path / "not-created"
    assert SpeechBrainEmbedder(cache)._model is None
    assert SileroVAD()._model is None
    assert PyannoteDiarizer()._pipeline is None
    assert not cache.exists()


@pytest.mark.parametrize("device", ["", "gpu", "cuda:-1", "cpu:0", 1])
@pytest.mark.parametrize("backend", [SpeechBrainEmbedder, SileroVAD, PyannoteDiarizer])
def test_invalid_device(backend, device):
    with pytest.raises(ValueError, match="device"):
        backend(device=device)


@pytest.mark.parametrize(
    "audio,rate,pattern",
    [
        (np.zeros((16000, 1), dtype=np.float32), 16000, "mono"),
        (np.zeros(16000, dtype=np.float32), 8000, "16000"),
        (np.zeros(16000, dtype=np.int16), 16000, "floating"),
        (np.full(16000, np.nan), 16000, "finite"),
        (np.full(16000, np.inf), 16000, "finite"),
        (np.full(16000, 1.01), 16000, "within"),
        (np.zeros(15999, dtype=np.float32), 16000, "at least 1 seconds"),
    ],
)
def test_embedder_rejects_invalid_audio_before_loading(audio, rate, pattern):
    embedder = SpeechBrainEmbedder()
    embedder._load = Mock(side_effect=AssertionError("must validate before model load"))
    with pytest.raises(ValueError, match=pattern):
        embedder.encode(audio, rate)
    embedder._load.assert_not_called()


def test_ecapa_revision_copy_contract_and_normalized_embedding(
    monkeypatch, fake_torch, tmp_path, samples
):
    model = SimpleNamespace(encode_batch=Mock(return_value=Tensor(np.ones((1, 1, 192)))))
    from_hparams = Mock(return_value=model)
    module_with(
        monkeypatch,
        "speechbrain.inference.classifiers",
        EncoderClassifier=SimpleNamespace(from_hparams=from_hparams),
    )
    copy = object()
    module_with(
        monkeypatch,
        "speechbrain.utils.fetching",
        FetchConfig=SimpleNamespace,
        LocalStrategy=SimpleNamespace(COPY=copy),
    )
    embedder = SpeechBrainEmbedder(tmp_path)
    vector = embedder.encode(samples)
    assert vector.shape == (192,)
    assert vector.dtype == np.float32
    assert np.isfinite(vector).all()
    assert np.linalg.norm(vector) == pytest.approx(1.0)
    call = from_hparams.call_args.kwargs
    assert call["source"] == embedder.repository
    assert call["fetch_config"].revision == embedder.revision
    assert call["savedir"] == str(tmp_path / embedder.revision)
    assert call["local_strategy"] is copy
    assert call["run_opts"] == {"device": "cpu"}
    assert embedder.revision in embedder.model_id
    assert model.encode_batch.call_args.args[0].values.shape == (1, 16000)
    assert model.encode_batch.call_args.kwargs == {"normalize": False}
    assert fake_torch.inference_mode.call_count == 1
    embedder.encode(samples)
    from_hparams.assert_called_once()


@pytest.mark.parametrize("vector", [np.zeros(192), np.full(192, np.nan), np.ones(191)])
def test_invalid_embedding_never_reaches_identity_store(fake_torch, samples, vector):
    embedder = SpeechBrainEmbedder()
    embedder._torch = fake_torch
    embedder._model = SimpleNamespace(encode_batch=Mock(return_value=Tensor(vector)))
    with pytest.raises(RuntimeError, match="embedding"):
        embedder.encode(samples)


@pytest.mark.parametrize(
    "backend,method,extra",
    [
        (SpeechBrainEmbedder, "encode", "--extra ml"),
        (SileroVAD, "speech_spans", "--extra ml"),
        (PyannoteDiarizer, "diarize", "--extra diarization"),
    ],
)
def test_missing_optional_dependencies_have_install_command(
    monkeypatch, samples, backend, method, extra
):
    monkeypatch.setitem(sys.modules, "torch", None)
    with pytest.raises(RuntimeError, match=extra):
        getattr(backend(), method)(samples)


def test_silero_uses_installed_model_and_precise_sample_offsets(monkeypatch, fake_torch, samples):
    model = SimpleNamespace(to=Mock())
    model.to.return_value = model
    loader = Mock(return_value=model)
    timestamps = Mock(return_value=[{"start": 161, "end": 7999}])
    module_with(
        monkeypatch,
        "silero_vad",
        load_silero_vad=loader,
        get_speech_timestamps=timestamps,
    )
    vad = SileroVAD()
    assert vad.speech_spans(samples) == [(161 / 16000, 7999 / 16000)]
    loader.assert_called_once_with(onnx=False)
    model.to.assert_called_once_with("cpu")
    assert timestamps.call_args.kwargs == {"sampling_rate": 16000, "return_seconds": False}
    assert timestamps.call_args.args[0].values.shape == (16000,)
    timestamps.return_value = []
    assert vad.speech_spans(samples) == []
    loader.assert_called_once()


@pytest.mark.parametrize(
    "span", [{"start": -1, "end": 3}, {"start": 2, "end": 1}, {"start": 0, "end": 16001}]
)
def test_invalid_vad_intervals_fail(fake_torch, samples, span):
    vad = SileroVAD()
    vad._torch = fake_torch
    vad._model = object()
    vad._timestamps = Mock(return_value=[span])
    with pytest.raises(RuntimeError, match="interval"):
        vad.speech_spans(samples)


def test_pyannote_preserves_overlap_and_uses_current_api(monkeypatch, fake_torch, samples):
    annotation = SimpleNamespace(
        itertracks=Mock(
            return_value=[
                (SimpleNamespace(start=0.1, end=0.8), 0, "SPEAKER_00"),
                (SimpleNamespace(start=0.4, end=0.9), 1, "SPEAKER_01"),
            ]
        )
    )
    output = SimpleNamespace(
        speaker_diarization=annotation,
        exclusive_speaker_diarization=SimpleNamespace(itertracks=Mock(side_effect=AssertionError)),
    )
    pipeline = Mock(return_value=output)
    loader = Mock(return_value=pipeline)
    module_with(monkeypatch, "pyannote.audio", Pipeline=SimpleNamespace(from_pretrained=loader))
    monkeypatch.setenv("HF_TOKEN", "test-not-a-real-token")
    monkeypatch.delenv("PYANNOTE_METRICS_ENABLED", raising=False)
    monkeypatch.delenv("HF_HUB_DISABLE_TELEMETRY", raising=False)
    diarizer = PyannoteDiarizer(device="cuda:0")
    turns = diarizer.diarize(samples, min_speakers=2, max_speakers=50)
    assert turns == [(0.1, 0.8, "SPEAKER_00"), (0.4, 0.9, "SPEAKER_01")]
    loader.assert_called_once_with(
        diarizer.model_id, revision=diarizer.revision, token="test-not-a-real-token"
    )
    pipeline.to.assert_called_once_with("cuda:0")
    assert pipeline.call_args.kwargs == {"min_speakers": 2, "max_speakers": 50}
    assert pipeline.call_args.args[0]["waveform"].values.shape == (1, 16000)
    assert pipeline.call_args.args[0]["sample_rate"] == 16000
    annotation.itertracks.assert_called_once_with(yield_label=True)
    assert os.environ["PYANNOTE_METRICS_ENABLED"] == "0"
    assert os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"
    diarizer.diarize(samples, num_speakers=2)
    loader.assert_called_once()


@pytest.mark.parametrize(
    "counts",
    [
        {"num_speakers": 0},
        {"num_speakers": True},
        {"min_speakers": 1.5},
        {"max_speakers": -1},
        {"min_speakers": 5, "max_speakers": 2},
        {"num_speakers": 2, "min_speakers": 3},
        {"num_speakers": 4, "max_speakers": 3},
    ],
)
def test_invalid_speaker_counts_fail_before_loading(samples, counts):
    diarizer = PyannoteDiarizer()
    diarizer._load = Mock(side_effect=AssertionError("must validate before model load"))
    with pytest.raises(ValueError):
        diarizer.diarize(samples, **counts)
    diarizer._load.assert_not_called()


def test_pyannote_model_access_errors_do_not_expose_credentials(monkeypatch, fake_torch, samples):
    loader = Mock(side_effect=RuntimeError("request failed with token secret-value"))
    module_with(monkeypatch, "pyannote.audio", Pipeline=SimpleNamespace(from_pretrained=loader))
    with pytest.raises(RuntimeError, match="Accept the model conditions") as exc:
        PyannoteDiarizer(token="secret-value").diarize(samples)
    assert "secret-value" not in str(exc.value)
    assert exc.value.__suppress_context__


def test_legacy_pyannote_output_fails_explicitly(fake_torch, samples):
    diarizer = PyannoteDiarizer()
    diarizer._torch = fake_torch
    diarizer._pipeline = Mock(return_value=SimpleNamespace(itertracks=Mock()))
    with pytest.raises(RuntimeError, match="supported version"):
        diarizer.diarize(samples)


def diarizer_with_turns(fake_torch, turns):
    class Annotation:
        def itertracks(self, yield_label=False):
            assert yield_label is True
            for track, (start, end, label) in enumerate(turns):
                yield SimpleNamespace(start=start, end=end), track, label

    def pipeline(audio, *, num_speakers=None, min_speakers=None, max_speakers=None):
        return SimpleNamespace(speaker_diarization=Annotation())

    diarizer = PyannoteDiarizer()
    diarizer._torch = fake_torch
    diarizer._pipeline = pipeline
    return diarizer


def test_pyannote_intersects_observed_padded_end_with_source_duration(fake_torch):
    # Observed Community-1 output on both CPU and CUDA for an 18.8-second input.
    raw = [(16.75409375, 18.96471875, "SPEAKER_01")]
    samples = np.full(300800, 0.01, dtype=np.float32)
    diarizer = diarizer_with_turns(fake_torch, raw)
    turns = diarizer.diarize(samples)
    assert turns == [(16.75409375, 18.8, "SPEAKER_01")]
    assert validate_turns([Turn(*turn) for turn in turns], samples.size / 16000) == [
        Turn(16.75409375, 18.8, "SPEAKER_01")
    ]
    assert raw == [(16.75409375, 18.96471875, "SPEAKER_01")]


@pytest.mark.parametrize(
    "start,end,expected",
    [
        (-0.2, 0.3, [(0.0, 0.3, "A")]),
        (-0.2, 1.2, [(0.0, 1.0, "A")]),
        (0.0, 1.0, [(0.0, 1.0, "A")]),
        (0.0, 1.0000625, [(0.0, 1.0, "A")]),
        (-1.0, -0.1, []),
        (-1.0, 0.0, []),
        (1.0, 1.2, []),
        (1.1, 1.2, []),
        (0.9999375, 1.2, [(0.9999375, 1.0, "A")]),
    ],
)
def test_pyannote_keeps_only_positive_source_intersections(
    fake_torch, samples, start, end, expected
):
    diarizer = diarizer_with_turns(fake_torch, [(start, end, "A")])
    assert diarizer.diarize(samples) == expected


@pytest.mark.parametrize(
    "start,end",
    [
        (np.nan, 0.5),
        (0.1, np.nan),
        (-np.inf, 0.5),
        (0.0, np.inf),
        (0.9, 0.2),
        (0.5, 0.5),
        (-0.5, -0.5),
        (-0.2, -0.3),
    ],
)
def test_invalid_pyannote_intervals_still_fail_before_intersection(fake_torch, samples, start, end):
    diarizer = diarizer_with_turns(fake_torch, [(start, end, "A")])
    with pytest.raises(RuntimeError, match="invalid speaker interval"):
        diarizer.diarize(samples)


def test_pyannote_source_intersection_preserves_overlapping_tracks(fake_torch, samples):
    diarizer = diarizer_with_turns(fake_torch, [(-0.1, 0.6, "A"), (0.4, 1.3, "B"), (0.4, 0.7, "C")])
    assert diarizer.diarize(samples) == [
        (0.0, 0.6, "A"),
        (0.4, 1.0, "B"),
        (0.4, 0.7, "C"),
    ]
