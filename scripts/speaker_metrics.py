"""Manifest-bound, anonymous offline metrics for voiceup-open-set-v1.

This module never reads audio, contacts a service, or trusts aggregate counters.
Its input is private; its output contains only bounded protocol metadata and counts.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import PurePosixPath, PureWindowsPath

PROTOCOL = "voiceup-open-set-v1"
MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
MODEL_REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"
ROLES = {"enrollment", "known_query", "unknown_query", "new_enrollment", "return_query"}
TERMINAL = {"succeeded", "failed"}
STATUSES = TERMINAL | {"pending", "queued", "running"}
SPLITS = {"dev-clean", "dev-other", "test-clean", "test-other", "train-clean-100"}
OUTCOMES = ("correct_identity", "wrong_identity", "unknown", "ambiguous", "failed")
# Offline input budgets; these do not limit the application's profile population.
MAX_MANIFEST_PEOPLE_PER_ROLE = 200
MAX_RECORDINGS = 1500
MAX_OPERATIONS = 20000
QUALITY_ERRORS = {
    "insufficient_speech",
    "inconsistent_audio",
    "clipped_audio",
    "invalid_audio",
    "audio_limit",
    "unsupported_audio",
}
NAMED_ERRORS = QUALITY_ERRORS | {"profile_limit"}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def text(value):
    return isinstance(value, str) and 0 < len(value.strip()) <= 250


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def counter(value):
    return type(value) is int and value >= 0


def canonical_hash(value):
    try:
        data = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (ValueError, TypeError, RecursionError):
        raise ValueError("invalid_json_value") from None
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def strict_json(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("invalid_json_constant")

    try:
        return json.loads(payload, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("invalid_json") from None


def policy(value):
    require(
        isinstance(value, dict) and set(value) == {"match_threshold", "new_threshold", "margin"},
        "invalid_policy",
    )
    require(all(number(item) for item in value.values()), "invalid_policy")
    require(
        -1 <= value["new_threshold"] < value["match_threshold"] <= 1 and 0 <= value["margin"] <= 2,
        "invalid_policy",
    )
    return {key: float(value[key]) for key in ("match_threshold", "new_threshold", "margin")}


def validate_manifest(manifest, sizes):
    require(isinstance(manifest, dict), "invalid_manifest")
    require(
        type(manifest.get("schema_version")) is int and manifest["schema_version"] == 1,
        "invalid_manifest",
    )
    require(
        text(manifest.get("dataset_id"))
        and manifest.get("language") == "en"
        and manifest.get("split") in {"calibration", "test"},
        "invalid_manifest",
    )
    gallery, unknown = manifest.get("gallery_order"), manifest.get("unknown_order")
    for values in (gallery, unknown):
        require(
            isinstance(values, list)
            and len(values) <= MAX_MANIFEST_PEOPLE_PER_ROLE
            and all(text(item) for item in values),
            "invalid_person_order",
        )
        require(len(set(values)) == len(values), "duplicate_person")
    require(not set(gallery) & set(unknown), "known_unknown_overlap")
    require(
        isinstance(sizes, list) and 1 <= len(sizes) <= MAX_MANIFEST_PEOPLE_PER_ROLE + 1,
        "invalid_gallery_sizes",
    )
    require(
        all(type(size) is int and 0 <= size <= len(gallery) for size in sizes),
        "invalid_gallery_sizes",
    )
    require(
        sizes == sorted(set(sizes)) and (0 not in sizes or not gallery), "invalid_gallery_sizes"
    )
    rows = manifest.get("recordings")
    require(isinstance(rows, list) and len(rows) <= MAX_RECORDINGS, "invalid_recordings")
    by_id, hashes, paths, utterances, chapters, counts = {}, set(), set(), set(), {}, Counter()
    for row in rows:
        require(isinstance(row, dict), "invalid_recording")
        require(
            all(
                text(row.get(key))
                for key in ("id", "speaker_id", "source_split", "chapter_id", "path")
            ),
            "invalid_recording",
        )
        require(row.get("role") in ROLES and row["source_split"] in SPLITS, "invalid_recording")
        digest, duration = row.get("sha256"), row.get("duration_seconds")
        require(
            isinstance(digest, str) and re.fullmatch("[0-9a-f]{64}", digest) is not None,
            "invalid_source_hash",
        )
        require(number(duration) and 0 < duration <= 120, "invalid_duration")
        path = row["path"]
        require(
            "\\" not in path
            and "\x00" not in path
            and not PurePosixPath(path).is_absolute()
            and not PureWindowsPath(path).drive
            and ".." not in PurePosixPath(path).parts,
            "unsafe_audio_path",
        )
        require(
            row["id"] not in by_id and digest not in hashes and path not in paths,
            "duplicate_recording",
        )
        source_ids = row.get("source_utterance_ids")
        require(
            isinstance(source_ids, list)
            and 1 <= len(source_ids) <= 500
            and all(text(item) for item in source_ids),
            "invalid_utterances",
        )
        require(
            len(set(source_ids)) == len(source_ids) and not utterances.intersection(source_ids),
            "duplicate_utterance",
        )
        key = (row["speaker_id"], row["source_split"], row["chapter_id"])
        require(key not in chapters or chapters[key] == row["role"], "source_role_leakage")
        chapters[key] = row["role"]
        by_id[row["id"]] = row
        hashes.add(digest)
        paths.add(path)
        utterances.update(source_ids)
        counts[row["speaker_id"], row["role"]] += 1
        allowed = gallery if row["role"] in {"enrollment", "known_query"} else unknown
        require(row["speaker_id"] in allowed, "unexpected_person")
    for person in gallery:
        require(
            counts[person, "enrollment"] == 1 and counts[person, "known_query"] >= 1,
            "unsupported_known_person",
        )
    require(
        all(counts[person, "unknown_query"] >= 1 for person in unknown),
        "unsupported_unknown_person",
    )
    new_people = {row["speaker_id"] for row in rows if row["role"] == "new_enrollment"}
    returned = {row["speaker_id"] for row in rows if row["role"] == "return_query"}
    require(
        new_people == returned
        and all(counts[person, "new_enrollment"] == 1 for person in new_people),
        "invalid_return_plan",
    )
    if "returning_speaker_id" in manifest:
        require(new_people == {manifest["returning_speaker_id"]}, "invalid_return_plan")
    expected = {}
    for row in rows:
        role = row["role"]
        if role == "enrollment" and row["speaker_id"] in gallery[: max(sizes)]:
            expected["enrollment", "enroll", row["id"]] = row
        elif role in {"new_enrollment", "return_query"}:
            expected["return", "enroll" if role == "new_enrollment" else "identify", row["id"]] = (
                row
            )
        for size in sizes:
            if (
                role == "unknown_query"
                or role == "known_query"
                and row["speaker_id"] in gallery[:size]
            ):
                expected[size, "identify", row["id"]] = row
    require(len(expected) <= MAX_OPERATIONS, "operation_limit")
    return expected


def validate_operations(source, manifest, expected, sizes, frozen_policy):
    operations = source.get("operations")
    require(
        isinstance(operations, list) and len(operations) <= MAX_OPERATIONS, "invalid_operations"
    )
    observed, ids, jobs = {}, set(), set()
    for operation in operations:
        require(isinstance(operation, dict), "invalid_operation")
        stage = operation.get("stage")
        require(type(stage) is int or stage in ("enrollment", "return"), "invalid_operation_stage")
        require(
            text(operation.get("operation_id")) and operation["operation_id"] not in ids,
            "duplicate_operation_id",
        )
        require(text(operation.get("recording_id")), "invalid_operation_recording")
        require(operation.get("purpose") in {"enroll", "identify"}, "invalid_operation_purpose")
        key = (stage, operation["purpose"], operation["recording_id"])
        require(key in expected and key not in observed, "unexpected_or_duplicate_operation")
        row = expected[key]
        for field in ("speaker_id", "role", "source_split", "chapter_id", "source_utterance_ids"):
            require(operation.get(field) == row[field], "operation_truth_mismatch")
        require(operation.get("source_sha256") == row["sha256"], "operation_source_hash_mismatch")
        require(
            number(operation.get("duration_seconds"))
            and operation["duration_seconds"] == row["duration_seconds"],
            "operation_duration_mismatch",
        )
        require(
            operation.get("kind") == ("unknown" if row["role"] == "unknown_query" else "known"),
            "operation_kind_mismatch",
        )
        require(operation.get("status") in STATUSES, "invalid_operation_status")
        job = operation.get("job_public_id")
        if job is not None:
            require(text(job) and job not in jobs, "invalid_or_duplicate_job")
            jobs.add(job)
        if "attempt_count" in operation:
            require(counter(operation["attempt_count"]), "invalid_attempt_count")
        result = operation.get("result")
        if operation["status"] == "succeeded":
            require(isinstance(result, dict), "missing_terminal_result")
            require(
                result.get("model_id") == MODEL_ID
                and result.get("model_revision") == MODEL_REVISION,
                "model_contract_mismatch",
            )
            require(policy(result.get("policy")) == frozen_policy, "policy_contract_mismatch")
        else:
            require(
                result is None
                and operation.get("decision") is None
                and operation.get("predicted_speaker_id") is None,
                "non_success_decision",
            )
        ids.add(operation["operation_id"])
        observed[key] = operation
    profile_people, profile_stage = {}, {}
    for key, operation in observed.items():
        if key[1] != "enroll" or operation["status"] != "succeeded":
            continue
        result = operation["result"]
        profile = result.get("profile_public_id")
        require(
            result.get("decision") == "enrolled" and text(profile), "invalid_enrollment_decision"
        )
        require(profile not in profile_people, "duplicate_enrollment_profile")
        profile_people[profile] = operation["speaker_id"]
        profile_stage[profile] = key[0]
    for key, operation in observed.items():
        if key[1] != "identify" or operation["status"] != "succeeded":
            continue
        result = operation["result"]
        decision = result.get("decision")
        require(
            decision in {"recognized", "unknown", "ambiguous"}
            and operation.get("decision") == decision,
            "invalid_identification_decision",
        )
        profile = result.get("profile_public_id")
        if decision == "recognized":
            require(text(profile) and profile in profile_people, "unmapped_prediction")
            predicted = profile_people[profile]
            require(operation.get("predicted_speaker_id") == predicted, "prediction_truth_mismatch")
            gallery = (
                set(manifest["gallery_order"][: key[0]])
                if type(key[0]) is int
                else set(manifest["gallery_order"][: max(sizes)])
                | {
                    item["speaker_id"]
                    for item in expected.values()
                    if item["role"] == "new_enrollment"
                }
            )
            require(
                predicted in gallery
                and (key[0] == "return" or profile_stage[profile] == "enrollment"),
                "prediction_outside_enrolled_gallery",
            )
        else:
            require(
                profile is None and operation.get("predicted_speaker_id") is None,
                "abstention_with_prediction",
            )
    returns = [row for row in operations if row["stage"] == "return"]
    if "return_phase" in source:
        view = source["return_phase"]
        require(isinstance(view, list) and len(view) == len(returns), "return_view_mismatch")
        require(
            all(isinstance(row, dict) and text(row.get("operation_id")) for row in view),
            "return_view_mismatch",
        )
        mapping = {row["operation_id"]: row for row in view}
        require(
            len(mapping) == len(view) and mapping == {row["operation_id"]: row for row in returns},
            "return_view_mismatch",
        )
    return observed


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def progress(keys, observed):
    statuses = Counter(observed[key]["status"] for key in keys if key in observed)
    present = sum(statuses.values())
    terminal = statuses["succeeded"] + statuses["failed"]
    return {
        "planned": len(keys),
        "observed": present,
        "succeeded": statuses["succeeded"],
        "failed": statuses["failed"],
        "pending": present - terminal,
        "missing": len(keys) - present,
        "terminal": terminal,
    }


def failure_summary(rows):
    errors = Counter()
    quality = unclassified = 0
    for row in rows:
        if row["status"] != "failed":
            continue
        code = row.get("error_code")
        is_quality = isinstance(code, str) and code in QUALITY_ERRORS
        errors[
            code if isinstance(code, str) and code in NAMED_ERRORS else "unreported_or_unsupported"
        ] += 1
        quality += int(is_quality)
        unclassified += int(not is_quality)
    return {"quality": quality, "other_or_unclassified": unclassified}, dict(sorted(errors.items()))


def f1(tp, fp, fn, support):
    return ratio(2 * tp, 2 * tp + fp + fn) if support else None


def check_mapping(supplied, calculated, *, rates=False):
    require(
        isinstance(supplied, dict) and set(supplied) <= set(calculated), "invalid_summary_fields"
    )
    for key, value in supplied.items():
        if rates:
            expected = calculated[key]
            require(
                value is None
                if expected is None
                else number(value) and math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12),
                "summary_rate_mismatch",
            )
        else:
            require(counter(value) and value == calculated[key], "summary_count_mismatch")


def summarize_stage(size, manifest, expected, observed):
    people = manifest["gallery_order"][:size]
    enroll_keys = [
        key
        for key, row in expected.items()
        if key[0] == "enrollment" and row["speaker_id"] in people
    ]
    query_keys = [key for key in expected if type(key[0]) is int and key[0] == size]
    enrollment, probes = progress(enroll_keys, observed), progress(query_keys, observed)
    complete = (
        enrollment["terminal"] == enrollment["planned"] and probes["terminal"] == probes["planned"]
    )
    known = sum(expected[key]["role"] == "known_query" for key in query_keys)
    unknown = len(query_keys) - known
    counts = {
        f"{kind}_{suffix}": 0
        for kind in ("known", "unknown")
        for suffix in ("completed", "job_failed", "recognized", "unknown", "ambiguous")
    }
    counts.update(
        known_planned=known,
        unknown_planned=unknown,
        known_correct=0,
        known_wrong=0,
        known_rejected=0,
        unknown_false_accepted=0,
    )
    matrix = {kind: dict.fromkeys(OUTCOMES, 0) for kind in ("known", "unknown")}
    individual = {person: {"tp": 0, "fp": 0, "support": 0} for person in people}
    for key in query_keys:
        truth = expected[key]
        kind = "known" if truth["role"] == "known_query" else "unknown"
        if kind == "known":
            individual[truth["speaker_id"]]["support"] += 1
        operation = observed.get(key)
        if operation is None or operation["status"] not in TERMINAL:
            continue
        counts[f"{kind}_completed"] += 1
        if operation["status"] == "failed":
            counts[f"{kind}_job_failed"] += 1
            matrix[kind]["failed"] += 1
            continue
        decision = operation["decision"]
        counts[f"{kind}_{decision}"] += 1
        if decision == "recognized":
            predicted = operation["predicted_speaker_id"]
            correct = kind == "known" and predicted == truth["speaker_id"]
            matrix[kind]["correct_identity" if correct else "wrong_identity"] += 1
            individual[predicted]["tp" if correct else "fp"] += 1
            counts[
                "known_correct"
                if correct
                else "known_wrong"
                if kind == "known"
                else "unknown_false_accepted"
            ] += 1
        else:
            matrix[kind][decision] += 1
            if kind == "known":
                counts["known_rejected"] += 1
    for kind, planned in (("known", known), ("unknown", unknown)):
        counts[f"{kind}_not_run"] = planned - counts[f"{kind}_completed"]
    rates = {
        "DIR": ratio(counts["known_correct"], known),
        "known_misidentification": ratio(counts["known_wrong"], known),
        "FPIR_observed_lower_bound": ratio(counts["unknown_false_accepted"], unknown),
        "FPIR_worst_case_upper_bound": ratio(
            counts["unknown_false_accepted"]
            + counts["unknown_job_failed"]
            + counts["unknown_not_run"],
            unknown,
        ),
        "unknown_detection_recall": ratio(counts["unknown_unknown"], unknown),
    }
    tp, fp, fn = (
        counts["known_correct"],
        counts["known_wrong"] + counts["unknown_false_accepted"],
        known - counts["known_correct"],
    )
    macro = (
        sum(
            f1(item["tp"], item["fp"], item["support"] - item["tp"], item["support"])
            for item in individual.values()
        )
        / len(individual)
        if individual
        else None
    )
    identity = {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, known),
        "micro_f1": f1(tp, fp, fn, known),
        "macro_f1": macro,
    }
    utp, ufp, ufn = (
        counts["unknown_unknown"],
        counts["known_unknown"],
        unknown - counts["unknown_unknown"],
    )
    unknown_metrics = {
        "true_positive": utp,
        "false_positive": ufp,
        "false_negative": ufn,
        "precision": ratio(utp, utp + ufp),
        "recall": ratio(utp, unknown),
        "f1": f1(utp, ufp, ufn, unknown),
    }
    uf1 = unknown_metrics["f1"]
    score = (
        None
        if macro is None or uf1 is None
        else 0.0
        if macro == 0 or uf1 == 0
        else 200 * macro * uf1 / (macro + uf1)
    )
    result = {
        "gallery_size_planned": size,
        "gallery_size_enrolled": enrollment["succeeded"],
        "enrollment_failed": enrollment["failed"],
        "support": {
            "known_speakers": len(people),
            "unknown_speakers": len(manifest["unknown_order"]),
            "known_probes": known,
            "unknown_probes": unknown,
        },
        "enrollment": enrollment,
        "probes": probes,
        "all_planned_operations_terminal": complete,
        "counts": counts,
        "rates": rates,
        "outcome_matrix": matrix,
        "identity": identity,
        "unknown": unknown_metrics,
        "enrollment_coverage": ratio(enrollment["succeeded"], enrollment["planned"])
        if complete
        else None,
        "decision_coverage": ratio(
            counts["known_recognized"]
            + counts["unknown_recognized"]
            + counts["known_unknown"]
            + counts["unknown_unknown"],
            known + unknown,
        )
        if complete
        else None,
        "voiceup_score": score if complete else None,
    }
    observed_probes = [observed[key] for key in query_keys if key in observed]
    result["failure_counts"] = {
        kind: failure_summary([row for row in observed_probes if row["kind"] == kind])[0]
        for kind in ("known", "unknown")
    }
    result["error_counts"] = failure_summary(observed_probes)[1]
    return result


def summarize_return(expected, observed):
    keys = [key for key in expected if key[0] == "return"]
    enroll = progress([key for key in keys if key[1] == "enroll"], observed)
    query = progress([key for key in keys if key[1] == "identify"], observed)
    outcomes = dict.fromkeys(OUTCOMES, 0)
    for key in keys:
        if key[1] != "identify" or key not in observed:
            continue
        row = observed[key]
        if row["status"] == "failed":
            outcomes["failed"] += 1
        elif row["status"] == "succeeded":
            decision = row["decision"]
            outcome = (
                (
                    "correct_identity"
                    if row["predicted_speaker_id"] == row["speaker_id"]
                    else "wrong_identity"
                )
                if decision == "recognized"
                else decision
            )
            outcomes[outcome] += 1
    enrollment_failures, enrollment_errors = failure_summary(
        [observed[key] for key in keys if key[1] == "enroll" and key in observed]
    )
    query_failures, query_errors = failure_summary(
        [observed[key] for key in keys if key[1] == "identify" and key in observed]
    )
    return {
        "enrollment": enroll,
        "probes": query,
        "enrollment_succeeded": enroll["succeeded"],
        "enrollment_failed": enroll["failed"],
        "queries": query["observed"],
        "correct": outcomes["correct_identity"],
        "wrong": outcomes["wrong_identity"],
        "unknown": outcomes["unknown"],
        "ambiguous": outcomes["ambiguous"],
        "query_failed": outcomes["failed"],
        "enrollment_quality_failed": enrollment_failures["quality"],
        "enrollment_other_or_unclassified_failed": enrollment_failures["other_or_unclassified"],
        "query_quality_failed": query_failures["quality"],
        "query_other_or_unclassified_failed": query_failures["other_or_unclassified"],
        "error_counts": {"enrollment": enrollment_errors, "queries": query_errors},
        "all_planned_operations_terminal": enroll["terminal"] == enroll["planned"]
        and query["terminal"] == query["planned"],
    }


def summarize_metrics(source, manifest):
    require(
        isinstance(source, dict)
        and type(source.get("schema_version")) is int
        and source["schema_version"] == 1,
        "invalid_source_report",
    )
    require(
        isinstance(source.get("status"), str) and source["status"] in {"complete", "incomplete"},
        "invalid_source_status",
    )
    source_complete = source["status"] == "complete" and source.get("error_code") is None
    binding = source.get("binding")
    require(isinstance(binding, dict), "missing_manifest_binding")
    digest = canonical_hash(manifest)
    require(binding.get("manifest_sha256") == digest, "manifest_binding_mismatch")
    sizes = binding.get("gallery_sizes")
    expected = validate_manifest(manifest, sizes)
    require(
        source.get("dataset_id") == manifest["dataset_id"]
        and source.get("split") == manifest["split"],
        "source_manifest_mismatch",
    )
    require(
        source.get("model_id") == MODEL_ID
        and source.get("model_revision") == MODEL_REVISION
        and binding.get("model_revision") == MODEL_REVISION,
        "model_contract_mismatch",
    )
    frozen_policy = policy(source.get("frozen_policy"))
    require(policy(binding.get("policy")) == frozen_policy, "policy_binding_mismatch")
    observed = validate_operations(source, manifest, expected, sizes, frozen_policy)
    supplied_stages = source.get("stages")
    require(
        isinstance(supplied_stages, list) and len(supplied_stages) == len(sizes),
        "stage_plan_mismatch",
    )
    stages = []
    for size, supplied in zip(sizes, supplied_stages, strict=True):
        require(
            isinstance(supplied, dict)
            and type(supplied.get("gallery_size_planned")) is int
            and supplied["gallery_size_planned"] == size,
            "stage_plan_mismatch",
        )
        result = summarize_stage(size, manifest, expected, observed)
        for field in ("gallery_size_enrolled", "enrollment_failed"):
            if field in supplied:
                require(
                    counter(supplied[field]) and supplied[field] == result[field],
                    "enrollment_summary_mismatch",
                )
        for field in ("counts", "rates"):
            if field in supplied:
                check_mapping(supplied[field], result[field], rates=field == "rates")
        if "error_counts" in supplied:
            errors = Counter(
                row.get("error_code", "unknown")
                for key, row in observed.items()
                if type(key[0]) is int and key[0] == size and row["status"] == "failed"
            )
            check_mapping(supplied["error_counts"], errors)
            require(supplied["error_counts"] == dict(errors), "summary_error_count_mismatch")
        if "complete_decisions" in supplied:
            complete_decisions = not any(
                result["counts"][f"{kind}_{suffix}"]
                for kind in ("known", "unknown")
                for suffix in ("job_failed", "not_run")
            )
            require(
                type(supplied["complete_decisions"]) is bool
                and supplied["complete_decisions"] == complete_decisions,
                "complete_decisions_mismatch",
            )
        result["metrics_complete"] = source_complete and result["all_planned_operations_terminal"]
        if not result["metrics_complete"]:
            result["rates"] = dict.fromkeys(result["rates"], None)
            result["voiceup_score"] = result["decision_coverage"] = result[
                "enrollment_coverage"
            ] = None
            for container, fields in (
                (result["identity"], ("precision", "recall", "micro_f1", "macro_f1")),
                (result["unknown"], ("precision", "recall", "f1")),
            ):
                for field in fields:
                    container[field] = None
        stages.append(result)
    returns = summarize_return(expected, observed)
    if "return_phase_planned" in source:
        require(
            isinstance(source["return_phase_planned"], dict)
            and set(source["return_phase_planned"]) == {"enrollments", "queries"},
            "invalid_return_plan_summary",
        )
        check_mapping(
            source["return_phase_planned"],
            {
                "enrollments": returns["enrollment"]["planned"],
                "queries": returns["probes"]["planned"],
            },
        )
    all_complete = (
        source_complete
        and all(item["all_planned_operations_terminal"] for item in stages)
        and returns["all_planned_operations_terminal"]
    )
    return {
        "schema_version": 2,
        "metrics_protocol": PROTOCOL,
        "source_run_complete": source_complete,
        "status": "complete" if all_complete else "incomplete",
        "split": manifest["split"],
        "manifest_sha256": digest,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "policy": frozen_policy,
        "operation_count": len(observed),
        "planned_operation_count": len(expected),
        "job_status_counts": {
            status: sum(row["status"] == status for row in observed.values())
            for status in sorted(STATUSES)
        },
        "stages": stages,
        "return_phase": returns,
        "limitations": [
            "Offline re-scoring of existing observations is not a new blind experiment or model improvement.",
            "English read speech does not establish Turkish meeting, overlap, session or microphone generalization.",
            "Shared speakers, chapters and nested galleries are dependent; no population confidence interval is claimed for F1 or VoiceUp Score.",
            "Failed enrollment speakers remain in planned known support; incomplete stages have no reported rates or scores.",
            "Ambiguous and failed probes are not successful unknown rejections; VoiceUp Score is not accuracy or standard F1.",
            "Manifest binding checks recorded provenance, not the current audio bytes or authenticity of the producer.",
        ],
    }
