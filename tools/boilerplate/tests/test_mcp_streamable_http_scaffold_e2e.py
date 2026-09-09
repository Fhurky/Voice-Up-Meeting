"""Real-boundary HTTP governance to trusted-local stdio creation workflow."""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from kt_scaffold.bundle import observed_tree_digest

ARGUMENTS = {
    "project_intent": "Validate a governed vendor-neutral VS Code coding lab.",
    "primary_domain": "developer-experience",
    "product_name": "AI Lab VS Code Demo",
    "product_slug": "ai-lab-vscode-demo",
    "tenant_header": "x-tenant-id",
    "locales": ["en", "tr"],
    "observability": True,
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


def _wait_for_listener(process: subprocess.Popen[str], port: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(f"HTTP MCP exited early:\n{stdout}\n{stderr}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise AssertionError("HTTP MCP did not start listening")


def test_http_governance_and_local_stdio_creation_are_explicitly_separate(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "kt_scaffold",
            "mcp",
            "--transport",
            "streamable-http",
            "--port",
            str(port),
            "--path",
            "/governance",
        ],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_listener(process, port)

        async def exercise() -> None:
            async with (
                streamable_http_client(f"http://127.0.0.1:{port}/governance") as streams,
                ClientSession(streams[0], streams[1]) as remote,
            ):
                await remote.initialize()
                remote_tools = {tool.name for tool in (await remote.list_tools()).tools}
                assert "project_create" not in remote_tools
                assert "project_scaffold" not in remote_tools
                assert (await remote.list_prompts()).prompts == []
                blueprint_call = await remote.call_tool("project_blueprint", arguments=ARGUMENTS)
                assert not blueprint_call.is_error
                remote_blueprint = cast(dict[str, Any], blueprint_call.structured_content)

            parameters = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "kt_scaffold",
                    "mcp",
                    "--workspace-root",
                    str(workspace),
                ],
                cwd=tmp_path,
            )
            async with (
                stdio_client(parameters) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as local,
            ):
                await local.initialize()
                local_tools = {tool.name for tool in (await local.list_tools()).tools}
                assert "project_create" in local_tools
                created_call = await local.call_tool(
                    "project_create",
                    arguments={
                        **ARGUMENTS,
                        "agent_clients": ["github-copilot-vscode"],
                    },
                )
                assert not created_call.is_error
                created = cast(dict[str, Any], created_call.structured_content)

            receipt = created["receipt"]
            assert receipt["provenance"] == "local-mcp-observed"
            assert receipt["status"] == "created"
            assert receipt["observed_tree_digest"] == observed_tree_digest(workspace)
            project_manifest = json.loads(
                (workspace / ".kt-scaffold/project-manifest.json").read_text(encoding="utf-8")
            )
            assert project_manifest == remote_blueprint["project_manifest"]

        asyncio.run(exercise())
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
