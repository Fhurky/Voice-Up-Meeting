"""Contract checks for the vendor-neutral Agent Platform assets and evidence."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from kt_scaffold.agent_platform.compiler import compile_agent_projections
from kt_scaffold.agent_platform.projection_store import INERT_LOCK_PATH
from kt_scaffold.project import project_init

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "agent-platform"
SCHEMA_PATH = PLATFORM / "agent-contract.schema.json"
AGENT_POLICY_SCHEMA_PATH = PLATFORM / "agent-policy.schema.json"
AGENT_CATALOG_SCHEMA_PATH = PLATFORM / "agent-catalog.schema.json"
ORCHESTRATION_SCHEMA_PATH = PLATFORM / "orchestration.schema.json"
DECISION_POLICY_SCHEMA_PATH = PLATFORM / "decision-policy.schema.json"
EXAMPLE_PATH = PLATFORM / "examples" / "pr-reviewer.agent.yml"
CATALOG_PATH = PLATFORM / "agent-catalog.yml"
ORCHESTRATION_PATH = PLATFORM / "orchestrations" / "governed-review.yml"
DECISION_POLICY_PATH = PLATFORM / "policies" / "aggregation" / "governed-review.yml"
MATRIX_PATH = PLATFORM / "client-capabilities.yml"
CROSSWALK_PATH = PLATFORM / "standards-crosswalk.yml"
RUNTIME_CANDIDATE_SCHEMA_PATH = PLATFORM / "runtime-candidate.schema.json"
CONFORMANCE_SNAPSHOT_SCHEMA_PATH = PLATFORM / "conformance-snapshot.schema.json"
RUNTIME_CANDIDATE_PATH = PLATFORM / "conformance" / "candidates" / "macos-arm64-2026-08-19.yml"
CONFORMANCE_SNAPSHOT_PATH = PLATFORM / "conformance" / "runs" / "macos-arm64-2026-08-19.yml"
RUNTIME_ADMISSION_STATUS_PATH = (
    ROOT / "docs" / "evidence" / "agent-platform-runtime-admission-2026-08-19.md"
)
PRD_DIR = ROOT / "specs" / "agent-platform" / "PRDs" / "001-vendor-neutral-agent-contract"
PILOT_AGENT_IDS = {
    "application-security",
    "code-review",
    "requirements-scope",
    "test-automation",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _document_status(body: str) -> str:
    matches = re.findall(r"^Status: (Draft|Accepted)$", body, flags=re.MULTILINE)
    assert len(matches) == 1
    return matches[0]


def _object_schemas(value: object) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("type") == "object":
            found.append(value)
        for nested in value.values():
            found.extend(_object_schemas(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_object_schemas(nested))
    return found


def _keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            found.add(key.lower())
            found.update(_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            found.update(_keys(nested))
    return found


def test_agent_schema_is_strict_and_example_is_valid() -> None:
    schema = _load_json(SCHEMA_PATH)
    example = _load_yaml(EXAMPLE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)

    object_schemas = _object_schemas(schema)
    assert object_schemas
    assert all(item.get("additionalProperties") is False for item in object_schemas)


def test_runtime_candidate_inventory_is_exact_strict_and_not_admitted() -> None:
    schema = _load_json(RUNTIME_CANDIDATE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    candidate = _load_yaml(RUNTIME_CANDIDATE_PATH)
    validator = Draft202012Validator(schema)
    validator.validate(candidate)

    clients = {item["id"]: item for item in candidate["clients"]}
    assert set(clients) == {
        "codex",
        "claude-code",
        "github-copilot-vscode",
        "cursor",
    }
    assert clients["codex"]["version"] == "0.147.0"
    assert clients["claude-code"]["version"] == "2.1.227"
    codex_exploratory = {
        item["version"]: item for item in clients["codex"]["related_exploratory_artifacts"]
    }
    assert codex_exploratory["26.818.21641"]["sha256"] == (
        "fe6ca79e9099fe1507ed851fd34307254da7ba0695df0908e8bf1bbde54ec61c"
    )
    assert codex_exploratory["0.148.0-alpha.21"]["sha256"] == (
        "5e508bd40c1bdd2d9798a269839c16935c71941e5709c097b0a527bee52977ab"
    )
    assert all(item["conformance"] == "not_run" for item in clients.values())
    assert all(item["admission"] == "research" for item in clients.values())
    assert all(item["unresolved_runtime_bindings"] for item in clients.values())
    assert "alpha" not in clients["codex"]["version"]

    invalid = copy.deepcopy(candidate)
    invalid["clients"][0]["unexpected"] = True
    with pytest.raises(ValidationError):
        validator.validate(invalid)


def test_runtime_conformance_snapshot_is_strict_historical_and_not_admitted() -> None:
    schema = _load_json(CONFORMANCE_SNAPSHOT_SCHEMA_PATH)
    snapshot = _load_yaml(CONFORMANCE_SNAPSHOT_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    validator.validate(snapshot)

    runs = {item["client_id"]: item for item in snapshot["runs"]}
    assert set(runs) == {
        "claude-code",
        "codex",
        "cursor",
        "github-copilot-vscode",
    }
    assert snapshot["compiler"] == {
        "id": "kt-scaffold-agent-projection",
        "version": "1.0.1",
        "lock_sha256": "f1d55c0358d5f8417b35038c17398595741fa96be3311ec7134f1f91b987f190",
    }
    assert (
        snapshot["compiler"]["lock_sha256"]
        != compile_agent_projections(assets_root=PLATFORM).lock_sha256
    )
    assert snapshot["claim_boundary"]["full_suite_status"] == "not_run"
    assert snapshot["claim_boundary"]["runtime_admission"] == "research"
    assert runs["claude-code"]["result"]["status"] == "partial_pass"
    assert runs["codex"]["adapter_version"] == "1.0.2"
    assert runs["codex"]["runtime_artifact"]["candidate_scope"] == "exploratory"
    assert runs["codex"]["result"]["status"] == "partial_pass"
    assert runs["codex"]["result"]["workspace_unchanged"] is True
    assert any(
        check["id"] == "single-delegation" and check["status"] == "pass"
        for check in runs["codex"]["result"]["checks"]
    )
    assert runs["github-copilot-vscode"]["result"]["status"] == "partial_pass"
    assert runs["github-copilot-vscode"]["result"]["workspace_unchanged"] is True
    assert runs["cursor"]["result"]["status"] == "partial_pass"
    assert runs["cursor"]["result"]["workspace_unchanged"] is True
    assert all(item["review"]["disposition"] == "no-runtime-admission" for item in runs.values())

    invalid = copy.deepcopy(snapshot)
    invalid["claim_boundary"]["runtime_support"] = True
    with pytest.raises(ValidationError):
        validator.validate(invalid)


def test_runtime_admission_status_is_explicitly_fail_closed() -> None:
    report = RUNTIME_ADMISSION_STATUS_PATH.read_text(encoding="utf-8")

    assert "Overall disposition: **NO_RUNTIME_ADMISSION**" in report
    assert report.count("| Not admitted |") == 4
    assert "No owner receipt was fabricated" in report
    assert "T12 remains open" in report


def test_canonical_pilot_agent_packages_are_strict_complete_and_resolvable() -> None:
    agent_schema = _load_json(SCHEMA_PATH)
    policy_schema = _load_json(AGENT_POLICY_SCHEMA_PATH)
    agent_validator = Draft202012Validator(agent_schema)
    policy_validator = Draft202012Validator(policy_schema)
    catalog = _load_yaml(CATALOG_PATH)
    pilot_entries = [
        item for item in catalog["roles"] if item["migration_status"] == "canonical-implemented"
    ]

    Draft202012Validator.check_schema(policy_schema)
    assert {item["id"] for item in pilot_entries} == {
        "application-security",
        "code-review",
        "requirements-scope",
        "test-automation",
    }

    for entry in pilot_entries:
        package = PLATFORM / entry["canonical_path"]
        manifest = _load_yaml(package / "agent.yml")
        policy = _load_yaml(package / "policy.yml")
        agent_validator.validate(manifest)
        policy_validator.validate(policy)

        assert manifest["metadata"]["id"] == entry["id"]
        assert manifest["metadata"]["version"] == "1.0.0"
        assert manifest["metadata"]["lifecycle"] == "draft"
        assert policy["metadata"]["version"] == "1.0.0"
        assert policy["metadata"]["lifecycle"] == "draft"
        assert policy["lineage"]["authoritative"] is False
        assert policy["lineage"]["normalization_status"] == "canonical-normalized"

        instruction_path = (package / manifest["mission"]["instructions_ref"]).resolve()
        assert instruction_path.is_relative_to(package.resolve())
        assert instruction_path.is_file()

        policy_refs = {item["ref"] for item in manifest["requirements"]["policies"]}
        assert policy_refs == {policy["metadata"]["id"]}


def test_agent_manifest_rejects_unsafe_instruction_and_policy_references() -> None:
    schema = _load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    example = _load_yaml(EXAMPLE_PATH)

    for value in (
        "../instructions.md",
        "/workspace/instructions.md",
        "C:/workspace/instructions.md",
    ):
        invalid = copy.deepcopy(example)
        invalid["mission"]["instructions_ref"] = value
        with pytest.raises(ValidationError):
            validator.validate(invalid)

    invalid = copy.deepcopy(example)
    invalid["requirements"]["policies"][0]["ref"] = "rule:10-spec-first"
    with pytest.raises(ValidationError):
        validator.validate(invalid)


def test_desktop_seed_catalog_is_complete_but_non_authoritative() -> None:
    schema = _load_json(AGENT_CATALOG_SCHEMA_PATH)
    catalog = _load_yaml(CATALOG_PATH)
    roles = catalog["roles"]
    expected_roles = {
        "application-security",
        "autofix",
        "code-quality",
        "code-review",
        "devops",
        "documentation",
        "enterprise-architecture",
        "information-security",
        "observability",
        "oss-license",
        "privacy-kvkk",
        "requirements-scope",
        "supervisor",
        "test-automation",
    }

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(
        catalog
    )
    assert catalog["status"] == "implementation"
    assert catalog["as_of"] == "2026-08-18"
    assert catalog["source_lineage"]["authoritative"] is False
    assert catalog["source_lineage"]["mutation_allowed"] is False
    assert catalog["projection"]["status"] == "compiler-implemented"
    assert {item["id"] for item in roles} == expected_roles
    assert len(roles) == len(expected_roles)
    assert next(item for item in roles if item["id"] == "autofix")["migration_status"] == "deferred"
    assert next(item for item in roles if item["id"] == "supervisor")["classification"] == (
        "deterministic-orchestrator"
    )
    assert "/Users/" not in CATALOG_PATH.read_text(encoding="utf-8")


def test_governed_review_is_deterministic_fail_closed_and_excludes_autofix() -> None:
    orchestration_schema = _load_json(ORCHESTRATION_SCHEMA_PATH)
    decision_schema = _load_json(DECISION_POLICY_SCHEMA_PATH)
    orchestration = _load_yaml(ORCHESTRATION_PATH)
    policy = _load_yaml(DECISION_POLICY_PATH)

    Draft202012Validator.check_schema(orchestration_schema)
    Draft202012Validator.check_schema(decision_schema)
    Draft202012Validator(orchestration_schema).validate(orchestration)
    Draft202012Validator(decision_schema).validate(policy)

    worker_refs = {item["agent"] for item in orchestration["workers"]}
    assert worker_refs == set(policy["required_workers"])
    assert worker_refs == set(policy["weights"])
    assert orchestration["decision"]["engine"] == "deterministic-policy"
    assert orchestration["input"]["raw_source_visible_to_aggregator"] is False
    assert orchestration["prohibited_agents"] == ["agent:autofix"]
    assert set(policy["fail_closed"].values()) == {"MANUAL_REVIEW"}
    assert policy["thresholds"]["warning_score"] < policy["thresholds"]["fail_score"]
    assert policy["claim_boundary"]["runtime_admission"] is False
    assert policy["claim_boundary"]["production_decision"] is False


def test_production_projection_compiler_replaces_manual_previews_without_activation(
    tmp_path: Path, answers_factory: Any
) -> None:
    live_roots = {
        ".codex/agents",
        ".claude/agents",
        ".github/agents",
        ".cursor/agents",
    }
    assert not (PLATFORM / "examples" / "client-projections").exists()
    assert not (PLATFORM / "client-projection-fixture.schema.json").exists()
    assert all(not (ROOT / relative).exists() for relative in live_roots)

    compilation = compile_agent_projections(assets_root=PLATFORM)
    assert len(compilation.artifacts) == 16
    assert compilation.manifest.generation_status == "generated"
    assert compilation.manifest.activation_status == "not_activated"
    assert compilation.manifest.runtime_conformance == "not_run"
    assert compilation.manifest.runtime_admission == "research"

    generated = tmp_path / "production-compiler-boundary"
    result = project_init(generated, answers_factory())
    assert result["ok"] is True
    assert (generated / INERT_LOCK_PATH).is_file()
    assert all(not (generated / relative).exists() for relative in live_roots)

    managed = json.loads(
        (generated / ".kt-scaffold" / "manifest.json").read_text(encoding="utf-8")
    )["managed"]
    assert INERT_LOCK_PATH in managed
    assert (
        len([path for path in managed if path.startswith(".kt-scaffold/agent-projections/")]) == 17
    )
    assert all(
        not any(path == root or path.startswith(f"{root}/") for root in live_roots)
        for path in managed
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["metadata"].update({"provider": "vendor-a"}),
        lambda value: value.update({"endpoint": "private-service"}),
        lambda value: value["permissions"]["workspace"]["read"].append("/workspace/**"),
        lambda value: value["permissions"]["workspace"]["read"].append("C:/workspace/**"),
        lambda value: value["permissions"]["workspace"]["read"].append("./src/**"),
        lambda value: value["permissions"]["workspace"]["read"].append("../secrets/**"),
        lambda value: value["permissions"]["network"].update(
            {"mode": "denied", "registry_refs": ["egress:source-control"]}
        ),
        lambda value: value["delegation"].update({"allowed": False, "max_depth": 1}),
        lambda value: value["requirements"]["rules"].append(
            {"ref": "skill:wrong-reference-kind", "required": True}
        ),
        lambda value: value["requirements"]["commands"].append(
            {"ref": "skill:wrong-reference-kind", "required": True}
        ),
        lambda value: value["metadata"].update({"version": "1.2.3-01"}),
        lambda value: value["requirements"]["tools"].append(
            {
                "capability": "tool:dangerous-delete",
                "required": True,
                "access": "destructive",
                "approval": "never",
            }
        ),
        lambda value: value["permissions"]["workspace"]["write"].append("src/**"),
        lambda value: value["runtime"]["budgets"].update({"max_external_side_effects": 1}),
        lambda value: value["mission"].update({"objective": " " * 20}),
    ],
)
def test_agent_schema_rejects_unknown_or_unsafe_shape(mutation: Any) -> None:
    schema = _load_json(SCHEMA_PATH)
    example = copy.deepcopy(_load_yaml(EXAMPLE_PATH))
    mutation(example)

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(example)


def test_portable_manifest_has_no_vendor_or_secret_binding_keys() -> None:
    example = _load_yaml(EXAMPLE_PATH)
    forbidden = {
        "command",
        "credential",
        "endpoint",
        "env",
        "header",
        "model",
        "model_id",
        "provider",
        "token",
        "url",
    }
    assert _keys(example).isdisjoint(forbidden)


def test_high_risk_contracts_require_stronger_approval_and_evidence() -> None:
    schema = _load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    example = _load_yaml(EXAMPLE_PATH)

    r2 = copy.deepcopy(example)
    r2["metadata"]["risk_tier"] = "R2"
    with pytest.raises(ValidationError):
        validator.validate(r2)

    r2["evidence"]["minimum_tier"] = "L2"
    r2["evidence"]["approval_policy"]["minimum_approvers"] = 1
    validator.validate(r2)

    r3 = copy.deepcopy(r2)
    r3["metadata"]["risk_tier"] = "R3"
    r3["evidence"]["minimum_tier"] = "L3"
    with pytest.raises(ValidationError):
        validator.validate(r3)

    r3["evidence"]["approval_policy"]["minimum_approvers"] = 2
    r3["evidence"]["approval_policy"]["separation_of_duties"] = True
    validator.validate(r3)


def test_r0_contract_is_public_read_only_without_egress_or_delegation() -> None:
    schema = _load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    example = _load_yaml(EXAMPLE_PATH)
    example["metadata"]["risk_tier"] = "R0"
    example["data"]["max_classification"] = "public"
    validator.validate(example)

    example["requirements"]["tools"].append(
        {
            "capability": "tool:workspace-write",
            "required": True,
            "access": "write",
            "approval": "always",
        }
    )
    example["runtime"]["workspace_access"] = "workspace-write"
    example["permissions"]["workspace"]["write"] = ["src/**"]
    with pytest.raises(ValidationError):
        validator.validate(example)


def test_mcp_tools_carry_operation_level_access_and_approval() -> None:
    schema = _load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    example = _load_yaml(EXAMPLE_PATH)
    example["requirements"]["mcp"] = [
        {
            "registry_ref": "mcp:source-control",
            "required": True,
            "tools": [
                {
                    "capability": "tool:create-pull-request",
                    "required": True,
                    "access": "external-side-effect",
                    "approval": "on-external-side-effect",
                }
            ],
        }
    ]

    with pytest.raises(ValidationError):
        validator.validate(example)

    example["permissions"]["external_side_effects"] = "approval-required"
    example["runtime"]["budgets"]["max_external_side_effects"] = 1
    example["evidence"]["approval_policy"]["minimum_approvers"] = 1
    validator.validate(example)


def test_capability_matrix_has_complete_strict_client_coverage() -> None:
    matrix = _load_yaml(MATRIX_PATH)
    policy = matrix["policy"]
    capabilities = matrix["capabilities"]
    clients = matrix["clients"]

    capability_ids = [item["id"] for item in capabilities]
    assert len(capability_ids) == len(set(capability_ids))
    assert {client["id"] for client in clients} == {
        "claude-code",
        "codex",
        "cursor",
        "github-copilot-vscode",
    }

    allowed_statuses = set(policy["support_values"])
    allowed_projections = set(policy["projection_values"])
    allowed_maturity = set(policy["maturity_values"])
    allowed_lifecycle = set(policy["lifecycle_values"])
    allowed_strategies = set(policy["adapter_strategy_values"])
    allowed_lossiness = set(policy["lossiness_values"])
    source_ids = set(matrix["sources"])

    assert policy["manifest_capability_bindings"] == {
        "mission.instructions_ref": "custom-agents",
        "requirements.policies": "permission-policy",
        "requirements.rules": "project-instructions",
        "requirements.skills": "agent-skills",
        "requirements.commands": "reusable-commands",
        "requirements.hook_intents": "lifecycle-hooks",
        "requirements.mcp": "mcp-tools",
        "delegation": "custom-agents",
        "permissions": "permission-policy",
    }

    for client in clients:
        mappings = client["mappings"]
        if client["adapter"]["client_version_range"] == "unverified":
            assert all(mapping["volatile"] is True for mapping in client["mappings"])
        mapped_ids = [mapping["capability"] for mapping in mappings]
        assert mapped_ids == capability_ids
        assert len(mapped_ids) == len(set(mapped_ids))

        for mapping in mappings:
            assert mapping["applies_to_surfaces"]
            assert set(mapping["applies_to_surfaces"]) <= set(client["surfaces"])
            assert mapping["status"] in allowed_statuses
            assert mapping["projection"] in allowed_projections
            assert mapping["maturity"] in allowed_maturity
            assert mapping["lifecycle"] in allowed_lifecycle
            assert mapping["adapter_strategy"] in allowed_strategies
            assert mapping["lossiness"] in allowed_lossiness
            assert mapping["source_ids"]
            assert set(mapping["source_ids"]) <= source_ids

            if mapping["status"] == "supported":
                assert mapping["projection"] != "none"
                assert mapping["lossiness"] == "none"
            elif mapping["status"] == "degraded":
                assert mapping["limitations"]
                assert mapping["lossiness"] in {"bounded", "material"}
            else:
                assert mapping["projection"] == "none"
                assert mapping["adapter_strategy"] == "omit"

            if mapping["maturity"] in {"preview", "beta", "experimental"}:
                assert mapping["volatile"] is True
            if mapping["maturity"] == "unspecified":
                assert mapping["volatile"] is True
            if mapping["lifecycle"] in {"legacy", "deprecated"}:
                assert mapping["volatile"] is True

    used_source_ids = {
        source_id
        for client in clients
        for mapping in client["mappings"]
        for source_id in mapping["source_ids"]
    }
    assert used_source_ids == source_ids


def test_matrix_is_dated_primary_source_research_not_runtime_acceptance() -> None:
    matrix = _load_yaml(MATRIX_PATH)
    as_of = matrix["as_of"]
    allowed_hosts = {
        "code.claude.com",
        "code.visualstudio.com",
        "cursor.com",
        "learn.chatgpt.com",
    }

    assert as_of == "2026-08-18"
    assert matrix["status"] == "research"
    for source in matrix["sources"].values():
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https"
        assert parsed.hostname in allowed_hosts
        assert source["retrieved_at"] == as_of

    for client in matrix["clients"]:
        assert client["admission"]["state"] == "research"
        assert client["conformance"] == {
            "status": "not_run",
            "runtime_version": None,
            "model_profile_digest": None,
            "projection_digest": None,
            "test_run_id": None,
        }
        assert all(mapping["conformance_status"] == "not_run" for mapping in client["mappings"])


def test_standards_crosswalk_is_traceable_and_makes_no_conformance_claim() -> None:
    crosswalk = _load_yaml(CROSSWALK_PATH)
    boundary = crosswalk["claim_boundary"]

    assert crosswalk["kind"] == "AgentPlatformStandardsCrosswalk"
    assert crosswalk["as_of"] == "2026-08-18"
    assert crosswalk["status"] == "design-mapping"
    assert boundary["certification_claimed"] is False
    assert boundary["conformance_claimed"] is False
    assert boundary["mapping_completeness"] == "partial"

    expected_fields = {
        "id",
        "authority",
        "requirement_ids",
        "enforcement_points",
        "evidence",
        "accountable_role",
        "implementation_status",
        "assessment_status",
    }
    identifiers: list[str] = []
    for entry in crosswalk["entries"]:
        assert set(entry) == expected_fields
        identifiers.append(entry["id"])
        authority = entry["authority"]
        assert authority["control_refs"]
        assert authority["mapping_completeness"]
        assert urlparse(authority["url"]).scheme == "https"
        assert entry["requirement_ids"]
        assert all(
            re.fullmatch(r"Requirement (?:[1-9]|1[0-6])", requirement)
            for requirement in entry["requirement_ids"]
        )
        assert entry["enforcement_points"]
        assert entry["evidence"]
        assert entry["accountable_role"]
        assert entry["implementation_status"] == "proposed"
        assert entry["assessment_status"] == "not_assessed"
    assert len(identifiers) == len(set(identifiers))


def test_owner_decisions_are_accepted_resolved_and_traceable() -> None:
    prd = (PRD_DIR / "PRD.md").read_text(encoding="utf-8")
    normalized_prd = " ".join(prd.split())
    matches = re.findall(
        r"### Decision (1[4-8]) —[^\n]+\n(.*?)(?=\n### Decision|\n## Resolved questions)",
        prd,
        flags=re.DOTALL,
    )

    assert [number for number, _section in matches] == ["14", "15", "16", "17", "18"]
    assert "Owner decision status: Accepted" in prd
    assert "source snapshot was rechecked on 2026-08-18" in prd
    open_questions = prd.partition("## Resolved questions\n")[2].partition(
        "\n## Acceptance criteria"
    )[0]
    question_matches = re.findall(
        r"Open Question ([1-5]): (.*?)(?=\nOpen Question|\Z)",
        open_questions,
        flags=re.DOTALL,
    )
    assert [number for number, _section in question_matches] == ["1", "2", "3", "4", "5"]
    for decision_number, section in matches:
        question_number = str(int(decision_number) - 13)
        assert f"Resolves Open Question {question_number}" in section
        for field in (
            "Recommendation:",
            "Scope:",
            "Accountable owner:",
            "Required reviewers:",
            "Owner-review inputs:",
            "Required post-acceptance delivery/admission evidence:",
            "Residual risk:",
            "Owner disposition: Accepted",
            "Owner acceptance date: 2026-08-18",
        ):
            assert field in section
        question_section = dict(question_matches)[question_number]
        normalized_question = " ".join(question_section.split())
        assert f"Resolution: Decision {decision_number}." in normalized_question
        assert "Status: Resolved — Accepted." in normalized_question

    assert prd.count("Owner disposition: Accepted") == 5
    assert "A pre-release or alpha client is research-only and cannot be admitted" in prd
    assert re.search(
        r"effective parent\s+and live sandbox/approval/permission/session overrides", prd
    )
    assert "there is no automatic or in-session privilege elevation" in prd
    assert "reserves a tamper-evident audit record or writes a sealed local outbox" in prd
    assert "logical `Agent Control Registry`" in prd
    assert "Never credit a client-native hook as a preventive authorization control" in prd
    assert "`P90D` for R0, `P30D` for R1, `P14D` for" in prd
    assert re.search(r"This\s+pilot does not admit R3 direct execution", prd)
    assert "PRD acceptance admits no exact tuple." in normalized_prd
    assert "post-acceptance, schema-validated candidate manifest" in normalized_prd
    assert "stable Codex candidate exists, its cohort slot remains empty and fails closed" in (
        normalized_prd
    )
    assert "Agent tool and workload egress are denied; hosted inference transport" in normalized_prd
    assert "test-only post-acceptance conformance fixture" in normalized_prd
    assert "isolated conformance harness may materialize its candidate projection" in normalized_prd
    assert "ephemeral workspace's documented discovery path, such as `.codex/agents/*.toml`" in (
        normalized_prd
    )
    assert (
        "policy/design acceptance authorizes implementation; it does not assert completed delivery"
        in normalized_prd
    )
    assert "Requirements 4, 12, and 13" in normalized_prd
    assert "Decisions 3 and 6, Requirements 3, 12, and 14" in normalized_prd
    assert "signed revocation-state object" in normalized_prd
    assert "revocation-state digest, epoch, `checked_at`, and `next_update`" in normalized_prd


def test_accepted_spec_authorizes_plan_but_not_runtime_admission() -> None:
    prd = (PRD_DIR / "PRD.md").read_text(encoding="utf-8")
    plan = (PRD_DIR / "plan.md").read_text(encoding="utf-8")
    tasks = (PRD_DIR / "tasks.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "specs" / "agent-platform" / "roadmap.md").read_text(encoding="utf-8")
    source_register = (ROOT / "docs" / "evidence" / "kaynak-dogrulama-kaydi.md").read_text(
        encoding="utf-8"
    )

    assert _document_status(prd) == "Accepted"
    assert _document_status(roadmap) == "Draft"
    assert "Document version: 1.1.0" in prd
    assert "Acceptance date: 2026-08-20" in prd
    assert "Requirement 22:" in prd
    for number in range(23, 28):
        assert f"Requirement {number}:" in prd
    assert "Owner decision status: Accepted" in prd
    assert "- [x] The accountable owner marks this PRD `Status: Accepted`" in prd
    assert "PRD acceptance and adapter generation do not admit an exact tuple" in " ".join(
        prd.split()
    )
    assert "001-vendor-neutral-agent-contract/PRD.md" in roadmap
    roadmap_row = re.search(
        r"^\| 001 \| Vendor-neutral agent contract \| \[PRD\]"
        r"\(PRDs/001-vendor-neutral-agent-contract/PRD\.md\) \| (Draft|Accepted) \|$",
        roadmap,
        flags=re.MULTILINE,
    )
    assert roadmap_row is not None
    assert roadmap_row.group(1) == "Accepted"
    assert "Status: Active" in plan
    assert "Status: Active — L1 implementation complete; L2/L3 work remains" in tasks
    for task_id, title in (
        ("T01", "Record specification acceptance."),
        ("T06", "Integrate renderer and CLI operation boundary."),
        ("T07", "Implement safe activation and owned stale cleanup."),
        ("T09", "Implement registry/candidate/admission verifier interfaces."),
        ("T10", "Implement deterministic governed-review aggregator."),
        ("T14", "Update support and evidence documentation."),
        ("T15", "Run exact stable Codex R0 conformance."),
        ("T16", "Run exact stable Claude Code R1 conformance."),
        ("T17", "Issue time-bound owner admission receipts and done report."),
    ):
        assert f"- [x] **{task_id} — {title}**" in tasks
    for task_id, title in (
        ("T12", "Complete security, native-syntax, drift, rollback, and packaging tests."),
    ):
        assert f"- [ ] **{task_id} — {title}**" in tasks
        assert f"- **{task_id}:**" in tasks
    assert "Last checked / Son kontrol: **2026-08-20**" in source_register
    assert (
        "Client projection format sources checked / "
        "İstemci projection format kaynakları kontrolü:\n"
        "**2026-08-18**" in source_register
    )
    assert "Owner-review decision sources checked / Owner-review karar kaynakları kontrolü:" in (
        source_register
    )
    assert "**2026-08-18**" in source_register
    assert "agent-platform/client-capabilities.yml" in source_register
    assert "agent-platform/standards-crosswalk.yml" in source_register


def test_agent_platform_local_markdown_links_resolve() -> None:
    markdown_files = sorted((ROOT / "specs" / "agent-platform").rglob("*.md")) + [
        PLATFORM / "README.md",
    ]
    failures: list[str] = []
    for path in markdown_files:
        body = path.read_text(encoding="utf-8")
        for match in re.finditer(r"(?<!!)\[[^]]+\]\(([^)]+)\)", body):
            target = match.group(1).split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                failures.append(f"{path.relative_to(ROOT)} -> {target}")
    assert failures == []
