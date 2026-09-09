"""Fail when the release wheel omits governed assets or carries build residue."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path, PurePosixPath

REQUIRED_PACKAGE_PATHS = {
    "kt_scaffold/__init__.py",
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
    "kt_scaffold/cli.py",
    "kt_scaffold/local_creation.py",
    "kt_scaffold/mcp_surfaces.py",
    "kt_scaffold/py.typed",
    "kt_scaffold/server.py",
    "kt_scaffold/governance/local-reconciliation.md",
    "kt_scaffold/templates/common/README.md",
    "kt_scaffold/templates/common/.github/dependabot.yml",
    "kt_scaffold/templates/common/.github/workflows/backend-test.yml",
    "kt_scaffold/templates/common/.gitleaks.toml",
    "kt_scaffold/templates/common/dependency-admission.json",
    "kt_scaffold/templates/common/scripts/check-dependency-admission.py",
    "kt_scaffold/templates/common/scripts/compile-dependency-locks.sh",
    "kt_scaffold/templates/common/scripts/security-gate.sh",
    "kt_scaffold/templates/common/technology-profile.yml",
    "kt_scaffold/templates/python-fastapi/schema/profile.yml",
}
FORBIDDEN_PARTS = {
    ".claude-plugin",
    ".codex-plugin",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
    "playwright-report",
    "test-results",
}
FORBIDDEN_NAMES = {
    ".coverage",
    ".DS_Store",
    "CACHEDIR.TAG",
    "coverage.xml",
    "marketplace.json",
    "plugin.json",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def expected_agent_platform_assets(repository: Path) -> dict[str, bytes]:
    sys.path.insert(0, str(repository / "src"))
    try:
        from kt_scaffold.agent_platform import PRODUCTION_ASSET_RELATIVE_PATHS
    finally:
        sys.path.pop(0)
    return {
        relative: (repository / "agent-platform" / relative).read_bytes()
        for relative in PRODUCTION_ASSET_RELATIVE_PATHS
    }


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: assert_wheel.py <kt-scaffold.whl>")

    wheel = Path(sys.argv[1]).resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        fail(f"wheel does not exist: {wheel}")

    repository = Path(__file__).resolve().parents[2]
    expected_rules = {
        path.name
        for path in (repository / "rules").iterdir()
        if path.is_file() and path.suffix in {".md", ".json"}
    }
    expected_agent_platform = expected_agent_platform_assets(repository)

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = sorted(REQUIRED_PACKAGE_PATHS - names)
        if missing:
            fail(f"wheel is missing required package paths: {', '.join(missing)}")

        packaged_rules = {
            PurePosixPath(name).name
            for name in names
            if "/share/kt-scaffold/rules/" in name and not name.endswith("/")
        }
        if packaged_rules != expected_rules:
            missing_rules = sorted(expected_rules - packaged_rules)
            unexpected_rules = sorted(packaged_rules - expected_rules)
            fail(
                "wheel rule corpus mismatch: "
                f"missing={missing_rules or 'none'}, unexpected={unexpected_rules or 'none'}"
            )

        asset_marker = "/share/kt-scaffold/agent-platform/"
        packaged_agent_platform: dict[str, list[str]] = {}
        for name in names:
            if asset_marker not in name or name.endswith("/"):
                continue
            relative = name.split(asset_marker, maxsplit=1)[1]
            packaged_agent_platform.setdefault(relative, []).append(name)
        expected_asset_names = set(expected_agent_platform)
        packaged_asset_names = set(packaged_agent_platform)
        if packaged_asset_names != expected_asset_names:
            missing_assets = sorted(expected_asset_names - packaged_asset_names)
            unexpected_assets = sorted(packaged_asset_names - expected_asset_names)
            fail(
                "wheel Agent Platform asset mismatch: "
                f"missing={missing_assets or 'none'}, unexpected={unexpected_assets or 'none'}"
            )
        duplicates = sorted(
            relative for relative, paths in packaged_agent_platform.items() if len(paths) != 1
        )
        if duplicates:
            fail(f"wheel contains duplicate Agent Platform assets: {', '.join(duplicates)}")
        changed_assets = sorted(
            relative
            for relative, expected in expected_agent_platform.items()
            if archive.read(packaged_agent_platform[relative][0]) != expected
        )
        if changed_assets:
            fail(
                "wheel Agent Platform assets differ from canonical source: "
                f"{', '.join(changed_assets)}"
            )

        forbidden: list[str] = []
        for name in sorted(names):
            path = PurePosixPath(name)
            if FORBIDDEN_PARTS.intersection(path.parts) or name.endswith((".pyc", ".pyo")):
                forbidden.append(name)
            if path.name in FORBIDDEN_NAMES:
                forbidden.append(name)
        if forbidden:
            fail(f"wheel contains forbidden build/plugin residue: {', '.join(forbidden)}")

        entry_points = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        if len(entry_points) != 1:
            fail(f"expected one entry_points.txt, found {len(entry_points)}")
        entry_point_text = archive.read(entry_points[0]).decode("utf-8")
        if "kt-scaffold = kt_scaffold.cli:main" not in entry_point_text:
            fail("wheel does not expose the kt-scaffold console entry point")

    print(
        f"wheel content verified: {wheel.name} "
        f"({len(names)} entries, {len(expected_rules)} corpus files, "
        f"{len(expected_agent_platform)} Agent Platform assets)"
    )


if __name__ == "__main__":
    main()
