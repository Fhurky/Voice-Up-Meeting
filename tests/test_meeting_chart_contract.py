"""Meeting deployment selection is checked against actual Helm output."""

import copy
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def renderer():
    source = Path(__file__).resolve().parents[1] / "scripts" / "render_charts.py"
    spec = importlib.util.spec_from_file_location("meeting_chart_renderer", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def overlay(renderer):
    value = renderer.load_overlay(renderer.FIXTURES, "lab")
    value["inference"] = {"runtimeProfile": "x86_64-cu128", "meetingEnabled": False}
    return value


@pytest.mark.parametrize(
    "selection",
    [
        None,
        {"runtimeProfile": "unknown", "meetingEnabled": False},
        {"runtimeProfile": "x86_64-cu128", "meetingEnabled": "false"},
        {"runtimeProfile": "aarch64-cu129", "meetingEnabled": True},
        {"runtimeProfile": "x86_64-cu128"},
        {"meetingEnabled": False},
    ],
)
def test_overlay_rejects_missing_untyped_or_unadmitted_meeting_selection(
    renderer, overlay, selection
):
    if selection is None:
        overlay.pop("inference")
    else:
        overlay["inference"] = selection
    with pytest.raises(renderer.PolicyError):
        renderer.validate_overlay("test", overlay)


def test_chart_values_preserve_explicit_meeting_selection(renderer, overlay):
    overlay["inference"]["meetingEnabled"] = True
    values = renderer.chart_values("app-inference", overlay)
    assert values["runtimeProfile"] == "x86_64-cu128"
    assert values["meeting"]["enabled"] is True
    assert values["meeting"]["modelStorage"]["className"] == overlay["global"]["storageClass"]


@pytest.mark.parametrize("profile", ["x86_64-cu128", "aarch64-cu129"])
def test_actual_pilot_chart_preserves_existing_models_and_probes(
    renderer, overlay, tmp_path, profile
):
    overlay["inference"]["runtimeProfile"] = profile
    renderer.validate_overlay("pilot", overlay)
    documents = renderer.render_chart(renderer.CHARTS / "app-inference", overlay, tmp_path)
    renderer.validate_documents(documents, overlay["global"]["registry"])
    container = next(item for item in documents if item["kind"] == "Deployment")["spec"][
        "template"
    ]["spec"]["containers"][0]
    assert container["startupProbe"]["httpGet"]["path"] == "/live"
    assert container["readinessProbe"]["httpGet"]["path"] == "/ready"
    assert len([item for item in documents if item["kind"] == "PersistentVolumeClaim"]) == 1
    assert not any(
        item["mountPath"] in {"/models/asr", "/models/diarization"}
        for item in container["volumeMounts"]
    )


def test_actual_helm_rejects_arm_meeting_selection(renderer, overlay, tmp_path):
    overlay["inference"] = {"runtimeProfile": "aarch64-cu129", "meetingEnabled": True}
    with pytest.raises(renderer.PolicyError):
        renderer.render_chart(renderer.CHARTS / "app-inference", overlay, tmp_path)


@pytest.fixture(scope="module")
def meeting_documents(renderer, tmp_path_factory):
    value = renderer.load_overlay(renderer.FIXTURES, "lab")
    value["inference"] = {"runtimeProfile": "x86_64-cu128", "meetingEnabled": True}
    documents = renderer.render_chart(
        renderer.CHARTS / "app-inference", value, tmp_path_factory.mktemp("meeting-chart")
    )
    return documents, value["global"]["registry"]


def test_actual_meeting_chart_provides_models_probes_architecture_and_pvc(
    renderer, meeting_documents
):
    documents, registry = meeting_documents
    renderer.validate_documents(documents, registry)
    deployment = next(item for item in documents if item["kind"] == "Deployment")
    pod = renderer.pod_spec(deployment)
    container = pod["containers"][0]
    assert pod["nodeSelector"] == {"kubernetes.io/os": "linux", "kubernetes.io/arch": "amd64"}
    assert container["startupProbe"]["httpGet"]["path"] == "/meeting-ready"
    assert container["readinessProbe"]["httpGet"]["path"] == "/meeting-ready"
    assert container["livenessProbe"]["httpGet"]["path"] == "/live"
    mounts = {item["mountPath"]: item for item in container["volumeMounts"]}
    for component in ("diarization", "asr"):
        assert mounts[f"/models/{component}"]["subPath"] == component
        assert mounts[f"/models/{component}"]["readOnly"] is True
    claims = [item for item in documents if item["kind"] == "PersistentVolumeClaim"]
    assert len(claims) == 2


@pytest.mark.parametrize(
    "fault", ["readiness", "startup", "mount", "writable", "profile", "arch", "pvc", "enabled"]
)
def test_rendered_meeting_contract_rejects_inconsistent_runtime(renderer, meeting_documents, fault):
    documents, registry = meeting_documents
    changed = copy.deepcopy(documents)
    deployment = next(item for item in changed if item["kind"] == "Deployment")
    pod = renderer.pod_spec(deployment)
    container = pod["containers"][0]
    if fault in {"readiness", "startup"}:
        container[f"{fault}Probe"]["httpGet"]["path"] = "/ready"
    elif fault == "mount":
        container["volumeMounts"] = [
            item for item in container["volumeMounts"] if item["mountPath"] != "/models/asr"
        ]
    elif fault == "writable":
        next(item for item in container["volumeMounts"] if item["mountPath"] == "/models/asr")[
            "readOnly"
        ] = False
    elif fault == "profile":
        deployment["spec"]["template"]["metadata"]["annotations"][
            "voiceup.internal/runtime-profile"
        ] = "aarch64-cu129"
    elif fault == "arch":
        pod["nodeSelector"]["kubernetes.io/arch"] = "arm64"
    elif fault == "pvc":
        changed[:] = [
            item
            for item in changed
            if not (
                item["kind"] == "PersistentVolumeClaim"
                and item["metadata"]["name"] == "meeting-models"
            )
        ]
    else:
        next(
            item for item in container["env"] if item["name"] == "VOICEUP_INFERENCE_MEETING_ENABLED"
        )["value"] = "false"
    with pytest.raises(renderer.PolicyError):
        renderer.validate_documents(changed, registry)
