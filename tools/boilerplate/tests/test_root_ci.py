"""Contracts for the generator repository's egress-free CI layer."""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from kt_scaffold.agent_platform import PRODUCTION_ASSET_RELATIVE_PATHS

CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_NAMES = ("package-test.yml", "scaffold-matrix.yml")
REQUIRED_AGENT_PLATFORM_MODULES = (
    "kt_scaffold/agent_platform/__init__.py",
    "kt_scaffold/agent_platform/activation.py",
    "kt_scaffold/agent_platform/adapters/__init__.py",
    "kt_scaffold/agent_platform/adapters/base.py",
    "kt_scaffold/agent_platform/adapters/claude_code.py",
    "kt_scaffold/agent_platform/adapters/codex.py",
    "kt_scaffold/agent_platform/adapters/cursor.py",
    "kt_scaffold/agent_platform/adapters/vscode_copilot.py",
    "kt_scaffold/agent_platform/admission.py",
    "kt_scaffold/agent_platform/aggregation.py",
    "kt_scaffold/agent_platform/assets.py",
    "kt_scaffold/agent_platform/compiler.py",
    "kt_scaffold/agent_platform/contracts.py",
    "kt_scaffold/agent_platform/manifest.py",
    "kt_scaffold/agent_platform/models.py",
    "kt_scaffold/agent_platform/projection_store.py",
    "kt_scaffold/agent_platform/registry.py",
)


