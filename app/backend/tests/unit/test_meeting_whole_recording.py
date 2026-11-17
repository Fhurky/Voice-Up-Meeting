"""Whole-recording diarization contract: window turns, the provider shape and the private transport."""

import io
import json
import math
from uuid import uuid4

import httpx
import numpy as np
import pytest
import soundfile as sf
from pydantic import SecretStr, ValidationError

from app.core.config import get_settings
from app.domain.meeting import window_turns
from app.infrastructure.meeting_audio import MeetingAudioStorage
from app.infrastructure.meeting_inference import HttpMeetingAdapter
from app.services.meeting_ports import MeetingChunkResult, MeetingRecordingResult
from app.services.speaker_ports import SpeakerError

pytestmark = pytest.mark.unit

TRACKING = {
    "model_id": "pyannote/speaker-diarization-community-1",
    "model_revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
    "component": "embedding",
    "dimensions": 256,
}
IDENTITY = {
    "diarization": {
        "model_id": "pyannote/speaker-diarization-community-1",
        "revision": "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
        "recipe": "community-default-whole-v1",
    },
    "asr": {
        "model_id": "Systran/faster-whisper-large-v3",
        "revision": "edaa852ec7e145841d8ffdb056a99866b5f0a478",
    },
    "embedding": {
        "model_id": "speechbrain/spkrec-ecapa-voxceleb",
        "revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
        "dimensions": 192,
    },
}


def recording(seconds: float = 700.0, **changes) -> dict:
    payload = {
        "input_seconds": seconds,
        "sample_rate": 16000,
        "device": "cuda:0",
        "turns": [
            {"start": 1.0, "end": 400.0, "speaker": "SPEAKER_01"},
            {"start": 350.0, "end": 699.0, "speaker": "SPEAKER_00"},
        ],
        "exclusive_turns": [
            {"start": 1.0, "end": 375.0, "speaker": "SPEAKER_01"},
            {"start": 375.0, "end": 699.0, "speaker": "SPEAKER_00"},
        ],
        "speakers": [
            {"speaker": "SPEAKER_01", "tracking": {"embedding": [1.0] + [0.0] * 255, **TRACKING}},
            {"speaker": "SPEAKER_00", "tracking": None},
        ],
        "model_identity": IDENTITY,
    }
    payload.update(changes)
    return payload


def test_turns_are_clipped_to_a_window_and_made_relative() -> None:
    turns = [(1.0, 400.0, "A"), (350.0, 699.0, "B"), (700.0, 701.0, "C")]
    assert window_turns(turns, 295.0, 605.0) == [
        {"start": 0.0, "end": 105.0, "speaker": "A"},
        {"start": 55.0, "end": 310.0, "speaker": "B"},
    ]
    # A sliver at the window edge cannot become an empty turn.
    assert window_turns([(0.0, 295.0000001, "A")], 295.0, 605.0) == []


def test_recording_result_accepts_the_provider_shape() -> None:
    result = MeetingRecordingResult.model_validate(recording())
    assert [speaker.speaker for speaker in result.speakers] == ["SPEAKER_01", "SPEAKER_00"]


@pytest.mark.parametrize(
    "change",
    [
        {"speakers": [{"speaker": "SPEAKER_01", "tracking": None}]},
        {
            "speakers": [
                {"speaker": "SPEAKER_01", "tracking": None},
                {"speaker": "SPEAKER_01", "tracking": None},
                {"speaker": "SPEAKER_00", "tracking": None},
            ]
        },
        {"exclusive_turns": [{"start": 1.0, "end": 2.0, "speaker": "SPEAKER_09"}]},
        {"turns": [{"start": 1.0, "end": 14400.5, "speaker": "SPEAKER_01"}]},
        {
            "model_identity": {
                **IDENTITY,
                "diarization": {**IDENTITY["diarization"], "recipe": "community-vbx-fa015-v1"},
            }
        },
        {"input_seconds": 14401.0},
    ],
)
def test_inconsistent_recording_results_are_rejected(change) -> None:
    with pytest.raises(ValidationError):
        MeetingRecordingResult.model_validate(recording(**change))


def settings():
    return get_settings().model_copy(
        update={"inference_key": SecretStr("test-meeting-key-at-least-32-bytes")}
    )


async def blocks(data: bytes):
    for offset in range(0, len(data), 7000):
        yield data[offset : offset + 7000]


async def diarize(respond, data: bytes = b"\x01\x00" * 16000 * 700, rate: int = 16000):
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        return await HttpMeetingAdapter(settings(), client).diarize_recording(
            blocks(data),
            sample_rate=rate,
            size_bytes=len(data),
            job_public_id=str(uuid4()),
            tenant_public_id=str(uuid4()),
            max_speakers=12,
        )


async def test_whole_recording_is_streamed_with_its_rate_and_size() -> None:
    seen = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen["path"], seen["params"] = request.url.path, dict(request.url.params)
        seen["headers"], seen["body"] = request.headers, request.read()
        return httpx.Response(200, json=recording())

    data = b"\x01\x00" * 16000 * 700
    result = await diarize(respond, data)
    assert seen["path"] == "/v1/meeting-recording" and seen["params"] == {"max_speakers": "12"}
    assert seen["headers"]["content-type"] == "application/octet-stream"
    assert seen["headers"]["x-sample-rate"] == "16000"
    assert seen["headers"]["content-length"] == str(len(data))
    assert seen["headers"]["x-inference-key"] == "test-meeting-key-at-least-32-bytes"
    assert seen["body"] == data
    assert result.input_seconds == 700.0


