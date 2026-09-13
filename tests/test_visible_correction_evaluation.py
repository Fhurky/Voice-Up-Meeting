"""Visible proposals have distinct evidence from the legacy conservative policy."""

import importlib.util
import copy
from itertools import combinations
from pathlib import Path

import pytest


@pytest.fixture
def ledger():
    path = Path(__file__).resolve().parents[1] / "scripts/experiment_ledger.py"
    spec = importlib.util.spec_from_file_location("visible_ledger", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_visible_protocol_is_bound_to_its_new_policy(ledger):
    result = ledger.sanitize_result(
        {
            "protocol": "voiceup-context-review-visible-v1",
            "policy_version": "tr-context-words-v2",
            "reference_quality": "synthetic-authored",
            "status": "unscored",
        },
        "transcript_review",
    )
    assert result["protocol"] == "voiceup-context-review-visible-v1"
    assert result["policy_version"] == "tr-context-words-v2"
    assert result["metrics"] is None


@pytest.mark.parametrize("policy", [None, "tr-context-words-v1", "unknown"])
def test_visible_protocol_cannot_claim_the_legacy_policy(ledger, policy):
    with pytest.raises(ValueError, match="invalid_review_protocol"):
        ledger.sanitize_result(
            {
                "protocol": "voiceup-context-review-visible-v1",
                "policy_version": policy,
                "reference_quality": "synthetic-authored",
                "status": "unscored",
            },
            "transcript_review",
        )


def test_legacy_result_shape_remains_unchanged(ledger):
    result = ledger.sanitize_result(
        {
            "protocol": "voiceup-context-review-v1",
            "reference_quality": "synthetic-authored",
            "status": "unscored",
        },
        "transcript_review",
    )
    assert "policy_version" not in result
    assert result["protocol"] == "voiceup-context-review-v1"


VISIBILITY_FIELDS = ("visible_status_counts", "review_required_edits", "saveable_rows")


def visible_report():
    return {
        "status": "complete",
        "protocol": "voiceup-context-review-visible-v1",
        "policy_version": "tr-context-words-v2",
        "reference_quality": "synthetic-authored",
        "visible_status_counts": dict(unchanged=1, suggested=1, unmapped=1, invalid_output=1),
        "review_required_edits": 3,
        "saveable_rows": 1,
        "metrics": dict(
            planned_rows=5,
            completed_rows=4,
            failed_rows=1,
            reference_words=10,
            raw_errors=2,
            corrected_errors=1,
            changed_rows=1,
            improved_rows=1,
            worsened_rows=0,
            clean_rows=4,
            damaged_clean_rows=0,
            accepted_edits=2,
            beneficial_edits=1,
            harmful_edits=0,
            neutral_edits=1,
            rejected_edits=2,
            raw_wer=0.2,
            corrected_wer=0.1,
            edit_precision=0.5,
            clean_damage_rate=0,
            completion_coverage=0.8,
            change_coverage=0.2,
            elapsed_seconds=5,
            latency_median_seconds=1,
            latency_max_seconds=1,
        ),
    }


def append_visible(ledger, path, report):
    return ledger.record_experiment(
        path,
        experiment_id="visible-regression",
        metadata=dict(
            date="2026-09-13",
            dataset="authored-cases",
            dataset_revision="v1",
            language="tr",
            role="regression",
            pipeline="transcript-review",
        ),
        report=report,
        kind="transcript_review",
    )


def test_visible_counts_survive_public_snapshot_and_explain_delivered_output(ledger, tmp_path):
    report = visible_report()
    report.update(model_output="PRIVATE_MODEL_TEXT", original="PRIVATE_SOURCE_TEXT")
    result = ledger.sanitize_result(report, "transcript_review")
    assert {key: result[key] for key in VISIBILITY_FIELDS} == {
        key: report[key] for key in VISIBILITY_FIELDS
    }
    path = tmp_path / "results.md"
    assert append_visible(ledger, path, report)
    text = path.read_text(encoding="utf-8")
    assert "Ulaşan yanıt 4" in text
    assert "değişmedi 1; öneri 1; eşlenemedi 1; geçersiz çıktı 1" in text
    assert "Kayda uygun satır 1; inceleme işaretli öneri 3" in text
    assert "yanıtın ulaşması geçerli veya doğru öneri olduğu anlamına gelmez" in text
    assert "PRIVATE" not in text
    assert (
        ledger.read_snapshots(path)[0]["result"]["visible_status_counts"]
        == report["visible_status_counts"]
    )


@pytest.mark.parametrize(
    "present", [fields for size in (1, 2) for fields in combinations(VISIBILITY_FIELDS, size)]
)
def test_visibility_fields_are_all_or_none(ledger, present):
    report = visible_report()
    for field in set(VISIBILITY_FIELDS) - set(present):
        del report[field]
    with pytest.raises(ValueError, match="invalid_review_visibility"):
        ledger.sanitize_result(report, "transcript_review")


@pytest.mark.parametrize(
    "changes",
    [
        {"visible_status_counts": None},
        {"visible_status_counts": dict(unchanged=1, suggested=1, unmapped=1)},
        {
            "visible_status_counts": dict(
                unchanged=1, suggested=1, unmapped=1, invalid_output=1, private="PRIVATE"
            )
        },
        {"visible_status_counts": dict(unchanged=True, suggested=1, unmapped=1, invalid_output=1)},
        {"visible_status_counts": dict(unchanged=2, suggested=1, unmapped=1, invalid_output=1)},
        {"visible_status_counts": dict(unchanged=1, suggested=0, unmapped=2, invalid_output=1)},
        {"review_required_edits": -1},
        {"review_required_edits": True},
        {"review_required_edits": 0.5},
        {"review_required_edits": 5},
        {"saveable_rows": True},
        {"saveable_rows": -1},
        {"saveable_rows": 2},
    ],
)
def test_visible_counters_reject_wrong_shapes_types_and_arithmetic(ledger, changes):
    report = visible_report()
    report.update(changes)
    with pytest.raises(ValueError):
        ledger.sanitize_result(report, "transcript_review")


def test_visibility_checks_joint_proposal_budget(ledger):
    report = visible_report()
    report["metrics"].update(
        accepted_edits=8, neutral_edits=7, rejected_edits=5, edit_precision=0.125
    )
    with pytest.raises(ValueError, match="review_visibility_mismatch"):
        ledger.sanitize_result(report, "transcript_review")


def test_noncomplete_run_cannot_claim_unbound_visible_counts(ledger):
    report = visible_report()
    report["status"] = "unscored"
    with pytest.raises(ValueError, match="invalid_review_visibility"):
        ledger.sanitize_result(report, "transcript_review")


def test_historical_visible_snapshot_without_counts_replays_without_rewrite(ledger, tmp_path):
    report = visible_report()
    historical = copy.deepcopy(report)
    for field in VISIBILITY_FIELDS:
        del historical[field]
    result = ledger.sanitize_result(historical, "transcript_review")
    assert not set(VISIBILITY_FIELDS) & result.keys()
    path = tmp_path / "results.md"
    assert append_visible(ledger, path, historical)
    original = path.read_bytes()
    assert not append_visible(ledger, path, historical)
    assert path.read_bytes() == original
    assert append_visible(ledger, path, report)
    assert path.read_bytes().startswith(original)
    values = ledger.read_snapshots(path)
    assert [row["revision"] for row in values] == [1, 2]
    assert not set(VISIBILITY_FIELDS) & values[0]["result"].keys()
    assert values[1]["result"]["saveable_rows"] == 1
