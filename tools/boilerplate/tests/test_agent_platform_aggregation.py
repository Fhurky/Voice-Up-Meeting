from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any, Literal, cast

import pytest
import yaml

from kt_scaffold.agent_platform.aggregation import (
    PROHIBITED_AUTOFIX,
    REQUIRED_WORKERS,
    GovernedReviewConfigurationError,
    aggregate_governed_review,
    load_governed_review_configuration,
    seal_worker_report,
    worker_report_sha256,
)
from kt_scaffold.agent_platform.manifest import canonical_json
from kt_scaffold.agent_platform.models import (
    AggregationReasonCode,
    EvidenceReference,
    WorkerFinding,
    WorkerFindingReport,
    WorkerFindingReportPayload,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "agent-platform"
REQUEST_SHA256 = hashlib.sha256(b"bounded-review-request").hexdigest()
EVIDENCE_SHA256 = hashlib.sha256(b"normalized-evidence").hexdigest()


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


def _report(
    worker: str,
    *,
    score: int = 0,
    confidence: int = 9_000,
    request_sha256: str = REQUEST_SHA256,
    status: Literal["completed", "timeout"] = "completed",
) -> WorkerFindingReport:
    findings: tuple[WorkerFinding, ...] = ()
    if status == "completed":
        findings = (
            WorkerFinding(
                finding_id="finding-1",
                risk_score_basis_points=score,
                confidence_basis_points=confidence,
                evidence=(
                    EvidenceReference(
                        artifact_id="evidence:normalized-1",
                        sha256=EVIDENCE_SHA256,
                    ),
                ),
            ),
        )
    payload = WorkerFindingReportPayload(
        worker=worker,
        request_sha256=request_sha256,
        status=status,
        findings=findings,
    )
    return seal_worker_report(payload)


def _reports(scores: tuple[int, int, int, int] = (0, 0, 0, 0)) -> tuple[WorkerFindingReport, ...]:
    return tuple(
        _report(worker, score=score) for worker, score in zip(REQUIRED_WORKERS, scores, strict=True)
    )


def _reason_values(result: Any) -> set[str]:
    return {item.value for item in result.reason_codes}


def test_configuration_is_strictly_bound_to_four_workers_and_research_claims() -> None:
    configuration = load_governed_review_configuration(ASSETS)

    assert configuration.required_workers == REQUIRED_WORKERS
    assert configuration.aggregator_version == "1.0.0"
    assert configuration.scoring_algorithm == "max-worker-risk-weighted-mean-v1"
    assert configuration.prohibited_workers == (PROHIBITED_AUTOFIX,)
    assert [item.worker for item in configuration.weights] == list(REQUIRED_WORKERS)
    assert [item.weight_micros for item in configuration.weights] == [
        600_000,
        800_000,
        1_400_000,
        600_000,
    ]
    assert configuration.thresholds.fail_score_basis_points == 6_000
    assert configuration.thresholds.warning_score_basis_points == 2_500
    assert configuration.thresholds.confidence_floor_basis_points == 5_500
    assert configuration.raw_source_visible_to_aggregator is False
    assert configuration.thresholds_calibrated is False
    assert configuration.runtime_admission is False
    assert configuration.production_decision is False


def test_weighted_aggregation_is_byte_stable_and_order_independent() -> None:
    reports = _reports((1_000, 2_000, 8_000, 1_000))

    first = aggregate_governed_review(
        reports,
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )
    second = aggregate_governed_review(
        tuple(reversed(reports)),
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )

    assert first == second
    assert canonical_json(first.model_dump(mode="json")) == canonical_json(
        second.model_dump(mode="json")
    )
    assert first.decision == "WARNING"
    assert first.aggregator_version == "1.0.0"
    assert first.scoring_algorithm == "max-worker-risk-weighted-mean-v1"
    assert first.risk_score_basis_points == 4_118
    assert first.compliance_score_basis_points == 5_882
    assert _reason_values(first) == {"AGG_THRESHOLD_WARNING"}
    assert [item.worker for item in first.worker_traces] == sorted(REQUIRED_WORKERS)
    assert all(item.state == "valid" for item in first.worker_traces)
    assert first.thresholds_calibrated is False
    assert first.production_decision is False


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ((0, 0, 0, 0), "PASS"),
        ((10_000, 10_000, 10_000, 10_000), "FAIL"),
    ],
)
def test_threshold_decisions_remain_research_only(
    scores: tuple[int, int, int, int], expected: str
) -> None:
    result = aggregate_governed_review(
        _reports(scores),
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )

    assert result.decision == expected
    assert result.thresholds_calibrated is False
    assert result.runtime_admission is False
    assert result.production_decision is False


