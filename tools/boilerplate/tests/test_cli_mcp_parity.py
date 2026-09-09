"""Byte-level parity between every CLI command and its local operation entry point."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

import kt_scaffold.operations as operations_module
from kt_scaffold.cli import main, stable_json
from kt_scaffold.models import Answers
from kt_scaffold.project import project_init

GATE_OUTPUT = """\
KT_GATE_STEP name=configuration status=started
KT_GATE_STEP name=configuration status=passed
KT_GATE_STEP name=configuration-sync status=started
KT_GATE_STEP name=configuration-sync status=passed
KT_GATE_SCOPE scope=all postgres_integration=required database_mode=disposable-test
KT_GATE_STEP name=database-test-create status=started
KT_GATE_STEP name=database-test-create status=passed
KT_GATE_STEP name=database-migrations-apply status=started
KT_GATE_STEP name=database-migrations-apply status=passed
KT_GATE_STEP name=backend-static status=started
KT_GATE_STEP name=backend-static status=passed
KT_GATE_STEP name=backend-tests status=started
KT_GATE_TESTS name=backend-tests runner=pytest total=7 passed=7 failed=0 skipped=0
KT_GATE_STEP name=backend-tests status=passed
KT_GATE_STEP name=database-validate status=started
KT_GATE_STEP name=database-validate status=passed
KT_GATE_STEP name=openapi-contract status=started
KT_GATE_STEP name=openapi-contract status=passed
KT_GATE_STEP name=frontend-static status=started
KT_GATE_STEP name=frontend-static status=passed
KT_GATE_STEP name=frontend-tests status=started
KT_GATE_TESTS name=frontend-tests runner=vitest total=5 passed=5 failed=0 skipped=0
KT_GATE_STEP name=frontend-tests status=passed
KT_GATE_STEP name=frontend-types-contract status=started
KT_GATE_STEP name=frontend-types-contract status=passed
KT_GATE_STEP name=governance-drift status=started
KT_GATE_STEP name=governance-drift status=passed
KT_GATE_STEP name=charts-render status=started
KT_GATE_STEP name=charts-render status=passed
KT_GATE_STEP name=database-test-drop status=started
KT_GATE_STEP name=database-test-drop status=passed
KT_GATE_STEP name=browser-readiness status=started
KT_GATE_STEP name=browser-readiness status=passed
KT_GATE_STEP name=browser-scenarios status=started
KT_GATE_TESTS name=browser-scenarios runner=playwright total=2 passed=2 failed=0 skipped=0
KT_GATE_STEP name=browser-scenarios status=passed
quality gate passed: all (python-fastapi)
"""


def _tree_contents(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _accept_spec(root: Path, relative: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("Status: Draft", "Status: Accepted", 1), encoding="utf-8")


def test_cli_parity_for_all_local_applicator_operations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Equivalent CLI and local operation calls return identical results and trees."""

    cli_root = tmp_path / "cli-project"
    mcp_root = tmp_path / "mcp-project"
    observed_gate_commands: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cwd = Path(str(kwargs["cwd"]))
        observed_gate_commands.append((command, cwd))
        return subprocess.CompletedProcess(command, 0, stdout=GATE_OUTPUT, stderr="")

    monkeypatch.setattr(operations_module.subprocess, "run", fake_run)
    compared: list[str] = []

    def assert_parity(
        operation: str,
        cli_arguments: list[str],
        mcp_call: Callable[[], dict[str, object]],
    ) -> dict[str, object]:
        exit_code = main(cli_arguments)
        captured = capsys.readouterr()
        assert exit_code == 0, f"{operation}: {captured.out}{captured.err}"
        assert captured.err == "", f"{operation}: unexpected CLI stderr"

        mcp_result = mcp_call()
        cli_bytes = captured.out.encode("utf-8")
        mcp_bytes = stable_json(mcp_result).encode("utf-8")
        assert cli_bytes == mcp_bytes, f"{operation}: CLI and MCP envelopes differ"

        payload = json.loads(cli_bytes)
        assert {"ok", "changes", "warnings", "next_steps"} <= payload.keys()
        assert payload["ok"] is True
        assert _tree_contents(cli_root) == _tree_contents(mcp_root), (
            f"{operation}: CLI and MCP mutations differ"
        )
        compared.append(operation)
        return payload

    intent = "Audit internal payment controls with deterministic, offline evidence."
    init_cli = [
        "init",
        "--target-dir",
        str(cli_root),
        "--intent",
        intent,
        "--primary-domain",
        "payments",
        "--product-name",
        "Parity Control Surface",
        "--product-slug",
        "parity-ledger",
        "--env-prefix",
        "ZZCLIMCP_",
        "--api-prefix",
        "/api/parity-ledger/v1",
        "--tenant-header",
        "x-bank-tenant-id",
        "--locales",
        "tr,en",
        "--no-observability",
    ]
    assert_parity(
        "project_init",
        init_cli,
        lambda: operations_module.init_operation(
            target_dir=str(mcp_root),
            project_intent=intent,
            primary_domain="payments",
            product_name="Parity Control Surface",
            product_slug="parity-ledger",
            env_prefix="ZZCLIMCP_",
            api_prefix="/api/parity-ledger/v1",
            tenant_header="x-bank-tenant-id",
            locales=["tr", "en"],
            observability=False,
        ),
    )

    updated_name = "Parity Control Surface v2"
    assert_parity(
        "scaffold_update",
        [
            "update",
            "--target-dir",
            str(cli_root),
            "--set",
            f"product_name={updated_name}",
        ],
        lambda: operations_module.update_operation(
            target_dir=str(mcp_root),
            answer_overrides={"product_name": updated_name},
        ),
    )

    assert_parity(
        "rules_list",
        ["rules", "--target-dir", str(cli_root), "--scope", "governance"],
        lambda: operations_module.rules_list_operation(
            target_dir=str(mcp_root), scope="governance"
        ),
    )
    rule_ids = ["00-project-overview", "10-spec-first"]
    assert_parity(
        "rules_get",
        ["rule", "--target-dir", str(cli_root), *rule_ids],
        lambda: operations_module.rules_get_operation(ids=rule_ids, target_dir=str(mcp_root)),
    )
    render_result = assert_parity(
        "clients_render",
        [
            "render",
            "--target-dir",
            str(cli_root),
            "--client",
            "codex",
            "--agent-client",
            "codex",
            "--agent-client",
            "cursor",
            "--mode",
            "write",
        ],
        lambda: operations_module.clients_render_operation(
            target_dir=str(mcp_root),
            clients=["codex"],
            agent_clients=["codex", "cursor"],
            mode="write",
        ),
    )
    projection = render_result["agent_projection"]
    assert isinstance(projection, dict)
    assert projection["artifact_count"] == 8
    lock = json.loads(
        (cli_root / ".kt-scaffold/agent-projections/PROJECTIONS.lock.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(lock["artifacts"]) == 8
    assert {item["client_id"] for item in lock["artifacts"]} == {"codex", "cursor"}

    spec_result = assert_parity(
        "spec_new",
        [
            "spec",
            "--target-dir",
            str(cli_root),
            "--domain",
            "payments",
            "--capability",
            "payment-review",
            "--intent",
            "Let authorized reviewers inspect payment decisions.",
            "--mode",
            "comprehensive",
        ],
        lambda: operations_module.spec_new_operation(
            domain="payments",
            capability="payment-review",
            intent="Let authorized reviewers inspect payment decisions.",
            mode="comprehensive",
            target_dir=str(mcp_root),
        ),
    )
    spec_path = str(spec_result["spec_path"])
    _accept_spec(cli_root, spec_path)
    _accept_spec(mcp_root, spec_path)
    assert _tree_contents(cli_root) == _tree_contents(mcp_root)

    assert_parity(
        "backend_domain_new",
        [
            "domain",
            "--target-dir",
            str(cli_root),
            "--spec-path",
            spec_path,
            "--tenant-scoped",
            "--permission",
            "read=payment_review:read",
        ],
        lambda: operations_module.backend_domain_new_operation(
            spec_path=spec_path,
            tenant_scoped=True,
            permissions={"read": "payment_review:read"},
            target_dir=str(mcp_root),
        ),
    )
    assert_parity(
        "frontend_page_new",
        [
            "page",
            "--target-dir",
            str(cli_root),
            "--spec-path",
            spec_path,
            "--page",
            "payment-review",
            "--route",
            "/payment-review",
            "--permission",
            "payment_review:read",
        ],
        lambda: operations_module.frontend_page_new_operation(
            spec_path=spec_path,
            page="payment-review",
            route="/payment-review",
            permission="payment_review:read",
            target_dir=str(mcp_root),
        ),
    )
    change_summary = "Add the accepted payment-review persistence authority."
    assert_parity(
        "schema_change_prepare",
        [
            "schema",
            "--target-dir",
            str(cli_root),
            "--spec-path",
            spec_path,
            "--change-summary",
            change_summary,
            "--migration-name",
            "payment-review",
        ],
        lambda: operations_module.schema_change_prepare_operation(
            spec_path=spec_path,
            change_summary=change_summary,
            migration_name="payment-review",
            target_dir=str(mcp_root),
        ),
    )
    assert_parity(
        "quality_gate",
        [
            "gate",
            "--target-dir",
            str(cli_root),
            "--scope",
            "all",
            "--include-browser",
            "--allow-project-code-execution",
        ],
        lambda: operations_module.quality_gate_operation(
            allow_project_code_execution=True,
            scope="all",
            include_browser=True,
            target_dir=str(mcp_root),
        ),
    )
    assert_parity(
        "browser_scenario_new",
        [
            "scenario",
            "--target-dir",
            str(cli_root),
            "--spec-path",
            spec_path,
            "--suite",
            "payments",
            "--scenario-title",
            "Review payment",
            "--acceptance-point",
            "An authorized reviewer sees the payment decision.",
        ],
        lambda: operations_module.browser_scenario_new_operation(
            spec_path=spec_path,
            suite="payments",
            scenario_title="Review payment",
            acceptance_points=["An authorized reviewer sees the payment decision."],
            target_dir=str(mcp_root),
        ),
    )
    assert_parity(
        "done_report",
        [
            "done",
            "--target-dir",
            str(cli_root),
            "--change-summary",
            "Payment-review walking skeleton",
            "--claimed-tier",
            "L2",
        ],
        lambda: operations_module.done_report_operation(
            change_summary="Payment-review walking skeleton",
            claimed_tier="L2",
            target_dir=str(mcp_root),
        ),
    )

    assert compared == [
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
    ]
    assert observed_gate_commands == [
        (
            [str(cli_root / "scripts/quality-gate.sh"), "all", "--include-browser"],
            cli_root.resolve(),
        ),
        (
            [str(mcp_root / "scripts/quality-gate.sh"), "all", "--include-browser"],
            mcp_root.resolve(),
        ),
    ]


def test_cli_rejects_unknown_agent_client_before_dispatch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["render", "--agent-client", "unknown-client"])

    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--agent-client" in captured.err
    assert "invalid choice: 'unknown-client'" in captured.err


def test_projection_conflict_is_a_failed_operation_and_cli_result(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli_root = tmp_path / "cli-project"
    operation_root = tmp_path / "operation-project"
    answers = answers_factory()
    project_init(cli_root, answers)
    project_init(operation_root, answers)
    relative = ".kt-scaffold/agent-projections/.codex/agents/code-review.toml"
    lock_relative = ".kt-scaffold/agent-projections/PROJECTIONS.lock.json"

    for root in (cli_root, operation_root):
        projection = root / relative
        projection.write_text(
            projection.read_text(encoding="utf-8") + "edited outside the compiler\n",
            encoding="utf-8",
        )
    expected_lock = (cli_root / lock_relative).read_bytes()

    exit_code = main(["render", "--target-dir", str(cli_root), "--mode", "write"])
    captured = capsys.readouterr()
    operation_result = operations_module.clients_render_operation(
        target_dir=str(operation_root),
        mode="write",
    )

    assert exit_code == 1
    assert captured.err == ""
    assert captured.out == stable_json(operation_result)
    assert operation_result["ok"] is False
    assert operation_result["lock_updated"] is False
    assert {"path": relative, "action": "conflict"} in operation_result["changes"]
    assert (cli_root / lock_relative).read_bytes() == expected_lock
    assert (operation_root / lock_relative).read_bytes() == expected_lock
    assert _tree_contents(cli_root) == _tree_contents(operation_root)
