"""Deterministic, fail-closed aggregation of integrity-bound worker findings."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal, NoReturn, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from jsonschema.exceptions import SchemaError  # type: ignore[import-untyped]
from pydantic import ValidationError

from kt_scaffold.agent_platform.assets import production_asset_paths
from kt_scaffold.agent_platform.manifest import canonical_json
from kt_scaffold.agent_platform.models import (
    AggregationReasonCode,
    AggregationThresholds,
    EvidenceReference,
    GovernedReviewConfiguration,
    GovernedReviewDecision,
    WorkerAggregationTrace,
    WorkerFinding,
    WorkerFindingReport,
    WorkerFindingReportPayload,
    WorkerWeight,
)

SUPPORTED_ORCHESTRATION_VERSION = "1.0.0"
SUPPORTED_POLICY_VERSION = "1.0.0"
AGGREGATOR_VERSION: Literal["1.0.0"] = "1.0.0"
SCORING_ALGORITHM: Literal["max-worker-risk-weighted-mean-v1"] = "max-worker-risk-weighted-mean-v1"
REQUIRED_WORKERS = (
    "agent:requirements-scope",
    "agent:code-review",
    "agent:application-security",
    "agent:test-automation",
)
PROHIBITED_AUTOFIX = "agent:autofix"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_AGENT_RE = re.compile(r"^agent:[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_RAW_SOURCE_KEYS = frozenset(
    {"raw_source", "source_code", "source_text", "content", "diff", "patch", "prompt"}
)
_EVIDENCE_FIELDS = frozenset({"artifact_id", "sha256"})
_FINDING_FIELDS = frozenset(
    {"finding_id", "risk_score_basis_points", "confidence_basis_points", "evidence"}
)
_PAYLOAD_FIELDS = frozenset(
    {
        "schema_version",
        "kind",
        "output_contract",
        "worker",
        "request_sha256",
        "status",
        "findings",
    }
)
_REPORT_FIELDS = _PAYLOAD_FIELDS | {"report_sha256"}
Decision = Literal["PASS", "WARNING", "FAIL", "MANUAL_REVIEW"]
TraceState = Literal[
    "valid",
    "missing",
    "duplicate",
    "invalid",
    "tampered",
    "request-mismatch",
    "timeout",
    "low-confidence",
    "prohibited",
    "unexpected",
]


class GovernedReviewConfigurationError(ValueError):
    """The source-owned orchestration or decision policy is invalid."""

    def __init__(self, detail: str) -> None:
        self.code = "AGG_CONFIGURATION_INVALID"
        self.detail = detail
        super().__init__(f"{self.code}: {detail}")


class _WorkerReportInputError(ValueError):
    """A worker report could not be reconstructed at the trust boundary."""


def _config_fail(detail: str) -> NoReturn:
    raise GovernedReviewConfigurationError(detail)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_model_state(
    value: object,
    expected_type: type[object],
    expected_fields: frozenset[str],
    label: str,
) -> dict[str, object]:
    if type(value) is not expected_type:
        raise _WorkerReportInputError(f"{label} has an invalid runtime type")
    state_value: object = object.__getattribute__(value, "__dict__")
    extra_value: object = object.__getattribute__(value, "__pydantic_extra__")
    if type(state_value) is not dict or extra_value is not None:
        raise _WorkerReportInputError(f"{label} has invalid runtime state")
    state = cast(dict[str, object], state_value)
    if set(state) != expected_fields:
        raise _WorkerReportInputError(f"{label} does not contain exactly the declared fields")
    return state


def _mapping_state(
    value: object,
    expected_fields: frozenset[str],
    label: str,
) -> dict[str, object]:
    if type(value) is not dict:
        raise _WorkerReportInputError(f"{label} has an invalid runtime type")
    state = cast(dict[str, object], value)
    if set(state) != expected_fields:
        raise _WorkerReportInputError(f"{label} does not contain exactly the declared fields")
    return state


def _string(value: object, label: str) -> str:
    if type(value) is not str:
        raise _WorkerReportInputError(f"{label} must be a plain string")
    return value


def _integer(value: object, label: str) -> int:
    if type(value) is not int:
        raise _WorkerReportInputError(f"{label} must be a plain integer")
    return value


def _sequence(value: object, label: str, *, model_state: bool) -> list[object] | tuple[object, ...]:
    if model_state:
        if type(value) is not tuple:
            raise _WorkerReportInputError(f"{label} has an invalid model container type")
        return cast(tuple[object, ...], value)
    if type(value) is list:
        return cast(list[object], value)
    if type(value) is tuple:
        return cast(tuple[object, ...], value)
    raise _WorkerReportInputError(f"{label} must be a plain list or tuple")


def _evidence_data(value: object) -> dict[str, object]:
    model_state = type(value) is EvidenceReference
    state = (
        _exact_model_state(value, EvidenceReference, _EVIDENCE_FIELDS, "evidence reference")
        if model_state
        else _mapping_state(value, _EVIDENCE_FIELDS, "evidence reference")
    )
    return {
        "artifact_id": _string(state["artifact_id"], "evidence artifact_id"),
        "sha256": _string(state["sha256"], "evidence sha256"),
    }


def _finding_data(value: object) -> dict[str, object]:
    model_state = type(value) is WorkerFinding
    state = (
        _exact_model_state(value, WorkerFinding, _FINDING_FIELDS, "worker finding")
        if model_state
        else _mapping_state(value, _FINDING_FIELDS, "worker finding")
    )
    evidence = _sequence(state["evidence"], "finding evidence", model_state=model_state)
    return {
        "finding_id": _string(state["finding_id"], "finding_id"),
        "risk_score_basis_points": _integer(
            state["risk_score_basis_points"], "risk_score_basis_points"
        ),
        "confidence_basis_points": _integer(
            state["confidence_basis_points"], "confidence_basis_points"
        ),
        "evidence": tuple(_evidence_data(item) for item in evidence),
    }


def _payload_data_from_state(
    state: dict[str, object],
    *,
    model_state: bool,
) -> dict[str, object]:
    findings = _sequence(state["findings"], "report findings", model_state=model_state)
    return {
        "schema_version": _string(state["schema_version"], "schema_version"),
        "kind": _string(state["kind"], "kind"),
        "output_contract": _string(state["output_contract"], "output_contract"),
        "worker": _string(state["worker"], "worker"),
        "request_sha256": _string(state["request_sha256"], "request_sha256"),
        "status": _string(state["status"], "status"),
        "findings": tuple(_finding_data(item) for item in findings),
    }


def _payload_data(value: object) -> dict[str, object]:
    if type(value) is WorkerFindingReport:
        state = _exact_model_state(
            value, WorkerFindingReport, _REPORT_FIELDS, "worker finding report"
        )
        return _payload_data_from_state(state, model_state=True)
    if type(value) is WorkerFindingReportPayload:
        state = _exact_model_state(
            value, WorkerFindingReportPayload, _PAYLOAD_FIELDS, "worker finding report payload"
        )
        return _payload_data_from_state(state, model_state=True)
    raise _WorkerReportInputError("worker finding report payload has an invalid runtime type")


def _report_data(value: object) -> dict[str, object]:
    if type(value) is WorkerFindingReport:
        model_state = True
        state = _exact_model_state(
            value, WorkerFindingReport, _REPORT_FIELDS, "worker finding report"
        )
    else:
        model_state = False
        state = _mapping_state(value, _REPORT_FIELDS, "worker finding report")
    data = _payload_data_from_state(state, model_state=model_state)
    data["report_sha256"] = _string(state["report_sha256"], "report_sha256")
    return data


def _sanitize_payload(value: object) -> WorkerFindingReportPayload:
    try:
        if type(value) is WorkerFindingReport:
            report = WorkerFindingReport.model_validate(_report_data(value))
            data = _payload_data(report)
        else:
            data = _payload_data(value)
        return WorkerFindingReportPayload.model_validate(data)
    except ValidationError as exc:
        raise _WorkerReportInputError("worker finding report payload is invalid") from exc


def _sanitize_report(value: object) -> WorkerFindingReport:
    try:
        return WorkerFindingReport.model_validate(_report_data(value))
    except ValidationError as exc:
        raise _WorkerReportInputError("worker finding report is invalid") from exc


def _sanitized_payload_sha256(payload: WorkerFindingReportPayload) -> str:
    return _sha256(canonical_json(_payload_data(payload)).encode("utf-8"))


def _load_json(path: Path, source: str) -> tuple[dict[str, Any], bytes]:
    try:
        data = path.read_bytes()
        value = json.loads(data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _config_fail(f"cannot load JSON {source}: {exc}")
    if not isinstance(value, dict):
        _config_fail(f"{source} must contain a JSON object")
    return value, data


def _load_yaml(path: Path, source: str) -> tuple[dict[str, Any], bytes]:
    try:
        data = path.read_bytes()
        value = yaml.safe_load(data)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        _config_fail(f"cannot load YAML {source}: {exc}")
    if not isinstance(value, dict):
        _config_fail(f"{source} must contain a YAML mapping")
    return value, data


def _validate_schema(instance: object, schema: Mapping[str, Any], source: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        _config_fail(f"invalid schema for {source}: {exc.message}")
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda item: tuple(str(part) for part in item.path),
    )
    if errors:
        first = errors[0]
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in first.path
        )
        _config_fail(f"{source}{location}: {first.message}")


def _scaled_integer(value: object, scale: int, label: str) -> int:
    try:
        scaled = Decimal(str(value)) * scale
    except (InvalidOperation, ValueError):
        _config_fail(f"{label} is not an exact decimal")
    integral = scaled.to_integral_value()
    if scaled != integral:
        _config_fail(f"{label} exceeds the supported deterministic precision")
    return int(integral)


def load_governed_review_configuration(
    assets_root: str | Path | None = None,
) -> GovernedReviewConfiguration:
    """Strictly load the canonical orchestration and research decision policy."""

    try:
        assets = production_asset_paths(assets_root)
    except ValueError as exc:
        _config_fail(str(exc))
    orchestration_schema, _ = _load_json(
        assets["orchestration.schema.json"], "orchestration.schema.json"
    )
    policy_schema, _ = _load_json(
        assets["decision-policy.schema.json"], "decision-policy.schema.json"
    )
    orchestration, orchestration_bytes = _load_yaml(
        assets["orchestrations/governed-review.yml"],
        "orchestrations/governed-review.yml",
    )
    policy, policy_bytes = _load_yaml(
        assets["policies/aggregation/governed-review.yml"],
        "policies/aggregation/governed-review.yml",
    )
    _validate_schema(orchestration, orchestration_schema, "orchestrations/governed-review.yml")
    _validate_schema(policy, policy_schema, "policies/aggregation/governed-review.yml")

    workers = tuple(item["agent"] for item in orchestration["workers"])
    policy_workers = tuple(policy["required_workers"])
    weights = policy["weights"]
    prohibited = tuple(sorted(orchestration["prohibited_agents"]))
    if workers != REQUIRED_WORKERS or policy_workers != REQUIRED_WORKERS:
        _config_fail("orchestration and policy must bind the canonical four workers in order")
    if len(workers) != len(set(workers)) or set(weights) != set(REQUIRED_WORKERS):
        _config_fail("required workers and decision weights must be one-to-one")
    if PROHIBITED_AUTOFIX not in prohibited or set(prohibited).intersection(workers):
        _config_fail("AutoFix must be prohibited and cannot be a governed-review worker")
    if orchestration["execution"]["max_parallel"] != len(REQUIRED_WORKERS):
        _config_fail("parallelism must equal the four isolated workers")
    if orchestration["decision"]["policy_ref"] != policy["metadata"]["id"]:
        _config_fail("orchestration policy reference does not match the decision policy")
    if orchestration["metadata"]["owner"] != policy["metadata"]["owner"]:
        _config_fail("orchestration and decision policy owners differ")

    worker_weights = tuple(
        WorkerWeight(
            worker=worker,
            weight_micros=_scaled_integer(weights[worker], 1_000_000, f"weight {worker}"),
        )
        for worker in REQUIRED_WORKERS
    )
    raw_thresholds = policy["thresholds"]
    try:
        compliance_baseline = _scaled_integer(
            raw_thresholds["compliance_baseline"], 100, "compliance_baseline"
        )
        if compliance_baseline != 10_000:
            _config_fail("compliance_baseline must normalize to 10000 basis points")
        thresholds = AggregationThresholds(
            fail_score_basis_points=_scaled_integer(
                raw_thresholds["fail_score"], 100, "fail_score"
            ),
            warning_score_basis_points=_scaled_integer(
                raw_thresholds["warning_score"], 100, "warning_score"
            ),
            confidence_floor_basis_points=_scaled_integer(
                raw_thresholds["confidence_floor"], 10_000, "confidence_floor"
            ),
            compliance_baseline_basis_points=10_000,
        )
        return GovernedReviewConfiguration(
            aggregator_version=AGGREGATOR_VERSION,
            scoring_algorithm=SCORING_ALGORITHM,
            orchestration_version=orchestration["metadata"]["version"],
            orchestration_sha256=_sha256(orchestration_bytes),
            policy_version=policy["metadata"]["version"],
            policy_sha256=_sha256(policy_bytes),
            required_workers=REQUIRED_WORKERS,
            prohibited_workers=prohibited,
            weights=worker_weights,
            thresholds=thresholds,
            raw_source_visible_to_aggregator=orchestration["input"][
                "raw_source_visible_to_aggregator"
            ],
            verify_result_integrity=orchestration["decision"]["verify_result_integrity"],
            thresholds_calibrated=policy["claim_boundary"]["production_decision"],
            runtime_admission=policy["claim_boundary"]["runtime_admission"],
            production_decision=policy["claim_boundary"]["production_decision"],
        )
    except ValidationError as exc:
        _config_fail(f"invalid normalized governed-review configuration: {exc.errors()[0]['msg']}")


def worker_report_sha256(
    report: WorkerFindingReportPayload | WorkerFindingReport,
) -> str:
    """Return the digest over the strict payload, excluding its claimed digest."""

    return _sanitized_payload_sha256(_sanitize_payload(report))


def seal_worker_report(payload: WorkerFindingReportPayload) -> WorkerFindingReport:
    """Create an integrity-bound report without adding time or runtime claims."""

    sanitized = _sanitize_payload(payload)
    return WorkerFindingReport.model_validate(
        {
            **_payload_data(sanitized),
            "report_sha256": _sanitized_payload_sha256(sanitized),
        }
    )


def _contains_raw_source(value: object, depth: int = 0) -> bool:
    if depth > 12:
        return False
    if isinstance(value, dict):
        keys = dict.keys(value)
        if any(type(key) is str and str.lower(key) in _RAW_SOURCE_KEYS for key in keys):
            return True
        return any(_contains_raw_source(child, depth + 1) for child in dict.values(value))
    if isinstance(value, WorkerFindingReportPayload | WorkerFinding | EvidenceReference):
        state_value: object = object.__getattribute__(value, "__dict__")
        if type(state_value) is not dict:
            return False
        return _contains_raw_source(state_value, depth + 1)
    if type(value) is list or type(value) is tuple:
        return any(_contains_raw_source(child, depth + 1) for child in value)
    return False


def _worker_hint(value: object) -> str | None:
    candidate: object | None = None
    if isinstance(value, dict):
        candidate = dict.get(value, "worker")
    elif isinstance(value, WorkerFindingReportPayload):
        state_value: object = object.__getattribute__(value, "__dict__")
        if type(state_value) is dict:
            candidate = dict.get(state_value, "worker")
    if type(candidate) is str and _AGENT_RE.fullmatch(candidate):
        return candidate
    return None


def _decision(
    configuration: GovernedReviewConfiguration,
    *,
    decision: Decision,
    reasons: set[AggregationReasonCode],
    request_sha256: str,
    traces: Sequence[WorkerAggregationTrace],
    risk_score_basis_points: int | None = None,
    compliance_score_basis_points: int | None = None,
) -> GovernedReviewDecision:
    return GovernedReviewDecision(
        decision=decision,
        reason_codes=tuple(sorted(reasons, key=lambda item: item.value)),
        aggregator_version=configuration.aggregator_version,
        scoring_algorithm=configuration.scoring_algorithm,
        request_sha256=request_sha256,
        orchestration_ref=configuration.orchestration_ref,
        orchestration_version=configuration.orchestration_version,
        orchestration_sha256=configuration.orchestration_sha256,
        policy_ref=configuration.policy_ref,
        policy_version=configuration.policy_version,
        policy_sha256=configuration.policy_sha256,
        worker_traces=tuple(sorted(traces, key=lambda item: (item.worker, item.state))),
        risk_score_basis_points=risk_score_basis_points,
        compliance_score_basis_points=compliance_score_basis_points,
        thresholds_calibrated=False,
        runtime_admission=False,
        production_decision=False,
    )


def aggregate_governed_review(
    reports: Sequence[WorkerFindingReport | Mapping[str, object]],
    *,
    expected_request_sha256: str,
    assets_root: str | Path | None = None,
) -> GovernedReviewDecision:
    """Aggregate normalized finding signals; never accept request or raw-source content."""

    if not _SHA256_RE.fullmatch(expected_request_sha256):
        raise ValueError("expected_request_sha256 must be a lowercase SHA-256 digest")
    selected = load_governed_review_configuration(assets_root)
    reasons: set[AggregationReasonCode] = set()
    if (
        selected.orchestration_version != SUPPORTED_ORCHESTRATION_VERSION
        or selected.policy_version != SUPPORTED_POLICY_VERSION
    ):
        reasons.add(AggregationReasonCode.UNKNOWN_POLICY_VERSION)

    parsed_by_worker: dict[str, list[WorkerFindingReport]] = defaultdict(list)
    invalid_workers: set[str] = set()
    if len(reports) > 16:
        reasons.add(AggregationReasonCode.INVALID_SCHEMA)
    else:
        for supplied in reports:
            hint = _worker_hint(supplied)
            if hint == PROHIBITED_AUTOFIX:
                reasons.add(AggregationReasonCode.PROHIBITED_AGENT)
            if _contains_raw_source(supplied):
                reasons.update(
                    {
                        AggregationReasonCode.RAW_SOURCE_REJECTED,
                        AggregationReasonCode.INVALID_SCHEMA,
                    }
                )
                if hint:
                    invalid_workers.add(hint)
                continue
            try:
                report = _sanitize_report(supplied)
            except _WorkerReportInputError:
                reasons.add(AggregationReasonCode.INVALID_SCHEMA)
                if hint:
                    invalid_workers.add(hint)
                continue
            parsed_by_worker[report.worker].append(report)

    traces: list[WorkerAggregationTrace] = []
    weight_by_worker = {item.worker: item.weight_micros for item in selected.weights}
    score_by_worker: dict[str, int] = {}
    required_set = set(selected.required_workers)

    for worker in sorted(set(parsed_by_worker) - required_set):
        report = parsed_by_worker[worker][0]
        state: TraceState = "prohibited" if worker in selected.prohibited_workers else "unexpected"
        reasons.add(
            AggregationReasonCode.PROHIBITED_AGENT
            if state == "prohibited"
            else AggregationReasonCode.UNEXPECTED_WORKER
        )
        traces.append(
            WorkerAggregationTrace(
                worker=worker,
                state=state,
                claimed_sha256=report.report_sha256,
                observed_sha256=worker_report_sha256(report),
                finding_count=len(report.findings),
            )
        )

    for worker in selected.required_workers:
        worker_reports = parsed_by_worker.get(worker, [])
        if not worker_reports:
            missing_state: TraceState
            if worker in invalid_workers:
                missing_state = "invalid"
                reasons.add(AggregationReasonCode.INVALID_SCHEMA)
            else:
                missing_state = "missing"
                reasons.add(AggregationReasonCode.MISSING_WORKER)
            traces.append(WorkerAggregationTrace(worker=worker, state=missing_state))
            continue
        if len(worker_reports) != 1:
            reasons.add(AggregationReasonCode.DUPLICATE_WORKER)
            traces.append(WorkerAggregationTrace(worker=worker, state="duplicate"))
            continue

        report = worker_reports[0]
        observed = worker_report_sha256(report)
        risk_score = max(
            (finding.risk_score_basis_points for finding in report.findings), default=0
        )
        report_state: TraceState = "valid"
        if observed != report.report_sha256:
            reasons.add(AggregationReasonCode.INTEGRITY_FAILURE)
            report_state = "tampered"
        if report.request_sha256 != expected_request_sha256:
            reasons.add(AggregationReasonCode.REQUEST_DIGEST_MISMATCH)
            if report_state == "valid":
                report_state = "request-mismatch"
        if report.status == "timeout":
            reasons.add(AggregationReasonCode.TIMEOUT)
            if report_state == "valid":
                report_state = "timeout"
        if any(
            finding.confidence_basis_points < selected.thresholds.confidence_floor_basis_points
            for finding in report.findings
        ):
            reasons.add(AggregationReasonCode.LOW_CONFIDENCE)
            if report_state == "valid":
                report_state = "low-confidence"
        if report_state == "valid":
            score_by_worker[worker] = risk_score
        traces.append(
            WorkerAggregationTrace(
                worker=worker,
                state=report_state,
                claimed_sha256=report.report_sha256,
                observed_sha256=observed,
                finding_count=len(report.findings),
                risk_score_basis_points=risk_score if report_state == "valid" else None,
                weight_micros=weight_by_worker[worker],
            )
        )

    if reasons:
        return _decision(
            selected,
            decision="MANUAL_REVIEW",
            reasons=reasons,
            request_sha256=expected_request_sha256,
            traces=traces,
        )

    total_weight = sum(weight_by_worker[worker] for worker in selected.required_workers)
    weighted_sum = sum(
        score_by_worker[worker] * weight_by_worker[worker] for worker in selected.required_workers
    )
    risk_score = (weighted_sum + total_weight // 2) // total_weight
    compliance_score = selected.thresholds.compliance_baseline_basis_points - risk_score
    if risk_score >= selected.thresholds.fail_score_basis_points:
        outcome: Decision = "FAIL"
        threshold_reason = AggregationReasonCode.THRESHOLD_FAIL
    elif risk_score >= selected.thresholds.warning_score_basis_points:
        outcome = "WARNING"
        threshold_reason = AggregationReasonCode.THRESHOLD_WARNING
    else:
        outcome = "PASS"
        threshold_reason = AggregationReasonCode.SCORE_PASS
    return _decision(
        selected,
        decision=outcome,
        reasons={threshold_reason},
        request_sha256=expected_request_sha256,
        traces=traces,
        risk_score_basis_points=risk_score,
        compliance_score_basis_points=compliance_score,
    )


__all__ = [
    "AGGREGATOR_VERSION",
    "PROHIBITED_AUTOFIX",
    "REQUIRED_WORKERS",
    "SCORING_ALGORITHM",
    "GovernedReviewConfigurationError",
    "aggregate_governed_review",
    "load_governed_review_configuration",
    "seal_worker_report",
    "worker_report_sha256",
]
