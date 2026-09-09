from __future__ import annotations

import hashlib
import json
import shutil
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from pydantic import ValidationError

from kt_scaffold.agent_platform.compiler import compile_agent_projections
from kt_scaffold.agent_platform.contracts import AgentPlatformContractError
from kt_scaffold.agent_platform.manifest import canonical_json
from kt_scaffold.agent_platform.models import (
    CompilationResult,
    ReasonCode,
    revalidate_compilation_result,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "agent-platform"

EXPECTED_PATHS = {
    *(
        f".codex/agents/{agent}.toml"
        for agent in (
            "application-security",
            "code-review",
            "requirements-scope",
            "test-automation",
        )
    ),
    *(
        f".claude/agents/{agent}.md"
        for agent in (
            "application-security",
            "code-review",
            "requirements-scope",
            "test-automation",
        )
    ),
    *(
        f".github/agents/{agent}.agent.md"
        for agent in (
            "application-security",
            "code-review",
            "requirements-scope",
            "test-automation",
        )
    ),
    *(
        f".cursor/agents/{agent}.md"
        for agent in (
            "application-security",
            "code-review",
            "requirements-scope",
            "test-automation",
        )
    ),
}


def _copy_assets(tmp_path: Path) -> Path:
    destination = tmp_path / "agent-platform"
    shutil.copytree(ASSETS, destination)
    return destination


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _frontmatter(content: str) -> dict[str, Any]:
    header, _ = content[4:].split("\n---\n", 1)
    value = yaml.safe_load(header)
    assert isinstance(value, dict)
    return value


def _first_matrix_mapping(matrix: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], matrix["clients"][0]["mappings"][0])


def _remove_projection_enum(matrix: dict[str, Any]) -> None:
    matrix["policy"]["projection_values"].remove("none")


def _add_invalid_mapping_surface(matrix: dict[str, Any]) -> None:
    _first_matrix_mapping(matrix)["applies_to_surfaces"] = ["unknown-surface"]


def _make_source_date_stale(matrix: dict[str, Any]) -> None:
    next(iter(matrix["sources"].values()))["retrieved_at"] = "2026-08-17"


def _make_client_version_non_exact(matrix: dict[str, Any]) -> None:
    matrix["clients"][0]["adapter"]["client_version_range"] = "==0.147.0-alpha.1"


def _add_unused_source(matrix: dict[str, Any]) -> None:
    matrix["sources"]["unused-source"] = {
        "url": "https://learn.chatgpt.com/docs/unused",
        "retrieved_at": matrix["as_of"],
    }


def _coerce_mapping_boolean(matrix: dict[str, Any]) -> None:
    _first_matrix_mapping(matrix)["volatile"] = "true"


def test_compiler_produces_deterministic_content_addressed_4_by_4_set() -> None:
    first = compile_agent_projections(assets_root=ASSETS)
    second = compile_agent_projections(assets_root=ASSETS)

    assert first.files() == second.files()
    assert first.lock_sha256 == second.lock_sha256
    assert len(first.artifacts) == 16
    assert len(first.files()) == 17
    assert set(first.files()) == {*EXPECTED_PATHS, "PROJECTIONS.lock.json"}
    assert Counter(item.client_id for item in first.artifacts) == {
        "claude-code": 4,
        "codex": 4,
        "cursor": 4,
        "github-copilot-vscode": 4,
    }
    for artifact in first.artifacts:
        assert artifact.sha256 == hashlib.sha256(artifact.content.encode("utf-8")).hexdigest()
        assert artifact.semantic_losses
        assert len(artifact.external_controls) == 6
        assert artifact.generation_status == "implemented"
        assert artifact.runtime_admission == "research"
        assert artifact.runtime_conformance == "not_run"
        assert "==" in artifact.client_version_range

    lock = json.loads(first.lock_content)
    assert first.lock_content == canonical_json(lock)
    assert first.lock_sha256 == hashlib.sha256(first.lock_content.encode()).hexdigest()
    assert lock["generation_status"] == "generated"
    assert lock["activation_status"] == "not_activated"
    assert lock["runtime_admission"] == "research"
    assert lock["runtime_conformance"] == "not_run"
    assert len(lock["artifacts"]) == 16
    assert "created_at" not in lock
    assert "generated_at" not in lock


