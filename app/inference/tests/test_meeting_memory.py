"""Meeting memory evidence binds quality and both vectors to the retained PCM."""

import base64
import hashlib
import io

import numpy as np
import pytest
import soundfile as sf

from voiceup_inference.config import Settings
from voiceup_inference.meeting_memory import verify_memory
from voiceup_inference.model_bundle import MODEL_ID, MODEL_REVISION


def wav(samples, rate=16000):
    stream = io.BytesIO()
    sf.write(stream, samples, rate, format="WAV", subtype="PCM_16")
    return stream.getvalue()


def vector(dimension, index=0):
    return [float(i == index) for i in range(dimension)]


def tracking(index=0):
    return {
        "embedding": vector(256, index),
        "dimensions": 256,
        "component": "embedding",
        "model_id": "pyannote/speaker-diarization-community-1",
        "model_revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
    }


class VoiceModels:
    def voice_embedding(self, samples):
        return np.array(vector(256))


class Pilot:
    class embedder:
        dimension = 192

        @staticmethod
        def encode(samples, sample_rate=16000):
            return np.array(vector(192))

    class vad:
        @staticmethod
        def speech_spans(samples, sample_rate):
            return [(0.0, len(samples) / sample_rate)]


def request():
    samples = np.concatenate([np.full(8 * 16000, value) for value in (0.1, 0.2, 0.3)])
    body = wav(samples)
    contexts = [
        {
            "start": n * 128000,
            "end": (n + 1) * 128000,
            "voiced_ranges": [
                {"start": n * 128000 + 4000, "end": (n + 1) * 128000 - 4000}
            ],
        }
        for n in range(3)
    ]
    return {
        "audio_base64": base64.b64encode(body).decode(),
        "sample_rate": 16000,
        "contexts": contexts,
        "target": tracking(),
        "competitors": [tracking(1)],
    }, body


def test_quality_evidence_hashes_only_the_retained_original_pcm():
    payload, original = request()
    result = verify_memory(
        payload,
        VoiceModels(),
        Pilot(),
        Settings(internal_key="meeting-test-key-01234567890123456789"),
    )
    assert result["status"] == "usable"
    assert result["validated_seconds"] == 22.5
    assert result["accepted_context_indices"] == [0, 1, 2]
    assert result["input_sha256"] == hashlib.sha256(original).hexdigest()
    raw, rate = sf.read(io.BytesIO(original), dtype="int16")
    retained = np.concatenate(
        [raw[row["start"] : row["end"]] for row in result["validated_ranges"]]
    )
    assert result["retained_sha256"] == hashlib.sha256(wav(retained, rate)).hexdigest()
    assert result["embedding192"] == vector(192)
    assert result["memory_embedding"] == tracking()
    assert (
        result["ecapa_model_id"] == MODEL_ID
        and result["ecapa_model_revision"] == MODEL_REVISION
    )


def test_repeated_pcm_does_not_increase_qualified_speech_or_context_count():
    payload, _ = request()
    payload["audio_base64"] = base64.b64encode(wav(np.full(24 * 16000, 0.1))).decode()
    result = verify_memory(
        payload,
        VoiceModels(),
        Pilot(),
        Settings(internal_key="meeting-test-key-01234567890123456789"),
    )
    assert result["validated_seconds"] == 7.5
    assert result["accepted_context_indices"] == [0]


@pytest.mark.parametrize("invalid", ["hash_shape", "outside", "overlap", "dimensions"])
def test_untrusted_private_context_cannot_authorize_unrelated_audio(invalid):
    payload, _ = request()
    if invalid == "hash_shape":
        payload["audio_base64"] = "not-base64!"
    if invalid == "outside":
        payload["contexts"][0]["voiced_ranges"][0]["end"] = 128001
    if invalid == "overlap":
        payload["contexts"][1]["start"] = 1
    if invalid == "dimensions":
        payload["target"]["embedding"] = vector(192)
    from voiceup_inference.errors import InferenceError

    with pytest.raises(InferenceError):
        verify_memory(
            payload,
            VoiceModels(),
            Pilot(),
            Settings(internal_key="meeting-test-key-01234567890123456789"),
        )


def test_private_http_memory_enforces_auth_context_and_exact_retained_shape():
    from fastapi.testclient import TestClient
    from test_meeting_runtime import MeetingFixture
    from test_service import HEADERS

    from voiceup_inference.api import create_app
    from voiceup_inference.runtime import InferenceRuntime

    class Models(VoiceModels, MeetingFixture):
        pass

    headers = {**HEADERS, "Content-Type": "application/json"}
    settings = Settings(internal_key=HEADERS["X-Inference-Key"], meeting_enabled=True)
    runtime = InferenceRuntime(
        settings, loader=lambda _: Pilot(), meeting_loader=lambda _: Models()
    )
    payload, _ = request()
    with TestClient(create_app(settings, runtime)) as client:
        assert client.post("/v1/meeting-memory", json=payload).status_code == 401
        result = client.post("/v1/meeting-memory", headers=headers, json=payload)
        assert result.status_code == 200
        assert result.json()["validated_seconds"] == 22.5
        assert "audio_base64" not in result.json()
        assert (
            client.post(
                "/v1/meeting-memory",
                headers={**headers, "Content-Length": str(37 * 1024 * 1024)},
                json={},
            ).status_code
            == 413
        )
        assert (
            client.post(
                "/v1/meeting-memory",
                headers=headers,
                json={**payload, "purpose": "enroll"},
            ).status_code
            == 422
        )