async def test_recording_duration_must_match_the_source() -> None:
    with pytest.raises(SpeakerError) as error:
        await diarize(lambda _: httpx.Response(200, json=recording(650.0)))
    assert error.value.code == "model_mismatch"


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (503, "inference_busy", "inference_busy"),
        (422, "clipped_audio", "clipped_audio"),
        (413, "audio_limit", "audio_limit"),
        (500, "anything", "inference_unavailable"),
    ],
)
async def test_recording_errors_keep_stable_codes(status, code, expected) -> None:
    with pytest.raises(SpeakerError) as error:
        await diarize(lambda _: httpx.Response(status, json={"detail": {"code": code}}))
    assert error.value.code == expected


async def test_unreadable_recording_response_is_a_model_mismatch() -> None:
    with pytest.raises(SpeakerError) as error:
        await diarize(lambda _: httpx.Response(200, content=b"not json"))
    assert error.value.code == "model_mismatch"


def wav(seconds: float, rate: int = 16000) -> bytes:
    stream = io.BytesIO()
    sf.write(stream, [0.1] * round(seconds * rate), rate, format="WAV", subtype="PCM_16")
    return stream.getvalue()


async def test_attributed_chunk_sends_its_turns_before_the_audio(observed_chunk) -> None:
    seen = {}
    turns = {"turns": [{"start": 0.0, "end": 16.0, "speaker": "SPEAKER_00"}]}
    turns["exclusive_turns"] = turns["turns"]

    def respond(request: httpx.Request) -> httpx.Response:
        seen["headers"], seen["body"] = request.headers, request.read()
        seen["path"], seen["params"] = request.url.path, dict(request.url.params)
        return httpx.Response(200, json=observed_chunk)

    audio = wav(16)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await HttpMeetingAdapter(settings(), client).analyze_attributed(
            audio, turns, job_public_id=str(uuid4()), tenant_public_id=str(uuid4()), language="tr"
        )
    size = int(seen["headers"]["x-turns-bytes"])
    assert seen["path"] == "/v1/meeting-chunks/attributed" and seen["params"] == {"language": "tr"}
    assert json.loads(seen["body"][:size]) == turns
    assert seen["body"][size:] == audio
    assert result.model_identity.diarization.recipe == "community-default-whole-v1"


async def test_attributed_chunk_may_only_name_the_speakers_it_was_given(observed_chunk) -> None:
    turns = {"turns": [{"start": 0.0, "end": 16.0, "speaker": "OTHER"}]}
    turns["exclusive_turns"] = turns["turns"]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=observed_chunk))
    ) as client:
        with pytest.raises(SpeakerError) as error:
            await HttpMeetingAdapter(settings(), client).analyze_attributed(
                wav(16),
                turns,
                job_public_id=str(uuid4()),
                tenant_public_id=str(uuid4()),
                language=None,
            )
    assert error.value.code == "model_mismatch"


def test_attributed_chunk_with_speech_ranges_is_a_valid_result(observed_chunk) -> None:
    # Real attributed chunks carry voice activity ranges for candidate contexts.
    payload = {
        **observed_chunk,
        "vad": {
            "model_id": "silero-vad",
            "model_version": "6.2.1",
            "model_sha256": "e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720",
            "ranges": [{"start": 0.5, "end": 15.5}],
        },
    }
    result = MeetingChunkResult.model_validate(payload)
    assert result.model_identity.diarization.recipe == "community-default-whole-v1"
    without_recipe = {
        **payload,
        "model_identity": {**IDENTITY, "diarization": {**IDENTITY["diarization"], "recipe": None}},
    }
    with pytest.raises(ValidationError):
        MeetingChunkResult.model_validate(without_recipe)


@pytest.fixture
def observed_chunk():
    seconds = 16.0
    return {
        "input_seconds": seconds,
        "sample_rate": 16000,
        "device": "cuda:0",
        "turns": [{"start": 0.0, "end": seconds, "speaker": "SPEAKER_00"}],
        "exclusive_turns": [{"start": 0.0, "end": seconds, "speaker": "SPEAKER_00"}],
        "segments": [{"start": 1.0, "end": 2.0, "text": "merhaba"}],
        "words": [{"start": 1.0, "end": 2.0, "word": " merhaba", "probability": 0.9}],
        "language": "tr",
        "language_probability": 1.0,
        "tracks": [
            {
                "speaker": "SPEAKER_00",
                "status": "usable",
                "embedding": [1.0] + [0.0] * 191,
                "dimensions": 192,
                "validated_ranges": [{"start": 0.0, "end": seconds}],
                "validated_seconds": seconds,
                "used_seconds": seconds,
                "windows_count": 2,
                "min_pair_similarity": 1.0,
                "preprocessing_version": "vad-windows-v1",
                "tracking": None,
            }
        ],
        "model_identity": IDENTITY,
    }


@pytest.mark.parametrize(("rate", "channels"), [(16000, 1), (44100, 2)])
def test_recording_blocks_are_mono_pcm16_at_the_source_rate(tmp_path, rate, channels) -> None:
    storage, key = MeetingAudioStorage(tmp_path), "0" * 32 + ".meeting"
    left = np.sin(np.arange(rate * 3) * 2 * math.pi * 440 / rate) * 0.5
    right = left * 0.2
    samples = np.stack([left, right], axis=1) if channels == 2 else left
    sf.write(storage.path(key), samples, rate, format="WAV", subtype="PCM_16")
    assert storage.recording_info(key) == (rate, rate * 3)
    data = b"".join(storage.recording_blocks(key, block_frames=10000))
    assert len(data) == rate * 3 * 2
    expected = (sf.read(storage.path(key), always_2d=True)[0].mean(axis=1) * 32768).round()
    assert np.max(np.abs(np.frombuffer(data, dtype="<i2") - expected)) <= 1
