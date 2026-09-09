"""HTTP and audio quality tests with explicit deterministic model doubles."""

import json
import logging
from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from voiceup_inference.api import create_app
from voiceup_inference.config import Settings
from voiceup_inference.errors import InferenceError
from voiceup_inference.model_bundle import MODEL_ID, MODEL_REVISION
from voiceup_inference.runtime import InferenceRuntime, ModelHandles, require_cuda

HEADERS = {
    "X-Inference-Key": "test-internal-key-at-least-32-characters",
    "X-Job-Id": "f6a912e0-f57e-4a2c-bde1-271d2ef216c8",
    "X-Tenant-Id": "e2d21086-43b1-4b51-ae0b-951f1e843735",
    "Content-Type": "application/octet-stream",
}


def audio_file(seconds=12, *, format="WAV", rate=16000, amplitude=0.1):
    # Tone is a decode/quality fixture only; the VAD double returns its whole span.
    samples = amplitude * np.sin(2 * np.pi * 220 * np.arange(round(seconds * rate)) / rate)
    stream = BytesIO()
    sf.write(stream, samples, rate, format=format, subtype="PCM_16")
    return stream.getvalue()


class FixtureEmbedder:
    model_id = f"{MODEL_ID}@{MODEL_REVISION}"
    dimension = 192

    def __init__(self, inconsistent=False):
        self.calls = 0
        self.inconsistent = inconsistent

    def encode(self, samples, sample_rate=16000):
        vector = np.zeros(192, dtype=np.float32)
        vector[self.calls % 2 if self.inconsistent else 0] = 1
        self.calls += 1
        return vector


class FixtureVAD:
    def speech_spans(self, samples, sample_rate=16000):
        return [(0.0, len(samples) / sample_rate)]


def runtime_and_app(**settings_overrides):
    settings = Settings(internal_key=HEADERS["X-Inference-Key"], **settings_overrides)
    embedder = FixtureEmbedder()
    runtime = InferenceRuntime(settings, loader=lambda _: ModelHandles(embedder, FixtureVAD()))
    return runtime, create_app(settings, runtime), embedder


@pytest.mark.parametrize("format", ["WAV", "FLAC"])
def test_enrollment_http_contract_and_resampling(format):
    _, app, _ = runtime_and_app()
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200
        response = client.post(
            "/v1/embeddings?purpose=enroll",
            headers=HEADERS,
            content=audio_file(format=format, rate=24000),
        )
    assert response.status_code == 200
    result = response.json()
    assert result["model_id"] == MODEL_ID
    assert result["model_revision"] == MODEL_REVISION
    assert result["dimensions"] == 192
    assert len(result["embedding"]) == 192
    assert np.linalg.norm(result["embedding"]) == pytest.approx(1)
    assert result["speech_seconds"] == pytest.approx(12)
    assert result["windows_count"] == 2
    assert result["device"] == "cuda:0"  # Contract fixture, not GPU evidence.
    assert "gpu_peak_allocated_bytes" not in result["quality"]
    assert "gpu_peak_reserved_bytes" not in result["quality"]
    assert result["quality"]["execution_seconds"] > 0


@pytest.mark.parametrize(
    "purpose,seconds,expected",
    [
        ("identify", 3, 200),
        ("identify", 2.9, 422),
        ("enroll", 9, 422),
        ("enroll", 10, 200),
    ],
)
def test_minimum_usable_speech(purpose, seconds, expected):
    _, app, _ = runtime_and_app()
    with TestClient(app) as client:
        response = client.post(
            f"/v1/embeddings?purpose={purpose}", headers=HEADERS, content=audio_file(seconds)
        )
    assert response.status_code == expected
    if expected == 422:
        assert response.json()["detail"]["code"] == "insufficient_speech"


