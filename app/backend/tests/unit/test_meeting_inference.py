"""Validate a real provider response shape with sanitized text and voice vectors."""

import copy
import io
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import soundfile as sf
from pydantic import SecretStr

from app.core.config import get_settings
from app.infrastructure.meeting_inference import HttpMeetingAdapter
from app.services.meeting_ports import MeetingChunkResult
from app.services.speaker_ports import SpeakerError

pytestmark = pytest.mark.unit


@pytest.fixture
def observed_payload():
    path = Path(__file__).parents[1] / "fixtures/meeting_chunk_actual.json"
    return json.loads(path.read_text(encoding="utf-8"))["payload"]


def audio(seconds=16):
    stream = io.BytesIO()
    sf.write(stream, [0.0] * round(16000 * seconds), 16000, format="WAV", subtype="PCM_16")
    return stream.getvalue()


async def call(payload, *, status=200):
    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-meeting-key-at-least-32-bytes")}
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                status,
                content=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
        )
    ) as client:
        return await HttpMeetingAdapter(settings, client).analyze(
            audio(),
            job_public_id=str(uuid4()),
            tenant_public_id=str(uuid4()),
            language="en",
            max_speakers=5,
            num_speakers=None,
        )


def controlled_usable_candidate(observed_payload):
    """A positive validation candidate, explicitly not a real model quality claim."""
    payload = copy.deepcopy(observed_payload)
    turn = max(payload["turns"], key=lambda item: item["end"] - item["start"])
    start, end = turn["start"], min(turn["end"], turn["start"] + 8.0)
    track = next(item for item in payload["tracks"] if item["speaker"] == turn["speaker"])
    track.update(
        status="usable",
        embedding=[1.0] + [0.0] * 191,
        validated_ranges=[{"start": start, "end": end}],
        validated_seconds=end - start,
        used_seconds=end - start,
        windows_count=1,
        min_pair_similarity=1.0,
    )
    return payload


async def test_controlled_usable_candidate_is_validated(observed_payload):
    result = await call(controlled_usable_candidate(observed_payload))
    assert any(track.status == "usable" and track.embedding is not None for track in result.tracks)


def controlled_tracking_candidate(observed_payload):
    """Native Community (N, 256) shape; synthetic values cannot certify identity."""
    payload = copy.deepcopy(observed_payload)
    for track in payload["tracks"]:
        track["tracking"] = {
            "embedding": [1.0] + [0.0] * 255,
            "model_id": payload["model_identity"]["diarization"]["model_id"],
            "model_revision": payload["model_identity"]["diarization"]["revision"],
            "component": "embedding",
            "dimensions": 256,
        }
    return payload


async def test_tagged_tracking_does_not_authorize_memory_for_an_abstaining_track(observed_payload):
    result = await call(controlled_tracking_candidate(observed_payload))
    for track in result.tracks:
        assert track.tracking.dimensions == 256
        assert track.tracking.embedding == [1.0] + [0.0] * 255
        assert track.embedding is None and track.validated_seconds == 0


async def test_legacy_checkpoint_without_tracking_remains_valid(observed_payload):
    payload = copy.deepcopy(observed_payload)
    for track in payload["tracks"]:
        track.pop("tracking", None)
    result = await call(payload)
    assert all(track.tracking is None for track in result.tracks)


@pytest.mark.parametrize(
    "change",
    ["dimension", "length", "norm", "zero", "nan", "model", "revision", "component", "extra"],
)
async def test_tagged_tracking_is_strict_and_cannot_reuse_ecapa_identity(observed_payload, change):
    payload = controlled_tracking_candidate(observed_payload)
    tracking = payload["tracks"][0]["tracking"]
    if change == "dimension":
        tracking["dimensions"] = 192
    elif change == "length":
        tracking["embedding"] = [1.0] + [0.0] * 191
    elif change == "norm":
        tracking["embedding"][0] = 2.0
    elif change == "zero":
        tracking["embedding"][0] = 0.0
    elif change == "nan":
        tracking["embedding"][0] = float("nan")
    elif change == "model":
        tracking["model_id"] = payload["model_identity"]["embedding"]["model_id"]
    elif change == "revision":
        tracking["model_revision"] = "0" * 40
    elif change == "component":
        tracking["component"] = "plda"
    else:
        tracking["unapproved"] = True
    with pytest.raises(SpeakerError) as captured:
        await call(payload)
    assert captured.value.code == "model_mismatch"


