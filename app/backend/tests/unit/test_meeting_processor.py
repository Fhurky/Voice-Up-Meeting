"""The backend reads and requests the processor through one strict inference contract."""

import json

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.meeting_inference import HttpMeetingAdapter
from app.services.speaker_ports import SpeakerError


def settings() -> Settings:
    return Settings(inference_key="k" * 32, jwt_secret="s" * 40)


STATE = {
    "device": "cuda:0",
    "gpu_available": True,
    "cpu_available": True,
    "switching": False,
    "last_error": None,
}


async def adapter_call(respond, call):
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        return await call(HttpMeetingAdapter(settings(), client))


async def test_state_names_the_processor_not_the_device_index() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/meeting-processor" and request.method == "GET"
        assert request.headers["x-inference-key"] == "k" * 32
        return httpx.Response(200, json=STATE)

    assert (await adapter_call(respond, lambda a: a.processor()))["device"] == "gpu"


async def test_switch_sends_the_requested_processor() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST" and json.loads(request.content) == {"device": "cpu"}
        return httpx.Response(202, json={**STATE, "switching": True})

    state = await adapter_call(respond, lambda a: a.switch_processor("cpu"))
    assert state["switching"] is True


@pytest.mark.parametrize(
    ("status", "code", "expected", "http"),
    [
        (503, "inference_busy", "inference_busy", 409),
        (409, "processor_unavailable", "processor_unavailable", 409),
        (500, "other", "inference_unavailable", 503),
    ],
)
async def test_errors_keep_stable_codes(status: int, code: str, expected: str, http: int) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": {"code": code}})

    with pytest.raises(SpeakerError) as error:
        await adapter_call(respond, lambda a: a.switch_processor("cpu"))
    assert error.value.code == expected and error.value.status_code == http


@pytest.mark.parametrize(
    "document",
    [
        {**STATE, "device": "tpu"},
        {**STATE, "switching": "no"},
        {**STATE, "extra": 1},
        {**STATE, "last_error": "secret detail"},
        [],
    ],
)
async def test_a_wrong_contract_is_a_model_error(document) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=document)

    with pytest.raises(SpeakerError) as error:
        await adapter_call(respond, lambda a: a.processor())
    assert error.value.code == "model_mismatch"


async def test_an_unreachable_service_is_unavailable() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(SpeakerError) as error:
        await adapter_call(respond, lambda a: a.processor())
    assert error.value.code == "inference_unavailable"
