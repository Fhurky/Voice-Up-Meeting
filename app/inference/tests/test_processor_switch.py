"""The processor changes by starting the service again in its own process."""

import os
import sys
import threading

import pytest
import torch
from fastapi.testclient import TestClient

from voiceup_inference import runtime as runtime_module
from voiceup_inference.api import create_app
from voiceup_inference.config import Settings
from voiceup_inference.errors import InferenceError
from voiceup_inference.runtime import InferenceRuntime, replace_process

KEY = "x" * 32
PROFILES = {"cuda:0": "x86_64-cu126", "cpu": "x86_64-meeting-cpu"}


class Loads:
    """A device in `broken` fails to load its meeting models."""

    def __init__(self, broken=()):
        self.order, self.broken = [], set(broken)

    def models(self, settings):
        self.order.append(settings.device)
        return object()

    def meeting(self, settings):
        if settings.device in self.broken:
            raise RuntimeError("no memory")
        return object()


class Replacements(list):
    def __call__(self, settings, switch):
        self.append((settings.device, settings.runtime_profile, switch))


def service(loads, replace=None, device="cuda:0", switch=""):
    runtime = InferenceRuntime(
        Settings(
            internal_key=KEY,
            device=device,
            runtime_profile=PROFILES[device],
            meeting_enabled=True,
            processor_switch=switch,
        ),
        loader=loads.models,
        meeting_loader=loads.meeting,
        replace=replace if replace is not None else Replacements(),
    )
    if not switch:
        runtime.initialize()
    return runtime


@pytest.fixture(autouse=True)
def no_grace(monkeypatch):
    monkeypatch.setattr(runtime_module, "RESPONSE_GRACE_SECONDS", 0)


@pytest.fixture
def gpu_visible(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.version, "cuda", "12.6")


def assert_slot_taken(runtime):
    with pytest.raises(InferenceError) as error:
        with runtime.claim():
            pass
    assert error.value.code == "inference_busy"


@pytest.mark.parametrize(
    ("device", "target", "expected"),
    [("cuda:0", "cpu", ("cpu", "x86_64-meeting-cpu", "selected")), ("cpu", "gpu", ("cuda:0", "x86_64-cu126", "selected"))],
)
def test_change_starts_again_with_the_matching_profile(gpu_visible, device, target, expected):
    replaced = Replacements()
    runtime = service(Loads(), replaced, device)
    assert runtime.begin_processor_switch(target)["switching"] is True
    runtime.join_processor_switch()
    assert replaced == [expected]
    assert_slot_taken(runtime)


def test_asking_for_the_current_processor_does_nothing(gpu_visible):
    replaced = Replacements()
    runtime = service(Loads(), replaced)
    assert runtime.begin_processor_switch("gpu")["switching"] is False
    runtime.join_processor_switch()
    assert replaced == []


