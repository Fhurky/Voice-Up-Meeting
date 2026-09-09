"""MCP transport runner for separated local and remote authority surfaces."""

from __future__ import annotations

from typing import Literal

from kt_scaffold.mcp_surfaces import (
    LOCAL_PROMPT_ALIASES,
    LOCAL_TOOL_ALIASES,
    build_governance_server,
    build_local_server,
)

RuntimeTransport = Literal["stdio", "streamable-http"]
MCP_RECOMMENDED_REGISTRATION_NAME = "kt"
MCP_TOOL_ALIASES = LOCAL_TOOL_ALIASES
MCP_PROMPT_ALIASES = LOCAL_PROMPT_ALIASES


def run(
    *,
    transport: RuntimeTransport = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp",
    workspace_root: str | None = None,
) -> None:
    """Run a workspace-blind HTTP plane or explicitly bound trusted local stdio plane."""

    if transport == "streamable-http":
        if workspace_root is not None:
            raise ValueError(
                "workspace-root is supported only by the trusted local stdio transport"
            )
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError(
                "the MCP application binds loopback only; expose it through the bank OAuth/TLS "
                "gateway sidecar"
            )
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if not path.startswith("/") or ".." in path.split("/"):
            raise ValueError("Streamable HTTP path must be an absolute safe URL path")
        build_governance_server().run(
            transport="streamable-http",
            host=host,
            port=port,
            streamable_http_path=path,
            json_response=True,
            stateless_http=True,
            max_request_body_size=1024 * 1024,
        )
        return
    selected = (
        build_local_server(workspace_root)
        if workspace_root is not None
        else build_governance_server()
    )
    selected.run(transport="stdio")


__all__ = [
    "MCP_PROMPT_ALIASES",
    "MCP_RECOMMENDED_REGISTRATION_NAME",
    "MCP_TOOL_ALIASES",
    "run",
]
