"""Private meeting transport with observed producer shapes and real audio decoding."""

from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from test_service import HEADERS, FixtureEmbedder, FixtureVAD, audio_file

from voiceup_inference.api import create_app
from voiceup_inference.config import Settings
from voiceup_inference.models import ModelHandles
from voiceup_inference.runtime import InferenceRuntime


class MeetingFixture:
    def __init__(self):
        self.counts = None

    def diarize(self, audio, *, max_speakers=None, num_speakers=None):
        self.counts = (max_speakers, num_speakers)
        # Community-1's actual 18.8-second fixture produced padded end 18.96471875.
        return {
            "speaker_diarization": [
                {
                    "start": 0.0,
                    "end": audio.duration + 0.16471875,
                    "speaker": "SPEAKER_00",
                }
            ],
            "exclusive_speaker_diarization": [
                {"start": 0.0, "end": audio.duration, "speaker": "SPEAKER_00"}
            ],
            "speaker_embeddings": {"SPEAKER_00": [1.0] + [0.0] * 255},
        }

    def transcribe(self, audio, language):
        # Exact faster-whisper 1.2.1 Word and Segment field names from its wheel.
        return {
            "language": language or "en",
            "language_probability": 0.99,
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.2,
                    "text": " Hello world.",
                    "words": [
                        {
                            "start": 0.0,
                            "end": 0.5,
                            "word": " Hello",
                            "probability": 0.9,
                        },
                        {
                            "start": 0.5,
                            "end": 1.2,
                            "word": " world.",
                            "probability": 0.8,
                        },
                    ],
                }
            ],
        }


def client_runtime(**overrides):
    settings = Settings(
        internal_key=HEADERS["X-Inference-Key"], meeting_enabled=True, **overrides
    )
    runtime = InferenceRuntime(
        settings,
        loader=lambda _: ModelHandles(FixtureEmbedder(), FixtureVAD()),
        meeting_loader=lambda _: MeetingFixture(),
    )
    return runtime, TestClient(create_app(settings, runtime))


def test_meeting_http_resamples_and_keeps_transcript_with_validated_voice_ranges():
    _, client = client_runtime()
    with client:
        response = client.post(
            "/v1/meeting-chunks?language=en",
            headers=HEADERS,
            content=audio_file(18.8, rate=24000),
        )
    assert response.status_code == 200
    result = response.json()
    assert result["input_seconds"] == pytest.approx(18.8)
    assert result["turns"][0] == {"start": 0.0, "end": 18.8, "speaker": "SPEAKER_00"}
    assert result["words"][0] == {
        "start": 0.0,
        "end": 0.5,
        "word": " Hello",
        "probability": 0.9,
    }
    assert result["tracks"][0]["speaker"] == "SPEAKER_00"
    assert result["tracks"][0]["validated_seconds"] == pytest.approx(18.8)
    assert result["model_identity"]["embedding"]["dimensions"] == 192
    assert result["tracks"][0]["tracking"] == {
        "embedding": [1.0] + [0.0] * 255,
        "model_id": result["model_identity"]["diarization"]["model_id"],
        "model_revision": result["model_identity"]["diarization"]["revision"],
        "component": "embedding",
        "dimensions": 256,
    }
    assert result["language"] == "en"


def test_meeting_exports_source_vad_for_candidates_after_acoustic_mapping():
    _, client = client_runtime()
    with client:
        response = client.post(
            "/v1/meeting-chunks", headers=HEADERS, content=audio_file(4)
        )
    assert response.status_code == 200
    result = response.json()
    assert result["vad"] == {
        "model_id": "silero-vad",
        "model_version": "6.2.1",
        "model_sha256": "e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720",
        "ranges": [{"start": 0.0, "end": 4.0}],
    }
    assert all("candidate_contexts" not in track for track in result["tracks"])