async def test_observed_payload_and_context_round_trip(observed_payload):
    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-meeting-key-at-least-32-bytes")}
    )
    job, tenant = str(uuid4()), str(uuid4())
    source = audio()

    def producer(request: httpx.Request):
        assert request.url.path == "/v1/meeting-chunks"
        assert dict(request.url.params) == {"language": "en", "max_speakers": "5"}
        assert request.headers["X-Job-Id"] == job
        assert request.headers["X-Tenant-Id"] == tenant
        assert request.headers["X-Inference-Key"] == settings.inference_key.get_secret_value()
        assert request.content == source
        assert request.extensions["timeout"]["read"] == settings.meeting_chunk_timeout_seconds
        return httpx.Response(200, json=observed_payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(producer)) as client:
        result = await HttpMeetingAdapter(settings, client).analyze(
            source,
            job_public_id=job,
            tenant_public_id=tenant,
            language="en",
            max_speakers=5,
            num_speakers=None,
        )
    assert isinstance(result, MeetingChunkResult)
    assert result.model_dump(exclude_unset=True) == observed_payload
    assert result.words and result.turns and result.device == "cuda:0"


@pytest.mark.parametrize(
    "change",
    [
        "model",
        "revision",
        "duration",
        "time",
        "zero_time",
        "word_probability",
        "vector",
        "vector_norm",
        "nonfinite_vector",
        "nonfinite_time",
        "range_source",
        "range_other_speaker",
        "range_sum",
        "nonusable_embedding",
        "unknown_field",
    ],
)
async def test_invalid_provider_evidence_fails_closed(observed_payload, change):
    payload = controlled_usable_candidate(observed_payload)
    track = next(item for item in payload["tracks"] if item["status"] == "usable")
    if change == "model":
        payload["model_identity"]["asr"]["model_id"] = "unapproved"
    elif change == "revision":
        payload["model_identity"]["embedding"]["revision"] = "0" * 40
    elif change == "duration":
        payload["input_seconds"] = 71.0
    elif change == "time":
        payload["turns"][0]["end"] = 17.0
    elif change == "zero_time":
        payload["words"][0]["end"] = payload["words"][0]["start"]
    elif change == "word_probability":
        payload["words"][0]["probability"] = 2.0
    elif change == "vector":
        track["embedding"] = [0.0] * 191
    elif change == "vector_norm":
        track["embedding"] = [2.0] + [0.0] * 191
    elif change == "nonfinite_vector":
        track["embedding"][0] = float("nan")
    elif change == "nonfinite_time":
        payload["turns"][0]["start"] = float("inf")
    elif change == "range_source":
        track["validated_ranges"][0]["end"] = 17.0
    elif change == "range_other_speaker":
        payload["turns"].append({"start": 0.0, "end": 16.0, "speaker": "OTHER"})
        other = copy.deepcopy(track)
        other.update(
            speaker="OTHER",
            status="insufficient_speech",
            embedding=None,
            validated_ranges=[],
            validated_seconds=0.0,
            used_seconds=0.0,
            windows_count=0,
            min_pair_similarity=None,
        )
        payload["tracks"].append(other)
    elif change == "range_sum":
        track["validated_seconds"] += 1.0
    elif change == "nonusable_embedding":
        track["status"] = "insufficient_speech"
    else:
        payload["secret"] = "must-not-return"
    with pytest.raises(SpeakerError, match="model_mismatch"):
        await call(payload)


@pytest.mark.parametrize(
    "status,code,expected",
    [
        (503, "inference_busy", "inference_busy"),
        (503, "meeting_disabled", "inference_unavailable"),
        (503, "meeting_model_load_failed", "inference_unavailable"),
        (401, "unauthorized", "inference_unavailable"),
        (422, "invalid_audio", "invalid_audio"),
    ],
)
async def test_provider_errors_preserve_safe_retry_meaning(status, code, expected):
    with pytest.raises(SpeakerError, match=expected):
        await call({"detail": {"code": code}}, status=status)


async def test_streamed_response_is_bounded_and_closed():
    class Oversized(httpx.AsyncByteStream):
        def __init__(self):
            self.closed = False
            self.yielded = 0

        async def __aiter__(self):
            for _ in range(200):
                self.yielded += 1
                yield b" " * 65536

        async def aclose(self):
            self.closed = True

    stream = Oversized()
    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-meeting-key-at-least-32-bytes")}
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, headers={"Content-Type": "application/json"}, stream=stream
            )
        )
    ) as client:
        with pytest.raises(SpeakerError, match="model_mismatch"):
            await HttpMeetingAdapter(settings, client).analyze(
                audio(),
                job_public_id=str(uuid4()),
                tenant_public_id=str(uuid4()),
                language=None,
                max_speakers=None,
                num_speakers=None,
            )
    assert stream.closed
    assert stream.yielded < 200


async def test_silence_result_is_typed_without_a_language(observed_payload):
    payload = copy.deepcopy(observed_payload)
    for key in ("turns", "exclusive_turns", "words", "segments", "tracks"):
        payload[key] = []
    payload["language"], payload["language_probability"] = None, 0.0
    result = await call(payload)
    assert result.language is None and not result.words
