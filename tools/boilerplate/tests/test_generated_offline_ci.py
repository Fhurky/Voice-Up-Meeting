"""Fail-closed contracts for generated workflows that build Compose services."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPOSITORY_ROOT / "src/kt_scaffold/templates/common"
WORKFLOW_ROOT = TEMPLATE_ROOT / ".github/workflows"
VERIFY_SCRIPT = TEMPLATE_ROOT / "scripts/verify-offline-bundle.sh"
WORKFLOW_NAMES = ("backend-test.yml", "frontend-test.yml", "schema-check.yml")


def _workflow(name: str) -> tuple[str, dict[str, Any]]:
    text = (WORKFLOW_ROOT / name).read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def _verification_step(parsed: dict[str, Any]) -> str:
    jobs = list(parsed["jobs"].values())
    assert len(jobs) == 1
    matches = [
        step
        for step in jobs[0]["steps"]
        if step.get("name") == "Verify and wire admitted offline inputs"
    ]
    assert len(matches) == 1
    return str(matches[0]["run"])


def _host_oci_platform() -> str:
    architectures = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}
    return f"{platform.system().lower()}/{architectures[platform.machine().lower()]}"


def _seal_bundle(bundle: Path) -> str:
    files = {
        "BUILD-MATRIX": f"oci-platform={_host_oci_platform()}\n",
        "npm-cache/index.json": "{}\n",
        "runtime-images.tar": "admitted OCI archive\n",
        "wheelhouse/generator/generator.whl": "generator wheel\n",
        "wheelhouse/python-fastapi/profile.whl": "profile wheel\n",
    }
    for relative, content in files.items():
        path = bundle / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    entries = []
    for relative in sorted(files):
        digest = hashlib.sha256((bundle / relative).read_bytes()).hexdigest()
        entries.append(f"{digest}  ./{relative}\n")
    manifest = bundle / "SHA256SUMS"
    manifest.write_text("".join(entries), encoding="utf-8")
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def _run_verifier(bundle: Path | None, digest: str = "0" * 64) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if bundle is None:
        environment.pop("KT_SCAFFOLD_OFFLINE_BUNDLE", None)
    else:
        environment["KT_SCAFFOLD_OFFLINE_BUNDLE"] = str(bundle)
    environment["KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256"] = digest
    return subprocess.run(
        ["sh", str(VERIFY_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


@pytest.mark.parametrize("name", WORKFLOW_NAMES)
def test_building_workflows_are_admitted_bundle_only(name: str) -> None:
    text, parsed = _workflow(name)
    environment = parsed["env"]
    verification = _verification_step(parsed)

    assert environment["DEPENDENCY_MODE"] == "offline"
    assert environment["KT_SCAFFOLD_OFFLINE_BUNDLE"] == ("${{ vars.KT_SCAFFOLD_OFFLINE_BUNDLE }}")
    assert environment["KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256"] == (
        "${{ vars.KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256 }}"
    )
    assert "scripts/verify-offline-bundle.sh" in verification
    assert (
        "PYTHON_WHEELHOUSE_CONTEXT=$KT_SCAFFOLD_OFFLINE_BUNDLE/wheelhouse/python-fastapi"
    ) in verification
    assert "NPM_CACHE_CONTEXT=$KT_SCAFFOLD_OFFLINE_BUNDLE/npm-cache" in verification
    assert "PRISMA_ENGINES_CONTEXT=" not in verification
    assert 'docker load --input "$KT_SCAFFOLD_OFFLINE_BUNDLE/runtime-images.tar"' in verification
    assert text.index("Verify and wire admitted offline inputs") < text.index("--build")
    assert "docker pull" not in text
    assert "curl " not in text
    assert "wget " not in text


def test_bundle_verifier_refuses_missing_tampered_and_unadmitted_inputs(tmp_path: Path) -> None:
    missing = _run_verifier(None)
    assert missing.returncode == 2
    assert "KT_SCAFFOLD_OFFLINE_BUNDLE is required" in missing.stderr

    bundle = tmp_path / "bundle"
    admitted_digest = _seal_bundle(bundle)
    accepted = _run_verifier(bundle, admitted_digest)
    assert accepted.returncode == 0, accepted.stderr
    assert f"offline bundle verified: {bundle}" in accepted.stdout

    (bundle / "runtime-images.tar").write_text("tampered\n", encoding="utf-8")
    tampered = _run_verifier(bundle, admitted_digest)
    assert tampered.returncode == 2
    assert "checksum verification failed" in tampered.stderr

    _seal_bundle(bundle)
    manifest = bundle / "SHA256SUMS"
    without_runtime = "".join(
        line
        for line in manifest.read_text(encoding="utf-8").splitlines(keepends=True)
        if not line.endswith("  ./runtime-images.tar\n")
    )
    manifest.write_text(without_runtime, encoding="utf-8")
    unsealed_runtime = _run_verifier(bundle, hashlib.sha256(manifest.read_bytes()).hexdigest())
    assert unsealed_runtime.returncode == 2
    assert "unsealed or missing files" in unsealed_runtime.stderr

    _seal_bundle(bundle)
    manifest.write_text(manifest.read_text(encoding="utf-8") + "# mutation\n", encoding="utf-8")
    changed_manifest = _run_verifier(bundle, admitted_digest)
    assert changed_manifest.returncode == 2
    assert "manifest does not match the bank admission digest" in changed_manifest.stderr


def test_bundle_verifier_rejects_unsealed_files_and_symbolic_links(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    admitted_digest = _seal_bundle(bundle)
    (bundle / "wheelhouse/generator/injected.whl").write_text("unsealed\n", encoding="utf-8")

    unsealed = _run_verifier(bundle, admitted_digest)

    assert unsealed.returncode == 2
    assert "unsealed or missing files" in unsealed.stderr
    (bundle / "wheelhouse/generator/injected.whl").unlink()
    (bundle / "npm-cache/escape").symlink_to(tmp_path / "outside")

    linked = _run_verifier(bundle, admitted_digest)

    assert linked.returncode == 2
    assert "must not contain symbolic links" in linked.stderr


@pytest.mark.parametrize("name", WORKFLOW_NAMES)
def test_workflow_bootstrap_exports_absolute_compose_contexts_and_loads_images(
    tmp_path: Path,
    name: str,
) -> None:
    _, parsed = _workflow(name)
    verification = _verification_step(parsed)
    project = tmp_path / "generated"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    verifier = scripts / "verify-offline-bundle.sh"
    shutil.copyfile(VERIFY_SCRIPT, verifier)
    verifier.chmod(0o755)

    bundle = tmp_path / "admitted-bundle"
    admitted_digest = _seal_bundle(bundle)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$*" > "$DOCKER_LOG"\n',
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)
    github_environment = tmp_path / "github.env"
    environment = os.environ.copy()
    environment.update(
        {
            "DEPENDENCY_MODE": str(parsed["env"]["DEPENDENCY_MODE"]),
            "DOCKER_LOG": str(docker_log),
            "GITHUB_ENV": str(github_environment),
            "KT_SCAFFOLD_OFFLINE_BUNDLE": str(bundle),
            "KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256": admitted_digest,
            "PATH": f"{fake_bin}{os.pathsep}{environment['PATH']}",
        }
    )

    completed = subprocess.run(
        ["bash", "-c", f"set -euo pipefail\n{verification}"],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    exported = dict(
        line.split("=", maxsplit=1)
        for line in github_environment.read_text(encoding="utf-8").splitlines()
    )
    assert environment["DEPENDENCY_MODE"] == "offline"
    assert exported == {
        "NPM_CACHE_CONTEXT": str(bundle / "npm-cache"),
        "PYTHON_WHEELHOUSE_CONTEXT": str(bundle / "wheelhouse/python-fastapi"),
    }
    assert all(Path(path).is_absolute() for path in exported.values())
    assert docker_log.read_text(encoding="utf-8").strip() == (
        f"load --input {bundle / 'runtime-images.tar'}"
    )
