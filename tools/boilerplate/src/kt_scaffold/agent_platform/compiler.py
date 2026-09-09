"""Pure canonical-to-client projection compiler; generation never activates files."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kt_scaffold.agent_platform.adapters import ADAPTERS
from kt_scaffold.agent_platform.contracts import (
    EXPECTED_AGENT_IDS,
    EXPECTED_CLIENT_IDS,
    AgentPlatformContractError,
    load_canonical_platform,
)
from kt_scaffold.agent_platform.manifest import (
    build_projection_manifest,
    serialize_projection_manifest,
)
from kt_scaffold.agent_platform.models import (
    CompilationResult,
    ContentReference,
    DocumentationSource,
    GenerationStatus,
    ProjectionArtifact,
    ReasonCode,
)

COMPILER_VERSION = "1.0.1"


def _omitted_optional_capabilities(contract: dict[str, Any]) -> tuple[str, ...]:
    requirements = contract["requirements"]
    omitted: set[str] = set()
    for key in ("policies", "rules", "skills", "commands"):
        entries = requirements[key]
        omitted.update(str(item["ref"]) for item in entries if not item["required"])
    tools = requirements["tools"]
    omitted.update(str(item["capability"]) for item in tools if not item["required"])
    mcp_entries = requirements["mcp"]
    for entry in mcp_entries:
        if not entry["required"]:
            omitted.add(str(entry["registry_ref"]))
        omitted.update(str(tool["capability"]) for tool in entry["tools"] if not tool["required"])
    hook_intents = requirements["hook_intents"]
    omitted.update(str(item["id"]) for item in hook_intents if not item["required"])
    return tuple(sorted(omitted))


def _select_ids(
    requested: tuple[str, ...] | None,
    available: tuple[str, ...],
    label: str,
) -> tuple[str, ...]:
    if requested is None:
        return available
    if not requested or len(requested) != len(set(requested)):
        raise AgentPlatformContractError(
            ReasonCode.SEMANTIC_VALIDATION_FAILED,
            f"{label} selection must be non-empty and contain no duplicates",
        )
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise AgentPlatformContractError(
            ReasonCode.ADAPTER_NOT_FOUND
            if label == "client"
            else ReasonCode.SEMANTIC_VALIDATION_FAILED,
            f"unknown {label} selection: {', '.join(unknown)}",
        )
    return tuple(item for item in available if item in requested)


def compile_agent_projections(
    *,
    assets_root: str | Path | None = None,
    agent_ids: tuple[str, ...] | None = None,
    client_ids: tuple[str, ...] | None = None,
) -> CompilationResult:
    """Compile inert client files and a lock in memory without touching a project."""

    platform = load_canonical_platform(assets_root)
    selected_agents = _select_ids(agent_ids, EXPECTED_AGENT_IDS, "agent")
    selected_clients = _select_ids(client_ids, EXPECTED_CLIENT_IDS, "client")
    packages = {item.agent_id: item for item in platform.agents}
    adapters = {item.client_id: item for item in ADAPTERS}
    if tuple(sorted(adapters)) != EXPECTED_CLIENT_IDS:
        raise AgentPlatformContractError(
            ReasonCode.ADAPTER_NOT_FOUND,
            "production adapter registry does not match the four-client matrix",
        )
    matrix_clients = {item.id for item in platform.capability_matrix.clients}
    if matrix_clients != set(adapters):
        raise AgentPlatformContractError(
            ReasonCode.MATRIX_INVALID,
            "adapter registry and capability matrix client ids differ",
        )
    matrix_registrations = {item.id: item.adapter for item in platform.capability_matrix.clients}
    matrix_clients_by_id = {item.id: item for item in platform.capability_matrix.clients}
    for client_id, adapter in adapters.items():
        registration = matrix_registrations[client_id]
        if (
            adapter.adapter_id != registration.id
            or adapter.adapter_version != registration.version
            or registration.generation_status != GenerationStatus.IMPLEMENTED
        ):
            raise AgentPlatformContractError(
                ReasonCode.ADAPTER_NOT_FOUND,
                f"{client_id} adapter does not match the exact implemented matrix selector",
            )
    matrix_ref = next(
        item for item in platform.platform_inputs if item.path == "client-capabilities.yml"
    )

    artifacts: list[ProjectionArtifact] = []
    seen_paths: set[str] = set()
    for client_id in selected_clients:
        adapter = adapters[client_id]
        matrix_client = matrix_clients_by_id[client_id]
        registration = matrix_client.adapter
        documentation_source_ids = sorted(
            {
                source_id
                for mapping in matrix_client.mappings
                if mapping.capability in {"custom-agents", "permission-policy"}
                for source_id in mapping.source_ids
            }
        )
        documentation_sources = tuple(
            DocumentationSource(
                id=source_id,
                url=platform.capability_matrix.sources[source_id].url,
                retrieved_at=platform.capability_matrix.sources[source_id].retrieved_at,
            )
            for source_id in documentation_source_ids
        )
        for agent_id in selected_agents:
            package = packages[agent_id]
            try:
                rendered = adapter.render(package)
                relative_path = adapter.relative_path(agent_id)
                digest = hashlib.sha256(rendered.content.encode("utf-8")).hexdigest()
                artifact = ProjectionArtifact(
                    client_id=client_id,
                    agent_id=agent_id,
                    relative_path=relative_path,
                    media_type=adapter.media_type,
                    adapter_id=adapter.adapter_id,
                    adapter_version=adapter.adapter_version,
                    client_version_range=registration.client_version_range,
                    generation_status="implemented",
                    candidate_inventory_ref=registration.candidate_inventory_ref,
                    runtime_admission="research",
                    runtime_conformance="not_run",
                    canonical_schema_version=package.contract["schema_version"],
                    canonical_contract_version=package.contract["metadata"]["version"],
                    documentation_sources=documentation_sources,
                    omitted_optional_capabilities=_omitted_optional_capabilities(package.contract),
                    content=rendered.content,
                    sha256=digest,
                    inputs=(*package.inputs, ContentReference(**matrix_ref.model_dump())),
                    mapped_fields=rendered.mapped_fields,
                    semantic_losses=rendered.semantic_losses,
                    external_controls=rendered.external_controls,
                    validations=rendered.validations,
                )
            except AgentPlatformContractError:
                raise
            except (TypeError, ValueError) as exc:
                raise AgentPlatformContractError(
                    ReasonCode.OUTPUT_VALIDATION_FAILED,
                    f"{client_id}/{agent_id} projection failed validation: {exc}",
                ) from exc
            if artifact.relative_path in seen_paths:
                raise AgentPlatformContractError(
                    ReasonCode.DUPLICATE_OUTPUT,
                    f"duplicate projection output: {artifact.relative_path}",
                )
            seen_paths.add(artifact.relative_path)
            artifacts.append(artifact)

    ordered = tuple(sorted(artifacts, key=lambda item: (item.client_id, item.agent_id)))
    expected_count = len(selected_agents) * len(selected_clients)
    if len(ordered) != expected_count:
        raise AgentPlatformContractError(
            ReasonCode.OUTPUT_VALIDATION_FAILED,
            f"expected {expected_count} projections, produced {len(ordered)}",
        )
    manifest = build_projection_manifest(
        platform,
        ordered,
        compiler_version=COMPILER_VERSION,
    )
    lock_content, lock_sha256 = serialize_projection_manifest(manifest)
    return CompilationResult(
        artifacts=ordered,
        manifest=manifest,
        lock_content=lock_content,
        lock_sha256=lock_sha256,
    )


__all__ = ["COMPILER_VERSION", "compile_agent_projections"]
