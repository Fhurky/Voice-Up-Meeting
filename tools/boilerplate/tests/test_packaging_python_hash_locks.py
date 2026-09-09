"""Artifact-identity contracts for the connected-factory Python bundle build."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFLINE_BUNDLE = ROOT / "packaging/offline-bundle.sh"
APPSEC_DOCKERFILE = ROOT / "Dockerfile"
VERSION_LOCK = ROOT / "packaging/requirements.lock"
GENERATOR_LOCK = ROOT / "packaging/locks/generator-linux-amd64-cp313-musllinux.requirements.lock"
BUILD_LOCK = ROOT / "packaging/locks/build-system.requirements.lock"
ALPINE_RUNTIME_LOCK = ROOT / "packaging/locks/alpine-runtime-packages.lock"
HASH_PATTERN = re.compile(r"--hash=sha256:([0-9a-f]{64})(?:\s|$)")


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _hashed_requirements(path: Path) -> dict[str, tuple[str, str]]:
    logical = path.read_text(encoding="utf-8").replace("\\\n", " ")
    requirements: dict[str, tuple[str, str]] = {}
    for raw_line in logical.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirement, *_ = line.split()
        name, version = requirement.split("==", maxsplit=1)
        hashes = HASH_PATTERN.findall(line)
        assert len(hashes) == 1, f"{path}: expected one admitted artifact for {requirement}"
        normalized = _normalize(name)
        assert normalized not in requirements
        requirements[normalized] = (version, hashes[0])
    return requirements


def _version_requirements(path: Path) -> dict[str, str]:
    requirements: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", maxsplit=1)
        requirements[_normalize(name)] = version
    return requirements


def test_default_generator_lock_hashes_exactly_the_complete_version_lock() -> None:
    expected = _version_requirements(VERSION_LOCK)
    admitted = _hashed_requirements(GENERATOR_LOCK)

    assert {name: version for name, (version, _) in admitted.items()} == expected


def test_build_frontend_and_backend_pins_are_in_the_admitted_generator_set() -> None:
    generator = _hashed_requirements(GENERATOR_LOCK)
    build = _hashed_requirements(BUILD_LOCK)
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    backend_requirements = {
        _normalize(requirement.split("==", maxsplit=1)[0]): requirement.split("==", maxsplit=1)[1]
        for requirement in pyproject["build-system"]["requires"]
    }

    assert {"build", "packaging", "pyproject-hooks", "setuptools", "wheel"} == set(build)
    for name, version in backend_requirements.items():
        assert build[name][0] == version
    for name, identity in build.items():
        assert generator[name] == identity


def test_bundle_resolves_by_hash_before_code_runs_and_builds_without_isolation() -> None:
    script = OFFLINE_BUNDLE.read_text(encoding="utf-8")

    subprocess.run(["sh", "-n", str(OFFLINE_BUNDLE)], check=True)
    assert script.index("--require-hashes") < script.index('"$python" -m venv')
    assert 'PIP_NO_INDEX=1 "$work/build-env/bin/python" -m build' in script
    assert "--no-isolation" in script
    assert 'cp "$resolved_generator_lock" "$bundle/generator-requirements.lock"' in script
    assert 'cp "$resolved_build_system_lock" "$bundle/build-system-requirements.lock"' in script
    assert "generator-requirements-lock-sha256=" in script
    assert "build-system-lock-sha256=" in script
    assert "alpine-runtime-lock-sha256=" in script
    assert "shasum -a 256 -c -" in script
    assert "apk fetch --available --output /apk" in script
    assert '"$root/agent-platform/runtime-candidate.schema.json"' in script
    assert '"$root/agent-platform/agents"' in script
    assert "examples/client-projections" not in script
    assert "conformance/candidates" not in script


def test_appsec_image_builds_from_reviewed_hash_locks_and_keeps_runtime_minimal() -> None:
    dockerfile = APPSEC_DOCKERFILE.read_text(encoding="utf-8")

    assert "FROM ${KT_SCAFFOLD_BASE_IMAGE} AS builder" in dockerfile
    assert dockerfile.count("--require-hashes") == 2
    assert dockerfile.index("--require-hashes") < dockerfile.index("python -m build")
    assert "PIP_NO_INDEX=1 /build-env/bin/python -m build" in dockerfile
    assert "COPY --from=builder /wheelhouse/ /opt/wheelhouse/" in dockerfile
    assert "COPY --from=builder /dist/kt_scaffold-*.whl /opt/wheelhouse/" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "packaging/wheelhouse" not in dockerfile
    assert "agent-platform/runtime-candidate.schema.json" in dockerfile
    assert "COPY agent-platform/agents/ agent-platform/agents/" in dockerfile
    assert "examples/client-projections" not in dockerfile
    assert "conformance/candidates" not in dockerfile
    assert "COPY packaging/locks/alpine-runtime-packages.lock" in dockerfile
    assert "sha256sum -c -" in dockerfile
    assert (
        'apk add --no-cache --no-network --repositories-file /dev/null "/tmp/${package_file}"'
        in dockerfile
    )


def test_alpine_runtime_lock_is_architecture_complete_and_digest_pinned() -> None:
    records: dict[str, tuple[str, str, str]] = {}
    for raw_line in ALPINE_RUNTIME_LOCK.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        docker_arch, alpine_arch, package_spec, digest = line.split()
        assert docker_arch not in records
        assert package_spec == "sqlite-libs=3.53.4-r0"
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
        records[docker_arch] = (alpine_arch, package_spec, digest)

    assert set(records) == {"amd64", "arm64"}
    assert records["amd64"][0] == "x86_64"
    assert records["arm64"][0] == "aarch64"


def test_offline_generator_installs_only_the_sealed_runtime_apk() -> None:
    dockerfile = (ROOT / "packaging/Dockerfile").read_text(encoding="utf-8")

    assert "COPY alpine-runtime-packages.lock" in dockerfile
    assert "COPY apk/ /opt/apk/" in dockerfile
    assert "sha256sum -c -" in dockerfile
    assert (
        "apk add --no-cache --no-network --repositories-file /dev/null "
        '"/opt/apk/${package_file}"' in dockerfile
    )


def test_non_default_generator_matrix_requires_an_explicit_reviewed_hash_lock(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        ["sh", str(OFFLINE_BUNDLE), str(tmp_path / "bundle")],
        env={**os.environ, "GENERATOR_PYTHON_VERSION": "311"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "non-default generator matrix requires GENERATOR_REQUIREMENTS_LOCK" in completed.stderr
    assert not (tmp_path / "bundle").exists()


def test_bundle_requires_a_native_platform_artifact_factory() -> None:
    script = OFFLINE_BUNDLE.read_text(encoding="utf-8")

    assert 'factory_platform="$factory_os/$factory_arch"' in script
    assert 'if [ "$factory_platform" != "$oci_platform" ]' in script
    assert (
        "npm optional dependencies, Playwright and OCI images require a native matrix runner"
        in script
    )


def test_bundle_contains_no_node_backend_or_prisma_engine_context() -> None:
    script = OFFLINE_BUNDLE.read_text(encoding="utf-8")

    assert "prisma" not in script.lower()
    assert "templates/node-nestjs" not in script


def test_pip_rejects_same_name_and_version_with_substituted_bytes(tmp_path: Path) -> None:
    admitted_hash = _hashed_requirements(BUILD_LOCK)["wheel"][1]
    mirror = tmp_path / "mirror"
    destination = tmp_path / "download"
    mirror.mkdir()
    substituted = mirror / "wheel-0.45.1-py3-none-any.whl"
    substituted.write_bytes(b"different bytes under the admitted filename")
    requirement = tmp_path / "requirements.lock"
    requirement.write_text(
        f"wheel==0.45.1 --hash=sha256:{admitted_hash}\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--disable-pip-version-check",
            "--no-index",
            "--only-binary=:all:",
            "--require-hashes",
            "--find-links",
            str(mirror),
            "--dest",
            str(destination),
            "-r",
            str(requirement),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "DO NOT MATCH THE HASHES" in completed.stderr
    assert not destination.exists() or not any(destination.iterdir())
