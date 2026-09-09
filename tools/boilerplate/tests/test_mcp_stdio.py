"""Protocol conformance for the workspace-independent MCP stdio surface."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_contract import assert_local_discovery_contract

from kt_scaffold.bundle import observed_tree_digest


def test_stdio_creates_the_bound_workspace_without_download_or_shell(tmp_path: Path) -> None:
    async def exercise_server() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "kt_scaffold", "mcp", "--workspace-root", str(tmp_path)],
            cwd=tmp_path,
        )
        async with (
            stdio_client(parameters) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            initialized = await session.initialize()
            assert initialized.protocol_version
            assert initialized.server_info.version == "0.3.0"
            await assert_local_discovery_contract(session)
            arguments = {
                "project_intent": "Validate a governed vendor-neutral VS Code coding lab.",
                "primary_domain": "developer-experience",
                "product_name": "AI Lab VS Code Demo",
                "product_slug": "ai-lab-vscode-demo",
                "tenant_header": "x-tenant-id",
                "locales": ["en", "tr"],
                "observability": True,
                "agent_clients": ["github-copilot-vscode"],
            }
            created = await session.call_tool("project_create", arguments=arguments)
            assert not created.is_error
            receipt = created.structured_content["receipt"]
            assert receipt["provenance"] == "local-mcp-observed"
            assert receipt["status"] == "created"
            assert receipt["file_count"] > 300
            assert receipt["entry_count"] >= receipt["file_count"]
            assert receipt["observed_tree_digest"] == observed_tree_digest(tmp_path)
            repeated = await session.call_tool("proje_olustur", arguments=arguments)
            assert not repeated.is_error
            repeated_receipt = repeated.structured_content["receipt"]
            assert repeated_receipt["status"] == "unchanged"
            assert repeated_receipt["observed_tree_digest"] == receipt["observed_tree_digest"]

    asyncio.run(exercise_server())
    answers = (tmp_path / ".kt-scaffold/answers.yml").read_text(encoding="utf-8")
    assert "github-copilot-vscode" in answers
    projection_root = tmp_path / ".kt-scaffold/agent-projections"
    assert len(list(projection_root.glob(".github/agents/*.agent.md"))) == 4
    assert not list(projection_root.glob(".codex/agents/*.toml"))
