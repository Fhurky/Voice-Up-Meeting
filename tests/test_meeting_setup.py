"""Explicit local meeting setup keeps the existing runtime choices and admission boundary."""

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import create_autospec

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def setup_module():
    spec = importlib.util.spec_from_file_location(
        "meeting_setup", ROOT / "scripts/setup-local-meeting.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verify_only_never_downloads_builds_or_enables(setup_module, tmp_path):
    run = create_autospec(setup_module.run, return_value=None)
    check = create_autospec(setup_module.verify_wheels, return_value=None)
    setup_module.prepare(tmp_path, verify_only=True, runner=run, wheel_verifier=check)
    commands = [call.args[0] for call in run.call_args_list]
    assert commands and all(
        "--verify" in command or "check-dependency-admission.py" in str(command)
        for command in commands
    )
    assert not (tmp_path / "outputs/local-meeting-enabled.txt").exists()
    assert check.call_count == 1


def test_prepare_writes_selection_only_after_verified_offline_build(setup_module, tmp_path):
    calls = []
    marker = tmp_path / "outputs/local-meeting-enabled.txt"

    def run(command, *, root, timeout=1800):
        assert not marker.exists()
        calls.append(command)
        return (
            "npipe://local"
            if "context" in command
            else "linux/amd64"
            if "version" in command
            else ""
        )

    check = create_autospec(setup_module.verify_wheels, return_value=None)
    setup_module.prepare(tmp_path, runner=run, wheel_verifier=check)
    assert marker.read_text() == "enabled\n"
    build = next(command for command in calls if "build" in command)
    assert (
        "--network=none" not in build
    )  # Compose takes the enforced network from the reviewed Dockerfile/overlay.
    assert "app/infra/docker-compose.meeting.yml" in build and build[-2:] == ["build", "inference"]
    assert sum("check-dependency-admission.py" in str(command) for command in calls) == 2
    assert check.call_count == 1


def test_failed_preparation_does_not_enable_or_replace_existing_intent(setup_module, tmp_path):
    marker = tmp_path / "outputs/local-meeting-enabled.txt"
    marker.parent.mkdir()
    marker.write_text("enabled\n")

    def fail(command, *, root, timeout=1800):
        raise RuntimeError("fixture_failure")

    with pytest.raises(RuntimeError, match="fixture_failure"):
        setup_module.prepare(tmp_path, runner=fail)
    assert marker.read_text() == "enabled\n"


def test_meeting_overlay_is_explicit_local_cuda_and_preserves_security():
    import yaml

    overlay = yaml.safe_load((ROOT / "app/infra/docker-compose.meeting.yml").read_text())
    inference = overlay["services"]["inference"]
    assert set(overlay["services"]) == {"inference"}
    assert inference["build"]["dockerfile"] == "app/inference/Dockerfile.meeting"
    assert inference["build"]["network"] == "none"
    assert inference["environment"]["VOICEUP_INFERENCE_MEETING_ENABLED"] == "true"
    assert set(inference["build"]["additional_contexts"]) == {"wheelhouse", "meeting_wheelhouse"}
    assert all(
        mount["read_only"] and mount["bind"]["create_host_path"] is False
        for mount in inference["volumes"]
    )
    assert "ports" not in inference


@pytest.mark.parametrize(
    "relative", ["app/infra/nginx/nginx.spark.conf", "app/inference/nginx.spark.conf"]
)
def test_private_proxy_exposes_only_exact_meeting_routes(relative):
    config = (ROOT / relative).read_text()
    assert "location = /meeting-ready {" in config
    assert "location = /v1/meeting-chunks {" in config
    assert "proxy_read_timeout 600s;" in config
    assert "location / {\n    return 404;" in config


def test_remote_docker_is_rejected_before_any_file_or_image_preparation(
    setup_module, tmp_path, monkeypatch
):
    monkeypatch.setenv("DOCKER_HOST", "ssh://remote-host")
    run = create_autospec(setup_module.run, return_value="")
    with pytest.raises(ValueError, match="local_docker_required"):
        setup_module.prepare(tmp_path, runner=run)
    run.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_arm_docker_does_not_enable_the_x86_meeting_extension(setup_module, tmp_path, monkeypatch):
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    run = create_autospec(
        setup_module.run, side_effect=["unix:///var/run/docker.sock", "linux/arm64"]
    )
    with pytest.raises(ValueError, match="local_linux_x86_64_required"):
        setup_module.prepare(tmp_path, runner=run)
    assert run.call_count == 2 and list(tmp_path.iterdir()) == []


def test_real_compose_merge_keeps_base_model_and_readonly_gpu_boundary(tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("# Explicit non-secret fixture configuration\n")
    env = {
        **os.environ,
        "COMPOSE_PROFILES": "",
        "INFERENCE_INTERNAL_KEY": "fixture-inference-key-" + "x" * 40,
        "RUNTIME_DATABASE_PASSWORD": "fixture-runtime-password",
    }
    command = [
        "docker",
        "compose",
        "--env-file",
        str(dotenv),
        "--project-directory",
        str(ROOT / "app/infra"),
        "-p",
        "meeting-config-test",
        "-f",
        str(ROOT / "app/infra/docker-compose.local.yml"),
        "-f",
        str(ROOT / "app/infra/docker-compose.meeting.yml"),
        "config",
        "--format",
        "json",
    ]
    result = subprocess.run(command, env=env, capture_output=True, timeout=20, check=False)
    assert result.returncode == 0, "Compose resolution failed; secret-bearing output withheld"
    service = json.loads(result.stdout)["services"]["inference"]
    assert service["platform"] == "linux/amd64"
    assert service["image"] == "voiceup-inference-meeting:local"
    assert service["environment"]["VOICEUP_INFERENCE_DEVICE"] == "cuda:0"
    assert service["environment"]["VOICEUP_INFERENCE_RUNTIME_PROFILE"] == "x86_64-cu128"
    assert service["environment"]["VOICEUP_INFERENCE_MEETING_ENABLED"] == "true"
    mounts = {mount["target"]: mount for mount in service["volumes"]}
    assert set(mounts) == {"/models/speaker", "/models/diarization", "/models/asr"}
    assert all(mount["read_only"] for mount in mounts.values())
    assert service["read_only"] and service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert not service.get("ports") and service["build"]["network"] == "none"
    assert service["deploy"]["resources"]["reservations"]["devices"][0]["capabilities"] == ["gpu"]


@pytest.fixture
def wheel_root(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/prepare-spark-wheelhouse.py").write_bytes(
        (ROOT / "scripts/prepare-spark-wheelhouse.py").read_bytes()
    )
    (tmp_path / "app/inference").mkdir(parents=True)
    for directory, lock, name in (
        ("inference-wheelhouse", "requirements.txt", "base"),
        ("meeting-inference-wheelhouse", "requirements.meeting-x86_64.txt", "extension"),
    ):
        folder = tmp_path / "models" / directory
        folder.mkdir(parents=True)
        payload = (name + " locked artifact bytes").encode()
        (folder / f"{name}-1.0-py3-none-any.whl").write_bytes(payload)
        (tmp_path / "app/inference" / lock).write_text(
            f"{name}==1.0 --hash=sha256:{hashlib.sha256(payload).hexdigest()}\n"
        )
    return tmp_path


def test_real_filesystem_wheel_hashes_are_checked_without_installing(setup_module, wheel_root):
    setup_module.verify_wheels(wheel_root)


@pytest.mark.parametrize(
    "mutation, error",
    [
        ("tamper", "wheel_hash_mismatch"),
        ("missing", "wheelhouse_incomplete"),
        ("extra", "unexpected_wheel"),
    ],
)
def test_incomplete_or_changed_wheelhouse_is_not_accepted(
    setup_module, wheel_root, mutation, error
):
    wheel = wheel_root / "models/meeting-inference-wheelhouse/extension-1.0-py3-none-any.whl"
    if mutation == "tamper":
        wheel.write_bytes(b"modified")
    elif mutation == "missing":
        wheel.unlink()
    else:
        wheel.with_name("unknown-1.0-py3-none-any.whl").write_bytes(b"extra")
    with pytest.raises(ValueError, match=error):
        setup_module.verify_wheels(wheel_root)