def test_worker_report_digest_covers_normalized_payload_only() -> None:
    report = _report(REQUIRED_WORKERS[0], score=2_500)

    assert worker_report_sha256(report) == report.report_sha256
    assert set(report.model_dump()) == {
        "schema_version",
        "kind",
        "output_contract",
        "worker",
        "request_sha256",
        "status",
        "findings",
        "report_sha256",
    }
    assert set(report.findings[0].model_dump()) == {
        "finding_id",
        "risk_score_basis_points",
        "confidence_basis_points",
        "evidence",
    }


def test_shadowed_serializer_cannot_hide_forged_severity() -> None:
    reports = list(_reports())
    original = reports[0]
    forged_finding = original.findings[0].model_copy(update={"risk_score_basis_points": 10_000})
    forged = original.model_copy(
        update={
            "findings": (forged_finding,),
            "model_dump": original.model_dump,
        }
    )
    reports[0] = forged

    assert forged.findings[0].risk_score_basis_points == 10_000
    assert forged.model_dump(mode="python")["findings"][0]["risk_score_basis_points"] == 0
    with pytest.raises(ValueError, match="exactly the declared fields"):
        worker_report_sha256(forged)

    result = aggregate_governed_review(
        reports,
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )

    assert result.decision == "MANUAL_REVIEW"
    assert _reason_values(result) == {"AGG_INVALID_SCHEMA"}
    assert result.risk_score_basis_points is None


def test_shadowed_serializer_cannot_hide_forged_request_digest() -> None:
    reports = list(_reports())
    original = reports[0]
    forged_request = hashlib.sha256(b"forged-request").hexdigest()
    forged = original.model_copy(
        update={
            "request_sha256": forged_request,
            "model_dump": original.model_dump,
        }
    )
    reports[0] = forged

    assert forged.request_sha256 == forged_request
    assert forged.model_dump(mode="python")["request_sha256"] == REQUEST_SHA256
    result = aggregate_governed_review(
        reports,
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )

    assert result.decision == "MANUAL_REVIEW"
    assert _reason_values(result) == {"AGG_INVALID_SCHEMA"}


def test_shadowed_serializer_cannot_hide_forged_worker() -> None:
    reports = list(_reports())
    original = reports[0]
    forged = original.model_copy(
        update={
            "worker": PROHIBITED_AUTOFIX,
            "model_dump": original.model_dump,
        }
    )
    reports[0] = forged

    assert forged.worker == PROHIBITED_AUTOFIX
    assert forged.model_dump(mode="python")["worker"] == REQUIRED_WORKERS[0]
    result = aggregate_governed_review(
        reports,
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )

    assert result.decision == "MANUAL_REVIEW"
    assert {"AGG_INVALID_SCHEMA", "AGG_PROHIBITED_AGENT"}.issubset(_reason_values(result))


def test_model_copy_cannot_hide_raw_source_as_an_undeclared_field() -> None:
    reports = list(_reports())
    original = reports[0]
    forged = original.model_copy(update={"raw_source": "must never reach the aggregator"})
    reports[0] = forged

    assert "raw_source" not in forged.model_dump(mode="python")
    result = aggregate_governed_review(
        reports,
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )

    assert result.decision == "MANUAL_REVIEW"
    assert _reason_values(result) == {"AGG_INVALID_SCHEMA", "AGG_RAW_SOURCE_REJECTED"}


