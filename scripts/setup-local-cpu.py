#!/usr/bin/env python3
"""Prepare the local Linux CPU stack, or start its verified files without downloads."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from local_runtime_config import dotenv_values

MINIMUM_COMPOSE = (2, 24, 4)
ARCHITECTURES = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}
IMAGE = re.compile(r"[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64}\Z")
MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
MODEL_REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"


class SetupError(RuntimeError):
    """An actionable error without subprocess output or configuration secrets."""


def run(argv, *, cwd, timeout, env=None):
    """Never relay command output: Docker/Compose failures can contain credentials."""
    try:
        result = subprocess.run(
            [str(value) for value in argv],
            cwd=cwd,
            timeout=timeout,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise SetupError("Command timed out; retry the named setup step.") from None
    except OSError:
        raise SetupError("Command unavailable; check Python, Docker and the POSIX shell.") from None
    if result.returncode:
        raise SetupError("Command failed; captured output was withheld to protect local secrets.")
    return result.stdout.strip()


def shell():
    # Windows uses Git's POSIX shell, never an unrelated WSL distribution.
    git_shell = Path("C:/Program Files/Git/bin/bash.exe")
    if os.name == "nt" and git_shell.is_file():
        return str(git_shell)
    result = shutil.which("sh")
    if not result:
        raise SetupError("A POSIX shell is required for the existing stack wrappers.")
    return result


def read_values(path):
    try:
        return dotenv_values(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except (OSError, ValueError):
        raise SetupError("Invalid app/infra/.env; existing values were not replaced.") from None


def atomic_text(path, value):
    """Replace only the launcher's mode marker; remove its own temporary file on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(value)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def preflight(root, runner, *, switch_mode, start_only):
    if sys.version_info < (3, 11):
        raise SetupError("Python 3.11 or newer is required; Python 3.13 is recommended.")
    env_path = root / "app/infra/.env"
    values = read_values(env_path)
    for source in (os.environ, values):
        if any(value for key, value in source.items() if key.startswith("COMPOSE_")):
            raise SetupError("Remove COMPOSE_* overrides before selecting the local CPU stack.")
    host = os.environ.get("DOCKER_HOST", "")
    if host and not host.startswith(("unix://", "npipe://")):
        raise SetupError("Local CPU setup requires a local Docker endpoint.")
    endpoint = runner(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        cwd=root,
        timeout=15,
    )
    if not endpoint.startswith(("unix://", "npipe://")):
        raise SetupError("Local CPU setup requires a local Docker endpoint.")
    server = runner(
        ["docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}"], cwd=root, timeout=15
    )
    operating_system, _, docker_arch = server.partition("/")
    if operating_system != "linux" or docker_arch not in ARCHITECTURES:
        raise SetupError("Docker must run Linux containers on ARM64 or x86_64.")
    arch = ARCHITECTURES[docker_arch]
    version = runner(["docker", "compose", "version", "--short"], cwd=root, timeout=15)
    matched = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", version)
    if not matched or tuple(int(value) for value in matched.groups()) < MINIMUM_COMPOSE:
        raise SetupError("Docker Compose 2.24.4 or newer is required for the CPU override.")
    marker = root / "outputs/local-runtime-mode.txt"
    mode = marker.read_text(encoding="utf-8").strip() if marker.exists() else None
    if mode not in {None, "local", "spark", "cpu"}:
        raise SetupError("Unknown saved runtime mode; inspect outputs/local-runtime-mode.txt.")
    active = runner(
        [
            "docker",
            "ps",
            "--filter",
            "label=com.docker.compose.project=voiceup",
            "--format",
            "{{.ID}}",
        ],
        cwd=root,
        timeout=15,
    )
    if mode != "cpu" and active:
        raise SetupError(
            "Another VoiceUp mode is running; stop it with its existing stack wrapper, then retry --switch-mode."
        )
    if mode in {"local", "spark"} and not switch_mode:
        raise SetupError(
            "A different mode is saved; stop its services and explicitly retry --switch-mode."
        )
    if start_only and mode != "cpu":
        raise SetupError("CPU mode is not prepared; run python3 scripts/setup-local-cpu.py first.")
    if values.get("CPU_ARCH", arch) != arch or os.environ.get("CPU_ARCH", arch) != arch:
        raise SetupError(
            "CPU_ARCH does not match the Docker server; existing configuration was preserved."
        )
    return arch


