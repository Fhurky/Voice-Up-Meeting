"""Pin the private JSON boundary, including fields a source-mismatched provider cannot omit."""

import base64
import hashlib
import io
import json

import httpx
import pytest
import soundfile as sf
from pydantic import SecretStr

from app.core.config import Settings
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.meeting_memory_inference import HttpMeetingMemoryAdapter
from app.services.meeting_memory_ports import MemoryContext, MemoryFrameRange
from app.services.meeting_ports import MeetingTracking
from app.services.speaker_ports import SpeakerError


@pytest.mark.parametrize(
    "mode",
    ["valid", "wrong_hash", "wrong_frames", "missing_model", "compressed", "oversized", "busy"],
)
async def test_private_memory_transport_is_bounded_and_source_bound(mode: str) -> None:
    stream = io.BytesIO()
    sf.write(stream, [0.1] * 48000, 16000, format="WAV", subtype="PCM_16")
    audio = stream.getvalue()
    context = MemoryContext(
        start=0, end=48000, voiced_ranges=[MemoryFrameRange(start=0, end=48000)]
    )
    target = MeetingTracking(
        embedding=[1.0] + [0.0] * 255,
        model_id="pyannote/speaker-diarization-community-1",
        model_revision="3533c8cf8e369892e6b79ff1bf80f7b0286a54ee",
        component="embedding",
        dimensions=256,
    )

    def downstream(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/meeting-memory"
        body = json.loads(request.content)
        assert set(body) == {"audio_base64", "sample_rate", "contexts", "target", "competitors"}
        assert base64.b64decode(body["audio_base64"]) == audio
        assert body["contexts"] == [context.model_dump()]
        assert request.headers["X-Inference-Key"] == "test-only-memory-key-with-32-bytes"
        response = {
            "ecapa_model_id": MODEL_ID,
            "ecapa_model_revision": MODEL_REVISION,
            "input_sha256": hashlib.sha256(audio).hexdigest(),
            "retained_sha256": None,
            "input_frames": 48000,
            "sample_rate": 16000,
            "quality_version": "meeting-natural-context-v1",
            "status": "insufficient_speech",
            "accepted_context_indices": [],
            "validated_ranges": [],
            "validated_seconds": 0.0,
            "windows_count": 0,
            "device": "cpu",
            "embedding192": None,
            "memory_embedding": None,
        }
        if mode == "wrong_hash":
            response["input_sha256"] = "0" * 64
        if mode == "wrong_frames":
            response["input_frames"] = 47000
        if mode == "missing_model":
            del response["ecapa_model_revision"]
        if mode == "compressed":
            return httpx.Response(
                200, stream=httpx.ByteStream(b"invalid"), headers={"Content-Encoding": "gzip"}
            )
        if mode == "oversized":
            return httpx.Response(200, content=b" " * (128 * 1024 + 1))
        if mode == "busy":
            return httpx.Response(503, json={"detail": {"code": "inference_busy"}})
        return httpx.Response(200, json=response)

    settings = Settings(
        inference_url="http://inference:8090",
        inference_key=SecretStr("test-only-memory-key-with-32-bytes"),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(downstream)) as client:
        adapter = HttpMeetingMemoryAdapter(settings, client)
        if mode == "valid":
            result = await adapter.verify(
                audio,
                contexts=[context],
                target=target,
                competitors=[],
                job_public_id="job",
                tenant_public_id="tenant",
            )
            assert result.status == "insufficient_speech"
        else:
            with pytest.raises(
                SpeakerError, match="inference_busy" if mode == "busy" else "model_mismatch"
            ):
                await adapter.verify(
                    audio,
                    contexts=[context],
                    target=target,
                    competitors=[],
                    job_public_id="job",
                    tenant_public_id="tenant",
                )
