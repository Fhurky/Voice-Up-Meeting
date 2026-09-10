"""Real filesystem, HTTP producer serialization and bounded upload contracts."""

import io
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
import pytest
import soundfile as sf

from app.core.config import get_settings
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.audio_storage import AudioStorage
from app.infrastructure.speaker_inference import HttpEmbeddingAdapter
from app.main import create_application
from app.scripts import speaker_worker
from app.services.speaker_ports import SpeakerError

pytestmark = pytest.mark.unit


class BytesSource:
    def __init__(self, data: bytes) -> None:
        self.stream = io.BytesIO(data)

    async def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)


def wave(seconds: int = 1) -> bytes:
    data = io.BytesIO()
    sf.write(data, [0.1] * (16000 * seconds), 16000, format="WAV")
    return data.getvalue()


async def test_owned_audio_is_decoded_and_opaque(tmp_path: Path) -> None:
    settings = get_settings().model_copy(update={"audio_storage_path": tmp_path})
    storage = AudioStorage(settings)
    stored = await storage.receive(BytesSource(wave()), "../../user.wav")
    assert stored.format == "WAV" and stored.duration_seconds == 1
    assert (tmp_path / stored.key).exists()
    assert "user" not in stored.key
    with pytest.raises(SpeakerError):
        storage.path("../outside.audio")
    await storage.remove(stored.key)
    assert not list(tmp_path.iterdir())


async def test_invalid_and_oversized_audio_leave_no_files(tmp_path: Path) -> None:
    settings = get_settings().model_copy(
        update={"audio_storage_path": tmp_path, "audio_max_bytes": 1024}
    )
    storage = AudioStorage(settings)
    with pytest.raises(SpeakerError, match="audio_limit"):
        await storage.receive(BytesSource(wave()), "sample.wav")
    with pytest.raises(SpeakerError, match="unsupported_audio"):
        await storage.receive(BytesSource(b"garbage"), "sample.wav")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("purpose", ["enroll", "identify"])
@pytest.mark.parametrize("device", ["cuda:0", "cpu"])
async def test_http_adapter_matches_producer_contract(
    purpose: Literal["enroll", "identify"],
    device: str,
) -> None:
    from pydantic import SecretStr

    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-inference-key-at-least-32-bytes")}
    )
    job, tenant = str(uuid4()), str(uuid4())

    def producer(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        assert dict(request.url.params) == {"purpose": purpose}
        assert request.headers["X-Job-Id"] == job
        assert request.headers["X-Tenant-Id"] == tenant
        assert request.headers["X-Inference-Key"] == settings.inference_key.get_secret_value()
        assert request.content == b"fixture-source"
        return httpx.Response(
            200,
            json={
                "embedding": [1.0] + [0.0] * 191,
                "model_id": MODEL_ID,
                "model_revision": MODEL_REVISION,
                "dimensions": 192,
                "speech_seconds": 12.0,
                "windows_count": 2,
                "device": device,  # Producer contract fixture, not hardware execution evidence.
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(producer)) as client:
        result = await HttpEmbeddingAdapter(settings, client).embed(
            b"fixture-source", purpose=purpose, job_public_id=job, tenant_public_id=tenant
        )
    assert len(result.embedding) == 192 and result.speech_seconds == 12
    assert result.device == device


@pytest.mark.parametrize(
    "status,code",
    [(413, "audio_limit"), (422, "insufficient_speech"), (503, "inference_unavailable")],
)
async def test_http_adapter_does_not_turn_quality_errors_into_success(
    status: int, code: str
) -> None:
    from pydantic import SecretStr

    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-inference-key-at-least-32-bytes")}
    )

    def producer(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": {"code": code, "message": "safe"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(producer)) as client:
        with pytest.raises(SpeakerError, match=code):
            await HttpEmbeddingAdapter(settings, client).embed(
                b"fixture",
                purpose="enroll",
                job_public_id=str(uuid4()),
                tenant_public_id=str(uuid4()),
            )


async def test_http_adapter_rejects_wrong_model_and_incomplete_response() -> None:
    from pydantic import SecretStr

    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-inference-key-at-least-32-bytes")}
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"embedding": [0.0] * 192, "model_revision": "wrong"}
            )
        )
    ) as client:
        with pytest.raises(SpeakerError, match="model_mismatch"):
            await HttpEmbeddingAdapter(settings, client).embed(
                b"fixture",
                purpose="identify",
                job_public_id=str(uuid4()),
                tenant_public_id=str(uuid4()),
            )


@pytest.mark.parametrize(
    "purpose,seconds,windows", [("enroll", 10 - 5e-7, 2), ("identify", 3 - 5e-7, 1)]
)
async def test_http_adapter_accepts_producer_minimum_tolerance(
    purpose: Literal["enroll", "identify"], seconds: float, windows: int
) -> None:
    from pydantic import SecretStr

    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-inference-key-at-least-32-bytes")}
    )
    payload = {
        "embedding": [1.0] + [0.0] * 191,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": 192,
        "speech_seconds": seconds,
        "windows_count": windows,
        "device": "cuda:0",
    }
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        result = await HttpEmbeddingAdapter(settings, client).embed(
            b"fixture", purpose=purpose, job_public_id=str(uuid4()), tenant_public_id=str(uuid4())
        )
    assert result.speech_seconds == seconds


@pytest.mark.parametrize("device", ["mps", "cpu:0", "cuda", "cuda:-1", "cuda:0\n", "CPU"])
async def test_http_adapter_rejects_unapproved_device_response(device: str) -> None:
    from pydantic import SecretStr

    settings = get_settings().model_copy(
        update={"inference_key": SecretStr("test-inference-key-at-least-32-bytes")}
    )
    payload = {
        "embedding": [1.0] + [0.0] * 191,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": 192,
        "speech_seconds": 12.0,
        "windows_count": 2,
        "device": device,
    }
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(SpeakerError, match="model_mismatch"):
            await HttpEmbeddingAdapter(settings, client).embed(
                b"fixture",
                purpose="enroll",
                job_public_id=str(uuid4()),
                tenant_public_id=str(uuid4()),
            )


async def test_chunked_multipart_limit_returns_typed_413(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.main.get_settings", lambda: get_settings().model_copy(update={"audio_max_bytes": 1024})
    )
    application = create_application()

    async def chunks():
        yield b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="sample.wav"\r\nContent-Type: audio/wav\r\n\r\n'
        yield b"x" * 70000
        yield b"\r\n--boundary--\r\n"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.post(
            f"{get_settings().api_prefix}/recordings",
            content=chunks(),
            headers={
                "content-type": "multipart/form-data; boundary=boundary",
                get_settings().tenant_header: str(uuid4()),
                "Idempotency-Key": str(uuid4()),
            },
        )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "audio_limit"


def test_worker_health_requires_recent_successful_heartbeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "heartbeat"
    monkeypatch.setattr(speaker_worker, "HEARTBEAT_PATH", path)
    assert speaker_worker.healthcheck() is False
    path.touch()
    assert speaker_worker.healthcheck() is True
    modified = path.stat().st_mtime
    monkeypatch.setattr(
        speaker_worker.time, "time", lambda: modified + get_settings().job_timeout_seconds + 61
    )
    assert speaker_worker.healthcheck() is False