def validate_configuration(config, arch):
    try:
        services = config["services"]
        inference = services["inference"]
        environment = inference["environment"]
        reservations = inference.get("deploy", {}).get("resources", {}).get("reservations", {})
        port = services["nginx"]["ports"][0]
        if (
            environment["VOICEUP_INFERENCE_DEVICE"] != "cpu"
            or environment["VOICEUP_INFERENCE_RUNTIME_PROFILE"] != f"{arch}-cpu"
            or inference["build"]["args"]["CPU_ARCH"] != arch
            or inference.get("devices")
            or inference.get("ports")
            or reservations.get("devices")
            or not inference["read_only"]
            or inference["user"] != "10001:10001"
            or not config["networks"]["default"]["internal"]
            or services["backend"]["environment"]["VOICEUP_INFERENCE_URL"]
            != "http://inference:8090"
            or port["host_ip"] != "127.0.0.1"
            or not 1 <= int(port["published"]) <= 65535
        ):
            raise ValueError
        return int(port["published"])
    except (KeyError, TypeError, ValueError, IndexError):
        raise SetupError("CPU Compose configuration violates the local CPU boundary.") from None


def preparation_images(root, config):
    images = set()
    for service in config["services"].values():
        if "build" not in service:
            images.add(service["image"])
        for key, value in service.get("build", {}).get("args", {}).items():
            if key.endswith("BASE_IMAGE"):
                images.add(value)
    source = (root / "app/inference/Dockerfile.cpu").read_text(encoding="utf-8")
    match = re.search(r"(?m)^FROM ([^\s]+)\s*$", source)
    if not match:
        raise SetupError("Dockerfile.cpu must declare its reviewed literal base image.")
    images.add(match[1])
    if any(not isinstance(value, str) or not IMAGE.fullmatch(value) for value in images):
        raise SetupError("Every downloaded image must use a reviewed SHA-256 digest.")
    return sorted(images)


def wait_http_ready(url):
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with opener.open(url, timeout=3) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            pass
        time.sleep(1)
    raise SetupError("Local web readiness timed out; inspect VoiceUp service status.")