def test_compilation_result_rejects_artifact_inventory_missing_from_manifest() -> None:
    result = compile_agent_projections(assets_root=ASSETS, client_ids=("codex",))

    with pytest.raises(ValidationError, match="inventory does not match artifacts"):
        CompilationResult(
            artifacts=result.artifacts[:-1],
            manifest=result.manifest,
            lock_content=result.lock_content,
            lock_sha256=result.lock_sha256,
        )


def test_compilation_result_rejects_lock_manifest_substitution() -> None:
    result = compile_agent_projections(assets_root=ASSETS, client_ids=("codex",))
    substituted_manifest = result.manifest.model_copy(update={"compiler_version": "9.9.9"})
    substituted_lock = canonical_json(substituted_manifest.model_dump(mode="json"))

    with pytest.raises(ValidationError, match="does not match the result manifest"):
        CompilationResult(
            artifacts=result.artifacts,
            manifest=result.manifest,
            lock_content=substituted_lock,
            lock_sha256=hashlib.sha256(substituted_lock.encode("utf-8")).hexdigest(),
        )


def test_compilation_result_rejects_artifact_metadata_substitution() -> None:
    result = compile_agent_projections(assets_root=ASSETS, client_ids=("codex",))
    substituted = result.artifacts[0].model_copy(update={"adapter_version": "9.9.9"})

    with pytest.raises(ValidationError, match="inventory does not match artifacts"):
        CompilationResult(
            artifacts=(substituted, *result.artifacts[1:]),
            manifest=result.manifest,
            lock_content=result.lock_content,
            lock_sha256=result.lock_sha256,
        )


def test_compilation_result_rejects_top_level_input_digest_substitution() -> None:
    result = compile_agent_projections(assets_root=ASSETS, client_ids=("codex",))
    manifest_inputs = tuple(
        item.model_copy(update={"sha256": "9" * 64})
        if item.path == "client-capabilities.yml"
        else item
        for item in result.manifest.inputs
    )
    substituted_manifest = result.manifest.model_copy(update={"inputs": manifest_inputs})
    substituted_lock = canonical_json(substituted_manifest.model_dump(mode="json"))

    with pytest.raises(ValidationError, match="do not bind every artifact input"):
        CompilationResult(
            artifacts=result.artifacts,
            manifest=substituted_manifest,
            lock_content=substituted_lock,
            lock_sha256=hashlib.sha256(substituted_lock.encode("utf-8")).hexdigest(),
        )


def test_boundary_revalidation_ignores_shadowed_instance_model_dump() -> None:
    result = compile_agent_projections(assets_root=ASSETS, client_ids=("codex",))
    malicious = result.artifacts[0].model_copy(update={"content": "MALICIOUS\n"})
    tampered = result.model_copy(update={"artifacts": (malicious, *result.artifacts[1:])})
    shadowed = tampered.model_copy(
        update={"model_dump": lambda **_: result.model_dump(mode="python")}
    )

    with pytest.raises(ValueError, match="unexpected runtime fields"):
        revalidate_compilation_result(shadowed)


def test_adapters_emit_only_conservative_documented_agent_fields() -> None:
    result = compile_agent_projections(assets_root=ASSETS)
    by_path = {item.relative_path: item.content for item in result.artifacts}

    codex = tomllib.loads(by_path[".codex/agents/code-review.toml"])
    assert set(codex) == {"name", "description", "sandbox_mode", "developer_instructions"}
    assert codex["name"] == "code_review"
    assert codex["sandbox_mode"] == "read-only"
    assert (
        "Use the local shell only for read-only workspace inspection."
        in codex["developer_instructions"]
    )
    assert "Never execute project code" in codex["developer_instructions"]

    codex_artifact = next(
        item for item in result.artifacts if item.relative_path == ".codex/agents/code-review.toml"
    )
    assert codex_artifact.adapter_version == "1.0.2"
    assert {field.canonical for field in codex_artifact.mapped_fields} >= {
        "requirements.tools[tool:workspace-read]"
    }
    assert {loss.code for loss in codex_artifact.semantic_losses} >= {
        "AP_LOSS_CODEX_WORKSPACE_READ_TOOL_INHERITED"
    }
    assert {item.adapter_version for item in result.artifacts if item.client_id != "codex"} == {
        "1.0.1"
    }

    claude = _frontmatter(by_path[".claude/agents/code-review.md"])
    assert claude == {
        "name": "code-review",
        "description": (
            "Reviews a bounded change for concrete correctness, security, regression, and test "
            "risks."
        ),
        "tools": "Read, Glob, Grep",
        "disallowedTools": "Write, Edit, Bash, Agent",
        "model": "inherit",
        "permissionMode": "plan",
    }

    vscode = _frontmatter(by_path[".github/agents/code-review.agent.md"])
    assert vscode["tools"] == ["read", "search"]
    assert "agents" not in vscode and "model" not in vscode and "hooks" not in vscode

    cursor = _frontmatter(by_path[".cursor/agents/code-review.md"])
    assert cursor["readonly"] is True and cursor["is_background"] is False

    test_projection = _frontmatter(by_path[".github/agents/test-automation.agent.md"])
    assert test_projection["description"].endswith("this projection cannot execute tests.")
    assert "admitted disposable runner" in by_path[".github/agents/test-automation.agent.md"]
    assert all("Projection safety envelope" in content for content in by_path.values())


