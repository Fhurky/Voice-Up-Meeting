"""Local setup preserves dotenv values and never selects an unrelated Compose project."""

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_existing_quoted_exported_values_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    prepare = load_script("prepare-local-config")
    path = tmp_path / ".env"
    token = "existing_fixture_secret_" + "x" * 32
    original = f'\ufeff  export JWT_SECRET = "{token}" # preserve\nAPP_HTTP_PORT=8173\n'
    path.write_text(original, encoding="utf-8")
    prepare.prepare_config(path)
    updated = path.read_text(encoding="utf-8-sig")
    assert updated.count("JWT_SECRET") == 1
    assert token in updated and "APP_HTTP_PORT=8173" in updated
    assert "INFERENCE_INTERNAL_KEY=" in updated
    prepare.prepare_config(path)
    assert path.read_text(encoding="utf-8-sig") == updated


def test_invalid_existing_secret_fails_without_rewriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    prepare = load_script("prepare-local-config")
    path = tmp_path / ".env"
    original = "JWT_SECRET=\n"
    path.write_text(original)
    with pytest.raises(ValueError, match="JWT_SECRET"):
        prepare.prepare_config(path)
    assert path.read_text() == original


def test_runtime_provisioning_parses_quotes_and_pins_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    provision = load_script("provision-local-runtime")
    env_path = tmp_path / "app/infra/.env"
    env_path.parent.mkdir(parents=True)
    env_path.write_text('export RUNTIME_DATABASE_PASSWORD = "' + "x" * 40 + '"\n')
    calls = []

    def fake_run(command, **kwargs):
        from types import SimpleNamespace

        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(provision.subprocess, "run", fake_run)
    provision.provision_runtime(tmp_path)
    command, options = calls[0]
    assert command[command.index("-p") + 1] == "voiceup"
    assert "x" * 40 not in " ".join(command)
    assert "BEGIN;" in options["input"] and "COMMIT;" in options["input"]
    assert "pg_auth_members" in options["input"]
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE" in options["input"]


def test_startup_uses_resolved_port_and_cannot_pull_images(tmp_path: Path) -> None:
    from test_spark_startup import build_native_docker, calls, make_startup, run_startup

    # The native fixture cannot invoke Docker or change any application service.
    startup = make_startup(tmp_path, build_native_docker(tmp_path / "native-fixture"))
    (tmp_path / "models/speaker-pilot").mkdir(parents=True)
    (tmp_path / "models/speaker-pilot/manifest.json").write_text("{}")
    result = run_startup(startup, arguments="-Mode Local")
    assert result.returncode == 0, result.stderr
    assert "VoiceUp: http://127.0.0.1:8173" in result.stdout
    up = [call for call in calls(startup) if "up" in call]
    assert len(up) == 1
    assert up[0][up[0].index("--pull") + 1] == "never"
    assert up[0][up[0].index("-p") + 1] == "voiceup"


@pytest.mark.parametrize("mode", ["local", "spark", "x86_64", "aarch64"])
@pytest.mark.parametrize("explicit", [False, True], ids=["default", "disabled-with-user"])
def test_real_compose_local_admin_settings_remain_local_and_inherited(
    tmp_path: Path, mode: str, explicit: bool
) -> None:
    docker = shutil.which("docker")
    assert docker, "Docker CLI is required for the local admin Compose contract"
    infra = SCRIPTS.parent / "app/infra"
    env_file = tmp_path / "fixture.env"
    fixture = (
        "INFERENCE_INTERNAL_KEY=fixture-inference-" + "x" * 32 + "\n"
        "RUNTIME_DATABASE_PASSWORD=fixture-runtime-" + "x" * 32 + "\n"
        "GRAFANA_ADMIN_PASSWORD=fixture-grafana\n"
    )
    if mode in {"x86_64", "aarch64"}:
        fixture += f"CPU_ARCH={mode}\n"
    if explicit:
        fixture += "LOCAL_ADMIN_LOGIN_ENABLED=false\nLOCAL_ADMIN_USERNAME=fixture-admin\n"
    env_file.write_text(fixture, encoding="utf-8")
    command = [
        docker,
        "compose",
        "--project-directory",
        str(infra),
        "--env-file",
        str(env_file),
        "-p",
        "voiceup-local-admin-contract",
        "-f",
        str(infra / "docker-compose.local.yml"),
        "-f",
        str(infra / "docker-compose.observability.yml"),
    ]
    if mode != "local":
        layer = "spark" if mode == "spark" else "cpu"
        command += ["-f", str(infra / f"docker-compose.{layer}.yml")]
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COMPOSE_", "LOCAL_ADMIN_"))
        and key
        not in {
            "CPU_ARCH",
            "INFERENCE_INTERNAL_KEY",
            "RUNTIME_DATABASE_PASSWORD",
            "GRAFANA_ADMIN_PASSWORD",
        }
    }
    result = subprocess.run(
        [*command, "--profile", "*", "config", "--format", "json"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, "Compose contract failed; resolved values withheld"
    services = json.loads(result.stdout)["services"]
    for name in ("backend", "worker", "migrate"):
        configured = services[name]["environment"]
        assert configured["VOICEUP_LOCAL_ADMIN_LOGIN_ENABLED"] == ("false" if explicit else "true")
        assert configured["VOICEUP_LOCAL_ADMIN_USERNAME"] == ("fixture-admin" if explicit else "")
        assert configured["VOICEUP_ENVIRONMENT"] == "development"
        assert not services[name].get("ports")
    assert all(port["host_ip"] == "127.0.0.1" for port in services["nginx"]["ports"])
    assert "VOICEUP_LOCAL_ADMIN_LOGIN_ENABLED" not in services["inference"]["environment"]
