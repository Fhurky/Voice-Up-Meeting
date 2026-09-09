"""Production inventory and resolver contracts for canonical Agent Platform assets."""

from __future__ import annotations

from pathlib import Path

import pytest

from kt_scaffold.agent_platform import (
    PRODUCTION_ASSET_RELATIVE_PATHS,
    AgentPlatformAssetsError,
    agent_platform_asset_path,
    agent_platform_assets_dir,
    production_asset_paths,
)


def test_development_resolver_returns_the_exact_production_inventory() -> None:
    root = agent_platform_assets_dir()
    assets = production_asset_paths()

    assert root.name == "agent-platform"
    assert tuple(assets) == PRODUCTION_ASSET_RELATIVE_PATHS
    assert all(path.is_file() and path.is_relative_to(root) for path in assets.values())
    assert not any(relative.startswith("examples/") for relative in assets)
    assert "client-projection-fixture.schema.json" not in assets


def test_explicit_asset_root_is_validated_without_falling_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KT_SCAFFOLD_AGENT_PLATFORM_DIR", str(tmp_path))

    with pytest.raises(AgentPlatformAssetsError, match="required Agent Platform asset is missing"):
        agent_platform_assets_dir()


@pytest.mark.parametrize(
    "relative",
    (
        "../agent-contract.schema.json",
        "examples/client-projections/manifest.yml",
        "client-projection-fixture.schema.json",
    ),
)
def test_single_asset_resolver_rejects_non_production_paths(relative: str) -> None:
    with pytest.raises(AgentPlatformAssetsError, match="not in production inventory"):
        agent_platform_asset_path(relative)
