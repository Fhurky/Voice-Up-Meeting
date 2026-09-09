"""Executable contracts for dependency admission and offline security propagation."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

import yaml

from kt_scaffold.models import Answers
from kt_scaffold.project import project_init

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPOSITORY_ROOT / "src/kt_scaffold/templates/common/scripts/check-dependency-admission.py"


def run_checker(root: Path, ledger: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(CHECKER), "--root", str(root)]
    if ledger is not None:
        command.extend(["--ledger", str(ledger)])
    return subprocess.run(command, check=False, capture_output=True, text=True)


def test_generator_dependency_admission_is_current_and_fails_on_authority_drift() -> None:
    accepted = run_checker(REPOSITORY_ROOT, REPOSITORY_ROOT / "dependency-admission.json")
    assert accepted.returncode == 0, accepted.stderr
    assert "86 coordinates" in accepted.stdout

    printed = subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(REPOSITORY_ROOT), "--print-inventory"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert printed.returncode == 0, printed.stderr
    inventory = json.loads(printed.stdout)["inventory"]
    assert (
        sum(
            item.startswith("apk:packaging/locks/alpine-runtime-packages.lock:")
            for item in inventory
        )
        == 2
    )

    package = REPOSITORY_ROOT / "src/kt_scaffold/templates/common/app/frontend/package.json"
    original = package.read_text(encoding="utf-8")
    try:
        package.write_text(original.replace('"vite": "8.2.0"', '"vite": "8.2.1"'), encoding="utf-8")
        rejected = run_checker(REPOSITORY_ROOT, REPOSITORY_ROOT / "dependency-admission.json")
    finally:
        package.write_text(original, encoding="utf-8")
    assert rejected.returncode != 0
    assert "authority inventory drifted" in rejected.stderr


def test_fresh_scaffold_carries_enforced_admission_and_security_surface(
    tmp_path: Path, answers_factory: Callable[..., Answers]
) -> None:
    target = tmp_path / "project"
    answers = answers_factory()
    project_init(target, answers)

    for relative in (
        "dependency-admission.json",
        ".gitleaks.toml",
        ".pre-commit-config.yaml",
        ".github/dependabot.yml",
        "scripts/check-dependency-admission.py",
        "scripts/compile-dependency-locks.sh",
        "scripts/security-gate.sh",
        "app/frontend/.npmrc",
        "e2e/.npmrc",
    ):
        assert (target / relative).is_file(), relative

    accepted = subprocess.run(
        [sys.executable, "scripts/check-dependency-admission.py"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    assert accepted.returncode == 0, accepted.stderr
    assert "72 coordinates" in accepted.stdout

    printed = subprocess.run(
        [sys.executable, "scripts/check-dependency-admission.py", "--print-inventory"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    assert printed.returncode == 0, printed.stderr
    inventory = json.loads(printed.stdout)["inventory"]
    assert not any(item.startswith("oci:-") for item in inventory)

    workflow = (target / ".github/workflows/security-scan.yml").read_text(encoding="utf-8")
    assert "scripts/security-gate.sh" in workflow
    security_gate = (target / "scripts/security-gate.sh").read_text(encoding="utf-8")
    for command in ("gitleaks dir", "semgrep scan", "trivy fs", "sha256sum --check"):
        assert command in security_gate
    assert "--include-dev-deps --scanners vuln,misconfig,secret" in security_gate
    assert "trivy config --skip-check-update" in security_gate
    assert '--helm-values "$migration_values"' in security_gate

    dependabot = (target / ".github/dependabot.yml").read_text(encoding="utf-8")
    dependabot_config = yaml.safe_load(dependabot)
    assert len(dependabot_config["updates"]) == 4
    for update in dependabot_config["updates"]:
        assert update["cooldown"] == {"default-days": 30}
        assert len(update["groups"]) == 1
        group = next(iter(update["groups"].values()))
        assert group == {
            "applies-to": "version-updates",
            "patterns": ["*"],
            "update-types": ["minor", "patch"],
        }
    for npmrc_path in ("app/frontend/.npmrc", "e2e/.npmrc"):
        npmrc = (target / npmrc_path).read_text(encoding="utf-8")
        assert "min-release-age=7" in npmrc

    intl = (target / "app/frontend/src/contexts/IntlContext.tsx").read_text(encoding="utf-8")
    assert "current[part]" not in intl
    assert "Object.entries(current)" in intl

    nginx = (target / "app/infra/nginx/nginx.local.conf").read_text(encoding="utf-8")
    assert "proxy_set_header Upgrade $http_upgrade" not in nginx
    assert "proxy_set_header Upgrade $kt_websocket_upgrade" in nginx
    assert "arbitrary h2c is dropped" in nginx


def test_dependency_admission_selects_reviewed_observability_variant(
    tmp_path: Path, answers_factory: Callable[..., Answers]
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory(observability=False))

    accepted = subprocess.run(
        [sys.executable, "scripts/check-dependency-admission.py"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    assert accepted.returncode == 0, accepted.stderr
    assert "72 coordinates" in accepted.stdout

    answers = target / ".kt-scaffold/answers.yml"
    answers.write_text(
        answers.read_text(encoding="utf-8").replace("observability: false", "observability: true"),
        encoding="utf-8",
    )
    rejected = subprocess.run(
        [sys.executable, "scripts/check-dependency-admission.py"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "observability=true requires" in rejected.stderr


def test_admission_rejects_incomplete_immature_exception(
    tmp_path: Path, answers_factory: Callable[..., Answers]
) -> None:
    target = tmp_path / "project"
    answers = answers_factory()
    project_init(target, answers)
    ledger = target / "dependency-admission.json"
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    payload["exceptions"][1].pop("compatibility_evidence")
    ledger.write_text(json.dumps(payload), encoding="utf-8")

    rejected = subprocess.run(
        [sys.executable, "scripts/check-dependency-admission.py"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "requires compatibility_evidence" in rejected.stderr


def test_image_metadata_and_offline_identity_inventory_agree() -> None:
    image_path = REPOSITORY_ROOT / "src/kt_scaffold/templates/common/app/devops/images.yaml"
    images = yaml.safe_load(image_path.read_text(encoding="utf-8"))["images"]
    expected_sources = {
        "postgres": "postgres:17.10",
        "otelCollector": "otel/opentelemetry-collector-contrib:0.158.0",
        "loki": "grafana/loki:3.7.6",
        "grafana": "grafana/grafana:13.1.2",
    }
    for name, source in expected_sources.items():
        assert images[name]["source"] == source

    lock = (REPOSITORY_ROOT / "packaging/images.lock").read_text(encoding="utf-8")
    for image in images.values():
        assert f"{image['source']}@{image['digest']}" in lock

    env_example = (
        REPOSITORY_ROOT / "src/kt_scaffold/templates/common/app/infra/.env.example"
    ).read_text(encoding="utf-8")
    assert "\nNODE_BASE_IMAGE=" not in f"\n{env_example}"
    assert "FRONTEND_NODE_BASE_IMAGE=node:22.23.2-alpine3.23@sha256:" in env_example


def test_node_and_openapi_tooling_use_enforced_supported_boundaries() -> None:
    frontend = REPOSITORY_ROOT / "src/kt_scaffold/templates/common/app/frontend"
    package = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    assert package["engines"]["node"] == ">=22.13.0 <23"
    assert package["devDependencies"]["typescript"] == "5.9.3"
    assert package["devDependencies"]["typescript7"] == "npm:typescript@7.0.2"
    assert package["overrides"] == {"js-yaml": "4.3.1"}
    assert "engine-strict=true" in (frontend / ".npmrc").read_text(encoding="utf-8")

    workflow = (REPOSITORY_ROOT / ".github/workflows/scaffold-matrix.yml").read_text(
        encoding="utf-8"
    )
    assert "node-22" in workflow
    assert "node-24" not in workflow
    assert "setuptools==83.0.0 wheel==0.47.0" in workflow


def test_security_gate_uses_only_checksum_admitted_scanner_material(
    tmp_path: Path, answers_factory: Callable[..., Answers]
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    scanner = tmp_path / "scanner"
    trivy_cache = scanner / "trivy"
    trivy_cache.mkdir(parents=True)
    ruleset = scanner / "semgrep.yml"
    database = trivy_cache / "db.bin"
    ruleset.write_text("rules: []\n", encoding="utf-8")
    database.write_text("admitted database\n", encoding="utf-8")
    sums = scanner / "SHA256SUMS"

    def digest(path: Path) -> str:
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()

    sums.write_text(
        f"{digest(ruleset)}  semgrep.yml\n{digest(database)}  trivy/db.bin\n",
        encoding="utf-8",
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    for command in ("gitleaks", "semgrep", "trivy"):
        executable = fake_bin / command
        executable.write_text(
            "#!/usr/bin/env sh\n"
            f"printf '%s %s\\n' '{command}' \"$*\" >> '{calls}'\n"
            "case \"${1:-}\" in version|--version) echo 'test-version' ;; esac\n",
            encoding="utf-8",
        )
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "INTERNAL_SCANNER_MATERIAL_DIR": str(scanner),
        "INTERNAL_SCANNER_SHA256SUMS": str(sums),
        "INTERNAL_SCANNER_SHA256SUMS_SHA256": digest(sums),
        "INTERNAL_SCANNER_ADMITTED_ON": date.today().isoformat(),
        "INTERNAL_SCANNER_MAX_AGE_DAYS": "7",
        "INTERNAL_SEMGREP_RULESET": str(ruleset),
        "TRIVY_CACHE_DIR": str(trivy_cache),
    }
    accepted = subprocess.run(
        ["scripts/security-gate.sh"],
        cwd=target,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert accepted.returncode == 0, accepted.stderr
    call_text = calls.read_text(encoding="utf-8")
    assert "gitleaks dir" in call_text
    assert "semgrep scan" in call_text
    assert "trivy fs" in call_text
    assert "--include-dev-deps --scanners vuln,misconfig,secret" in call_text
    assert "trivy config" in call_text

    unsealed = trivy_cache / "unsealed.db"
    unsealed.write_text("not admitted\n", encoding="utf-8")
    rejected = subprocess.run(
        ["scripts/security-gate.sh"],
        cwd=target,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "unsealed or missing files" in rejected.stderr
    unsealed.unlink()

    ruleset.write_text("tampered\n", encoding="utf-8")
    rejected = subprocess.run(
        ["scripts/security-gate.sh"],
        cwd=target,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "FAILED" in rejected.stdout or "FAILED" in rejected.stderr