def setup(root, *, start_only=False, switch_mode=False, runner=run):
    root = root.resolve()
    arch = preflight(root, runner, switch_mode=switch_mode, start_only=start_only)
    env = {
        **os.environ,
        "CPU_ARCH": arch,
        "KT_SCAFFOLD_PYTHON": Path(sys.executable).as_posix(),
    }
    stack = [shell(), str(root / "scripts/stack.sh"), "--mode", "cpu"]

    def command(name, argv, timeout=60):
        print(name, flush=True)
        try:
            return runner(argv, cwd=root, timeout=timeout, env=env)
        except SetupError as exc:
            raise SetupError(f"{name}: {exc}") from None

    def python_script(name, *args, timeout=300):
        return command(name, [sys.executable, str(root / "scripts" / name), *args], timeout)

    env_path = root / "app/infra/.env"
    model_path = root / "models/speaker-pilot"
    if start_only:
        if not env_path.is_file():
            raise SetupError("Missing app/infra/.env; run python3 scripts/setup-local-cpu.py.")
        if read_values(env_path).get("CPU_ARCH") != arch:
            raise SetupError("CPU_ARCH is missing; run python3 scripts/setup-local-cpu.py.")
        if not (model_path / "manifest.json").is_file():
            raise SetupError(
                "Missing models/speaker-pilot; run python3 scripts/setup-local-cpu.py."
            )
        python_script("package-speaker-model.py", "--output", str(model_path), "--verify")
    else:
        command(
            "Check repository and Docker prerequisites",
            [shell(), str(root / "scripts/bootstrap.sh")],
        )
        python_script("prepare-local-config.py")
        if "CPU_ARCH" not in read_values(env_path):
            with env_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"\nCPU_ARCH={arch}\n")

    try:
        config = json.loads(
            command("Resolve CPU Compose configuration", [*stack, "config", "--format", "json"])
        )
    except json.JSONDecodeError:
        raise SetupError("Docker Compose returned an invalid configuration.") from None
    port = validate_configuration(config, arch)

    if not start_only:
        python_script("prepare-speaker-model.py", timeout=1800)
        python_script(
            "prepare-spark-wheelhouse.py",
            "--manifest",
            str(root / f"app/inference/cpu-{arch}-wheelhouse-manifest.json"),
            "--directory",
            str(root / f"models/inference-cpu-{arch}-wheelhouse"),
            timeout=3600,
        )
        python_script(
            "prepare-audio-libraries.py", "--arch", "arm64" if arch == "aarch64" else "amd64"
        )
        for image in preparation_images(root, config):
            command("Prepare digest-pinned image", ["docker", "pull", image], 1800)
        command(
            "Build local CPU services",
            [*stack, "build", "backend", "frontend", "worker", "migrate", "inference"],
            3600,
        )
        # Once CPU containers may exist, preserve CPU intent even if a later step fails.
        # Before this point a failed preparation leaves the previous mode untouched.
        atomic_text(root / "outputs/local-runtime-mode.txt", "cpu\n")
        command(
            "Start local database",
            [
                *stack,
                "up",
                "-d",
                "--no-build",
                "--pull",
                "never",
                "--wait",
                "--wait-timeout",
                "90",
                "postgres",
                "redis",
            ],
            120,
        )
        python_script("provision-local-runtime.py")
        command(
            "Apply existing database migrations",
            [shell(), str(root / "scripts/db.sh"), "apply"],
            180,
        )
        command(
            "Validate existing database migrations",
            [shell(), str(root / "scripts/db.sh"), "validate"],
            180,
        )

    for name, service in config["services"].items():
        image = service.get("image", f"voiceup-{name}")
        command(
            f"Check prepared image for {name}; rerun setup if missing",
            ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        )
    command(
        "Start prepared CPU services",
        [*stack, "up", "-d", "--no-build", "--pull", "never", "--wait", "--wait-timeout", "180"],
        210,
    )
    # Recreated web containers may have new addresses while an existing nginx keeps old DNS.
    command(
        "Refresh local web routing",
        [*stack, "exec", "-T", "nginx", "sh", "-c", "nginx -t && nginx -s reload"],
        15,
    )
    probe = "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8090/ready', timeout=3).read(4096).decode())"
    try:
        ready = json.loads(
            command(
                "Verify CPU model readiness",
                [*stack, "exec", "-T", "inference", "python", "-c", probe],
                15,
            )
        )
        if (
            ready.get("ready") is not True
            or ready.get("device") != "cpu"
            or type(ready.get("dimensions")) is not int
            or ready["dimensions"] != 192
            or ready.get("model_id") != MODEL_ID
            or ready.get("model_revision") != MODEL_REVISION
        ):
            raise ValueError
    except (json.JSONDecodeError, AttributeError, ValueError):
        raise SetupError("The prepared service did not confirm the expected CPU model.") from None
    wait_http_ready(f"http://127.0.0.1:{port}/api/voiceup/v1/readiness")
    print(f"VoiceUp: http://127.0.0.1:{port}\nModel mode: cpu ({arch})", flush=True)
    if not start_only:
        print(
            "Create your first account interactively: sh scripts/create-super-admin.sh", flush=True
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start-only",
        action="store_true",
        help="Use prepared local files and images; never download or build",
    )
    parser.add_argument(
        "--switch-mode",
        action="store_true",
        help="Explicitly replace a saved mode after its services have been stopped",
    )
    args = parser.parse_args()
    try:
        setup(
            Path(__file__).resolve().parents[1],
            start_only=args.start_only,
            switch_mode=args.switch_mode,
        )
    except (SetupError, OSError) as error:
        # OSError filenames may contain private connection paths. SetupError is sanitized.
        print(
            f"CPU setup failed: {error if isinstance(error, SetupError) else 'Local file operation failed.'}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
