"""Independent admitted embedding spaces veto mixed retained PCM without outputs."""

from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from test_meeting_coherence import varying_pcm
from test_meeting_memory import Pilot, VoiceModels, request, vector, wav
from test_meeting_runtime import MeetingFixture
from test_service import HEADERS

from voiceup_inference.api import create_app
from voiceup_inference.config import Settings
from voiceup_inference.meeting_coherence import has_secondary_voice
from voiceup_inference.runtime import InferenceRuntime


@pytest.mark.parametrize("dimensions", [192, 256])
def test_each_admitted_space_independently_detects_the_same_supported_groups(
    dimensions,
):
    samples = varying_pcm()
    assert has_secondary_voice(
        samples,
        lambda piece: np.array(vector(dimensions, int(piece[0] < 0))),
        [(0.0, 20.0)],
        dimensions=dimensions,
    )


@pytest.mark.parametrize("dimensions", [0, 128, 255, True, 192.0, "192"])
def test_unadmitted_dimensions_fail_before_model_execution(dimensions):
    def forbidden(_):
        pytest.fail("Invalid dimension must fail before inference")

    with pytest.raises(ValueError, match="invalid_coherence_dimensions"):
        has_secondary_voice(
            varying_pcm(), forbidden, [(0.0, 20.0)], dimensions=dimensions
        )


@pytest.mark.parametrize("dimensions, returned", [(192, 256), (256, 192)])
def test_embedding_populations_cannot_be_padded_or_combined(dimensions, returned):
    with pytest.raises(ValueError, match="dimension"):
        has_secondary_voice(
            varying_pcm(),
            lambda _: np.array(vector(returned)),
            [(0.0, 20.0)],
            dimensions=dimensions,
        )


def memory_client(we_mixed=False, ecapa_mixed=False, ecapa_error=None):
    calls = []

    class Models(VoiceModels, MeetingFixture):
        def voice_embedding(self, samples):
            if len(samples) == 32000:
                calls.append("we_probe")
                return np.array(vector(256, int(we_mixed and samples[0] < 0)))
            return np.array(vector(256))

    class Embedder:
        def encode(self, samples, sample_rate=16000):
            assert sample_rate == 16000
            if len(samples) == 32000:
                calls.append("ecapa_probe")
                if ecapa_error == "exception":
                    raise RuntimeError("private-model-error")
                if ecapa_error == "dimension":
                    return np.array(vector(256))
                return np.array(vector(192, int(ecapa_mixed and samples[0] < 0)))
            calls.append("final_ecapa")
            return np.array(vector(192))

    settings = Settings(internal_key=HEADERS["X-Inference-Key"], meeting_enabled=True)
    runtime = InferenceRuntime(
        settings,
        loader=lambda _: SimpleNamespace(vad=Pilot.vad(), embedder=Embedder()),
        meeting_loader=lambda _: Models(),
    )
    return TestClient(create_app(settings, runtime)), calls


def mixed_payload():
    import base64

    payload, _ = request()
    payload["audio_base64"] = base64.b64encode(
        wav(varying_pcm(seconds=24, second_voice_at=8))
    ).decode()
    return payload


@pytest.mark.parametrize(
    "we_mixed, ecapa_mixed", [(True, False), (False, True), (True, True)]
)
def test_either_independent_space_vetoes_before_any_persistable_output(
    we_mixed, ecapa_mixed
):
    client, calls = memory_client(we_mixed, ecapa_mixed)
    with client:
        response = client.post(
            "/v1/meeting-memory",
            headers={**HEADERS, "Content-Type": "application/json"},
            json=mixed_payload(),
        )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "inconsistent_audio"
    assert result["retained_sha256"] is None
    assert result["embedding192"] is result["memory_embedding"] is None
    assert result["validated_ranges"] == result["accepted_context_indices"] == []
    assert result["validated_seconds"] == result["windows_count"] == 0
    assert "final_ecapa" not in calls
    if we_mixed:
        assert "ecapa_probe" not in calls
    else:
        assert calls.index("ecapa_probe") > calls.index("we_probe")


def test_both_spaces_preserve_pure_pcm_and_the_separate_final_vectors():
    client, calls = memory_client()
    with client:
        response = client.post(
            "/v1/meeting-memory",
            headers={**HEADERS, "Content-Type": "application/json"},
            json=mixed_payload(),
        )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "usable"
    assert result["validated_seconds"] == 22.5
    assert result["embedding192"] == vector(192)
    assert result["memory_embedding"]["embedding"] == vector(256)
    assert calls.count("final_ecapa") == 1
    assert calls.count("ecapa_probe") == calls.count("we_probe") > 2
    assert calls[-1] == "final_ecapa"


@pytest.mark.parametrize("error", ["exception", "dimension"])
def test_secondary_encoder_failure_is_closed_and_private_over_http(error):
    client, calls = memory_client(ecapa_error=error)
    with client:
        response = client.post(
            "/v1/meeting-memory",
            headers={**HEADERS, "Content-Type": "application/json"},
            json=mixed_payload(),
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "meeting_inference_failed"
    assert "private-model-error" not in response.text
    assert "embedding192" not in response.json()
    assert "final_ecapa" not in calls
