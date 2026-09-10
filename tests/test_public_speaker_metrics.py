"""Exact open-set metrics and strict offline evidence boundaries."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
POLICY = {"match_threshold": 0.55, "new_threshold": 0.45, "margin": 0.1}
MODEL = "speechbrain/spkrec-ecapa-voxceleb"
REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"


@pytest.fixture
def metrics():
    spec = importlib.util.spec_from_file_location(
        "speaker_metrics", ROOT / "scripts/speaker_metrics.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def fixture(known=None, unknown=None, sizes=None, returns=False):
    known = {"A": 2, "B": 2} if known is None else known
    unknown = {"U": 2} if unknown is None else unknown
    gallery = list(known)
    sizes = [len(gallery)] if sizes is None else sizes
    rows = []

    def add(person, role, index):
        identifier = f"private-{person}-{role}-{index}"
        rows.append(
            {
                "id": identifier,
                "speaker_id": person,
                "role": role,
                "source_split": "test-clean",
                "chapter_id": f"chapter-{person}-{role}",
                "source_utterance_ids": [f"utterance-{identifier}"],
                "path": f"clips/{identifier}.wav",
                "sha256": hashlib.sha256(identifier.encode()).hexdigest(),
                "duration_seconds": 30.0 if role in ("enrollment", "new_enrollment") else 15.0,
            }
        )

    for person, count in known.items():
        add(person, "enrollment", 0)
        for index in range(count):
            add(person, "known_query", index)
    for person, count in unknown.items():
        for index in range(count):
            add(person, "unknown_query", index)
    if returns:
        add(next(iter(unknown)), "new_enrollment", 0)
        add(next(iter(unknown)), "return_query", 0)
    manifest = {
        "schema_version": 1,
        "dataset_id": "fixture",
        "language": "en",
        "split": "test",
        "gallery_order": gallery,
        "unknown_order": list(unknown),
        "recordings": rows,
    }
    if returns:
        manifest["returning_speaker_id"] = next(iter(unknown))
    operations = []

    def op(row, stage):
        purpose = "enroll" if row["role"] in ("enrollment", "new_enrollment") else "identify"
        operation = {
            "operation_id": f"{stage}:{purpose}:{row['id']}",
            "recording_id": row["id"],
            **{
                key: row[key]
                for key in (
                    "speaker_id",
                    "role",
                    "source_split",
                    "chapter_id",
                    "source_utterance_ids",
                    "duration_seconds",
                )
            },
            "source_sha256": row["sha256"],
            "stage": stage,
            "purpose": purpose,
            "kind": "unknown" if row["role"] == "unknown_query" else "known",
            "status": "succeeded",
            "job_public_id": f"job-{len(operations)}",
            "attempt_count": 1,
            "result": {
                "model_id": MODEL,
                "model_revision": REVISION,
                "policy": POLICY,
                "profile_name": "SECRET PRIVATE NAME",
                "profile_public_id": f"profile-{row['speaker_id']}",
                "decision": "enrolled",
            },
        }
        if purpose == "identify":
            decide(operation, "unknown" if operation["kind"] == "unknown" else row["speaker_id"])
        operations.append(operation)

    for row in rows:
        if row["role"] == "enrollment" and row["speaker_id"] in gallery[: max(sizes)]:
            op(row, "enrollment")
    for size in sizes:
        for row in rows:
            if (
                row["role"] == "unknown_query"
                or row["role"] == "known_query"
                and row["speaker_id"] in gallery[:size]
            ):
                op(row, size)
    for row in rows:
        if row["role"] in ("new_enrollment", "return_query"):
            op(row, "return")
    source = {
        "schema_version": 1,
        "status": "complete",
        "dataset_id": "fixture",
        "split": "test",
        "model_id": MODEL,
        "model_revision": REVISION,
        "frozen_policy": POLICY,
        "binding": {
            "manifest_sha256": canonical(manifest),
            "gallery_sizes": sizes,
            "policy": POLICY,
            "model_revision": REVISION,
            "tenant_id": "SECRET-TENANT",
        },
        "operations": operations,
        "stages": [{"gallery_size_planned": size} for size in sizes],
        "return_phase": [row for row in operations if row["stage"] == "return"],
        "return_phase_planned": {"enrollments": int(returns), "queries": int(returns)},
    }
    return source, manifest


def decide(row, prediction):
    if prediction in ("failed", "pending"):
        row.update(status=prediction, result=None)
        row.pop("decision", None)
        row.pop("predicted_speaker_id", None)
        return
    decision = prediction if prediction in ("unknown", "ambiguous") else "recognized"
    row.update(
        status="succeeded",
        decision=decision,
        predicted_speaker_id=prediction if decision == "recognized" else None,
    )
    row["result"].update(
        decision=decision,
        profile_public_id=f"profile-{prediction}" if decision == "recognized" else None,
    )


def probes(source):
    return [row for row in source["operations"] if type(row["stage"]) is int]


def stage(metrics, source, manifest):
    return metrics.summarize_metrics(source, manifest)["stages"][0]


def test_documented_exact_six_probe_example(metrics):
    source, manifest = fixture()
    for row, prediction in zip(
        probes(source), ["A", "B", "B", "unknown", "B", "unknown"], strict=True
    ):
        decide(row, prediction)
    actual = stage(metrics, source, manifest)
    assert actual["identity"] == {
        "true_positive": 2,
        "false_positive": 2,
        "false_negative": 2,
        "precision": 0.5,
        "recall": 0.5,
        "micro_f1": 0.5,
        "macro_f1": pytest.approx(8 / 15),
    }
    assert actual["unknown"]["f1"] == 0.5
    assert actual["voiceup_score"] == pytest.approx(1600 / 31)
    assert actual["decision_coverage"] == 1
    assert actual["outcome_matrix"] == {
        "known": {
            "correct_identity": 2,
            "wrong_identity": 1,
            "unknown": 1,
            "ambiguous": 0,
            "failed": 0,
        },
        "unknown": {
            "correct_identity": 0,
            "wrong_identity": 1,
            "unknown": 1,
            "ambiguous": 0,
            "failed": 0,
        },
    }


def test_uneven_support_macro_and_failed_unknown(metrics):
    source, manifest = fixture({"A": 3, "B": 2}, {"U": 3})
    for row, prediction in zip(
        probes(source),
        ["A", "B", "unknown", "B", "ambiguous", "unknown", "A", "failed"],
        strict=True,
    ):
        decide(row, prediction)
    actual = stage(metrics, source, manifest)
    assert actual["identity"]["micro_f1"] == pytest.approx(4 / 9)
    assert actual["identity"]["macro_f1"] == 0.45
    assert actual["unknown"]["f1"] == 0.4
    assert actual["voiceup_score"] == pytest.approx(720 / 17)
    assert actual["decision_coverage"] == 0.75
    assert actual["rates"]["FPIR_observed_lower_bound"] == pytest.approx(1 / 3)
    assert actual["rates"]["FPIR_worst_case_upper_bound"] == pytest.approx(2 / 3)


def test_failed_enrollment_stays_supported_without_double_penalty(metrics):
    source, manifest = fixture({"A": 1, "B": 1}, {"U": 1})
    decide(source["operations"][1], "failed")
    decide(probes(source)[1], "failed")
    actual = stage(metrics, source, manifest)
    assert actual["all_planned_operations_terminal"] is True
    assert actual["enrollment_coverage"] == 0.5
    assert actual["identity"]["recall"] == 0.5
    assert actual["identity"]["macro_f1"] == 0.5
    assert actual["voiceup_score"] == pytest.approx(200 / 3)


@pytest.mark.parametrize("prediction", ["unknown", "ambiguous", "failed"])
def test_no_correct_identity_cannot_receive_positive_score(metrics, prediction):
    source, manifest = fixture()
    for row in probes(source):
        decide(row, prediction)
    actual = stage(metrics, source, manifest)
    assert actual["identity"]["precision"] is None
    assert actual["identity"]["recall"] == 0
    assert (
        actual["identity"]["micro_f1"]
        == actual["identity"]["macro_f1"]
        == actual["voiceup_score"]
        == 0
    )
    if prediction != "unknown":
        assert actual["unknown"]["f1"] == actual["decision_coverage"] == 0


@pytest.mark.parametrize("known,unknown", [({}, {"U": 1}), ({"A": 1}, {}), ({}, {})])
def test_absent_classes_are_undefined(metrics, known, unknown):
    source, manifest = fixture(known, unknown)
    actual = stage(metrics, source, manifest)
    assert actual["voiceup_score"] is None
    if not known:
        assert actual["identity"]["macro_f1"] is None
        assert actual["identity"]["recall"] is None
    if not unknown:
        assert actual["unknown"]["f1"] is None


@pytest.mark.parametrize(
    "target,status",
    [
        ("probe", "missing"),
        ("probe", "pending"),
        ("enrollment", "missing"),
        ("enrollment", "pending"),
    ],
)
def test_incomplete_stage_exposes_counts_and_null_scores(metrics, target, status):
    source, manifest = fixture()
    row = probes(source)[-1] if target == "probe" else source["operations"][0]
    if target == "enrollment":
        for query in probes(source):
            if query["speaker_id"] == row["speaker_id"]:
                decide(query, "failed")
    if status == "missing":
        source["operations"].remove(row)
    else:
        decide(row, "pending")
    actual = stage(metrics, source, manifest)
    assert actual["all_planned_operations_terminal"] is False
    assert actual["voiceup_score"] is None
    assert all(
        actual["identity"][key] is None for key in ("precision", "recall", "micro_f1", "macro_f1")
    )
    assert all(actual["unknown"][key] is None for key in ("precision", "recall", "f1"))
    assert all(value is None for value in actual["rates"].values())
    assert actual["decision_coverage"] is actual["enrollment_coverage"] is None
    assert actual["enrollment" if target == "enrollment" else "probes"][status] == 1


def test_nested_galleries_reuse_probes_without_pooling(metrics):
    source, manifest = fixture(sizes=[1, 2], returns=True)
    actual = metrics.summarize_metrics(source, manifest)
    assert [row["support"]["known_probes"] for row in actual["stages"]] == [2, 4]
    assert actual["return_phase"]["queries"] == 1
    assert "voiceup_score" not in actual
    assert all(row["voiceup_score"] == 100 for row in actual["stages"])


def test_return_failure_does_not_change_main_score(metrics):
    source, manifest = fixture(returns=True)
    for row in source["return_phase"]:
        decide(row, "failed")
    actual = metrics.summarize_metrics(source, manifest)
    assert actual["stages"][0]["voiceup_score"] == 100
    assert actual["return_phase"]["enrollment_failed"] == 1
    assert actual["return_phase"]["query_failed"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "manifest_hash",
        "duplicate_id",
        "duplicate_semantic",
        "duplicate_job",
        "truth",
        "role",
        "hash",
        "chapter",
        "utterance",
        "duration",
        "purpose",
        "stage",
        "kind",
        "decision",
        "unmapped",
        "prediction",
        "null_profile",
        "unknown_profile",
        "unenrolled",
        "future_profile",
        "boolean_stage",
        "unsupported_person",
        "negative_count",
        "boolean_count",
        "forged_count",
        "forged_rate",
        "return_view",
        "return_plan",
        "bad_status",
        "bad_model",
        "bad_policy",
    ],
)
def test_rejects_malformed_or_forged_evidence(metrics, mutation):
    source, manifest = fixture(sizes=[1, 2], returns=True)
    row = probes(source)[0]
    if mutation == "manifest_hash":
        manifest["dataset_id"] = "changed"
    elif mutation in ("duplicate_id", "duplicate_semantic", "duplicate_job"):
        duplicate = copy.deepcopy(row)
        if mutation != "duplicate_id":
            duplicate["operation_id"] = "distinct"
        if mutation == "duplicate_semantic":
            duplicate["job_public_id"] = "distinct-job"
        source["operations"].append(duplicate)
    elif mutation in (
        "truth",
        "role",
        "hash",
        "chapter",
        "utterance",
        "duration",
        "purpose",
        "stage",
        "kind",
    ):
        key = {
            "truth": "speaker_id",
            "hash": "source_sha256",
            "chapter": "chapter_id",
            "utterance": "source_utterance_ids",
            "duration": "duration_seconds",
        }.get(mutation, mutation)
        row[key] = (
            ["wrong"]
            if mutation == "utterance"
            else 99
            if mutation in ("duration", "stage")
            else "wrong"
        )
    elif mutation == "decision":
        row["result"]["decision"] = "enrolled"
    elif mutation == "unmapped":
        row["result"]["profile_public_id"] = "missing-profile"
    elif mutation == "prediction":
        row["predicted_speaker_id"] = "B"
    elif mutation == "null_profile":
        row["result"]["profile_public_id"] = None
    elif mutation == "unknown_profile":
        decide(row, "unknown")
        row["result"]["profile_public_id"] = "profile-A"
    elif mutation == "unenrolled":
        decide(source["operations"][0], "failed")
    elif mutation == "future_profile":
        decide(row, "B")
    elif mutation == "boolean_stage":
        row["stage"] = True
    elif mutation == "unsupported_person":
        manifest["recordings"] = [
            item
            for item in manifest["recordings"]
            if not (item["speaker_id"] == "B" and item["role"] == "known_query")
        ]
        source["binding"]["manifest_sha256"] = canonical(manifest)
    elif mutation in ("negative_count", "boolean_count", "forged_count"):
        source["stages"][0]["counts"] = {
            "known_correct": {"negative_count": -1, "boolean_count": True, "forged_count": 999}[
                mutation
            ]
        }
    elif mutation == "forged_rate":
        source["stages"][0]["rates"] = {"DIR": 5.0}
    elif mutation == "return_view":
        source["return_phase"] = []
    elif mutation == "return_plan":
        source["return_phase_planned"]["queries"] = True
    elif mutation == "bad_status":
        row["status"] = "SECRET-STATUS"
    elif mutation == "bad_model":
        source["model_id"] = "SECRET-MODEL"
    elif mutation == "bad_policy":
        source["frozen_policy"] = {**POLICY, "match_threshold": True}
    with pytest.raises(ValueError):
        metrics.summarize_metrics(source, manifest)


def test_supplied_summaries_must_equal_recomputation(metrics):
    source, manifest = fixture()
    actual = stage(metrics, source, manifest)
    source["stages"][0].update(
        counts=actual["counts"], rates=actual["rates"], gallery_size_enrolled=2, enrollment_failed=0
    )
    assert stage(metrics, source, manifest)["voiceup_score"] == 100


@pytest.mark.parametrize(
    "field,value",
    [
        ("error_counts", {"private_error": True}),
        ("error_counts", {"private_error": -1}),
        ("error_counts", {"private_error": 99}),
        ("gallery_size_enrolled", True),
        ("enrollment_failed", -1),
        ("complete_decisions", 1),
    ],
)
def test_all_supplied_stage_counters_are_checked(metrics, field, value):
    source, manifest = fixture()
    row = probes(source)[0]
    decide(row, "failed")
    row["error_code"] = "private_error"
    source["stages"][0][field] = value
    with pytest.raises(ValueError):
        metrics.summarize_metrics(source, manifest)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_hash",
        "duplicate_path",
        "duplicate_utterance",
        "duplicate_person",
        "duplicate_recording",
        "role_leakage",
        "unsafe_path",
        "nan_duration",
        "bool_duration",
        "bool_sizes",
        "overlap",
        "unknown_no_support",
        "unpaired_return",
        "negative_attempt",
        "boolean_attempt",
        "nonterminal_result",
        "return_missing_plan_key",
    ],
)
def test_manifest_and_operation_boundaries(metrics, mutation):
    source, manifest = fixture(returns=True)
    rows = manifest["recordings"]
    if mutation.startswith("duplicate_"):
        field = {
            "duplicate_hash": "sha256",
            "duplicate_path": "path",
            "duplicate_utterance": "source_utterance_ids",
            "duplicate_recording": "id",
        }.get(mutation)
        if field:
            rows[1][field] = rows[0][field]
        else:
            manifest["gallery_order"].append("A")
    elif mutation == "role_leakage":
        rows[1]["chapter_id"] = rows[0]["chapter_id"]
    elif mutation == "unsafe_path":
        rows[0]["path"] = "../private.wav"
    elif mutation in ("nan_duration", "bool_duration"):
        rows[0]["duration_seconds"] = float("nan") if mutation == "nan_duration" else True
    elif mutation == "bool_sizes":
        source["binding"]["gallery_sizes"] = [True]
    elif mutation == "overlap":
        manifest["unknown_order"].append("A")
    elif mutation == "unknown_no_support":
        manifest["unknown_order"].append("unsupported")
    elif mutation == "unpaired_return":
        manifest["recordings"] = [row for row in rows if row["role"] != "return_query"]
    elif mutation in ("negative_attempt", "boolean_attempt"):
        source["operations"][0]["attempt_count"] = -1 if mutation == "negative_attempt" else True
    elif mutation == "nonterminal_result":
        source["operations"][0]["status"] = "pending"
    elif mutation == "return_missing_plan_key":
        del source["return_phase_planned"]["queries"]
    source["binding"]["manifest_sha256"] = canonical(manifest)
    with pytest.raises(ValueError):
        metrics.summarize_metrics(source, manifest)


def test_missing_newcomer_query_is_separate_from_completed_main_score(metrics):
    source, manifest = fixture(returns=True)
    missing = source["return_phase"].pop()
    source["operations"].remove(missing)
    actual = metrics.summarize_metrics(source, manifest)
    assert actual["status"] == "incomplete"
    assert actual["stages"][0]["voiceup_score"] == 100
    assert actual["return_phase"]["probes"]["missing"] == 1
    assert not actual["return_phase"]["all_planned_operations_terminal"]


def test_legitimate_error_counter_is_checked_without_publishing_label(metrics):
    source, manifest = fixture()
    row = probes(source)[0]
    decide(row, "failed")
    row["error_code"] = "SECRET-PRIVATE-ERROR"
    source["stages"][0]["error_counts"] = {"SECRET-PRIVATE-ERROR": 1}
    actual = metrics.summarize_metrics(source, manifest)
    assert actual["stages"][0]["counts"]["known_job_failed"] == 1
    assert "SECRET" not in json.dumps(actual)


def test_quality_and_unclassified_failures_have_bounded_labels(metrics):
    source, manifest = fixture(returns=True)
    known, unknown = probes(source)[0], probes(source)[-1]
    for row, error in (
        (known, "insufficient_speech"),
        (unknown, "SECRET-FAILURE"),
        (source["return_phase"][0], "clipped_audio"),
        (source["return_phase"][1], None),
    ):
        decide(row, "failed")
        row["error_code"] = error
    actual = metrics.summarize_metrics(source, manifest)
    gallery = actual["stages"][0]
    assert gallery["error_counts"] == {"insufficient_speech": 1, "unreported_or_unsupported": 1}
    assert gallery["failure_counts"] == {
        "known": {"quality": 1, "other_or_unclassified": 0},
        "unknown": {"quality": 0, "other_or_unclassified": 1},
    }
    assert actual["return_phase"]["enrollment_quality_failed"] == 1
    assert actual["return_phase"]["query_other_or_unclassified_failed"] == 1
    assert "SECRET" not in json.dumps(actual)


def test_pending_error_payload_does_not_count_as_failed(metrics):
    source, manifest = fixture()
    row = probes(source)[-1]
    decide(row, "pending")
    row["error_code"] = "insufficient_speech"
    actual = stage(metrics, source, manifest)
    assert actual["error_counts"] == {}
    assert actual["failure_counts"]["unknown"] == {"quality": 0, "other_or_unclassified": 0}


def test_submit_capacity_failure_is_named_without_job_or_main_score_penalty(metrics):
    source, manifest = fixture(returns=True)
    rejected, returned = source["return_phase"]
    decide(rejected, "failed")
    rejected.update(error_code="profile_limit", attempt_count=0)
    rejected.pop("job_public_id")
    decide(returned, "unknown")
    actual = metrics.summarize_metrics(source, manifest)
    assert actual["source_run_complete"] is True and actual["status"] == "complete"
    assert actual["stages"][0]["voiceup_score"] == 100
    assert actual["stages"][0]["gallery_size_enrolled"] == 2
    returns = actual["return_phase"]
    assert returns["enrollment_succeeded"] == 0 and returns["enrollment_failed"] == 1
    assert returns["enrollment_quality_failed"] == 0
    assert returns["enrollment_other_or_unclassified_failed"] == 1
    assert returns["error_counts"]["enrollment"] == {"profile_limit": 1}
    assert returns["correct"] == 0 and returns["unknown"] == 1


def test_read_only_metrics_still_accept_historical_gallery_above_fifty(metrics):
    source, manifest = fixture(known={f"person-{index}": 1 for index in range(51)})
    original = copy.deepcopy((source, manifest))
    actual = metrics.summarize_metrics(source, manifest)
    assert actual["stages"][0]["gallery_size_planned"] == 51
    assert actual["stages"][0]["gallery_size_enrolled"] == 51
    assert actual["stages"][0]["identity"]["recall"] == 1
    assert (source, manifest) == original


def test_metrics_support_two_hundred_people_per_role_without_mutating_inputs(metrics):
    source, manifest = fixture(
        known={f"person-{index}": 3 for index in range(200)},
        unknown={f"unknown-{index}": 1 for index in range(200)},
        sizes=[50, 100, 200],
        returns=True,
    )
    original = copy.deepcopy((source, manifest))
    actual = metrics.summarize_metrics(source, manifest)
    assert actual["status"] == "complete"
    assert [row["gallery_size_enrolled"] for row in actual["stages"]] == [50, 100, 200]
    assert all(row["voiceup_score"] == 100 for row in actual["stages"])
    assert all(row["support"]["unknown_speakers"] == 200 for row in actual["stages"])
    assert actual["return_phase"]["correct"] == 1
    assert (source, manifest) == original


@pytest.mark.parametrize("role", ["known", "unknown"])
def test_metrics_reject_per_role_manifest_resource_budget_over_two_hundred(metrics, role):
    options = {role: {f"person-{index}": 1 for index in range(201)}}
    source, manifest = fixture(**options)
    with pytest.raises(ValueError, match="invalid_person_order"):
        metrics.summarize_metrics(source, manifest)


def test_metrics_keep_recording_and_operation_resource_budgets(metrics):
    _, manifest = fixture(
        known={f"person-{index}": 3 for index in range(200)},
        unknown={f"unknown-{index}": 1 for index in range(200)},
    )
    with pytest.raises(ValueError, match="operation_limit"):
        metrics.validate_manifest(manifest, list(range(1, 201)))
    manifest["recordings"] = [{}] * 1501
    with pytest.raises(ValueError, match="invalid_recordings"):
        metrics.validate_manifest(manifest, [200])


@pytest.mark.parametrize(
    "status,error",
    [
        ("incomplete", None),
        ("incomplete", "SECRET-GALLERY-ERROR"),
        ("complete", "SECRET-GALLERY-ERROR"),
    ],
)
def test_producer_final_invariant_failure_withholds_terminal_scores(metrics, status, error):
    source, manifest = fixture()
    source.update(status=status, error_code=error)
    actual = metrics.summarize_metrics(source, manifest)
    assert actual["status"] == "incomplete"
    assert actual["source_run_complete"] is False
    gallery = actual["stages"][0]
    assert gallery["all_planned_operations_terminal"] is True
    assert gallery["metrics_complete"] is False
    assert gallery["counts"]["known_correct"] == 4
    assert (
        gallery["voiceup_score"]
        is gallery["decision_coverage"]
        is gallery["enrollment_coverage"]
        is None
    )
    assert all(value is None for value in gallery["rates"].values())
    assert all(
        gallery["identity"][key] is None for key in ("precision", "recall", "micro_f1", "macro_f1")
    )
    assert all(gallery["unknown"][key] is None for key in ("precision", "recall", "f1"))
    assert "SECRET" not in json.dumps(actual)


@pytest.mark.parametrize("status", [None, True, 1, "SECRET-STATUS", [], {}])
def test_invalid_producer_status_is_rejected(metrics, status):
    source, manifest = fixture()
    source["status"] = status
    with pytest.raises(ValueError):
        metrics.summarize_metrics(source, manifest)


def test_anonymous_deterministic_output_contains_no_private_labels(metrics):
    source, manifest = fixture(returns=True)
    source["operations"][0]["error_code"] = "SECRET-ERROR"
    actual = metrics.summarize_metrics(source, manifest)
    encoded = json.dumps(actual)
    assert actual == metrics.summarize_metrics(source, manifest)
    assert actual["schema_version"] == 2
    assert actual["metrics_protocol"] == "voiceup-open-set-v1"
    for forbidden in (
        "SECRET",
        "profile-",
        "private-",
        "utterance-",
        "speaker_id",
        "tenant_id",
        "chapter-",
        "clips/",
    ):
        assert forbidden not in encoded


def invoke(tmp_path, source, manifest, extra=()):
    source_path, manifest_path, output = [
        tmp_path / name for name in ("input.json", "manifest.json", "output.json")
    ]
    source_path.write_text(json.dumps(source), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=4), encoding="utf-8")
    command = [
        sys.executable,
        str(ROOT / "scripts/report-public-speakers.py"),
        "--input",
        str(source_path),
        "--output",
        str(output),
        "--metrics-protocol",
        "voiceup-open-set-v1",
        "--manifest",
        str(manifest_path),
        *extra,
    ]
    return subprocess.run(command, capture_output=True, text=True, timeout=20), output, command


def test_actual_cli_canonical_binding_offline_and_no_overwrite(tmp_path):
    source, manifest = fixture()
    completed, output, command = invoke(tmp_path, source, manifest)
    assert completed.returncode == 0, completed.stderr
    before = output.read_bytes()
    actual = json.loads(before)
    assert actual["schema_version"] == 2
    assert actual["manifest_sha256"] == canonical(manifest)
    assert actual["stages"][0]["voiceup_score"] == 100
    repeated = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert repeated.returncode != 0
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    "case",
    [
        "no_manifest",
        "no_protocol",
        "bad_protocol",
        "mismatch",
        "manifest_output",
        "duplicate_json_key",
        "manifest_limit",
    ],
)
def test_cli_rejects_invalid_input_without_output(tmp_path, case):
    source, manifest = fixture()
    source_path, manifest_path, output = [
        tmp_path / name for name in ("input.json", "manifest.json", "output.json")
    ]
    source_path.write_text(json.dumps(source), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    command = [
        sys.executable,
        str(ROOT / "scripts/report-public-speakers.py"),
        "--input",
        str(source_path),
        "--output",
        str(output),
    ]
    if case != "no_protocol":
        command += [
            "--metrics-protocol",
            "bad" if case == "bad_protocol" else "voiceup-open-set-v1",
        ]
    if case != "no_manifest":
        command += ["--manifest", str(manifest_path)]
    if case == "mismatch":
        manifest_path.write_text("{}", encoding="utf-8")
    if case == "manifest_output":
        command[command.index("--output") + 1] = str(manifest_path)
    if case == "duplicate_json_key":
        source_path.write_text('{"operations": [], "operations": []}', encoding="utf-8")
    if case == "manifest_limit":
        manifest_path.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    before = manifest_path.read_bytes()
    completed = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert completed.returncode != 0
    assert not output.exists()
    assert manifest_path.read_bytes() == before
    assert "SECRET" not in completed.stderr + completed.stdout
