"""Aggregate evidence must preserve failures and omit source identities."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def reporter():
    spec = importlib.util.spec_from_file_location(
        "public_report", Path(__file__).parents[1] / "scripts/report-public-speakers.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe(speaker, correct=True, *, unknown=False, failed=False):
    return {
        "speaker_id": speaker,
        "predicted_speaker_id": speaker if correct else "another",
        "purpose": "identify",
        "stage": 5,
        "kind": "unknown" if unknown else "known",
        "status": "failed" if failed else "succeeded",
        "decision": "unknown" if unknown else "recognized",
        "source_split": "test-clean",
        "error_code": "insufficient_speech" if failed else None,
        "timing": {"execution_seconds": 0.2, "queue_seconds": 1.0},
        "result": {"device": "cuda:0", "profile_name": "private name"},
    }


def test_clustered_rate_counts_failures_and_is_reproducible(reporter):
    rows = [probe("A"), probe("A"), probe("B", failed=True)]
    actual = reporter.cluster_interval(rows, "known", "correct", samples=200)
    assert actual == reporter.cluster_interval(rows, "known", "correct", samples=200)
    assert actual["speakers"] == 2
    assert actual["probes"] == 3
    assert actual["point"] == pytest.approx(2 / 3)
    assert actual["lower"] <= actual["point"] <= actual["upper"]


def test_no_error_bootstrap_does_not_claim_zero_population_risk(reporter):
    actual = reporter.cluster_interval([probe("U", unknown=True)], "unknown", "false_accept")
    assert actual["point"] == 0
    assert actual["all_outcomes_identical"] is True
    assert "population" in actual["limitation"]


def test_anonymous_summary_does_not_copy_private_payload(reporter):
    source = {
        "status": "complete",
        "split": "test",
        "model_id": "model",
        "model_revision": "revision",
        "frozen_policy": {"match_threshold": 0.75},
        "binding": {"tenant_id": "private tenant", "manifest_sha256": "a" * 64},
        "stages": [
            {
                "gallery_size_planned": 5,
                "gallery_size_enrolled": 4,
                "enrollment_failed": 1,
                "counts": {"known_planned": 1, "unknown_planned": 0},
                "rates": {"DIR": 0},
                "wilson_95_probe_intervals": {},
            }
        ],
        "operations": [probe("private person", failed=True)],
        "return_phase": [],
    }
    result = reporter.summarize(source)
    rendered = str(result)
    assert "private" not in rendered
    assert result["stages"][0]["error_counts"] == {"insufficient_speech": 1}
    assert result["stages"][0]["gallery_size_enrolled"] == 4

    source["status"] = "incomplete"
    source["stages"][0]["counts"]["known_planned"] = 2
    incomplete = reporter.summarize(source)
    assert incomplete["stages"][0]["all_planned_probes_terminal"] is False
    assert incomplete["stages"][0]["by_source_split"] is None


def test_subset_statistics_keep_failed_probes(reporter):
    result = reporter.subset_counts([probe("A"), probe("B", failed=True), probe("U", unknown=True)])
    assert result == {
        "known_planned": 2,
        "unknown_planned": 1,
        "known_correct": 1,
        "known_wrong": 0,
        "known_ambiguous": 0,
        "known_unknown": 0,
        "unknown_false_accepted": 0,
        "unknown_unknown": 1,
        "unknown_ambiguous": 0,
        "known_job_failed": 1,
        "unknown_job_failed": 0,
    }


def test_invalid_stage_is_not_silently_dropped(reporter):
    with pytest.raises(ValueError):
        reporter.summarize({"status": "complete", "split": "test", "stages": []})


def test_return_outcomes_distinguish_wrong_identity_rejection_and_missing_queries(reporter):
    rows = [
        {"purpose": "enroll", "status": "succeeded"},
        {"purpose": "enroll", "status": "failed", "error_code": "inconsistent_audio"},
        {**probe("returning", correct=False), "stage": "return"},
        {**probe("returning"), "decision": "ambiguous", "predicted_speaker_id": None},
        {**probe("returning"), "decision": "unknown", "predicted_speaker_id": None},
        probe("returning", failed=True),
        probe("returning"),
        {"purpose": "identify", "status": "pending"},
    ]
    result = reporter.return_counts(rows, {"enrollments": 3, "queries": 8})
    assert {
        key: result[key] for key in ("enrollment_succeeded", "queries", "correct", "failed")
    } == {"enrollment_succeeded": 1, "queries": 6, "correct": 1, "failed": 2}
    assert result["enrollment_failed"] == 1
    assert result["enrollment_not_run"] == 1
    assert result["queries_planned"] == 8
    assert result["queries_terminal"] == 5
    assert result["queries_pending"] == 1
    assert result["queries_not_run"] == 2
    assert result["recognized_wrong"] == 1
    assert result["ambiguous"] == 1
    assert result["unknown"] == 1
    assert result["query_failed"] == 1
    assert result["query_quality_failed"] == 1
    assert result["query_error_counts"] == {"insufficient_speech": 1}
    assert result["all_planned_operations_terminal"] is False


def test_failed_return_enrollment_does_not_hide_unstarted_planned_query(reporter):
    rows = [{"purpose": "enroll", "status": "failed", "error_code": "inconsistent_audio"}]
    result = reporter.return_counts(rows, {"enrollments": 1, "queries": 1})
    assert result["enrollment_failed"] == 1
    assert result["queries"] == 0
    assert result["query_failed"] == 0
    assert result["queries_not_run"] == 1
    assert result["all_planned_operations_terminal"] is False


def test_historical_return_input_does_not_invent_planned_totals(reporter):
    result = reporter.return_counts([], None)
    assert result["queries_planned"] is None
    assert result["queries_not_run"] is None
    assert result["enrollments_planned"] is None
    assert result["all_planned_operations_terminal"] is None


@pytest.mark.parametrize(
    "planned",
    [
        {"enrollments": 1, "queries": 0},
        {"enrollments": True, "queries": 1},
        {"enrollments": -1, "queries": 1},
    ],
)
def test_inconsistent_return_plan_is_not_silently_truncated(reporter, planned):
    with pytest.raises(ValueError, match="invalid return phase plan"):
        reporter.return_counts([probe("returning")], planned)


def summary_source(rows):
    return {
        "status": "complete",
        "split": "test",
        "operations": rows,
        "stages": [
            {
                "gallery_size_planned": 5,
                "gallery_size_enrolled": 5,
                "enrollment_failed": 0,
                "counts": {"known_planned": len(rows), "unknown_planned": 0},
                "rates": {},
            }
        ],
        "return_phase": [],
    }


def test_fresh_train_clean_source_is_not_dropped_from_complete_strata(reporter):
    rows = [
        {**probe("A"), "source_split": "train-clean-100"},
        {**probe("B", failed=True), "source_split": "train-clean-100"},
    ]
    summary = reporter.summarize(summary_source(rows))
    counts = summary["stages"][0]["by_source_split"]["train-clean-100"]
    assert counts["known_planned"] == 2
    assert counts["known_correct"] == counts["known_job_failed"] == 1


def test_preprocessing_aggregate_uses_only_bounded_labels_for_successful_jobs(reporter):
    values = [
        "vad-windows-v1",
        "vad-packed-fallback-v1",
        None,
        "private-untrusted-value",
        {"private": "value"},
        ["private-list"],
        True,
    ]
    rows = []
    for index, version in enumerate(values):
        row = probe(str(index))
        row["result"]["preprocessing_version"] = version
        row["result"]["quality"] = {"private-extra": "must-not-escape"}
        rows.append(row)
    rows.append(probe("missing"))
    rows.append({**probe("malformed"), "result": None})
    rows.append(probe("failed", failed=True))
    pending = probe("pending")
    pending.update(status="pending", result={"preprocessing_version": "vad-windows-v1"})
    rows.append(pending)
    summary = reporter.summarize(summary_source(rows))
    assert summary["preprocessing_version_counts"] == {
        "vad-windows-v1": 1,
        "vad-packed-fallback-v1": 1,
        "unreported_or_unsupported": 7,
    }
    assert "private" not in str(summary) and "must-not-escape" not in str(summary)