def test_report_subclass_is_rejected_at_the_runtime_type_boundary() -> None:
    class WorkerFindingReportSubclass(WorkerFindingReport):
        pass

    reports = list(_reports())
    original = reports[0]
    forged = WorkerFindingReportSubclass.model_validate(original.model_dump(mode="python"))
    reports[0] = forged

    with pytest.raises(ValueError, match="invalid runtime type"):
        worker_report_sha256(forged)

    result = aggregate_governed_review(
        reports,
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )

    assert result.decision == "MANUAL_REVIEW"
    assert _reason_values(result) == {"AGG_INVALID_SCHEMA"}


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing", "AGG_MISSING_WORKER"),
        ("duplicate", "AGG_DUPLICATE_WORKER"),
        ("timeout", "AGG_TIMEOUT"),
        ("tampered", "AGG_INTEGRITY_FAILURE"),
        ("request-mismatch", "AGG_REQUEST_DIGEST_MISMATCH"),
        ("low-confidence", "AGG_LOW_CONFIDENCE"),
        ("invalid", "AGG_INVALID_SCHEMA"),
        ("raw-source", "AGG_RAW_SOURCE_REJECTED"),
        ("autofix", "AGG_PROHIBITED_AGENT"),
    ],
)
def test_worker_failures_route_to_manual_review(mutation: str, reason: str) -> None:
    reports: list[WorkerFindingReport | dict[str, Any]] = list(_reports())
    if mutation == "missing":
        reports.pop()
    elif mutation == "duplicate":
        reports.append(reports[0])
    elif mutation == "timeout":
        reports[-1] = _report(REQUIRED_WORKERS[-1], status="timeout")
    elif mutation == "tampered":
        changed = cast(WorkerFindingReport, reports[0]).model_dump(mode="python")
        changed["findings"][0]["risk_score_basis_points"] = 9_000
        reports[0] = changed
    elif mutation == "request-mismatch":
        reports[0] = _report(
            REQUIRED_WORKERS[0],
            request_sha256=hashlib.sha256(b"different-request").hexdigest(),
        )
    elif mutation == "low-confidence":
        reports[0] = _report(REQUIRED_WORKERS[0], confidence=5_499)
    elif mutation == "invalid":
        changed = cast(WorkerFindingReport, reports[0]).model_dump(mode="python")
        changed["unknown"] = True
        reports[0] = changed
    elif mutation == "raw-source":
        changed = cast(WorkerFindingReport, reports[0]).model_dump(mode="python")
        changed["raw_source"] = "must never reach the aggregator"
        reports[0] = changed
    elif mutation == "autofix":
        reports.append(_report(PROHIBITED_AUTOFIX))

    result = aggregate_governed_review(
        reports,
        expected_request_sha256=REQUEST_SHA256,
        assets_root=ASSETS,
    )

    assert result.decision == "MANUAL_REVIEW"
    assert reason in _reason_values(result)
    assert result.risk_score_basis_points is None
    assert result.compliance_score_basis_points is None
    assert result.production_decision is False


def test_unknown_policy_version_routes_to_manual_review(tmp_path: Path) -> None:
    assets = _copy_assets(tmp_path)
    policy_path = assets / "policies" / "aggregation" / "governed-review.yml"
    policy = _load_yaml(policy_path)
    policy["metadata"]["version"] = "2.0.0"
    _write_yaml(policy_path, policy)

    result = aggregate_governed_review(
        _reports(),
        expected_request_sha256=REQUEST_SHA256,
        assets_root=assets,
    )

    assert result.decision == "MANUAL_REVIEW"
    assert _reason_values(result) == {"AGG_UNKNOWN_POLICY_VERSION"}


@pytest.mark.parametrize("target", ["orchestration", "policy"])
def test_unknown_configuration_fields_fail_strict_schema(tmp_path: Path, target: str) -> None:
    assets = _copy_assets(tmp_path)
    if target == "orchestration":
        path = assets / "orchestrations" / "governed-review.yml"
    else:
        path = assets / "policies" / "aggregation" / "governed-review.yml"
    value = _load_yaml(path)
    value["unknown"] = True
    _write_yaml(path, value)

    with pytest.raises(GovernedReviewConfigurationError) as caught:
        load_governed_review_configuration(assets)

    assert caught.value.code == "AGG_CONFIGURATION_INVALID"


def test_configuration_rejects_autofix_as_a_worker(tmp_path: Path) -> None:
    assets = _copy_assets(tmp_path)
    orchestration_path = assets / "orchestrations" / "governed-review.yml"
    orchestration = _load_yaml(orchestration_path)
    orchestration["workers"][0]["agent"] = PROHIBITED_AUTOFIX
    _write_yaml(orchestration_path, orchestration)

    with pytest.raises(GovernedReviewConfigurationError):
        load_governed_review_configuration(assets)


def test_invalid_expected_digest_is_rejected_without_accepting_source() -> None:
    with pytest.raises(ValueError, match="expected_request_sha256"):
        aggregate_governed_review(
            _reports(),
            expected_request_sha256="not-a-digest",
            assets_root=ASSETS,
        )


def test_reason_enum_exposes_only_machine_readable_codes() -> None:
    assert all(item.value.startswith("AGG_") for item in AggregationReasonCode)
