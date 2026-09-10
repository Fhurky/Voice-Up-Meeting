"""Selected preprocessing provenance survives HTTP parsing without exposing provider quality data."""

from dataclasses import asdict
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.infrastructure.speaker_inference import HttpEmbeddingAdapter
from app.schemas.speaker_identity import SpeakerResult
from app.services.speaker_ports import SpeakerError

pytestmark = pytest.mark.unit


def producer_payload() -> dict:
    return {
        "embedding": [1.0] + [0.0] * 191,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": 192,
        "speech_seconds": 12.0,
        "windows_count": 2,
        "device": "cuda:0",
    }


@pytest.fixture
def inference_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("VOICEUP_INFERENCE_KEY", uuid4().hex)
    return Settings()


async def parse_response(payload: dict, settings: Settings):
    job, tenant = str(uuid4()), str(uuid4())

    def producer(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        assert dict(request.url.params) == {"purpose": "enroll"}
        assert request.headers["X-Job-Id"] == job
        assert request.headers["X-Tenant-Id"] == tenant
        assert request.content == b"fixture-audio"
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(producer)) as client:
        return await HttpEmbeddingAdapter(settings, client).embed(
            b"fixture-audio", purpose="enroll", job_public_id=job, tenant_public_id=tenant
        )


@pytest.mark.parametrize("version", ["vad-windows-v1", "vad-packed-fallback-v1"])
async def test_adapter_carries_only_allowed_preprocessing_metadata(
    version: str, inference_settings: Settings
) -> None:
    payload = producer_payload()
    payload["quality"] = {
        "preprocessing_version": version,
        "execution_seconds": 0.1,
        "private_source_audio": "must-not-escape",
        "nested": {"embedding": [123], "storage_key": "must-not-escape"},
    }
    result = asdict(await parse_response(payload, inference_settings))
    assert result == {
        "embedding": payload["embedding"],
        "speech_seconds": 12.0,
        "windows_count": 2,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "device": "cuda:0",
        "preprocessing_version": version,
    }


@pytest.mark.parametrize("legacy", [{}, {"quality": {}}, {"quality": None}])
async def test_adapter_does_not_invent_legacy_preprocessing_provenance(
    legacy: dict, inference_settings: Settings
) -> None:
    result = await parse_response({**producer_payload(), **legacy}, inference_settings)
    assert result.preprocessing_version is None


@pytest.mark.parametrize("version", ["unknown-v2", "", True, 1, [], {}])
async def test_adapter_rejects_unknown_or_malformed_preprocessing_version(
    version: object, inference_settings: Settings
) -> None:
    payload = {**producer_payload(), "quality": {"preprocessing_version": version}}
    with pytest.raises(SpeakerError, match="model_mismatch") as error:
        await parse_response(payload, inference_settings)
    assert error.value.status_code == 502


def test_historical_job_result_deserializes_with_unknown_preprocessing_version() -> None:
    stored = {
        "decision": "unknown",
        "speech_seconds": 12.0,
        "windows_count": 2,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "device": "cuda:0",
        "reason": "no_profiles",
        "policy": {"match_threshold": 0.55, "new_threshold": 0.45, "margin": 0.1},
    }
    result = SpeakerResult.model_validate(stored)
    assert result.preprocessing_version is None
    assert result.model_dump(mode="json")["preprocessing_version"] is None
    assert "preprocessing_version" not in stored
