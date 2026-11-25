"""One diarization pass over the whole recording, then chunks that reuse its speakers."""

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient
from test_meeting_runtime import MeetingFixture
from test_service import HEADERS, FixtureEmbedder, FixtureVAD, audio_file

from voiceup_inference.api import create_app
from voiceup_inference.config import Settings
from voiceup_inference.meeting_models import DIARIZATION_RECIPE, WHOLE_RECORDING_RECIPE
from voiceup_inference.models import ModelHandles
from voiceup_inference.runtime import InferenceRuntime


class RecordingFixture(MeetingFixture):
    """The model sees the whole recording once; speaker B speaks first."""

    def __init__(self, turns=None):
        super().__init__()
        self.calls = []
        self.recording_turns = turns

    def diarize(self, audio, *, max_speakers=None, num_speakers=None, recipe=DIARIZATION_RECIPE):
        self.calls.append((round(audio.duration, 3), max_speakers, num_speakers, recipe))
        rows = self.recording_turns or [
            {"start": 0.5, "end": 4.0, "speaker": "SPEAKER_01"},
            {"start": 4.0, "end": audio.duration, "speaker": "SPEAKER_00"},
        ]
        labels = sorted({row["speaker"] for row in rows})
        return {
            "speaker_diarization": rows,
            "exclusive_speaker_diarization": rows,
            "speaker_embeddings": {
                label: [0.0] * index + [1.0] + [0.0] * (255 - index) for index, label in enumerate(labels)
            },
        }


def client(fixture):
    settings = Settings(internal_key=HEADERS["X-Inference-Key"], meeting_enabled=True)
    runtime = InferenceRuntime(
        settings,
        loader=lambda _: ModelHandles(FixtureEmbedder(), FixtureVAD()),
        meeting_loader=lambda _: fixture,
    )
    return runtime, TestClient(create_app(settings, runtime))


def raw(seconds, rate=16000):
    samples = (np.sin(np.arange(round(seconds * rate)) * 2 * np.pi * 220 / rate) * 0.2 * 32767).astype("<i2")
    return samples.tobytes()


def recording_headers(rate=16000):
    return {**HEADERS, "Content-Type": "application/octet-stream", "X-Sample-Rate": str(rate)}


def test_whole_recording_is_diarized_once_with_the_models_own_recipe():
    fixture = RecordingFixture()
    _, http = client(fixture)
    with http:
        response = http.post(
            "/v1/meeting-recording?max_speakers=9", headers=recording_headers(44100), content=raw(400.0, 44100)
        )
    assert response.status_code == 200, response.text
    result = response.json()
    assert fixture.calls == [(400.0, 9, None, WHOLE_RECORDING_RECIPE)]
    assert result["input_seconds"] == pytest.approx(400.0)
    assert result["model_identity"]["diarization"]["recipe"] == WHOLE_RECORDING_RECIPE
    # Speakers are numbered by first speech, not by the model's label order.
    assert [row["speaker"] for row in result["speakers"]] == ["SPEAKER_01", "SPEAKER_00"]
    assert result["speakers"][0]["tracking"]["dimensions"] == 256
    assert result["turns"][0] == {"start": 0.5, "end": 4.0, "speaker": "SPEAKER_01"}
    assert set(result) == {
        "input_seconds", "sample_rate", "turns", "exclusive_turns", "speakers", "model_identity", "device"
    }


def test_a_long_meeting_may_have_more_turns_than_a_chunk():
    rows = [
        {"start": index * 0.1, "end": index * 0.1 + 0.08, "speaker": f"SPEAKER_{index % 12:02d}"}
        for index in range(6000)
    ]
    _, http = client(RecordingFixture(rows))
    with http:
        response = http.post("/v1/meeting-recording", headers=recording_headers(), content=raw(620.0))
    assert response.status_code == 200, response.text
    assert len(response.json()["turns"]) == 6000


@pytest.mark.parametrize(
    ("change", "status"),
    [
        ({"X-Sample-Rate": "7000"}, 400),
        ({"X-Sample-Rate": "abc"}, 400),
        ({"Content-Type": "audio/wav"}, 415),
        ({"X-Sample-Rate": ""}, 400),
        ({"X-Inference-Key": "y" * 32}, 401),
    ],
)
def test_recording_requests_are_checked_before_reading(change, status):
    fixture = RecordingFixture()
    _, http = client(fixture)
    with http:
        response = http.post("/v1/meeting-recording", headers={**recording_headers(), **change}, content=raw(2.0))
    assert response.status_code == status
    assert fixture.calls == []


def test_recording_and_chunks_share_the_busy_slot():
    runtime, http = client(RecordingFixture())
    with http, runtime.claim():
        response = http.post("/v1/meeting-recording", headers=recording_headers(), content=raw(2.0))
    assert response.status_code == 503 and response.json()["detail"]["code"] == "inference_busy"


def attributed(turns, exclusive=None, seconds=18.8, extra=None):
    document = json.dumps({"turns": turns, "exclusive_turns": exclusive or turns, **(extra or {})}).encode()
    return {**HEADERS, "Content-Type": "application/octet-stream", "X-Turns-Bytes": str(len(document))}, (
        document + audio_file(seconds, rate=24000)
    )


def test_attributed_chunk_reuses_the_meeting_speakers_without_diarizing():
    fixture = RecordingFixture()
    _, http = client(fixture)
    turns = [
        {"start": 0.0, "end": 9.0, "speaker": "SPEAKER_01"},
        {"start": 9.0, "end": 18.8, "speaker": "SPEAKER_00"},
    ]
    headers, body = attributed(turns)
    with http:
        response = http.post("/v1/meeting-chunks/attributed?language=tr", headers=headers, content=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert fixture.calls == []
    assert result["turns"] == turns
    assert [track["speaker"] for track in result["tracks"]] == ["SPEAKER_00", "SPEAKER_01"]
    assert all(track["tracking"] is None for track in result["tracks"])
    assert result["model_identity"]["diarization"]["recipe"] == WHOLE_RECORDING_RECIPE
    assert result["words"] and result["language"] == "tr"


@pytest.mark.parametrize(
    "document",
    [
        {"turns": [{"start": 0.0, "end": 400.0, "speaker": "A"}]},
        {"turns": [{"start": 2.0, "end": 1.0, "speaker": "A"}]},
        {"turns": [{"start": 0.0, "end": 1.0, "speaker": ""}]},
        {"turns": [], "exclusive_turns": [{"start": 0.0, "end": 1.0, "speaker": "B"}]},
        {"turns": [{"start": 0.0, "end": 1.0, "speaker": "A", "extra": 1}]},
    ],
)
def test_invalid_attributed_turns_are_refused(document):
    fixture = RecordingFixture()
    _, http = client(fixture)
    turns = document["turns"]
    headers, body = attributed(turns, document.get("exclusive_turns", turns))
    with http:
        response = http.post("/v1/meeting-chunks/attributed", headers=headers, content=body)
    assert response.status_code == 422


@pytest.mark.parametrize("value", [None, "0", "-1", "x", str(5 * 1024 * 1024)])
def test_attributed_chunk_requires_a_bounded_turn_document(value):
    _, http = client(RecordingFixture())
    headers, body = attributed([{"start": 0.0, "end": 1.0, "speaker": "A"}])
    headers = {key: item for key, item in headers.items() if key != "X-Turns-Bytes"}
    if value is not None:
        headers["X-Turns-Bytes"] = value
    with http:
        response = http.post("/v1/meeting-chunks/attributed", headers=headers, content=body)
    assert response.status_code == 400
