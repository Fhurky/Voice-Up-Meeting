#!/usr/bin/env python3
"""Prepare the explicitly selected local x86_64 meeting extension; never start a service."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, root: Path, timeout: int = 1800) -> str:
    result = subprocess.run(command, cwd=root, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        # Model download errors and Compose output can contain credentials or signed URLs.
        raise RuntimeError("meeting_preparation_step_failed")
    return result.stdout.decode("utf-8").strip()


def validate_local_docker(root: Path, runner=run) -> None:
    configured_host = os.environ.get("DOCKER_HOST", "")
    if configured_host and not configured_host.startswith(("unix://", "npipe://")):
        raise ValueError("local_docker_required")
    endpoint = runner(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        root=root,
        timeout=15,
    )
    if not endpoint.startswith(("unix://", "npipe://")):
        raise ValueError("local_docker_required")
    platform = runner(
        ["docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}"], root=root, timeout=15
    )
    if platform not in {"linux/amd64", "linux/x86_64"}:
        raise ValueError("local_linux_x86_64_required")


def locked_hashes(path: Path) -> dict[tuple[str, str], set[str]]:
    pins: dict[tuple[str, str], set[str]] = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", line)
        if match:
            current = (re.sub(r"[-_.]+", "-", match[1]).lower(), match[2])
            if current in pins:
                raise ValueError("duplicate_locked_package")
            pins[current] = set()
        if current is not None:
            pins[current].update(re.findall(r"--hash=sha256:([a-f0-9]{64})", line))
    if not pins or any(not hashes for hashes in pins.values()):
        raise ValueError("invalid_hash_lock")
    return pins


def verify_wheels(root: Path) -> None:
    helper = runpy.run_path(str(root / "scripts/prepare-spark-wheelhouse.py"))
    for directory, lock in (
        ("models/inference-wheelhouse", "app/inference/requirements.txt"),
        ("models/meeting-inference-wheelhouse", "app/inference/requirements.meeting-x86_64.txt"),
    ):
        expected = locked_hashes(helper["checked_path"](root / lock))
        folder = helper["checked_path"](root / directory)
        if not folder.is_dir():
            raise ValueError("wheelhouse_missing")
        seen = set()
        for wheel in folder.glob("*.whl"):
            helper["validate_filename"](wheel.name)
            helper["checked_path"](wheel)
            parts = wheel.name.split("-")
            if len(parts) < 5:
                raise ValueError("invalid_wheel_filename")
            package = (re.sub(r"[-_.]+", "-", parts[0]).lower(), parts[1])
            if package not in expected or package in seen:
                raise ValueError("unexpected_wheel")
            with wheel.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest not in expected[package]:
                raise ValueError("wheel_hash_mismatch")
            seen.add(package)
        if seen != set(expected):
            raise ValueError("wheelhouse_incomplete")


def prepare(
    root: Path = ROOT, *, verify_only: bool = False, runner=run, wheel_verifier=verify_wheels
) -> None:
    root = root.absolute()
    if not verify_only:
        validate_local_docker(root, runner)
    python = sys.executable

    def script(name, *arguments):
        return [python, str(root / "scripts" / name), *arguments]

    admission = script("check-dependency-admission.py", "--root", str(root))
    runner(admission, root=root)
    runner(
        script(
            "package-speaker-model.py", "--output", str(root / "models/speaker-pilot"), "--verify"
        ),
        root=root,
    )
    for name in ("prepare-diarization-model.py", "prepare-asr-model.py"):
        runner(script(name, "--root", str(root), *(["--verify"] if verify_only else [])), root=root)
    if not verify_only:
        runner(
            script(
                "prepare-spark-wheelhouse.py",
                "--manifest",
                str(root / "app/inference/meeting-x86_64-wheelhouse-manifest.json"),
                "--directory",
                str(root / "models/meeting-inference-wheelhouse"),
            ),
            root=root,
        )
    wheel_verifier(root)
    if verify_only:
        return
    runner(admission, root=root)
    runner(
        [
            "docker",
            "compose",
            "--project-directory",
            "app/infra",
            "-p",
            "voiceup",
            "-f",
            "app/infra/docker-compose.local.yml",
            "-f",
            "app/infra/docker-compose.meeting.yml",
            "build",
            "inference",
        ],
        root=root,
    )
    helper = runpy.run_path(str(ROOT / "scripts/prepare-spark-wheelhouse.py"))
    marker = helper["checked_path"](root / "outputs/local-meeting-enabled.txt")
    helper["directory_path"](marker.parent)
    if marker.exists() and marker.read_text(encoding="utf-8").strip() != "enabled":
        raise ValueError("invalid_meeting_selection")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=marker.parent, delete=False
    ) as source:
        temporary = Path(source.name)
        source.write("enabled\n")
        source.flush()
        os.fsync(source.fileno())
    try:
        helper["checked_path"](marker)
        os.replace(temporary, marker)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify offline without downloads, builds or selecting the extension",
    )
    arguments = parser.parse_args()
    try:
        prepare(verify_only=arguments.verify)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        print(
            "Meeting preparation failed; check admitted dependencies, local packages, Docker and disk space. Existing files and runtime selection were preserved.",
            file=sys.stderr,
        )
        return 1
    print(
        "Local meeting packages verified"
        if arguments.verify
        else "Local x86_64 meeting image prepared. Run scripts/start-local.ps1 -Mode Local to start it."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
