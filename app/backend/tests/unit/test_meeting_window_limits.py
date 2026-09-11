"""Decision 14 bounds survive the public-source to private-provider boundary."""

import io
import json
import wave
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import get_settings
from app.infrastructure.meeting_inference import MAX_REQUEST_BYTES, HttpMeetingAdapter
from app.services.meeting_ports import MeetingChunkResult, MeetingRange
from app.services.speaker_ports import SpeakerError


def silent_wav(frames: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(8000)
        writer.writeframes(b"\x00\x00" * frames)
    return buffer.getvalue()


def test_private_contract_accepts_310_seconds_and_rejects_a_later_frame() -> None:
    assert MeetingRange(start=309.0, end=310.0).end == 310
    with pytest.raises(ValidationError):
        MeetingRange(start=310.0, end=310 + 1 / 16000)
    fixture = Path(__file__).parents[1] / "fixtures/meeting_chunk_actual.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))["payload"]
    payload["input_seconds"] = 310.0
    assert MeetingChunkResult.model_validate(payload).input_seconds == 310
    payload["input_seconds"] += 1 / 16000
    with pytest.raises(ValidationError):
        MeetingChunkResult.model_validate(payload)
    assert MAX_REQUEST_BYTES >= 310 * 192000 * 2 + 44


@pytest.mark.parametrize("extra_frame", [False, True])
async def test_adapter_sends_only_source_bounded_310_second_audio(
    extra_frame: bool,
) -> None:
    fixture = Path(__file__).parents[1] / "fixtures/meeting_chunk_actual.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))["payload"]
    payload["input_seconds"] = 310.0
    captured = []

    def respond(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=payload)

    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-meeting-key-at-least-32-bytes")}
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        adapter = HttpMeetingAdapter(settings, client)
        request = adapter.analyze(
            silent_wav(310 * 8000 + int(extra_frame)),
            job_public_id=str(uuid4()),
            tenant_public_id=str(uuid4()),
            language="en",
            max_speakers=5,
            num_speakers=None,
        )
        if extra_frame:
            with pytest.raises(SpeakerError, match="invalid_audio"):
                await request
            assert not captured
        else:
            assert (await request).input_seconds == 310
            assert len(captured) == 1
            assert len(captured[0].content) == 310 * 8000 * 2 + 44
