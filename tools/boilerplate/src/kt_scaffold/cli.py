"""Command-line front door for every deterministic scaffold operation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from kt_scaffold import __version__
from kt_scaffold.agent_platform.contracts import EXPECTED_CLIENT_IDS

CLI_ALIASES = {
    "baslat": "init",
    "guncelle": "update",
    "kurallar": "rules",
    "kural": "rule",
    "yansit": "render",
    "spesifikasyon": "spec",
    "alan": "domain",
    "sayfa": "page",
    "sema": "schema",
    "kalite-kapisi": "gate",
    "senaryo": "scenario",
    "tamamla": "done",
    "paketi-uygula": "apply-bundle",
    "mbp": "mcp",
}


def _common_target(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target-dir", default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kt-scaffold")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", aliases=["baslat"])
    init.add_argument("--target-dir", default=".")
    init.add_argument("--answers")
    init.add_argument("--intent", dest="project_intent", default=argparse.SUPPRESS)
    init.add_argument("--primary-domain", default=argparse.SUPPRESS)
    init.add_argument("--product-name", default=argparse.SUPPRESS)
    init.add_argument("--product-slug", default=argparse.SUPPRESS)
    init.add_argument("--env-prefix", default=argparse.SUPPRESS)
    init.add_argument("--api-prefix", default=argparse.SUPPRESS)
    init.add_argument("--tenant-header", default=argparse.SUPPRESS)
    init.add_argument("--locales", default=argparse.SUPPRESS)
    init.add_argument(
        "--observability",
        action=argparse.BooleanOptionalAction,
        default=argparse.SUPPRESS,
    )
    init.add_argument(
        "--agent-client",
        dest="agent_clients",
        action="append",
        choices=EXPECTED_CLIENT_IDS,
        default=argparse.SUPPRESS,
        help="repeat to persist the project's inert Agent Platform client set",
    )

    update = subparsers.add_parser("update", aliases=["guncelle"])
    _common_target(update)
    update.add_argument("--set", action="append", default=[])

    rules = subparsers.add_parser("rules", aliases=["kurallar"])
    _common_target(rules)
    rules.add_argument("--scope")
    rules.add_argument("--path", dest="applies_to_path")
    rules.add_argument("--trigger", choices=["always", "path-match", "on-demand"])

    rule = subparsers.add_parser("rule", aliases=["kural"])
    _common_target(rule)
    rule.add_argument("ids", nargs="+")

    render = subparsers.add_parser("render", aliases=["yansit"])
    _common_target(render)
    render.add_argument("--client", dest="clients", action="append")
    render.add_argument(
        "--agent-client",
        dest="agent_clients",
        action="append",
        choices=EXPECTED_CLIENT_IDS,
        help="repeat to select inert Agent Platform projection clients",
    )
    render.add_argument("--mode", choices=["write", "check"], default="write")

    spec = subparsers.add_parser("spec", aliases=["spesifikasyon"])
    _common_target(spec)
    spec.add_argument("--domain", required=True)
    spec.add_argument("--capability", required=True)
    spec.add_argument("--intent", required=True)
    spec.add_argument("--mode", choices=["lean", "comprehensive"], default="lean")

    domain = subparsers.add_parser("domain", aliases=["alan"])
    _common_target(domain)
    domain.add_argument("--spec-path", required=True)
    domain.add_argument("--tenant-scoped", action=argparse.BooleanOptionalAction, default=True)
    domain.add_argument("--permission", action="append", default=[])

    page = subparsers.add_parser("page", aliases=["sayfa"])
    _common_target(page)
    page.add_argument("--spec-path", required=True)
    page.add_argument("--page", required=True)
    page.add_argument("--route", required=True)
    page.add_argument("--permission")

    schema = subparsers.add_parser("schema", aliases=["sema"])
    _common_target(schema)
    schema.add_argument("--spec-path", required=True)
    schema.add_argument("--change-summary", required=True)
    schema.add_argument("--migration-name", required=True)

    gate = subparsers.add_parser("gate", aliases=["kalite-kapisi"])
    _common_target(gate)
    gate.add_argument("--scope", choices=["backend", "frontend", "all"], default="all")
    gate.add_argument("--include-browser", action="store_true")
    gate.add_argument(
        "--allow-project-code-execution",
        action="store_true",
        help="confirm that the target's project-owned gate scripts are trusted",
    )
    gate.add_argument("--phase", choices=["execute", "prepare", "finalize"], default="execute")
    gate.add_argument("--evidence-output")
    gate.add_argument("--exit-code", type=int)
    gate.add_argument("--challenge")

    scenario = subparsers.add_parser("scenario", aliases=["senaryo"])
    _common_target(scenario)
    scenario.add_argument("--spec-path", required=True)
    scenario.add_argument("--suite", required=True)
    scenario.add_argument("--scenario-title", required=True)
    scenario.add_argument("--acceptance-point", action="append", default=[])

    done = subparsers.add_parser("done", aliases=["tamamla"])
    _common_target(done)
    done.add_argument("--change-summary", required=True)
    done.add_argument("--claimed-tier", choices=["L0", "L1", "L2", "L3"], required=True)

    apply_bundle = subparsers.add_parser("apply-bundle", aliases=["paketi-uygula"])
    apply_bundle.add_argument("--archive", required=True)
    apply_bundle.add_argument("--descriptor", required=True)
    apply_bundle.add_argument("--target-dir", required=True)

    mcp = subparsers.add_parser("mcp", aliases=["mbp"])
    mcp.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
    )
    mcp.add_argument("--host", default="127.0.0.1")
    mcp.add_argument("--port", type=int, default=8000)
    mcp.add_argument("--path", default="/mcp")
    mcp.add_argument(
        "--workspace-root",
        default=None,
        help="enable trusted local stdio creation bound to this explicit workspace root",
    )
    return parser


def _pairs(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected key=value, got {value}")
        key, item = value.split("=", 1)
        result[key] = item
    return result


def _dispatch(namespace: argparse.Namespace) -> dict[str, object]:
    from kt_scaffold.operations import (
        backend_domain_new_operation,
        browser_scenario_new_operation,
        clients_render_operation,
        done_report_operation,
        frontend_page_new_operation,
        init_operation,
        quality_gate_finalize_operation,
        quality_gate_operation,
        quality_gate_prepare_operation,
        rules_get_operation,
        rules_list_operation,
        schema_change_prepare_operation,
        spec_new_operation,
        update_operation,
    )

    command = CLI_ALIASES.get(namespace.command, namespace.command)
    data = vars(namespace).copy()
    data.pop("command")
    if command == "apply-bundle":
        from kt_scaffold.applicator import apply_scaffold_bundle
        from kt_scaffold.models import ScaffoldBundleDescriptor

        descriptor = ScaffoldBundleDescriptor.model_validate_json(
            Path(str(data["descriptor"])).read_text(encoding="utf-8")
        )
        receipt = apply_scaffold_bundle(
            str(data["archive"]),
            str(data["target_dir"]),
            descriptor,
        )
        result = {
            "ok": True,
            "changes": [],
            "warnings": [],
            "next_steps": ["Run scripts/bootstrap.sh and the complete local quality gate."],
            "receipt": receipt.model_dump(mode="json"),
        }
        return result
    if command == "init":
        answers_path = data.pop("answers", None)
        payload: dict[str, Any] = {}
        if answers_path:
            loaded = yaml.safe_load(Path(answers_path).read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("answers file must contain an object")
            payload.update(loaded)
        if "locales" in data and isinstance(data["locales"], str):
            data["locales"] = [item.strip() for item in data["locales"].split(",") if item.strip()]
        payload.update(data)
        target_dir = str(payload.pop("target_dir"))
        return init_operation(target_dir=target_dir, **payload)
    operations: dict[str, Callable[..., dict[str, object]]] = {
        "rules": rules_list_operation,
        "rule": rules_get_operation,
        "render": clients_render_operation,
        "spec": spec_new_operation,
        "page": frontend_page_new_operation,
        "schema": schema_change_prepare_operation,
        "done": done_report_operation,
    }
    if command == "update":
        raw = data.pop("set")
        data["answer_overrides"] = dict(_pairs(raw))
        return update_operation(**data)
    if command == "domain":
        raw_permissions = data.pop("permission")
        data["permissions"] = _pairs(raw_permissions)
        return backend_domain_new_operation(**data)
    if command == "scenario":
        data["acceptance_points"] = data.pop("acceptance_point")
        return browser_scenario_new_operation(**data)
    if command == "gate":
        evidence_path = data.get("evidence_output")
        if evidence_path:
            data["evidence_output"] = Path(str(evidence_path)).read_text(encoding="utf-8")
        phase = data.pop("phase")
        if phase == "prepare":
            data.pop("allow_project_code_execution")
            data.pop("evidence_output")
            data.pop("exit_code")
            data.pop("challenge")
            return quality_gate_prepare_operation(**data)
        if phase == "finalize":
            data.pop("allow_project_code_execution")
            if any(data.get(key) is None for key in ("evidence_output", "exit_code", "challenge")):
                raise ValueError(
                    "gate finalize requires --evidence-output, --exit-code and --challenge"
                )
            return quality_gate_finalize_operation(**data)
        data.pop("evidence_output")
        data.pop("exit_code")
        data.pop("challenge")
        return quality_gate_operation(**data)
    return operations[command](**data)


def stable_json(result: dict[str, object]) -> str:
    return json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(argv)
    namespace.command = CLI_ALIASES.get(namespace.command, namespace.command)
    if namespace.command == "mcp":
        from kt_scaffold.server import run

        try:
            run(
                transport=namespace.transport,
                host=namespace.host,
                port=namespace.port,
                path=namespace.path,
                workspace_root=namespace.workspace_root,
            )
        except ValueError as exc:
            sys.stderr.write(f"kt-scaffold mcp: {exc}\n")
            return 2
        return 0
    try:
        result = _dispatch(namespace)
    except (ValueError, ValidationError, OSError, RuntimeError) as exc:
        result = {
            "ok": False,
            "changes": [],
            "warnings": [str(exc)],
            "next_steps": [],
        }
        sys.stdout.write(stable_json(result))
        return 2
    sys.stdout.write(stable_json(result))
    return 0 if result.get("ok") else 1