@pytest.mark.parametrize(
    "format,subtype,channels",
    [
        ("FLAC", "PCM_16", 1),
        ("WAV", "FLOAT", 1),
        ("WAV", "PCM_16", 2),
    ],
)
def test_private_meeting_input_requires_source_mono_pcm16_wav(
    format, subtype, channels
):
    import io

    import soundfile as sf

    buffer = io.BytesIO()
    sf.write(buffer, np.zeros((16000, channels)), 16000, format=format, subtype=subtype)
    _, client = client_runtime()
    with client:
        response = client.post(
            "/v1/meeting-chunks", headers=HEADERS, content=buffer.getvalue()
        )
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_audio"


def test_meeting_disabled_does_not_block_existing_pilot():
    settings = Settings(internal_key=HEADERS["X-Inference-Key"])
    runtime = InferenceRuntime(
        settings, loader=lambda _: ModelHandles(FixtureEmbedder(), FixtureVAD())
    )
    with TestClient(create_app(settings, runtime)) as client:
        assert client.get("/ready").status_code == 200
        response = client.post("/v1/meeting-chunks", headers=HEADERS, content=b"")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "meeting_disabled"


@pytest.mark.parametrize(
    "headers,status", [({}, 401), ({**HEADERS, "X-Job-Id": "invalid"}, 422)]
)
def test_meeting_requires_internal_auth_and_context(headers, status):
    _, client = client_runtime()
    with client:
        response = client.post("/v1/meeting-chunks", headers=headers, content=b"")
    assert response.status_code == status


def test_meeting_and_pilot_share_busy_slot():
    runtime, client = client_runtime()
    with client, runtime.claim():
        response = client.post("/v1/meeting-chunks", headers=HEADERS, content=b"")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "inference_busy"


@pytest.mark.parametrize("seconds,status", [(310.0, 200), (310.01, 413)])
def test_meeting_input_is_bounded_to_310_seconds(seconds, status):
    _, client = client_runtime()
    with client:
        response = client.post(
            "/v1/meeting-chunks", headers=HEADERS, content=audio_file(seconds)
        )
    assert response.status_code == status


def test_no_usable_voice_keeps_words_but_returns_no_memory_ranges():
    runtime, client = client_runtime()
    with client:
        runtime._models.vad = SimpleNamespace(speech_spans=lambda *_: [(0, 1)])
        response = client.post(
            "/v1/meeting-chunks", headers=HEADERS, content=audio_file(10)
        )
    assert response.status_code == 200
    result = response.json()
    assert len(result["words"]) == 2
    assert result["tracks"][0]["embedding"] is None
    assert result["tracks"][0]["validated_ranges"] == []
    assert result["tracks"][0]["tracking"]["dimensions"] == 256


