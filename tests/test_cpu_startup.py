"""CPU setup contracts use temporary files and signature-constrained command doubles."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SECRET = "fixture-private-secret-" + "x" * 40
MODEL = {
    "ready": True,
    "device": "cpu",
    "dimensions": 192,
    "model_id": "speechbrain/spkrec-ecapa-voxceleb",
    "model_revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
}


@pytest.fixture
def launcher():
    path = ROOT / "scripts/setup-local-cpu.py"
    spec = importlib.util.spec_from_file_location("cpu_setup", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(ROOT / "scripts"))


def configuration(arch="aarch64"):
    return {
        "services": {
            "postgres": {"image": "postgres@sha256:" + "1" * 64},
            "inference": {
                "image": f"voiceup-inference-cpu:{arch}",
                "build": {"args": {"CPU_ARCH": arch}},
                "environment": {
                    "VOICEUP_INFERENCE_DEVICE": "cpu",
                    "VOICEUP_INFERENCE_RUNTIME_PROFILE": f"{arch}-cpu",
                },
                "read_only": True,
                "user": "10001:10001",
            },
            "backend": {
                "build": {"args": {"PYTHON_BASE_IMAGE": "python@sha256:" + "2" * 64}},
                "environment": {"VOICEUP_INFERENCE_URL": "http://inference:8090"},
            },
            "frontend": {
                "build": {"args": {"FRONTEND_NODE_BASE_IMAGE": "node@sha256:" + "3" * 64}}
            },
            "worker": {"build": {}},
            "migrate": {"build": {}},
            "nginx": {
                "image": "nginx@sha256:" + "4" * 64,
                "ports": [{"host_ip": "127.0.0.1", "published": "8173", "target": 8080}],
            },
        },
        "networks": {"default": {"internal": True}},
    }


class Commands:
    def __init__(self, root, arch="arm64"):
        self.root = root
        self.arch = arch
        self.os = "linux"
        self.version = "2.39.2"
        self.active = ""
        self.endpoint = "unix:///var/run/docker.sock"
        self.fail = None
        self.calls = []
        self.markers = []
        self.environments = []

    def __call__(self, argv, *, cwd, timeout, env=None):
        command = [str(value) for value in argv]
        self.calls.append(command)
        self.environments.append(env)
        marker = self.root / "outputs/local-runtime-mode.txt"
        self.markers.append(marker.read_text() if marker.exists() else None)
        if self.fail and self.fail in command:
            raise RuntimeError("fixture-command-failure")
        if command[:2] == ["docker", "version"]:
            return f"{self.os}/{self.arch}"
        if command[:3] == ["docker", "compose", "version"]:
            return self.version
        if command[:3] == ["docker", "context", "inspect"]:
            return self.endpoint
        if command[:2] == ["docker", "ps"]:
            return self.active
        if "config" in command:
            return json.dumps(configuration("aarch64" if self.arch == "arm64" else "x86_64"))
        if any(value.endswith("prepare-local-config.py") for value in command):
            path = self.root / "app/infra/.env"
            if not path.exists():
                path.write_text(f"JWT_SECRET={SECRET}\n")
        if any(value.endswith("prepare-speaker-model.py") for value in command):
            target = self.root / "models/speaker-pilot/manifest.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}")
        if "exec" in command and "inference" in command:
            return json.dumps(MODEL)
        return ""


@pytest.fixture
def prepared(tmp_path):
    (tmp_path / "app/infra").mkdir(parents=True)
    (tmp_path / "app/inference").mkdir(parents=True)
    (tmp_path / "app/inference/Dockerfile.cpu").write_text("FROM python@sha256:" + "5" * 64 + "\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/stack.sh").write_text("#!/bin/sh\n")
    return tmp_path


@pytest.mark.parametrize("arch,expected", [("arm64", "aarch64"), ("amd64", "x86_64")])
def test_first_setup_prepares_matching_artifacts_before_database_and_persists_mode(
    launcher, prepared, monkeypatch, arch, expected
):
    commands = Commands(prepared, arch)
    monkeypatch.setattr(launcher, "wait_http_ready", lambda url: None)
    launcher.setup(prepared, runner=commands)
    joined = [" ".join(command) for command in commands.calls]
    assert any(f"cpu-{expected}-wheelhouse-manifest.json" in command for command in joined)
    assert any(f"inference-cpu-{expected}-wheelhouse" in command for command in joined)
    assert any("prepare-audio-libraries.py --arch " + arch in command for command in joined)
    migration = next(i for i, command in enumerate(joined) if "db.sh apply" in command)
    provision = next(
        i for i, command in enumerate(joined) if "provision-local-runtime.py" in command
    )
    build = next(i for i, command in enumerate(commands.calls) if "build" in command)
    assert build < provision < migration
    assert any("bootstrap.sh" in command for command in joined)
    bootstrap = next(i for i, command in enumerate(joined) if "bootstrap.sh" in command)
    assert Path(commands.environments[bootstrap]["KT_SCAFFOLD_PYTHON"]) == Path(sys.executable)
    assert commands.markers[migration] == "cpu\n"
    assert (prepared / "outputs/local-runtime-mode.txt").read_text() == "cpu\n"
    assert f"CPU_ARCH={expected}" in (prepared / "app/infra/.env").read_text()
    assert not any(
        "spark" in command.lower() and "prepare-spark-wheelhouse.py" not in command
        for command in joined
    )


@pytest.mark.parametrize("kind", ["windows", "unknown_arch", "old_compose", "remote_docker"])
def test_unsupported_host_fails_before_local_files_or_mutations(launcher, prepared, kind):
    commands = Commands(prepared)
    if kind == "windows":
        commands.os = "windows"
    elif kind == "unknown_arch":
        commands.arch = "ppc64le"
    elif kind == "old_compose":
        commands.version = "2.20.0"
    else:
        commands.endpoint = "ssh://fixture-private-host"
    with pytest.raises(launcher.SetupError):
        launcher.setup(prepared, runner=commands)
    assert not (prepared / "app/infra/.env").exists()
    assert not (prepared / "outputs/local-runtime-mode.txt").exists()
    assert not any("up" in command or "pull" in command for command in commands.calls)


def test_old_host_python_fails_before_docker_or_local_files(launcher, prepared, monkeypatch):
    monkeypatch.setattr(launcher.sys, "version_info", (3, 10, 14))
    monkeypatch.setattr(
        launcher, "wait_http_ready", lambda url: pytest.fail("Old Python must not reach startup")
    )
    commands = Commands(prepared)
    with pytest.raises(launcher.SetupError, match="Python 3.11"):
        launcher.setup(prepared, runner=commands)
    assert not commands.calls
    assert not (prepared / "app/infra/.env").exists()


def test_bootstrap_uses_explicit_python_without_requiring_python3_on_path(tmp_path):
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    sh = str(git_bash) if git_bash.exists() else shutil.which("sh")
    assert sh
    fake = tmp_path / "fake-python"
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> "$BOOTSTRAP_CALLS"\n', newline="\n")
    fake.chmod(0o755)
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    docker = bin_path / "docker"
    docker.write_text("#!/bin/sh\nexit 0\n", newline="\n")
    docker.chmod(0o755)
    result = subprocess.run(
        [sh, str(ROOT / "scripts/bootstrap.sh")],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": str(bin_path),
            "KT_SCAFFOLD_PYTHON": fake.as_posix(),
            "BOOTSTRAP_CALLS": (tmp_path / "calls").as_posix(),
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, "bootstrap must reuse the selected Python"
    assert (tmp_path / "calls").read_text().splitlines() == [
        "scripts/check-governance-drift.py",
        "scripts/check-dependency-admission.py",
    ]


@pytest.mark.parametrize("mode", ["local", "spark"])
@pytest.mark.parametrize("switch", [False, True])
def test_other_running_mode_is_never_changed(launcher, prepared, mode, switch):
    marker = prepared / "outputs/local-runtime-mode.txt"
    marker.parent.mkdir()
    marker.write_text(mode + "\n")
    commands = Commands(prepared)
    commands.active = "fixture-container"
    with pytest.raises(launcher.SetupError, match="stop"):
        launcher.setup(prepared, switch_mode=switch, runner=commands)
    assert marker.read_text() == mode + "\n"
    assert not (prepared / "app/infra/.env").exists()
    assert not any("stop" in command or "down" in command for command in commands.calls)


def test_stopped_mode_needs_explicit_switch_and_build_failure_preserves_it(launcher, prepared):
    marker = prepared / "outputs/local-runtime-mode.txt"
    marker.parent.mkdir()
    marker.write_text("spark\n")
    commands = Commands(prepared)
    with pytest.raises(launcher.SetupError, match="switch-mode"):
        launcher.setup(prepared, runner=commands)
    commands.fail = "build"
    with pytest.raises(RuntimeError):
        launcher.setup(prepared, switch_mode=True, runner=commands)
    assert marker.read_text() == "spark\n"


def test_partial_database_failure_preserves_cpu_intent_and_existing_secrets(launcher, prepared):
    env_path = prepared / "app/infra/.env"
    original = f'export JWT_SECRET="{SECRET}" # keep\nAPP_HTTP_PORT=8173\n'
    env_path.write_text(original)
    commands = Commands(prepared)
    commands.fail = "up"
    with pytest.raises(RuntimeError):
        launcher.setup(prepared, runner=commands)
    assert env_path.read_text().startswith(original)
    assert (prepared / "outputs/local-runtime-mode.txt").read_text() == "cpu\n"


def test_daily_start_uses_only_prepared_images_and_validates_real_cpu_readiness(
    launcher, prepared, monkeypatch
):
    (prepared / "app/infra/.env").write_text(f"CPU_ARCH=aarch64\nJWT_SECRET={SECRET}\n")
    marker = prepared / "outputs/local-runtime-mode.txt"
    marker.parent.mkdir()
    marker.write_text("cpu\n")
    model = prepared / "models/speaker-pilot/manifest.json"
    model.parent.mkdir(parents=True)
    model.write_text("{}")
    observed_urls = []
    monkeypatch.setattr(launcher, "wait_http_ready", observed_urls.append)
    commands = Commands(prepared)
    launcher.setup(prepared, start_only=True, runner=commands)
    assert observed_urls == ["http://127.0.0.1:8173/api/voiceup/v1/readiness"]
    assert not any("pull" in command or "build" in command for command in commands.calls)
    starts = [command for command in commands.calls if "up" in command]
    assert len(starts) == 1
    assert "--no-build" in starts[0] and starts[0][starts[0].index("--pull") + 1] == "never"
    assert not any("prepare-" in " ".join(command) for command in commands.calls)
    assert any("image" in command and "inspect" in command for command in commands.calls)
    assert any("nginx -t && nginx -s reload" in command for command in commands.calls)


def test_daily_start_names_missing_model_without_starting_containers(launcher, prepared):
    (prepared / "app/infra/.env").write_text("CPU_ARCH=aarch64\n")
    marker = prepared / "outputs/local-runtime-mode.txt"
    marker.parent.mkdir()
    marker.write_text("cpu\n")
    commands = Commands(prepared)
    with pytest.raises(launcher.SetupError, match="models/speaker-pilot"):
        launcher.setup(prepared, start_only=True, runner=commands)
    assert not any("up" in command for command in commands.calls)


def test_subprocess_failure_and_timeout_never_expose_captured_secret(launcher, monkeypatch):
    def failure(argv, *, cwd, timeout, env, capture_output, text, check):
        return subprocess.CompletedProcess(argv, 1, stdout=SECRET, stderr=SECRET)

    monkeypatch.setattr(subprocess, "run", failure)
    with pytest.raises(launcher.SetupError) as failed:
        launcher.run(["docker", "info"], cwd=ROOT, timeout=1)
    assert SECRET not in str(failed.value)

    def timeout(argv, *, cwd, timeout, env, capture_output, text, check):
        raise subprocess.TimeoutExpired(argv, timeout, output=SECRET, stderr=SECRET)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(launcher.SetupError) as timed_out:
        launcher.run(["docker", "info"], cwd=ROOT, timeout=1)
    assert SECRET not in str(timed_out.value)


@pytest.mark.parametrize("arch", ["aarch64", "x86_64"])
def test_real_compose_cpu_overlay_has_no_gpu_or_external_model_port(tmp_path, arch):
    docker = shutil.which("docker")
    assert docker, "Docker CLI is required for the CPU Compose contract"
    env_file = tmp_path / "fixture.env"
    env_file.write_text(
        f"CPU_ARCH={arch}\nINFERENCE_INTERNAL_KEY={SECRET}\nRUNTIME_DATABASE_PASSWORD={SECRET}\nGRAFANA_ADMIN_PASSWORD={SECRET}\n"
    )
    result = subprocess.run(
        [
            docker,
            "compose",
            "--project-directory",
            str(ROOT / "app/infra"),
            "--env-file",
            str(env_file),
            "-f",
            str(ROOT / "app/infra/docker-compose.local.yml"),
            "-f",
            str(ROOT / "app/infra/docker-compose.observability.yml"),
            "-f",
            str(ROOT / "app/infra/docker-compose.cpu.yml"),
            "config",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={
            key: value
            for key, value in os.environ.items()
            if not key.startswith("COMPOSE_") and key != "CPU_ARCH"
        },
    )
    assert result.returncode == 0, "CPU Compose model could not be resolved"
    resolved = json.loads(result.stdout)
    model = resolved["services"]["inference"]
    assert not model.get("ports") and not model.get("devices")
    assert not model.get("deploy", {}).get("resources", {}).get("reservations", {}).get("devices")
    assert model["environment"]["VOICEUP_INFERENCE_DEVICE"] == "cpu"
    assert model["environment"]["VOICEUP_INFERENCE_RUNTIME_PROFILE"] == f"{arch}-cpu"
    assert model["read_only"] and model["user"] == "10001:10001"
    assert resolved["networks"]["default"]["internal"]
    assert resolved["services"]["nginx"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert model["build"]["args"]["CPU_ARCH"] == arch


@pytest.mark.parametrize(
    "field,value",
    [
        ("device", "cuda:0"),
        ("dimensions", True),
        ("ready", False),
        ("model_revision", "wrong-model"),
    ],
)
def test_wrong_model_readiness_cannot_claim_cpu_startup(
    launcher, prepared, monkeypatch, field, value
):
    commands = Commands(prepared)

    def runner(argv, *, cwd, timeout, env=None):
        result = commands(argv, cwd=cwd, timeout=timeout, env=env)
        if "exec" in argv and "inference" in argv:
            return json.dumps({**MODEL, field: value})
        return result

    monkeypatch.setattr(
        launcher, "wait_http_ready", lambda url: pytest.fail("Wrong model must not reach success")
    )
    with pytest.raises(launcher.SetupError, match="expected CPU model"):
        launcher.setup(prepared, runner=runner)


@pytest.mark.parametrize("override", ["CPU_ARCH", "COMPOSE_FILE", "COMPOSE_PROFILES"])
def test_conflicting_environment_is_preserved_and_rejected(launcher, prepared, override):
    path = prepared / "app/infra/.env"
    original = f"{override}=conflicting-fixture-value\n"
    path.write_text(original)
    commands = Commands(prepared)
    with pytest.raises(launcher.SetupError):
        launcher.setup(prepared, runner=commands)
    assert path.read_text() == original
    assert not any("up" in command or "pull" in command for command in commands.calls)


@pytest.mark.parametrize(
    "arguments,allowed",
    [
        (["ps"], True),
        (["--mode", "cpu", "ps"], True),
        (["--profile", "tools", "up"], False),
        (["-f", "other.yml", "up"], False),
    ],
)
def test_shell_stack_selects_cpu_mode_and_rejects_compose_overrides(tmp_path, arguments, allowed):
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    bash = str(git_bash) if git_bash.exists() else shutil.which("sh")
    assert bash
    (tmp_path / "scripts").mkdir()
    shutil.copyfile(ROOT / "scripts/stack.sh", tmp_path / "scripts/stack.sh")
    (tmp_path / "app/infra").mkdir(parents=True)
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs/local-runtime-mode.txt").write_text("cpu\n")
    (tmp_path / "fake-bin").mkdir()
    docker = tmp_path / "fake-bin/docker"
    docker.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n', newline="\n")
    docker.chmod(0o755)
    result = subprocess.run(
        [bash, "-c", 'PATH="$PWD/fake-bin:$PATH" sh scripts/stack.sh "$@"', "test", *arguments],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env={key: value for key, value in os.environ.items() if not key.startswith("COMPOSE_")},
    )
    assert (result.returncode == 0) is allowed
    if allowed:
        assert "docker-compose.cpu.yml" in result.stdout
        assert "docker-compose.spark.yml" not in result.stdout
        assert "voiceup" in result.stdout
    else:
        assert not result.stdout
