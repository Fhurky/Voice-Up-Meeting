"""Request-owned model residency preserves sequential inference and cleanup."""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from test_meeting_memory import Pilot, request
from test_service import HEADERS as PILOT_HEADERS

from voiceup_inference.api import create_app
from voiceup_inference.config import Settings
from voiceup_inference.meeting_memory import verify_memory
from voiceup_inference.meeting_models import LocalMeetingModels
from voiceup_inference.runtime import InferenceRuntime

HEADERS = {**PILOT_HEADERS, "Content-Type": "application/json"}


def precision():
    return (
        torch.backends.cuda.matmul.allow_tf32,
        torch.backends.cudnn.allow_tf32,
        torch.get_float32_matmul_precision(),
    )


@pytest.fixture
def resident_models(monkeypatch):
    original = precision()
    calls = []

    class Pipeline:
        fail = None

        def to(self, device):
            calls.append(("move", str(device)))
            torch.set_float32_matmul_precision("high")
            torch.backends.cudnn.allow_tf32 = False
            if self.fail == str(device):
                raise RuntimeError("private-device-error")
            return self

        def _embedding(self, waveform):
            assert waveform.shape[:2] == (1, 1)
            assert torch.is_inference_mode_enabled()
            calls.append(("encode", waveform.numpy().copy()))
            torch.set_float32_matmul_precision("high")
            torch.backends.cudnn.allow_tf32 = False
            if self.fail == "encode":
                raise RuntimeError("private-embedding-error")
            if self.fail == "shape":
                return np.zeros((2, 256))
            output = np.zeros((1, 256), dtype=np.float64)
            output[0, 0] = 1
            return output

    models = object.__new__(LocalMeetingModels)
    models._torch = torch
    models._device = torch.device("cuda:0")
    models._pipeline = Pipeline()
    models._voice_embedding_slot = Lock()
    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: calls.append(("cache",)))
    try:
        yield models, calls
    finally:
        torch.backends.cuda.matmul.allow_tf32 = original[0]
        torch.backends.cudnn.allow_tf32 = original[1]
        torch.set_float32_matmul_precision(original[2])


def moves(calls):
    return [call for call in calls if call[0] != "encode"]


def test_one_request_preserves_batch_one_order_samples_vectors_and_precision(
    resident_models,
):
    models, calls = resident_models
    samples = [np.linspace(-1, 1, n, dtype=np.float32) for n in (32000, 48000, 24000)]
    before = [sample.copy() for sample in samples]
    expected = [models.voice_embedding(sample) for sample in samples]
    original = precision()
    calls.clear()
    with models.voice_embedding_session() as encoder:
        observed = []
        for sample in samples:
            observed.append(encoder.voice_embedding(sample))
            assert precision() == original
    assert moves(calls) == [("move", "cuda:0"), ("move", "cpu"), ("cache",)]
    encoded = [call[1] for call in calls if call[0] == "encode"]
    for index in range(3):
        np.testing.assert_array_equal(observed[index], expected[index])
        np.testing.assert_array_equal(encoded[index][0, 0], before[index])
        np.testing.assert_array_equal(samples[index], before[index])
    assert precision() == original


@pytest.mark.parametrize("failure", ["cuda:0", "encode", "shape", "cpu", "body"])
def test_errors_restore_precision_release_residency_and_allow_next_request(
    resident_models, failure
):
    models, calls = resident_models
    models._pipeline.fail = failure
    original = precision()
    with pytest.raises((RuntimeError, ValueError)):
        with models.voice_embedding_session() as encoder:
            encoder.voice_embedding(np.zeros(32000, dtype=np.float32))
            if failure == "body":
                raise RuntimeError("private-body-error")
    assert ("move", "cpu") in calls
    assert precision() == original
    models._pipeline.fail = None
    with models.voice_embedding_session() as encoder:
        assert encoder.voice_embedding(np.zeros(32000, dtype=np.float32))[0] == 1


def test_empty_validation_session_does_not_upload_model(resident_models):
    models, calls = resident_models
    with models.voice_embedding_session():
        pass
    assert calls == []


def test_nested_concurrent_and_expired_sessions_fail_without_releasing_owner(
    resident_models,
):
    models, calls = resident_models
    samples = np.zeros(32000, dtype=np.float32)

    def new_session():
        with models.voice_embedding_session():
            pytest.fail("Concurrent session must not enter")

    with models.voice_embedding_session() as encoder:
        encoder.voice_embedding(samples)
        with pytest.raises(RuntimeError, match="meeting_embedding_session_busy"):
            new_session()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with pytest.raises(RuntimeError, match="meeting_embedding_session_busy"):
                executor.submit(new_session).result()
            with pytest.raises(RuntimeError, match="meeting_embedding_session_invalid"):
                executor.submit(encoder.voice_embedding, samples).result()
        assert moves(calls) == [("move", "cuda:0")]
        encoder.voice_embedding(samples)
    with pytest.raises(RuntimeError, match="meeting_embedding_session_invalid"):
        encoder.voice_embedding(samples)
    assert moves(calls) == [("move", "cuda:0"), ("move", "cpu"), ("cache",)]


def test_real_memory_http_uses_one_session_and_preserves_full_response(resident_models):
    models, calls = resident_models
    settings = Settings(internal_key=HEADERS["X-Inference-Key"], meeting_enabled=True)
    payload, _ = request()
    expected = verify_memory(payload, models, Pilot(), settings)
    calls.clear()
    runtime = InferenceRuntime(
        settings, loader=lambda _: Pilot(), meeting_loader=lambda _: models
    )
    with TestClient(create_app(settings, runtime)) as client:
        response = client.post("/v1/meeting-memory", headers=HEADERS, json=payload)
    assert response.status_code == 200
    assert response.json() == expected
    assert len([call for call in calls if call[0] == "encode"]) > 20
    assert moves(calls) == [("move", "cuda:0"), ("move", "cpu"), ("cache",)]


def test_memory_http_error_releases_both_slots_and_hides_provider_details(
    resident_models,
):
    models, calls = resident_models
    settings = Settings(internal_key=HEADERS["X-Inference-Key"], meeting_enabled=True)
    runtime = InferenceRuntime(
        settings, loader=lambda _: Pilot(), meeting_loader=lambda _: models
    )
    payload, _ = request()
    models._pipeline.fail = "encode"
    with TestClient(create_app(settings, runtime)) as client:
        response = client.post("/v1/meeting-memory", headers=HEADERS, json=payload)
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "meeting_inference_failed"
        assert "private-" not in response.text
        assert ("move", "cpu") in calls
        models._pipeline.fail = None
        response = client.post("/v1/meeting-memory", headers=HEADERS, json=payload)
        assert response.status_code == 200


def test_memory_validation_and_busy_responses_never_move_models(resident_models):
    models, calls = resident_models
    settings = Settings(internal_key=HEADERS["X-Inference-Key"], meeting_enabled=True)
    runtime = InferenceRuntime(
        settings, loader=lambda _: Pilot(), meeting_loader=lambda _: models
    )
    payload, _ = request()
    with TestClient(create_app(settings, runtime)) as client:
        assert (
            client.post("/v1/meeting-memory", headers=HEADERS, json={}).status_code
            == 422
        )
        with runtime.claim():
            response = client.post("/v1/meeting-memory", headers=HEADERS, json=payload)
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "inference_busy"
    assert calls == []
