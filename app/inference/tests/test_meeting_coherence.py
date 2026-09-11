"""Final retained PCM must not authorize two independently supported voices."""

import base64
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from test_meeting_memory import Pilot, request, vector, wav
from test_meeting_runtime import MeetingFixture
from test_service import HEADERS

from voiceup_inference.api import create_app
from voiceup_inference.config import Settings
from voiceup_inference.runtime import InferenceRuntime

RATE = 16000


def varying_pcm(seconds=20, second_voice_at=10):
    samples = np.linspace(0.05, 0.25, seconds * RATE, dtype=np.float32)
    samples[second_voice_at * RATE :] *= -1
    return samples


def distinct_voice(samples):
    return np.array(vector(256, int(float(samples[0]) < 0)))


def rejects(samples, encode=distinct_voice, spans=None):
    from voiceup_inference.meeting_coherence import has_secondary_voice

    if spans is None:
        spans = [(0.0, len(samples) / RATE)]
    return has_secondary_voice(samples, encode, spans)


def test_two_supported_different_voices_veto_the_whole_candidate():
    assert rejects(varying_pcm()) is True


def test_two_phonetic_groups_of_one_voice_are_preserved():
    def nearby_voice(samples):
        result = np.array(vector(256))
        if samples[0] < 0:
            result[:2] = [0.75, np.sqrt(1 - 0.75**2)]
        return result

    assert rejects(varying_pcm(), nearby_voice) is False


@pytest.mark.parametrize("cosine, expected", [(0.5499, True), (0.5501, False)])
def test_identity_separation_uses_the_fixed_point_fifty_five_boundary(cosine, expected):
    def separated_voice(samples):
        result = np.array(vector(256))
        if samples[0] < 0:
            result[:2] = [cosine, np.sqrt(1 - cosine**2)]
        return result

    assert rejects(varying_pcm(), separated_voice) is expected


def test_one_identical_center_and_empty_speech_are_not_secondary_voices():
    samples = varying_pcm()
    assert rejects(samples, lambda _: np.array(vector(256))) is False
    assert rejects(samples, spans=[]) is False


def test_one_short_outlier_cannot_supply_two_independent_windows():
    assert rejects(varying_pcm(second_voice_at=18)) is False


def test_repeated_pcm_does_not_supply_two_distinct_voice_windows():
    samples = varying_pcm(seconds=20, second_voice_at=20)
    repeated = np.linspace(-0.3, -0.2, 2 * RATE, dtype=np.float32)
    samples[8 * RATE : 10 * RATE] = repeated
    samples[14 * RATE : 16 * RATE] = repeated

    def only_whole_secondary(samples):
        return np.array(vector(256, int(np.all(samples < 0))))

    assert rejects(samples, only_whole_secondary) is False


def test_unvoiced_frames_do_not_qualify_a_second_voice():
    assert rejects(varying_pcm(), spans=[(0.0, 11.5)]) is False


@pytest.mark.parametrize("last", [13.0, 13.0 - 1 / RATE])
def test_three_unique_voiced_seconds_are_required_without_rounding_up(last):
    assert rejects(varying_pcm(), spans=[(0.0, 9.0), (10.0, last)]) is (last == 13.0)


@pytest.mark.parametrize("bad", [np.zeros(256), np.full(256, np.nan), np.ones(192)])
def test_invalid_model_vectors_fail_closed(bad):
    with pytest.raises(ValueError):
        rejects(varying_pcm(), lambda _: bad)


@pytest.mark.parametrize("mixed", [True, False])
def test_private_http_veto_runs_after_primary_context_checks_before_persistent_vectors(
    mixed,
):
    class Models(MeetingFixture):
        def voice_embedding(self, samples):
            # Whole contexts, 3-second guards and existing 1.5-second checks pass.
            # Only final 2-second windows expose the independent secondary voice.
            if len(samples) == 2 * RATE and mixed:
                return distinct_voice(samples)
            return np.array(vector(256))

    class Embedder:
        def __init__(self):
            self.calls = 0

        def encode(self, samples, sample_rate=RATE):
            self.calls += 1
            return np.array(vector(192))

    embedder = Embedder()
    pilot = SimpleNamespace(vad=Pilot.vad(), embedder=embedder)
    settings = Settings(internal_key=HEADERS["X-Inference-Key"], meeting_enabled=True)
    runtime = InferenceRuntime(
        settings, loader=lambda _: pilot, meeting_loader=lambda _: Models()
    )
    payload, _ = request()
    payload["audio_base64"] = base64.b64encode(
        wav(varying_pcm(seconds=24, second_voice_at=8))
    ).decode()
    with TestClient(create_app(settings, runtime)) as client:
        response = client.post(
            "/v1/meeting-memory",
            headers={**HEADERS, "Content-Type": "application/json"},
            json=payload,
        )
    assert response.status_code == 200
    result = response.json()
    if mixed:
        assert result["status"] == "inconsistent_audio"
        assert result["accepted_context_indices"] == result["validated_ranges"] == []
        assert result["validated_seconds"] == result["windows_count"] == 0
        assert result["embedding192"] is result["memory_embedding"] is None
        assert result["retained_sha256"] is None
        assert embedder.calls == 0
    else:
        assert result["status"] == "usable"
        assert result["validated_seconds"] == 22.5
        assert result["accepted_context_indices"] == [0, 1, 2]
        assert result["retained_sha256"] is not None
        assert result["embedding192"] == vector(192)
        assert embedder.calls == 1
