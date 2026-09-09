"""Canonical Agent Platform asset access for compilers and validators."""

from kt_scaffold.agent_platform.assets import (
    PRODUCTION_ASSET_RELATIVE_PATHS,
    AgentPlatformAssetsError,
    agent_platform_asset_path,
    agent_platform_assets_dir,
    production_asset_paths,
)

__all__ = [
    "PRODUCTION_ASSET_RELATIVE_PATHS",
    "AgentPlatformAssetsError",
    "agent_platform_asset_path",
    "agent_platform_assets_dir",
    "production_asset_paths",
]
