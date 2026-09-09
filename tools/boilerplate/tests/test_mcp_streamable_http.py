"""Protocol conformance for loopback Streamable HTTP knowledge tools."""

from __future__ import annotations

import asyncio
import http.client
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp_contract import assert_governance_mcp_contract

from kt_scaffold.cli import main
from kt_scaffold.server import run


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


def test_http_and_stdio_share_the_same_stateless_knowledge_surface(tmp_path: Path) -> None:
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
                ClientSession(streams[0], streams[1]) as session,
            ):
                initialized = await session.initialize()
                assert initialized.server_info.version == "0.3.0"
                await assert_governance_mcp_contract(session)

        asyncio.run(exercise())
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            "/governance",
            body=b"x" * (1024 * 1024 + 1),
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
        oversized = connection.getresponse()
        assert oversized.status == 413
        assert oversized.read() == b"Request body too large"
        connection.close()
        assert list(tmp_path.iterdir()) == []
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_http_application_refuses_direct_network_exposure() -> None:
    with pytest.raises(ValueError, match="binds loopback only"):
        run(transport="streamable-http", host="0.0.0.0")  # noqa: S104
    with pytest.raises(ValueError, match="port must be"):
        run(transport="streamable-http", port=0)
    with pytest.raises(ValueError, match="absolute safe URL path"):
        run(transport="streamable-http", path="relative")


def test_transport_dispatch_and_cli_error_paths(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[str] = []

    def fake_mcp_run(_server: object, *, transport: str, **_kwargs: object) -> None:
        calls.append(transport)

    monkeypatch.setattr("kt_scaffold.mcp_surfaces.MCPServer.run", fake_mcp_run)
    run(transport="stdio")
    run(transport="streamable-http", port=8123, path="/governance")
    assert calls == ["stdio", "streamable-http"]

    with pytest.raises(ValueError, match="workspace-root"):
        run(transport="streamable-http", workspace_root="example")

    def rejected_run(**_kwargs: object) -> None:
        raise ValueError("rejected transport")

    monkeypatch.setattr("kt_scaffold.server.run", rejected_run)
    assert main(["mcp", "--transport", "stdio"]) == 2
    assert "rejected transport" in capsys.readouterr().err
