"""Local operation and MCP knowledge-plane boundaries plus spec-first generation."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

import kt_scaffold.operations as operations_module
from kt_scaffold.cli import CLI_ALIASES, build_parser
from kt_scaffold.mcp_surfaces import (
    GOVERNANCE_TOOL_ALIASES,
    LOCAL_PROMPT_ALIASES,
    LOCAL_TOOL_ALIASES,
    build_governance_server,
    build_local_server,
)
from kt_scaffold.models import Answers
from kt_scaffold.operations import (
    backend_domain_new_operation,
    browser_scenario_new_operation,
    clients_render_operation,
    done_report_operation,
    frontend_page_new_operation,
    init_operation,
    quality_gate_operation,
    rules_get_operation,
    rules_list_operation,
    schema_change_prepare_operation,
    spec_new_operation,
    update_operation,
)
from kt_scaffold.render import COMMANDS
from kt_scaffold.report import validate_report

EXPECTED_TOOLS = {
    "project_init",
    "scaffold_update",
    "rules_list",
    "rules_get",
    "clients_render",
    "spec_new",
    "backend_domain_new",
    "frontend_page_new",
    "schema_change_prepare",
    "quality_gate",
    "browser_scenario_new",
    "done_report",
}
EXPECTED_LOCAL_MCP_TOOLS = {
    "project_blueprint",
    "project_create",
    "governance_catalog",
    "governance_artifacts_get",
    "governance_update_check",
    "reconciliation_validate",
    "proje_plani",
    "proje_olustur",
    "yonetisim_katalogu",
    "yonetisim_ogelerini_getir",
    "yonetisim_guncellemelerini_kontrol_et",
    "uyumlastirmayi_dogrula",
}
EXPECTED_GOVERNANCE_MCP_TOOLS = EXPECTED_LOCAL_MCP_TOOLS - {
    "project_create",
    "proje_olustur",
}
EXPECTED_MCP_PROMPTS = {"project_start", "proje_baslat"}


def _successful_gate_output(scope: str, *, browser: bool) -> str:
    steps = {
        "backend": [
            "configuration",
            "configuration-sync",
            "backend-static",
            "backend-tests",
            "database-validate",
            "openapi-contract",
        ],
        "frontend": [
            "configuration",
            "frontend-static",
            "frontend-tests",
            "frontend-types-contract",
        ],
        "all": [
            "configuration",
            "configuration-sync",
            "database-test-create",
            "database-migrations-apply",
            "backend-static",
            "backend-tests",
            "database-validate",
            "openapi-contract",
            "frontend-static",
            "frontend-tests",
            "frontend-types-contract",
            "governance-drift",
            "charts-render",
            "database-test-drop",
        ],
    }[scope]
    if browser:
        steps.extend(["browser-readiness", "browser-scenarios"])
    lines = [
        f"KT_GATE_SCOPE scope={scope} postgres_integration=required database_mode=disposable-test"
    ]
    test_markers = {
        "backend-tests": (
            "KT_GATE_TESTS name=backend-tests runner=pytest total=7 passed=7 failed=0 skipped=0"
        ),
        "frontend-tests": (
            "KT_GATE_TESTS name=frontend-tests runner=vitest total=5 passed=5 failed=0 skipped=0"
        ),
        "browser-scenarios": (
            "KT_GATE_TESTS name=browser-scenarios runner=playwright "
            "total=2 passed=2 failed=0 skipped=0"
        ),
    }
    for step in steps:
        lines.append(f"KT_GATE_STEP name={step} status=started")
        if step in test_markers:
            lines.append(test_markers[step])
        lines.append(f"KT_GATE_STEP name={step} status=passed")
    return "\n".join(lines) + "\n"


def _accept_spec(root: Path, relative: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("Status: Draft", "Status: Accepted", 1), encoding="utf-8")


def test_trusted_local_and_http_governance_mcp_have_distinct_authority(tmp_path: Path) -> None:
    command_names = {command.name for command in COMMANDS}
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    local = build_local_server(workspace)
    governance = build_governance_server()
    local_names = set(local._tool_manager._tools)  # noqa: SLF001 - contract inspection
    governance_names = set(governance._tool_manager._tools)  # noqa: SLF001
    parser = build_parser()
    subparser_action = next(
        action
        for action in parser._actions
        if action.dest == "command"  # noqa: SLF001
    )
    cli_names = set(subparser_action.choices) - {"mcp", "mbp"}  # type: ignore[attr-defined]

    assert command_names == EXPECTED_TOOLS
    assert local_names == EXPECTED_LOCAL_MCP_TOOLS
    assert governance_names == EXPECTED_GOVERNANCE_MCP_TOOLS
    assert set(LOCAL_TOOL_ALIASES) | set(LOCAL_TOOL_ALIASES.values()) == local_names
    assert set(GOVERNANCE_TOOL_ALIASES) | set(GOVERNANCE_TOOL_ALIASES.values()) == governance_names
    prompt_names = set(local._prompt_manager._prompts)  # noqa: SLF001 - contract inspection
    assert prompt_names == EXPECTED_MCP_PROMPTS
    assert set(LOCAL_PROMPT_ALIASES) | set(LOCAL_PROMPT_ALIASES.values()) == prompt_names
    assert not governance._prompt_manager._prompts  # noqa: SLF001
    assert cli_names == (
        {command.cli for command in COMMANDS} | (set(CLI_ALIASES) - {"mbp"}) | {"apply-bundle"}
    )
    assert len(COMMANDS) == 12


def test_render_cli_keeps_governance_and_agent_platform_selectors_disjoint() -> None:
    namespace = build_parser().parse_args(
        [
            "render",
            "--client",
            "codex",
            "--agent-client",
            "claude-code",
            "--agent-client",
            "github-copilot-vscode",
        ]
    )

    assert namespace.clients == ["codex"]
    assert namespace.agent_clients == ["claude-code", "github-copilot-vscode"]


@pytest.mark.parametrize(
    "operation",
    [
        lambda root, spec: backend_domain_new_operation(spec, target_dir=str(root)),
        lambda root, spec: frontend_page_new_operation(
            spec,
            page="payment-review",
            route="/payment-review",
            target_dir=str(root),
        ),
        lambda root, spec: schema_change_prepare_operation(
            spec,
            change_summary="Add the accepted payment review authority.",
            migration_name="payment-review",
            target_dir=str(root),
        ),
        lambda root, spec: browser_scenario_new_operation(
            spec,
            suite="payments",
            scenario_title="Review payment",
            acceptance_points=["An authorized reviewer sees the payment."],
            target_dir=str(root),
        ),
    ],
)
def test_spec_required_business_generators_refuse_draft_specs(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    operation: Callable[[Path, str], dict[str, object]],
) -> None:
    target = tmp_path / "project"
    init_operation(str(target), **answers_factory().model_dump(mode="json"))
    created = spec_new_operation(
        domain="payments",
        capability="payment-review",
        intent="Allow authorized reviewers to inspect a payment decision.",
        target_dir=str(target),
    )
    spec_path = str(created["spec_path"])

    with pytest.raises(ValueError, match="Status is Accepted"):
        operation(target, spec_path)


def test_spec_and_frontend_inputs_reject_empty_or_code_injection_values(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    init_operation(str(target), **answers_factory().model_dump(mode="json"))

    with pytest.raises(ValueError, match="intent is required"):
        spec_new_operation(
            domain="payments",
            capability="payment-review",
            intent="   ",
            target_dir=str(target),
        )

    created = spec_new_operation(
        domain="payments",
        capability="payment-review",
        intent="Review a payment decision.",
        target_dir=str(target),
    )
    spec_path = str(created["spec_path"])
    _accept_spec(target, spec_path)

    with pytest.raises(ValueError, match="absolute lowercase"):
        frontend_page_new_operation(
            spec_path,
            page="payment-review",
            route='/payment-review" element={<Injected />}',
            target_dir=str(target),
        )
    with pytest.raises(ValueError, match="resource:action"):
        frontend_page_new_operation(
            spec_path,
            page="payment-review",
            route="/payment-review",
            permission='payment_review:read" />',
            target_dir=str(target),
        )


def test_accepted_spec_drives_profile_native_schema_preparation(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    answers = answers_factory()
    init_operation(str(target), **answers.model_dump(mode="json"))
    created = spec_new_operation(
        domain="payments",
        capability="payment-review",
        intent="Allow authorized reviewers to inspect a payment decision.",
        target_dir=str(target),
    )
    spec_path = str(created["spec_path"])
    _accept_spec(target, spec_path)

    result = schema_change_prepare_operation(
        spec_path,
        change_summary="Add payment review persistence fields to the desired state.",
        migration_name="payment-review",
        target_dir=str(target),
    )
    profile = yaml.safe_load((target / "schema/profile.yml").read_text(encoding="utf-8"))

    assert result["ok"] is True
    expected_authority = "app/backend/app/domain/models"
    assert result["schema_authority_files"] == [expected_authority]
    assert profile["schema_authority"] == expected_authority
    assert result["generated_migration"] is None
    assert result["warnings"]


def test_domain_generator_updates_authority_and_registries_idempotently(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    answers = answers_factory()
    init_operation(str(target), **answers.model_dump(mode="json"))

    for capability in ("payment-review", "payment-release"):
        created = spec_new_operation(
            domain="payments",
            capability=capability,
            intent=f"Deliver the accepted {capability} behavior inside the active tenant.",
            target_dir=str(target),
        )
        spec_path = str(created["spec_path"])
        _accept_spec(target, spec_path)
        first = backend_domain_new_operation(spec_path, target_dir=str(target))
        second = backend_domain_new_operation(spec_path, target_dir=str(target))
        assert first["ok"] is True
        assert second["ok"] is True
        assert all(change["action"] == "skip" for change in second["changes"])

    registry = (target / "app/backend/app/domain/models/__init__.py").read_text()
    base = (target / "app/backend/app/db/base.py").read_text()
    router = (target / "app/backend/app/api/router.py").read_text()
    assert registry.count("PaymentReview") == 2
    assert registry.count("PaymentRelease") == 2
    assert base.count("PaymentReview") == 1
    assert base.count("PaymentRelease") == 1
    assert router.count("payment_review_router") == 2
    assert router.count("payment_release_router") == 2


def test_all_operations_execute_with_no_vcs_commands(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_commands: list[list[str]] = []

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        observed_commands.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=_successful_gate_output("all", browser=True),
            stderr="",
        )

    monkeypatch.setattr(operations_module.subprocess, "run", fake_run)
    target = tmp_path / "project"
    init_result = init_operation(
        str(target),
        **answers_factory(locales=["tr", "en"]).model_dump(mode="json"),
    )
    update_result = update_operation(str(target))
    listed = rules_list_operation(str(target))
    first_rule_id = str(listed["rules"][0]["id"])  # type: ignore[index]
    fetched = rules_get_operation([first_rule_id], str(target))
    rendered = clients_render_operation(str(target), mode="check")
    created = spec_new_operation(
        domain="payments",
        capability="payment-review",
        intent="Allow authorized reviewers to inspect a payment decision.",
        target_dir=str(target),
    )
    spec_path = str(created["spec_path"])
    _accept_spec(target, spec_path)
    domain = backend_domain_new_operation(spec_path, target_dir=str(target))
    page = frontend_page_new_operation(
        spec_path,
        page="payment-review",
        route="/payment-review",
        permission="payment_review:read",
        target_dir=str(target),
    )
    schema = schema_change_prepare_operation(
        spec_path,
        change_summary="Add payment review persistence fields.",
        migration_name="payment-review",
        target_dir=str(target),
    )
    scenario = browser_scenario_new_operation(
        spec_path,
        suite="payments",
        scenario_title="Review payment",
        acceptance_points=["Authorized reviewers see the review surface."],
        target_dir=str(target),
    )
    gate = quality_gate_operation(
        "all",
        include_browser=True,
        target_dir=str(target),
        allow_project_code_execution=True,
    )
    done = done_report_operation("Payment review skeleton", "L2", str(target))

    results = [
        init_result,
        update_result,
        listed,
        fetched,
        rendered,
        created,
        domain,
        page,
        schema,
        scenario,
        gate,
        done,
    ]
    assert len(results) == 12
    assert all(result["ok"] is True for result in results)
    assert observed_commands == [
        [str(target / "scripts/quality-gate.sh"), "all", "--include-browser"]
    ]
    assert all(command[0] not in {"git", "hg", "svn"} for command in observed_commands)
    assert validate_report(str(done["report_skeleton"]), locale="tr") == []

    evidence = json.loads((target / ".kt-scaffold/evidence.json").read_text(encoding="utf-8"))
    assert evidence["tier"] == "L2"
    assert evidence["counts"] == {"unit": 12, "browser": 2, "skipped": 0}
    assert done["tier_supported"] == "L2"

    assert (target / str(domain["files"][0])).exists()  # type: ignore[index]
    assert page["route_registered"] is True
    assert (target / str(scenario["scenario_path"])).is_file()
    assert scenario["runner_updated"] is True
    assert scenario["executable_assertions_required"] is True
    scenario_source = (target / str(scenario["scenario_path"])).read_text(encoding="utf-8")
    assert "throw new Error" in scenario_source
    assert "page.locator('main')" not in scenario_source
    assert (target / "e2e/payments/run-all.mjs").is_file()
    e2e_package = json.loads((target / "e2e/package.json").read_text(encoding="utf-8"))
    assert e2e_package["scripts"]["payments"] == "node payments/run-all.mjs"
    manifest = (target / "e2e/QUALITY_MANIFEST.md").read_text(encoding="utf-8")
    assert str(scenario["manifest_row"]) in manifest


def test_partial_quality_scope_never_claims_a_project_evidence_tier(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    init_operation(str(target), **answers_factory().model_dump(mode="json"))
    monkeypatch.setattr(
        operations_module.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command,
            0,
            _successful_gate_output("backend", browser=True),
            "",
        ),
    )

    result = quality_gate_operation(
        "backend",
        include_browser=True,
        target_dir=str(target),
        allow_project_code_execution=True,
    )

    assert result["ok"] is True
    assert result["tier_reached"] == "L0"
    evidence = json.loads((target / ".kt-scaffold/evidence.json").read_text(encoding="utf-8"))
    assert evidence["tier"] == "L0"
    assert evidence["browser"] is True


def test_quality_gate_requires_explicit_consent_before_project_code_execution(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    init_operation(str(target), **answers_factory().model_dump(mode="json"))

    def unexpected_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("untrusted project code was executed")

    monkeypatch.setattr(operations_module.subprocess, "run", unexpected_run)

    with pytest.raises(ValueError, match="allow_project_code_execution=true"):
        quality_gate_operation("all", target_dir=str(target))

    assert not (target / ".kt-scaffold/evidence.json").exists()


def test_quality_gate_rejects_a_modified_managed_script_before_execution(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    init_operation(str(target), **answers_factory().model_dump(mode="json"))
    gate = target / "scripts/quality-gate.sh"
    gate.write_text(gate.read_text(encoding="utf-8") + "\necho malicious\n", encoding="utf-8")

    def unexpected_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("modified project code was executed")

    monkeypatch.setattr(operations_module.subprocess, "run", unexpected_run)

    with pytest.raises(ValueError, match="differs from the scaffold manifest"):
        quality_gate_operation(
            "all",
            target_dir=str(target),
            allow_project_code_execution=True,
        )