def test_gpu_cannot_be_selected_when_the_service_cannot_see_one(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    replaced = Replacements()
    runtime = service(Loads(), replaced, "cpu")
    assert runtime.processor_state()["gpu_available"] is False
    with pytest.raises(InferenceError) as error:
        runtime.begin_processor_switch("gpu")
    assert error.value.code == "processor_unavailable" and error.value.status_code == 409
    assert replaced == []


def test_a_running_job_blocks_the_change(gpu_visible):
    replaced = Replacements()
    runtime = service(Loads(), replaced)
    with runtime.claim():
        with pytest.raises(InferenceError) as error:
            runtime.begin_processor_switch("cpu")
    assert error.value.code == "inference_busy"
    runtime.join_processor_switch()
    assert replaced == []


def test_a_job_waits_while_the_replacement_loads(gpu_visible):
    release, entered = threading.Event(), threading.Event()
    loads = Loads()
    original = loads.models

    def slow(settings):
        entered.set()
        release.wait(5)
        return original(settings)

    loads.models = slow
    runtime = service(loads, device="cpu", switch="selected")
    runtime.finish_processor_switch()
    assert entered.wait(5)
    assert runtime.processor_state()["switching"] is True
    with pytest.raises(InferenceError):
        runtime.meeting_readiness()
    release.set()
    runtime.join_processor_switch()
    state = runtime.processor_state()
    assert state["switching"] is False and state["last_error"] is None
    assert runtime.meeting_readiness()["device"] == "cpu"
    with runtime.claim():
        pass


def test_failed_load_returns_to_the_previous_processor(gpu_visible):
    replaced = Replacements()
    runtime = service(Loads(broken={"cpu"}), replaced, "cpu", "selected")
    runtime.finish_processor_switch()
    runtime.join_processor_switch()
    assert replaced == [("cuda:0", "x86_64-cu126", "returned")]
    assert_slot_taken(runtime)


def test_the_returned_service_reports_the_failure_and_works(gpu_visible):
    runtime = service(Loads(), switch="returned")
    runtime.finish_processor_switch()
    runtime.join_processor_switch()
    state = runtime.processor_state()
    assert state["device"] == "cuda:0" and state["switching"] is False
    assert state["last_error"] == "processor_switch_failed"
    assert runtime.meeting_readiness()["ready"] is True
    with runtime.claim():
        pass


def test_a_failed_return_does_not_start_again_forever(gpu_visible):
    replaced = Replacements()
    runtime = service(Loads(broken={"cuda:0"}), replaced, switch="returned")
    runtime.finish_processor_switch()
    runtime.join_processor_switch()
    assert replaced == [] and runtime.processor_state()["switching"] is False
    with pytest.raises(InferenceError):
        runtime.meeting_readiness()


def test_a_refused_replacement_keeps_the_running_service(gpu_visible):
    def refuse(settings, switch):
        raise OSError("refused")

    runtime = service(Loads(), refuse)
    runtime.begin_processor_switch("cpu")
    runtime.join_processor_switch()
    state = runtime.processor_state()
    assert state["device"] == "cuda:0" and state["switching"] is False
    assert state["last_error"] == "processor_switch_failed"
    with runtime.claim():
        pass


def test_replacement_runs_the_same_command_with_the_selected_processor(monkeypatch):
    calls = []
    monkeypatch.setattr(os, "execve", lambda *args: calls.append(args))
    monkeypatch.setenv("VOICEUP_INFERENCE_INTERNAL_KEY", KEY)
    replace_process(Settings(internal_key=KEY, device="cpu", runtime_profile="x86_64-meeting-cpu"), "selected")
    path, argv, environment = calls[0]
    assert path == sys.executable and argv == sys.orig_argv
    assert environment["VOICEUP_INFERENCE_DEVICE"] == "cpu"
    assert environment["VOICEUP_INFERENCE_RUNTIME_PROFILE"] == "x86_64-meeting-cpu"
    assert environment["VOICEUP_INFERENCE_PROCESSOR_SWITCH"] == "selected"
    assert environment["VOICEUP_INFERENCE_INTERNAL_KEY"] == KEY


def test_processor_routes_require_the_internal_key_and_a_known_processor(gpu_visible):
    replaced = Replacements()
    runtime = service(Loads(), replaced)
    headers = {"x-inference-key": KEY}
    with TestClient(create_app(runtime.settings, runtime)) as client:
        assert client.get("/v1/meeting-processor").status_code == 401
        assert client.post("/v1/meeting-processor", json={"device": "cpu"}).status_code == 401
        read = client.get("/v1/meeting-processor", headers=headers)
        assert read.status_code == 200
        assert set(read.json()) == {"device", "gpu_available", "cpu_available", "switching", "last_error"}
        for body in ({"device": "tpu"}, {}, []):
            assert client.post("/v1/meeting-processor", json=body, headers=headers).status_code == 422
        assert replaced == []
        change = client.post("/v1/meeting-processor", json={"device": "cpu"}, headers=headers)
        assert change.status_code == 202 and change.json()["switching"] is True
        runtime.join_processor_switch()
    assert replaced == [("cpu", "x86_64-meeting-cpu", "selected")]


def test_the_service_answers_while_a_replacement_loads(gpu_visible):
    release, entered = threading.Event(), threading.Event()
    loads = Loads()
    original = loads.meeting

    def slow(settings):
        entered.set()
        release.wait(5)
        return original(settings)

    loads.meeting = slow
    runtime = service(loads, device="cpu", switch="selected")
    with TestClient(create_app(runtime.settings, runtime)) as client:
        assert entered.wait(5)
        read = client.get("/v1/meeting-processor", headers={"x-inference-key": KEY})
        assert read.json()["device"] == "cpu" and read.json()["switching"] is True
        release.set()
        runtime.join_processor_switch()
        assert client.get("/v1/meeting-processor", headers={"x-inference-key": KEY}).json()["switching"] is False