def test_compilation_is_inert_and_does_not_write_into_asset_tree(tmp_path: Path) -> None:
    assets = _copy_assets(tmp_path)
    before = {
        path.relative_to(assets).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in assets.rglob("*")
        if path.is_file()
    }

    result = compile_agent_projections(assets_root=assets)

    after = {
        path.relative_to(assets).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in assets.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert all(not (assets / path).exists() for path in result.files())


def test_unknown_contract_field_fails_closed_at_schema_boundary(tmp_path: Path) -> None:
    assets = _copy_assets(tmp_path)
    contract_path = assets / "agents" / "code-review" / "agent.yml"
    contract = _load_yaml(contract_path)
    contract["metadata"]["vendor"] = "example"
    _write_yaml(contract_path, contract)

    with pytest.raises(AgentPlatformContractError) as caught:
        compile_agent_projections(assets_root=assets)

    assert caught.value.code == ReasonCode.SCHEMA_VALIDATION_FAILED
    assert "metadata" in caught.value.detail


def test_embedded_endpoint_fails_closed_at_semantic_boundary(tmp_path: Path) -> None:
    assets = _copy_assets(tmp_path)
    contract_path = assets / "agents" / "code-review" / "agent.yml"
    contract = _load_yaml(contract_path)
    contract["metadata"]["description"] = (
        "Review using https://private.example.invalid as an endpoint."
    )
    _write_yaml(contract_path, contract)

    with pytest.raises(AgentPlatformContractError) as caught:
        compile_agent_projections(assets_root=assets)

    assert caught.value.code == ReasonCode.SEMANTIC_VALIDATION_FAILED
    assert "endpoint URL" in caught.value.detail


def test_required_unmapped_matrix_capability_fails_closed(tmp_path: Path) -> None:
    assets = _copy_assets(tmp_path)
    matrix_path = assets / "client-capabilities.yml"
    matrix = _load_yaml(matrix_path)
    codex = next(item for item in matrix["clients"] if item["id"] == "codex")
    custom_agents = next(
        item for item in codex["mappings"] if item["capability"] == "custom-agents"
    )
    custom_agents.update(
        {
            "status": "unmapped",
            "projection": "none",
            "adapter_strategy": "omit",
            "lossiness": "material",
            "limitations": ["No safe projection exists."],
        }
    )
    _write_yaml(matrix_path, matrix)

    with pytest.raises(AgentPlatformContractError) as caught:
        compile_agent_projections(assets_root=assets)

    assert caught.value.code == ReasonCode.REQUIRED_CAPABILITY_UNMAPPED


@pytest.mark.parametrize(
    "mutation",
    [
        _remove_projection_enum,
        _add_invalid_mapping_surface,
        _make_source_date_stale,
        _make_client_version_non_exact,
        _add_unused_source,
        _coerce_mapping_boolean,
    ],
)
def test_matrix_strictness_rejects_incomplete_or_inexact_claims(
    tmp_path: Path, mutation: Any
) -> None:
    assets = _copy_assets(tmp_path)
    matrix_path = assets / "client-capabilities.yml"
    matrix = _load_yaml(matrix_path)
    mutation(matrix)
    _write_yaml(matrix_path, matrix)

    with pytest.raises(AgentPlatformContractError) as caught:
        compile_agent_projections(assets_root=assets)

    assert caught.value.code == ReasonCode.MATRIX_INVALID


def test_selection_rejects_unknown_client_without_writing() -> None:
    with pytest.raises(AgentPlatformContractError) as caught:
        compile_agent_projections(assets_root=ASSETS, client_ids=("unknown-client",))

    assert caught.value.code == ReasonCode.ADAPTER_NOT_FOUND
