"""Resolve the source-owned Agent Platform inputs in development and installed builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path, PurePosixPath

ASSET_DIRECTORY_ENV = "KT_SCAFFOLD_AGENT_PLATFORM_DIR"

# This allowlist is also the release inventory. Schema-test fixtures and machine-specific
# conformance receipts are deliberately not compiler inputs.
PRODUCTION_ASSET_RELATIVE_PATHS = (
    "agent-catalog.schema.json",
    "agent-catalog.yml",
    "agent-contract.schema.json",
    "agent-policy.schema.json",
    "agents/application-security/agent.yml",
    "agents/application-security/instructions.md",
    "agents/application-security/policy.yml",
    "agents/code-review/agent.yml",
    "agents/code-review/instructions.md",
    "agents/code-review/policy.yml",
    "agents/requirements-scope/agent.yml",
    "agents/requirements-scope/instructions.md",
    "agents/requirements-scope/policy.yml",
    "agents/test-automation/agent.yml",
    "agents/test-automation/instructions.md",
    "agents/test-automation/policy.yml",
    "client-capabilities.yml",
    "conformance-snapshot.schema.json",
    "decision-policy.schema.json",
    "orchestration.schema.json",
    "orchestrations/governed-review.yml",
    "policies/aggregation/governed-review.yml",
    "runtime-candidate.schema.json",
    "standards-crosswalk.yml",
)
_PRODUCTION_ASSET_SET = frozenset(PRODUCTION_ASSET_RELATIVE_PATHS)


class AgentPlatformAssetsError(ValueError):
    """The canonical Agent Platform asset set is unavailable or unsafe."""


def _candidate_roots() -> tuple[Path, ...]:
    explicit = os.environ.get(ASSET_DIRECTORY_ENV)
    if explicit:
        return (Path(explicit).expanduser(),)
    return (
        Path(__file__).resolve().parents[3] / "agent-platform",
        Path(sys.prefix) / "share" / "kt-scaffold" / "agent-platform",
    )


def _validated_assets(root: Path) -> dict[str, Path]:
    try:
        resolved_root = root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise AgentPlatformAssetsError(f"Agent Platform asset root does not exist: {root}") from exc
    if not resolved_root.is_dir():
        raise AgentPlatformAssetsError(f"Agent Platform asset root is not a directory: {root}")

    assets: dict[str, Path] = {}
    for relative in PRODUCTION_ASSET_RELATIVE_PATHS:
        relative_path = PurePosixPath(relative)
        candidate = resolved_root.joinpath(*relative_path.parts)
        if candidate.is_symlink():
            raise AgentPlatformAssetsError(
                f"symbolic-link Agent Platform asset rejected: {relative}"
            )
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise AgentPlatformAssetsError(
                f"required Agent Platform asset is missing: {relative}"
            ) from exc
        if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
            raise AgentPlatformAssetsError(f"invalid Agent Platform asset path: {relative}")
        assets[relative] = resolved
    return assets


def agent_platform_assets_dir() -> Path:
    """Return the validated development or installed canonical asset directory."""

    errors: list[str] = []
    for candidate in _candidate_roots():
        try:
            _validated_assets(candidate)
        except AgentPlatformAssetsError as exc:
            errors.append(str(exc))
            continue
        return candidate.resolve(strict=True)
    detail = "; ".join(errors)
    raise AgentPlatformAssetsError(
        "canonical Agent Platform assets not found; set "
        f"{ASSET_DIRECTORY_ENV} or install the governed asset bundle ({detail})"
    )


def production_asset_paths(root: str | Path | None = None) -> dict[str, Path]:
    """Return the exact allowlisted production inventory keyed by POSIX relative path."""

    selected = Path(root).expanduser() if root is not None else agent_platform_assets_dir()
    return _validated_assets(selected)


def agent_platform_asset_path(relative: str, root: str | Path | None = None) -> Path:
    """Resolve one allowlisted production asset without permitting path traversal or examples."""

    normalized = PurePosixPath(relative).as_posix()
    if normalized not in _PRODUCTION_ASSET_SET:
        raise AgentPlatformAssetsError(
            f"Agent Platform asset is not in production inventory: {relative}"
        )
    return production_asset_paths(root)[normalized]