def workflow_text(name: str) -> str:
    return (REPOSITORY_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", WORKFLOW_NAMES)
def test_workflows_are_valid_offline_self_hosted_contracts(
    name: str,
) -> None:
    text = workflow_text(name)
    parsed = yaml.safe_load(text)

    assert isinstance(parsed, dict)
    assert {"pull_request", "push", "workflow_dispatch"} <= set(parsed["on"])
    assert parsed["on"]["push"] == {"branches": ["staging", "main"]}
    assert parsed["permissions"] == {"contents": "read"}
    assert parsed["env"]["PIP_NO_INDEX"] == "1"
    assert "vars.KT_SCAFFOLD_CI_BUNDLE" in parsed["env"]["KT_SCAFFOLD_CI_BUNDLE"]

    action_uses = re.findall(r"^\s*uses:\s*([^\s]+)\s*$", text, flags=re.MULTILINE)
    assert action_uses
    assert action_uses == [f"actions/checkout@{CHECKOUT_SHA}"] * len(action_uses)
    for job in parsed["jobs"].values():
        labels = set(job["runs-on"])
        assert {"self-hosted", "linux", "bank-offline"} <= labels
        assert "pull_request.head.repo.full_name == github.repository" in job["if"]

    assert "curl " not in text
    assert "wget " not in text
    assert "pip install" in text
    assert "--no-index" in text
    assert "sha256sum --check SHA256SUMS" in text


def test_dependabot_version_updates_follow_maturity_and_grouping_policy() -> None:
    path = REPOSITORY_ROOT / ".github" / "dependabot.yml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert len(config["updates"]) == 5
    for update in config["updates"]:
        assert update["cooldown"] == {"default-days": 30}
        assert len(update["groups"]) == 1
        group = next(iter(update["groups"].values()))
        assert group == {
            "applies-to": "version-updates",
            "patterns": ["*"],
            "update-types": ["minor", "patch"],
        }


def test_package_workflow_covers_release_evidence() -> None:
    text = workflow_text("package-test.yml")

    for command in (
        'bin/ruff" check .',
        'bin/ruff" format --check src tests scripts/ci',
        'bin/mypy"',
        'bin/pytest" -q',
        "--cov=kt_scaffold",
        "--cov-fail-under=85",
        "-m build",
        "--no-isolation",
        "scripts/ci/assert_wheel.py",
        "smoke-project",
        "scripts/security-gate.sh",
        "dependency-admission.json",
    ):
        assert command in text

    lock = (REPOSITORY_ROOT / "packaging" / "requirements.lock").read_text(encoding="utf-8")
    assert "setuptools==83.0.0" in lock
    assert "wheel==0.47.0" in lock


def test_scaffold_workflow_covers_fixed_profile_and_live_drift() -> None:
    text = workflow_text("scaffold-matrix.yml")

    assert "python-fastapi" in text
    assert "node-nestjs" not in text
    assert "prisma" not in text.lower()
    for evidence in (
        "diff -qr",
        "render-clients.sh --check",
        "render-charts.sh --self-test",
        "scaffold-static-gate.sh",
        "DEPENDENCY_MODE=offline",
        "docker load --input",
        "scripts/db.sh apply",
        "scripts/create-super-admin.sh",
        "RUN_POSTGRES_INTEGRATION=1",
        "npm ci --offline --ignore-scripts --no-audit --no-fund",
        'PLAYWRIGHT_BROWSERS_PATH="$KT_SCAFFOLD_CI_BUNDLE/playwright"',
        "scripts/quality-gate.sh all --include-browser",
        "down --volumes --remove-orphans",
    ):
        assert evidence in text

    static_gate = REPOSITORY_ROOT / "scripts" / "ci" / "scaffold-static-gate.sh"
    assert static_gate.stat().st_mode & 0o100
    subprocess.run(["bash", "-n", str(static_gate)], check=True)


def test_wheel_inspector_accepts_complete_archive_and_rejects_plugin_residue(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "kt_scaffold-0.3.0-py3-none-any.whl"
    required = (
        "kt_scaffold/__init__.py",
        *REQUIRED_AGENT_PLATFORM_MODULES,
        "kt_scaffold/cli.py",
        "kt_scaffold/local_creation.py",
        "kt_scaffold/mcp_surfaces.py",
        "kt_scaffold/py.typed",
        "kt_scaffold/server.py",
        "kt_scaffold/governance/local-reconciliation.md",
        "kt_scaffold/templates/common/README.md",
        "kt_scaffold/templates/common/.github/workflows/backend-test.yml",
        "kt_scaffold/templates/common/.github/dependabot.yml",
        "kt_scaffold/templates/common/.gitleaks.toml",
        "kt_scaffold/templates/common/dependency-admission.json",
        "kt_scaffold/templates/common/scripts/check-dependency-admission.py",
        "kt_scaffold/templates/common/scripts/compile-dependency-locks.sh",
        "kt_scaffold/templates/common/scripts/security-gate.sh",
        "kt_scaffold/templates/common/technology-profile.yml",
        "kt_scaffold/templates/python-fastapi/schema/profile.yml",
    )

    def write_wheel(
        *,
        plugin_residue: bool,
        preview_residue: bool = False,
        omitted_package_path: str | None = None,
    ) -> None:
        with zipfile.ZipFile(wheel, "w") as archive:
            for name in required:
                if name == omitted_package_path:
                    continue
                archive.writestr(name, "fixture\n")
            for rule in (REPOSITORY_ROOT / "rules").iterdir():
                if rule.is_file() and rule.suffix in {".md", ".json"}:
                    archive.writestr(
                        f"kt_scaffold-0.3.0.data/data/share/kt-scaffold/rules/{rule.name}",
                        rule.read_bytes(),
                    )
            for relative in PRODUCTION_ASSET_RELATIVE_PATHS:
                archive.writestr(
                    f"kt_scaffold-0.3.0.data/data/share/kt-scaffold/agent-platform/{relative}",
                    (REPOSITORY_ROOT / "agent-platform" / relative).read_bytes(),
                )
            archive.writestr(
                "kt_scaffold-0.3.0.dist-info/entry_points.txt",
                "[console_scripts]\nkt-scaffold = kt_scaffold.cli:main\n",
            )
            if plugin_residue:
                archive.writestr("kt_scaffold/.codex-plugin/plugin.json", "{}\n")
            if preview_residue:
                archive.writestr(
                    "kt_scaffold-0.3.0.data/data/share/kt-scaffold/agent-platform/"
                    "examples/client-projections/manifest.yml",
                    "fixture\n",
                )

    inspector = REPOSITORY_ROOT / "scripts" / "ci" / "assert_wheel.py"
    write_wheel(plugin_residue=False)
    accepted = subprocess.run(
        [sys.executable, str(inspector), str(wheel)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert accepted.returncode == 0, accepted.stderr

    write_wheel(plugin_residue=True)
    rejected = subprocess.run(
        [sys.executable, str(inspector), str(wheel)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "plugin residue" in rejected.stderr

    write_wheel(plugin_residue=False, preview_residue=True)
    rejected_preview = subprocess.run(
        [sys.executable, str(inspector), str(wheel)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected_preview.returncode != 0
    assert "Agent Platform asset mismatch" in rejected_preview.stderr

    for omitted in REQUIRED_AGENT_PLATFORM_MODULES:
        write_wheel(plugin_residue=False, omitted_package_path=omitted)
        rejected_module = subprocess.run(
            [sys.executable, str(inspector), str(wheel)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert rejected_module.returncode != 0
        assert "wheel is missing required package paths" in rejected_module.stderr
        assert omitted in rejected_module.stderr


def test_python_package_discovery_excludes_namespace_residue() -> None:
    pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.setuptools.packages.find]" in pyproject
    assert "namespaces = false" in pyproject