@pytest.mark.parametrize("change", ["missing", "extra_label", "norm", "nan", "bool"])
def test_invalid_tracking_output_is_rejected_without_publishing_memory(change):
    runtime, client = client_runtime()
    with client:
        original = runtime._meeting_models.diarize

        def diarize(audio, *, max_speakers=None, num_speakers=None):
            result = original(
                audio, max_speakers=max_speakers, num_speakers=num_speakers
            )
            if change == "missing":
                result.pop("speaker_embeddings")
            elif change == "extra_label":
                result["speaker_embeddings"]["OTHER"] = [1.0] + [0.0] * 255
            else:
                result["speaker_embeddings"]["SPEAKER_00"][0] = {
                    "norm": 2.0,
                    "nan": float("nan"),
                    "bool": True,
                }[change]
            return result

        runtime._meeting_models.diarize = diarize
        response = client.post(
            "/v1/meeting-chunks", headers=HEADERS, content=audio_file(10)
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "meeting_inference_failed"


def test_unavailable_native_centroid_preserves_text_without_inventing_tracking():
    runtime, client = client_runtime()
    with client:
        original = runtime._meeting_models.diarize

        def diarize(audio, *, max_speakers=None, num_speakers=None):
            result = original(
                audio, max_speakers=max_speakers, num_speakers=num_speakers
            )
            result["speaker_embeddings"]["SPEAKER_00"] = None
            return result

        runtime._meeting_models.diarize = diarize
        runtime._models.vad = SimpleNamespace(speech_spans=lambda *_: [(0, 1)])
        response = client.post(
            "/v1/meeting-chunks", headers=HEADERS, content=audio_file(10)
        )
    assert response.status_code == 200
    result = response.json()
    assert result["words"] and result["tracks"][0]["tracking"] is None
    assert result["tracks"][0]["embedding"] is None
    assert result["tracks"][0]["validated_ranges"] == []


def test_silence_does_not_invoke_asr_or_create_hallucinated_words():
    runtime, client = client_runtime()

    def forbidden(*_):
        pytest.fail("ASR must not receive a chunk without detected speech")

    with client:
        runtime._models.vad = SimpleNamespace(speech_spans=lambda *_: [])
        runtime._meeting_models.transcribe = forbidden
        response = client.post(
            "/v1/meeting-chunks", headers=HEADERS, content=audio_file(10, amplitude=0)
        )
    assert response.status_code == 200
    assert response.json()["words"] == []
    assert response.json()["segments"] == []
    assert response.json()["tracks"] == []
    assert response.json()["turns"] == []
    assert response.json()["language"] is None


def test_optional_speaker_counts_reach_the_observed_provider():
    runtime, client = client_runtime()
    with client:
        response = client.post(
            "/v1/meeting-chunks?max_speakers=70&num_speakers=60",
            headers=HEADERS,
            content=audio_file(10),
        )
    assert response.status_code == 200
    assert runtime._meeting_models.counts == (70, 60)


@pytest.mark.parametrize(
    "query",
    [
        "max_speakers=0",
        "num_speakers=1001",
        "max_speakers=3&num_speakers=4",
        "max_speakers=true",
        "num_speakers=-1",
    ],
)
def test_invalid_speaker_count_rejected_before_audio(query):
    _, client = client_runtime()
    with client:
        response = client.post(
            "/v1/meeting-chunks?" + query, headers=HEADERS, content=b""
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_fifty_is_not_a_hard_participant_quota():
    runtime, client = client_runtime()
    with client:

        def diarize(audio, *, max_speakers=None, num_speakers=None):
            rows = [
                {"start": float(i), "end": float(i + 1), "speaker": f"SPEAKER_{i:02d}"}
                for i in range(60)
            ]
            return {
                "speaker_diarization": rows,
                "exclusive_speaker_diarization": rows,
                "speaker_embeddings": {
                    row["speaker"]: [1.0] + [0.0] * 255 for row in rows
                },
            }

        runtime._meeting_models.diarize = diarize
        response = client.post(
            "/v1/meeting-chunks?max_speakers=100",
            headers=HEADERS,
            content=audio_file(60),
        )
    assert response.status_code == 200
    assert len(response.json()["tracks"]) == 60


def test_meeting_loader_failure_is_secret_safe_and_pilot_stays_ready():
    runtime, client = client_runtime()

    def broken(_):
        raise RuntimeError("private-token-path-sentinel")

    runtime._meeting_loader = broken
    with client:
        assert client.get("/ready").status_code == 200
        response = client.get("/meeting-ready")
    assert response.status_code == 503
    assert "private-token-path-sentinel" not in response.text


def test_invalid_language_rejected_before_audio():
    _, client = client_runtime()
    with client:
        response = client.post(
            "/v1/meeting-chunks?language=../../secret", headers=HEADERS, content=b""
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_numeric_provider_scalars_are_normalized_without_accepting_strings():
    runtime, client = client_runtime()
    with client:
        original = runtime._meeting_models.transcribe

        def transcribe(audio, language):
            result = original(audio, language)
            for segment in result["segments"]:
                segment["start"], segment["end"] = (
                    np.float64(segment["start"]),
                    np.float64(segment["end"]),
                )
                for word in segment["words"]:
                    for key in ("start", "end", "probability"):
                        word[key] = np.float64(word[key])
            return result

        runtime._meeting_models.transcribe = transcribe
        response = client.post(
            "/v1/meeting-chunks", headers=HEADERS, content=audio_file(10)
        )
    assert response.status_code == 200
    assert response.json()["words"][0]["probability"] == 0.9