def test_inconsistent_windows_never_return_an_embedding():
    _, app, embedder = runtime_and_app()
    embedder.inconsistent = True
    with TestClient(app) as client:
        response = client.post(
            "/v1/embeddings?purpose=enroll", headers=HEADERS, content=audio_file()
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "inconsistent_audio"
    assert "embedding" not in response.json()


@pytest.mark.parametrize(
    "samples,code",
    [
        (np.zeros(160000), "insufficient_speech"),
        (np.ones(160000), "clipped_audio"),
    ],
)
def test_silence_and_clipping_are_rejected(samples, code):
    stream = BytesIO()
    sf.write(stream, samples, 16000, format="WAV", subtype="PCM_16")
    _, app, _ = runtime_and_app()
    with TestClient(app) as client:
        response = client.post(
            "/v1/embeddings?purpose=enroll", headers=HEADERS, content=stream.getvalue()
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code


def test_size_and_duration_bounded_before_inference():
    _, app, embedder = runtime_and_app(max_upload_bytes=500000, max_duration_seconds=5)
    with TestClient(app) as client:
        too_long = client.post(
            "/v1/embeddings?purpose=identify", headers=HEADERS, content=audio_file(6)
        )
        too_big = client.post(
            "/v1/embeddings?purpose=identify", headers=HEADERS, content=b"x" * 500001
        )
    assert too_long.status_code == too_big.status_code == 413
    assert embedder.calls == 0


def test_streamed_upload_limit_does_not_depend_on_content_length():
    _, app, embedder = runtime_and_app(max_upload_bytes=32)
    with TestClient(app) as client:
        response = client.post(
            "/v1/embeddings?purpose=identify",
            headers=HEADERS,
            content=iter([b"x" * 20, b"y" * 20]),
        )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "audio_limit"
    assert embedder.calls == 0


@pytest.mark.parametrize("payload", [b"", b"not an audio file", b"RIFF0000WAVEinvalid"])
def test_invalid_audio(payload):
    _, app, _ = runtime_and_app()
    with TestClient(app) as client:
        response = client.post("/v1/embeddings?purpose=identify", headers=HEADERS, content=payload)
    assert response.status_code in (400, 415, 422)
    assert "embedding" not in response.json()


def test_context_and_internal_key_required_and_errors_do_not_echo_secrets():
    _, app, _ = runtime_and_app()
    with TestClient(app) as client:
        for missing in ("X-Inference-Key", "X-Job-Id", "X-Tenant-Id"):
            headers = {key: value for key, value in HEADERS.items() if key != missing}
            response = client.post("/v1/embeddings?purpose=identify", headers=headers, content=b"")
            assert response.status_code in (401, 422)
            assert HEADERS["X-Inference-Key"] not in response.text


def test_one_slot_includes_upload_and_processing_and_recovers_after_error():
    runtime, app, _ = runtime_and_app()
    with TestClient(app) as client:
        with runtime.claim():
            busy = client.post(
                "/v1/embeddings?purpose=identify", headers=HEADERS, content=audio_file(3)
            )
        assert busy.status_code == 503
        assert busy.json()["detail"]["code"] == "inference_busy"
        failed = client.post("/v1/embeddings?purpose=identify", headers=HEADERS, content=b"bad")
        assert failed.status_code != 200
        good = client.post(
            "/v1/embeddings?purpose=identify", headers=HEADERS, content=audio_file(3)
        )
        assert good.status_code == 200


def test_initialization_failure_remains_explicit_readiness_failure():
    settings = Settings(internal_key=HEADERS["X-Inference-Key"])

    def unavailable(_):
        raise InferenceError("cuda_unavailable", "CUDA device is unavailable", 503)

    runtime = InferenceRuntime(settings, loader=unavailable)
    with TestClient(create_app(settings, runtime)) as client:
        assert client.get("/live").json() == {"alive": True}
        ready = client.get("/ready")
        response = client.post(
            "/v1/embeddings?purpose=identify", headers=HEADERS, content=audio_file(3)
        )
    assert ready.status_code == response.status_code == 503
    assert ready.json()["detail"]["code"] == "cuda_unavailable"


def test_cuda_availability_is_required_without_cpu_fallback():
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    with pytest.raises(InferenceError, match="CUDA"):
        require_cuda(torch, "cuda:0")
    with pytest.raises(ValueError):
        Settings(internal_key=HEADERS["X-Inference-Key"], device="cpu")


def test_settings_secret_and_spec_limits_are_enforced():
    for changes in (
        {"internal_key": "short"},
        {"max_upload_bytes": 50 * 1024 * 1024 + 1},
        {"max_duration_seconds": 121},
    ):
        with pytest.raises(ValueError):
            Settings(**({"internal_key": HEADERS["X-Inference-Key"]} | changes))


def test_invalid_configuration_does_not_expose_secret_in_error():
    secret = "private-short-test-secret"
    with pytest.raises(ValueError) as caught:
        Settings(internal_key=secret)
    assert secret not in str(caught.value)


def test_request_log_contains_only_safe_context(caplog):
    _, app, _ = runtime_and_app()
    caplog.set_level(logging.INFO, logger="voiceup.inference")
    with TestClient(app) as client:
        client.post("/v1/embeddings?purpose=identify", headers=HEADERS, content=audio_file(3))
        client.get("/private-path-that-must-not-be-logged")
    events = [
        json.loads(item.message) for item in caplog.records if item.name == "voiceup.inference"
    ]
    assert events[0]["job_id"] == HEADERS["X-Job-Id"]
    assert events[0]["status"] == 200
    assert events[1]["route"] == "other"
    assert HEADERS["X-Inference-Key"] not in caplog.text
    assert "private-path-that-must-not-be-logged" not in "".join(
        json.dumps(item) for item in events
    )
    assert "embedding" not in events[0]
