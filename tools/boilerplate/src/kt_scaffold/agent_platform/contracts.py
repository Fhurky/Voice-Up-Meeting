"""Fail-closed loading and validation for canonical Agent Platform inputs."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

import yaml
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from jsonschema.exceptions import SchemaError  # type: ignore[import-untyped]
from pydantic import ValidationError

from kt_scaffold.agent_platform.assets import production_asset_paths
from kt_scaffold.agent_platform.models import (
    AdapterStrategy,
    AdmissionState,
    CanonicalAgentPackage,
    CanonicalPlatform,
    ClientCapabilityMatrix,
    ConformanceStatus,
    ContentReference,
    GenerationStatus,
    Lifecycle,
    Lossiness,
    Maturity,
    ProjectionKind,
    ReasonCode,
    SupportStatus,
)

EXPECTED_AGENT_IDS = (
    "application-security",
    "code-review",
    "requirements-scope",
    "test-automation",
)
EXPECTED_CLIENT_IDS = (
    "claude-code",
    "codex",
    "cursor",
    "github-copilot-vscode",
)
EXPECTED_ADAPTER_VERSIONS = {
    client_id: "1.0.2" if client_id == "codex" else "1.0.1" for client_id in EXPECTED_CLIENT_IDS
}

_SECRET_RE = re.compile(
    r"(?:-----BEGIN [A-Z ]+ PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[oprsu]_[A-Za-z0-9]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}|\bBearer\s+[A-Za-z0-9._~+/=-]{12,})"
)
_ENV_RE = re.compile(r"(?:\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[A-Za-z_][A-Za-z0-9_]*%)")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_EXECUTABLE_RE = re.compile(
    r"^(?:sudo\s+|bash\s+|sh\s+|zsh\s+|pwsh\s+|powershell\s+|cmd(?:\.exe)?\s+/[ck]\s+|"
    r"python(?:3(?:\.\d+)?)?\s+|node\s+|npm\s+|npx\s+|curl\s+|wget\s+)",
    re.IGNORECASE,
)
_EXACT_VERSION_TUPLE_RE = re.compile(
    r"^(?:[a-z][a-z0-9-]*)?==[0-9]+\.[0-9]+\.[0-9]+"
    r"(?:;(?:[a-z][a-z0-9-]*)?==[0-9]+\.[0-9]+\.[0-9]+)*$"
)


class AgentPlatformContractError(ValueError):
    """Stable fail-closed error returned for invalid canonical inputs."""

    def __init__(self, code: ReasonCode, message: str) -> None:
        self.code = code
        self.detail = message
        super().__init__(f"{code.value}: {message}")


def _fail(code: ReasonCode, message: str) -> NoReturn:
    raise AgentPlatformContractError(code, message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bytes(path: Path, source: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        _fail(ReasonCode.ASSET_INVALID, f"unsafe or missing canonical asset: {source}")
    try:
        return path.read_bytes()
    except OSError as exc:
        _fail(ReasonCode.ASSET_INVALID, f"cannot read canonical asset {source}: {exc.strerror}")


def _load_json(path: Path, source: str) -> tuple[dict[str, Any], bytes]:
    data = _read_bytes(path, source)
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(ReasonCode.DOCUMENT_INVALID, f"invalid JSON in {source}: {exc}")
    if not isinstance(value, dict):
        _fail(ReasonCode.DOCUMENT_INVALID, f"{source} must contain a JSON object")
    return value, data


def _load_yaml(path: Path, source: str) -> tuple[dict[str, Any], bytes]:
    data = _read_bytes(path, source)
    try:
        value = yaml.safe_load(data)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        _fail(ReasonCode.DOCUMENT_INVALID, f"invalid YAML in {source}: {exc}")
    if not isinstance(value, dict):
        _fail(ReasonCode.DOCUMENT_INVALID, f"{source} must contain a YAML mapping")
    return value, data


def _json_path(parts: Sequence[object]) -> str:
    if not parts:
        return "$"
    return "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts)


def _validate_schema(instance: object, schema: Mapping[str, Any], source: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        _fail(ReasonCode.SCHEMA_INVALID, f"invalid schema for {source}: {exc.message}")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(instance), key=lambda item: tuple(str(x) for x in item.path)
    )
    if errors:
        first = errors[0]
        _fail(
            ReasonCode.SCHEMA_VALIDATION_FAILED,
            f"{source}{_json_path(list(first.path))}: {first.message}",
        )


def _walk_strings(
    value: object, path: tuple[object, ...] = ()
) -> list[tuple[tuple[object, ...], str]]:
    strings: list[tuple[tuple[object, ...], str]] = []
    if isinstance(value, str):
        strings.append((path, value))
    elif isinstance(value, Mapping):
        for key, child in value.items():
            strings.extend(_walk_strings(child, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            strings.extend(_walk_strings(child, (*path, index)))
    return strings


def _validate_no_embedded_authority(value: Mapping[str, Any], source: str) -> None:
    """Reject secrets, endpoints, environment interpolation, paths and command payloads."""

    for path, text in _walk_strings(value):
        stripped = text.strip()
        reason: str | None = None
        if _SECRET_RE.search(text):
            reason = "secret-like material"
        elif "http://" in text.lower() or "https://" in text.lower():
            reason = "provider or endpoint URL"
        elif _ENV_RE.search(text):
            reason = "environment interpolation"
        elif stripped.startswith("/") or _WINDOWS_ABSOLUTE_RE.match(stripped):
            reason = "absolute filesystem path"
        elif _EXECUTABLE_RE.match(stripped):
            reason = "executable command payload"
        if reason:
            _fail(
                ReasonCode.SEMANTIC_VALIDATION_FAILED,
                f"{source}{_json_path(path)} contains forbidden {reason}",
            )


def _validate_instruction_content(text: str, source: str) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if _SECRET_RE.search(line):
            reason = "secret-like material"
        elif "http://" in line.lower() or "https://" in line.lower():
            reason = "provider or endpoint URL"
        elif _ENV_RE.search(line):
            reason = "environment interpolation"
        elif stripped.startswith("/") or _WINDOWS_ABSOLUTE_RE.match(stripped):
            reason = "absolute filesystem path"
        elif _EXECUTABLE_RE.match(stripped):
            reason = "executable command payload"
        else:
            continue
        _fail(
            ReasonCode.SEMANTIC_VALIDATION_FAILED,
            f"{source}:{line_number} contains forbidden {reason}",
        )


def _safe_instruction_path(root: Path, agent_id: str, reference: object) -> Path:
    if not isinstance(reference, str):
        _fail(ReasonCode.SEMANTIC_VALIDATION_FAILED, f"{agent_id} instructions_ref is not a string")
    relative = PurePosixPath(reference)
    if (
        relative.is_absolute()
        or len(relative.parts) != 1
        or any(part in {"", ".", ".."} for part in relative.parts)
        or "\\" in reference
    ):
        _fail(
            ReasonCode.SEMANTIC_VALIDATION_FAILED,
            f"{agent_id} instructions_ref must be one package-local filename",
        )
    package_root = (root / "agents" / agent_id).resolve(strict=True)
    candidate = package_root / relative.name
    if candidate.is_symlink():
        _fail(ReasonCode.ASSET_INVALID, f"symbolic-link instructions rejected for {agent_id}")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        _fail(ReasonCode.ASSET_INVALID, f"instructions asset missing for {agent_id}")
    if not resolved.is_relative_to(package_root) or not resolved.is_file():
        _fail(ReasonCode.ASSET_INVALID, f"instructions path escapes package for {agent_id}")
    return resolved


def _validate_agent_semantics(
    agent_id: str,
    contract: dict[str, Any],
    policy: dict[str, Any],
    instructions: str,
) -> None:
    if contract["metadata"]["id"] != agent_id:
        _fail(ReasonCode.SEMANTIC_VALIDATION_FAILED, f"agent id mismatch for {agent_id}")
    expected_policy_id = f"policy:{agent_id}"
    if policy["metadata"]["id"] != expected_policy_id:
        _fail(ReasonCode.SEMANTIC_VALIDATION_FAILED, f"policy id mismatch for {agent_id}")
    policy_refs = [item for item in contract["requirements"]["policies"] if item["required"]]
    if [item["ref"] for item in policy_refs] != [expected_policy_id]:
        _fail(
            ReasonCode.SEMANTIC_VALIDATION_FAILED,
            f"{agent_id} must require exactly its package policy",
        )
    permissions = contract["permissions"]
    delegation = contract["delegation"]
    runtime = contract["runtime"]
    data = contract["data"]
    if (
        permissions["workspace"]["read"] != ["**"]
        or permissions["workspace"]["write"]
        or not {".env*", "**/.env*", "**/secrets/**"}.issubset(permissions["workspace"]["deny"])
        or permissions["network"] != {"mode": "denied", "registry_refs": []}
        or permissions["secrets"] != {"mode": "none", "registry_refs": []}
        or permissions["external_side_effects"] != "prohibited"
        or delegation["allowed"]
        or delegation["max_depth"] != 0
        or delegation["max_parallel"] != 1
        or delegation["allowed_agents"]
        or delegation["context_sharing"] != "minimal"
        or not runtime["sandbox_required"]
        or runtime["workspace_access"] != "read-only"
        or runtime["identity"] != "task-scoped"
        or runtime["budgets"]["max_external_side_effects"] != 0
        or data["memory"] != "forbidden"
        or data["retention"] != "none"
    ):
        _fail(
            ReasonCode.SEMANTIC_VALIDATION_FAILED,
            f"{agent_id} violates the read-only canonical safety invariant",
        )
    tools = contract["requirements"]["tools"]
    required_tools = [tool for tool in tools if tool["required"]]
    required_workspace_reads = [
        tool for tool in tools if tool["capability"] == "tool:workspace-read" and tool["required"]
    ]
    if (
        len(required_workspace_reads) != 1
        or required_tools != required_workspace_reads
        or any(tool["access"] != "read" for tool in tools)
    ):
        _fail(
            ReasonCode.SEMANTIC_VALIDATION_FAILED,
            f"{agent_id} must require one read-only workspace capability",
        )
    if contract["requirements"]["mcp"]:
        _fail(ReasonCode.SEMANTIC_VALIDATION_FAILED, f"{agent_id} may not embed MCP bindings")
    if not instructions.strip() or "\x00" in instructions or "\r" in instructions:
        _fail(
            ReasonCode.SEMANTIC_VALIDATION_FAILED,
            f"{agent_id} instructions must be non-empty UTF-8 text using LF",
        )
    _validate_no_embedded_authority(contract, f"agents/{agent_id}/agent.yml")
    _validate_no_embedded_authority(policy, f"agents/{agent_id}/policy.yml")
    _validate_instruction_content(instructions, f"agents/{agent_id}/instructions.md")


def _validate_matrix(matrix: ClientCapabilityMatrix) -> None:
    enum_claims = (
        (matrix.policy.support_values, tuple(SupportStatus)),
        (matrix.policy.projection_values, tuple(ProjectionKind)),
        (matrix.policy.maturity_values, tuple(Maturity)),
        (matrix.policy.lifecycle_values, tuple(Lifecycle)),
        (matrix.policy.adapter_strategy_values, tuple(AdapterStrategy)),
        (matrix.policy.lossiness_values, tuple(Lossiness)),
        (matrix.policy.conformance_values, tuple(ConformanceStatus)),
        (matrix.policy.admission_values, tuple(AdmissionState)),
        (matrix.policy.generation_values, tuple(GenerationStatus)),
    )
    if any(
        len(values) != len(set(values)) or set(values) != set(expected)
        for values, expected in enum_claims
    ):
        _fail(
            ReasonCode.MATRIX_INVALID, "capability matrix policy enum declarations are incomplete"
        )
    if matrix.policy.mapping_claim_only is not True:
        _fail(ReasonCode.MATRIX_INVALID, "capability matrix must remain mapping-claim-only")
    capability_ids = tuple(item.id for item in matrix.capabilities)
    if len(capability_ids) != len(set(capability_ids)):
        _fail(ReasonCode.MATRIX_INVALID, "capability matrix contains duplicate capability ids")
    client_ids = tuple(sorted(item.id for item in matrix.clients))
    if client_ids != EXPECTED_CLIENT_IDS:
        _fail(
            ReasonCode.MATRIX_INVALID, "capability matrix must contain the six production adapters"
        )
    source_ids = set(matrix.sources)
    if any(source.retrieved_at != matrix.as_of for source in matrix.sources.values()):
        _fail(ReasonCode.MATRIX_INVALID, "matrix source dates must equal the matrix as_of date")
    used_source_ids: set[str] = set()
    for client in matrix.clients:
        if len(client.surfaces) != len(set(client.surfaces)):
            _fail(ReasonCode.MATRIX_INVALID, f"{client.id} contains duplicate client surfaces")
        if (
            client.adapter.id != client.id
            or client.adapter.version != EXPECTED_ADAPTER_VERSIONS[client.id]
            or client.adapter.generation_status != GenerationStatus.IMPLEMENTED
            or client.adapter.candidate_inventory_ref != f"client:{client.id}"
            or not _EXACT_VERSION_TUPLE_RE.fullmatch(client.adapter.client_version_range)
        ):
            _fail(
                ReasonCode.MATRIX_INVALID,
                f"{client.id} must select implemented adapter "
                f"{EXPECTED_ADAPTER_VERSIONS[client.id]} and an exact runtime tuple",
            )
        mapping_ids = tuple(item.capability for item in client.mappings)
        if len(mapping_ids) != len(set(mapping_ids)) or set(mapping_ids) != set(capability_ids):
            _fail(
                ReasonCode.MATRIX_INVALID,
                f"{client.id} must map every canonical capability exactly once",
            )
        if client.admission.state != AdmissionState.RESEARCH:
            _fail(
                ReasonCode.MATRIX_INVALID,
                f"{client.id} generation input must not claim runtime admission",
            )
        if client.conformance.status != ConformanceStatus.NOT_RUN:
            _fail(
                ReasonCode.MATRIX_INVALID,
                f"{client.id} generation input must not claim runtime conformance",
            )
        for mapping in client.mappings:
            if len(mapping.applies_to_surfaces) != len(set(mapping.applies_to_surfaces)) or not set(
                mapping.applies_to_surfaces
            ).issubset(client.surfaces):
                _fail(
                    ReasonCode.MATRIX_INVALID,
                    f"{client.id}/{mapping.capability} has invalid surface scope",
                )
            if not set(mapping.source_ids).issubset(source_ids):
                _fail(
                    ReasonCode.MATRIX_INVALID,
                    f"{client.id}/{mapping.capability} references an unknown source",
                )
            used_source_ids.update(mapping.source_ids)
            definition = next(item for item in matrix.capabilities if item.id == mapping.capability)
            if mapping.status == SupportStatus.FORBIDDEN:
                _fail(
                    ReasonCode.FORBIDDEN_CAPABILITY,
                    f"{client.id}/{mapping.capability} is forbidden",
                )
            if definition.required and mapping.status == SupportStatus.UNMAPPED:
                _fail(
                    ReasonCode.REQUIRED_CAPABILITY_UNMAPPED,
                    f"{client.id}/{mapping.capability} is required and unmapped",
                )
            if definition.required and mapping.lossiness == Lossiness.MATERIAL:
                _fail(
                    ReasonCode.MATERIAL_SEMANTIC_LOSS,
                    f"{client.id}/{mapping.capability} has material semantic loss",
                )
        custom_agent = next(item for item in client.mappings if item.capability == "custom-agents")
        if (
            custom_agent.status not in {SupportStatus.SUPPORTED, SupportStatus.DEGRADED}
            or custom_agent.projection.value != "native"
            or custom_agent.adapter_strategy.value != "emit"
            or custom_agent.maturity.value in {"preview", "beta", "experimental"}
            or custom_agent.lifecycle.value != "current"
        ):
            _fail(
                ReasonCode.MATRIX_INVALID,
                f"{client.id} has no current non-preview custom-agent generation surface",
            )
    if used_source_ids != source_ids:
        _fail(ReasonCode.MATRIX_INVALID, "matrix sources must be referenced exactly by mappings")


def _required_package_capabilities(package: CanonicalAgentPackage) -> set[str]:
    requirements = package.contract["requirements"]
    required = {"custom-agents", "permission-policy"}
    bindings = {
        "policies": "permission-policy",
        "rules": "project-instructions",
        "skills": "agent-skills",
        "commands": "reusable-commands",
        "mcp": "mcp-tools",
        "hook_intents": "lifecycle-hooks",
    }
    for field, capability in bindings.items():
        if any(item["required"] for item in requirements[field]):
            required.add(capability)
    return required


def _validate_package_matrix_bindings(
    packages: Sequence[CanonicalAgentPackage], matrix: ClientCapabilityMatrix
) -> None:
    for package in packages:
        required = _required_package_capabilities(package)
        for client in matrix.clients:
            mappings = {item.capability: item for item in client.mappings}
            for capability in sorted(required):
                mapping = mappings[capability]
                if mapping.status == SupportStatus.UNMAPPED:
                    _fail(
                        ReasonCode.REQUIRED_CAPABILITY_UNMAPPED,
                        f"{client.id}/{package.agent_id}/{capability} is required and unmapped",
                    )
                if mapping.status == SupportStatus.FORBIDDEN:
                    _fail(
                        ReasonCode.FORBIDDEN_CAPABILITY,
                        f"{client.id}/{package.agent_id}/{capability} is forbidden",
                    )
                if mapping.lossiness == Lossiness.MATERIAL:
                    _fail(
                        ReasonCode.MATERIAL_SEMANTIC_LOSS,
                        f"{client.id}/{package.agent_id}/{capability} has material semantic loss",
                    )


def load_canonical_platform(root: str | Path | None = None) -> CanonicalPlatform:
    """Load the allowlisted canonical four-agent input set without producing files."""

    try:
        assets = production_asset_paths(root)
    except ValueError as exc:
        _fail(ReasonCode.ASSET_INVALID, str(exc))
    contract_schema, contract_schema_bytes = _load_json(
        assets["agent-contract.schema.json"], "agent-contract.schema.json"
    )
    policy_schema, policy_schema_bytes = _load_json(
        assets["agent-policy.schema.json"], "agent-policy.schema.json"
    )
    catalog_schema, catalog_schema_bytes = _load_json(
        assets["agent-catalog.schema.json"], "agent-catalog.schema.json"
    )
    catalog, catalog_bytes = _load_yaml(assets["agent-catalog.yml"], "agent-catalog.yml")
    _validate_schema(catalog, catalog_schema, "agent-catalog.yml")

    matrix_value, matrix_bytes = _load_yaml(
        assets["client-capabilities.yml"], "client-capabilities.yml"
    )
    try:
        matrix = ClientCapabilityMatrix.model_validate(matrix_value)
    except ValidationError as exc:
        first = exc.errors(include_url=False)[0]
        location = _json_path(first["loc"])
        _fail(ReasonCode.MATRIX_INVALID, f"client-capabilities.yml{location}: {first['msg']}")
    _validate_matrix(matrix)

    canonical_catalog_entries = [
        role["id"]
        for role in catalog["roles"]
        if isinstance(role.get("canonical_path"), str)
        and role["canonical_path"].startswith("agents/")
    ]
    canonical_catalog_ids = set(canonical_catalog_entries)
    if (
        len(canonical_catalog_entries) != len(set(canonical_catalog_entries))
        or canonical_catalog_ids != set(EXPECTED_AGENT_IDS)
        or any(
            role["canonical_path"] != f"agents/{role['id']}"
            for role in catalog["roles"]
            if isinstance(role.get("canonical_path"), str)
            and role["canonical_path"].startswith("agents/")
        )
    ):
        _fail(
            ReasonCode.SEMANTIC_VALIDATION_FAILED,
            "catalog canonical agent inventory does not match the production four-agent set",
        )

    packages: list[CanonicalAgentPackage] = []
    # Resolve instructions from the validated allowlist rather than following arbitrary refs.
    asset_root = assets["agent-contract.schema.json"].parent
    for agent_id in EXPECTED_AGENT_IDS:
        contract_ref = f"agents/{agent_id}/agent.yml"
        policy_ref = f"agents/{agent_id}/policy.yml"
        contract, contract_bytes = _load_yaml(assets[contract_ref], contract_ref)
        policy, policy_bytes = _load_yaml(assets[policy_ref], policy_ref)
        _validate_schema(contract, contract_schema, contract_ref)
        _validate_schema(policy, policy_schema, policy_ref)
        instruction_path = _safe_instruction_path(
            asset_root, agent_id, contract["mission"]["instructions_ref"]
        )
        instruction_ref = f"agents/{agent_id}/{instruction_path.name}"
        if instruction_ref not in assets or assets[instruction_ref] != instruction_path:
            _fail(
                ReasonCode.ASSET_INVALID,
                f"instructions ref for {agent_id} is outside the production inventory",
            )
        instruction_bytes = _read_bytes(instruction_path, instruction_ref)
        try:
            instructions = instruction_bytes.decode("utf-8")
        except UnicodeDecodeError:
            _fail(ReasonCode.DOCUMENT_INVALID, f"invalid UTF-8 in {instruction_ref}")
        _validate_agent_semantics(agent_id, contract, policy, instructions)
        packages.append(
            CanonicalAgentPackage(
                agent_id=agent_id,
                contract=contract,
                policy=policy,
                instructions=instructions,
                inputs=(
                    ContentReference(path=contract_ref, sha256=_sha256(contract_bytes)),
                    ContentReference(path=instruction_ref, sha256=_sha256(instruction_bytes)),
                    ContentReference(path=policy_ref, sha256=_sha256(policy_bytes)),
                ),
            )
        )

    platform_inputs = (
        ContentReference(path="agent-catalog.schema.json", sha256=_sha256(catalog_schema_bytes)),
        ContentReference(path="agent-catalog.yml", sha256=_sha256(catalog_bytes)),
        ContentReference(path="agent-contract.schema.json", sha256=_sha256(contract_schema_bytes)),
        ContentReference(path="agent-policy.schema.json", sha256=_sha256(policy_schema_bytes)),
        ContentReference(path="client-capabilities.yml", sha256=_sha256(matrix_bytes)),
    )
    _validate_package_matrix_bindings(packages, matrix)
    return CanonicalPlatform(
        agents=tuple(packages),
        capability_matrix=matrix,
        platform_inputs=platform_inputs,
    )


__all__ = [
    "AgentPlatformContractError",
    "EXPECTED_AGENT_IDS",
    "EXPECTED_CLIENT_IDS",
    "load_canonical_platform",
]
