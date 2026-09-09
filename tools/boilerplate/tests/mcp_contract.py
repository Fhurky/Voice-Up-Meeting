"""Reusable assertions for separated local and governance MCP surfaces."""

from __future__ import annotations

from typing import Any, cast

from kt_scaffold.mcp_surfaces import (
    GOVERNANCE_TOOL_ALIASES,
    LOCAL_PROMPT_ALIASES,
    LOCAL_TOOL_ALIASES,
)

FORBIDDEN_CONTEXT_KEYS = (
    "target_dir",
    "workspace",
    "workspace_root",
    "patch_set",
    "execution",
    "command",
    "archive",
    "applicator",
    "env_prefix",
    "api_prefix",
)


def _schema_without_function_title(schema: dict[str, Any]) -> dict[str, Any]:
    comparable = dict(schema)
    comparable.pop("title", None)
    return comparable


async def assert_governance_mcp_contract(session: Any) -> dict[str, Any]:
    prompts = await session.list_prompts()
    assert prompts.prompts == []
    listed = await session.list_tools()
    tools = {tool.name: tool for tool in listed.tools}
    expected = set(GOVERNANCE_TOOL_ALIASES) | set(GOVERNANCE_TOOL_ALIASES.values())
    assert set(tools) == expected
    assert "project_create" not in tools
    assert "project_scaffold" not in tools
    for english_name, turkish_name in GOVERNANCE_TOOL_ALIASES.items():
        english = tools[english_name]
        turkish = tools[turkish_name]
        assert english.input_schema.get("additionalProperties") is False
        assert turkish.input_schema.get("additionalProperties") is False
        assert _schema_without_function_title(
            english.input_schema
        ) == _schema_without_function_title(turkish.input_schema)
        assert english.description != turkish.description

    arguments = {
        "project_intent": "Audit internal payment controls with an LLM harness.",
        "primary_domain": "payments",
    }
    blueprint = await session.call_tool("project_blueprint", arguments=arguments)
    assert not blueprint.is_error
    assert blueprint.structured_content is not None
    metadata = cast(dict[str, Any], blueprint.structured_content)["project_manifest"]
    catalog = await session.call_tool("governance_catalog", arguments={"kind": "guidance"})
    assert not catalog.is_error
    update = await session.call_tool("governance_update_check", arguments={"metadata": metadata})
    assert not update.is_error
    proposal = cast(dict[str, Any], update.structured_content)["proposal"]
    reconciled = await session.call_tool(
        "reconciliation_validate", arguments={"proposal": proposal, "decisions": []}
    )
    assert not reconciled.is_error

    rejected = await session.call_tool(
        "project_blueprint", arguments={**arguments, "workspace_root": "forbidden"}
    )
    assert rejected.is_error
    return cast(dict[str, Any], blueprint.structured_content)


async def assert_local_discovery_contract(session: Any) -> dict[str, Any]:
    prompts = {prompt.name: prompt for prompt in (await session.list_prompts()).prompts}
    expected_prompts = set(LOCAL_PROMPT_ALIASES) | set(LOCAL_PROMPT_ALIASES.values())
    assert set(prompts) == expected_prompts
    rendered = await session.get_prompt(
        "project_start", arguments={"project_goal": "Build a governed VS Code lab."}
    )
    body = rendered.messages[0].content.text
    assert "call only project_create" in body
    assert "preinstalled generator" in body
    assert '["github-copilot-vscode"]' in body
    for forbidden in ("Python 3.13", "applicator.py", "curl", "--target-dir", "archive"):
        assert forbidden not in body

    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
    expected = set(LOCAL_TOOL_ALIASES) | set(LOCAL_TOOL_ALIASES.values())
    assert set(tools) == expected
    create = tools["project_create"]
    assert create.input_schema.get("additionalProperties") is False
    assert create.annotations is not None
    assert create.annotations.read_only_hint is False
    assert create.annotations.destructive_hint is False
    assert create.annotations.idempotent_hint is True
    assert create.annotations.open_world_hint is False
    for forbidden in FORBIDDEN_CONTEXT_KEYS:
        assert forbidden not in create.input_schema.get("properties", {})
    return tools
