"""Publish aggregate public-corpus evidence without audio or profile identities."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

PREPROCESSING_VERSIONS = ("vad-windows-v1", "vad-packed-fallback-v1")


def preprocessing_counts(rows: list[dict]) -> dict[str, int]:
    counts = dict.fromkeys((*PREPROCESSING_VERSIONS, "unreported_or_unsupported"), 0)
    for row in rows:
        if row.get("status") != "succeeded":
            continue
        result = row.get("result")
        version = result.get("preprocessing_version") if isinstance(result, dict) else None
        label = (
            version
            if isinstance(version, str) and version in PREPROCESSING_VERSIONS
            else "unreported_or_unsupported"
        )
        counts[label] += 1
    return counts


def outcome(row: dict, metric: str) -> bool:
    accepted = row["status"] == "succeeded" and row.get("decision") == "recognized"
    if metric == "false_accept":
        return accepted
    if metric != "correct":
        raise ValueError("unsupported metric")
    return accepted and row.get("predicted_speaker_id") == row["speaker_id"]


def cluster_interval(rows: list[dict], kind: str, metric: str, samples: int = 2000) -> dict | None:
    """Resample whole speakers so adjacent clips are never independent draws."""
    groups = defaultdict(list)
    for row in rows:
        if row["kind"] == kind:
            groups[row["speaker_id"]].append(int(outcome(row, metric)))
    if not groups:
        return None
    if not 1 <= samples <= 10000:
        raise ValueError("invalid bootstrap size")
    totals = [(sum(values), len(values)) for _, values in sorted(groups.items())]
    generator = random.Random("voiceup-speaker-bootstrap-v1")
    distribution = []
    for _ in range(samples):
        selected = generator.choices(totals, k=len(totals))
        distribution.append(sum(pair[0] for pair in selected) / sum(pair[1] for pair in selected))
    distribution.sort()
    successes, total = sum(pair[0] for pair in totals), sum(pair[1] for pair in totals)
    return {
        "method": "speaker-cluster percentile bootstrap, fixed seed, 95%",
        "samples": samples,
        "speakers": len(totals),
        "probes": total,
        "point": successes / total,
        "lower": distribution[max(0, math.ceil(samples * 0.025) - 1)],
        "upper": distribution[max(0, math.ceil(samples * 0.975) - 1)],
        "all_outcomes_identical": successes in {0, total},
        "limitation": "A degenerate interval does not establish zero population risk; finite speakers, shared conditions and unobserved outcomes limit inference.",
    }


def subset_counts(rows: list[dict]) -> dict:
    counts = dict.fromkeys(
        (
            "known_planned",
            "unknown_planned",
            "known_correct",
            "known_wrong",
            "known_ambiguous",
            "known_unknown",
            "unknown_false_accepted",
            "unknown_unknown",
            "unknown_ambiguous",
            "known_job_failed",
            "unknown_job_failed",
        ),
        0,
    )
    for row in rows:
        kind = row["kind"]
        counts[kind + "_planned"] += 1
        if row["status"] != "succeeded":
            counts[kind + "_job_failed"] += 1
        elif row["decision"] == "recognized":
            field = (
                "unknown_false_accepted"
                if kind == "unknown"
                else ("known_correct" if outcome(row, "correct") else "known_wrong")
            )
            counts[field] += 1
        else:
            counts[kind + "_" + row["decision"]] += 1
    return counts


def timing(rows: list[dict], key: str) -> dict | None:
    values = sorted(
        row["timing"][key]
        for row in rows
        if isinstance(row.get("timing"), dict)
        and type(row["timing"].get(key)) in (int, float)
        and math.isfinite(row["timing"][key])
        and row["timing"][key] >= 0
    )
    if not values:
        return None
    return {
        "count": len(values),
        "p50_seconds": values[math.ceil(len(values) * 0.5) - 1],
        "p95_seconds": values[math.ceil(len(values) * 0.95) - 1],
        "max_seconds": values[-1],
    }


def numeric_mapping(value: dict) -> dict:
    return {
        key: number
        for key, number in value.items()
        if type(number) in (int, float) and math.isfinite(number) or number is None
    }


def return_counts(rows: list[dict], planned: dict | None) -> dict:
    enrollments = [row for row in rows if row.get("purpose") == "enroll"]
    queries = [row for row in rows if row.get("purpose") == "identify"]
    terminal = {"succeeded", "failed"}
    if planned is not None and (
        not isinstance(planned, dict)
        or set(planned) != {"enrollments", "queries"}
        or any(type(number) is not int or number < 0 for number in planned.values())
        or planned["enrollments"] < len(enrollments)
        or planned["queries"] < len(queries)
    ):
        raise ValueError("invalid return phase plan")
    quality_errors = {
        "insufficient_speech",
        "inconsistent_audio",
        "clipped_audio",
        "invalid_audio",
        "audio_limit",
        "unsupported_audio",
    }
    result = {
        # Preserve historical keys; failed includes enrollment and query operations.
        "enrollment_succeeded": sum(row["status"] == "succeeded" for row in enrollments),
        "queries": len(queries),
        "correct": sum(outcome(row, "correct") for row in queries),
        "failed": sum(row["status"] == "failed" for row in rows),
        "enrollments_planned": planned["enrollments"] if planned is not None else None,
        "enrollments_observed": len(enrollments),
        "enrollment_failed": sum(row["status"] == "failed" for row in enrollments),
        "enrollment_pending": sum(row["status"] not in terminal for row in enrollments),
        "enrollment_not_run": planned["enrollments"] - len(enrollments)
        if planned is not None
        else None,
        "queries_planned": planned["queries"] if planned is not None else None,
        "queries_terminal": sum(row["status"] in terminal for row in queries),
        "queries_pending": sum(row["status"] not in terminal for row in queries),
        "queries_not_run": planned["queries"] - len(queries) if planned is not None else None,
        "recognized_wrong": sum(
            row["status"] == "succeeded"
            and row.get("decision") == "recognized"
            and not outcome(row, "correct")
            for row in queries
        ),
        "ambiguous": sum(
            row["status"] == "succeeded" and row.get("decision") == "ambiguous" for row in queries
        ),
        "unknown": sum(
            row["status"] == "succeeded" and row.get("decision") == "unknown" for row in queries
        ),
        "query_failed": sum(row["status"] == "failed" for row in queries),
        "query_quality_failed": sum(
            row["status"] == "failed" and row.get("error_code") in quality_errors for row in queries
        ),
        "query_error_counts": dict(
            Counter(
                row.get("error_code") or "unspecified"
                for row in queries
                if row["status"] == "failed"
            )
        ),
        "all_planned_operations_terminal": (
            len(enrollments) == planned["enrollments"]
            and len(queries) == planned["queries"]
            and all(row["status"] in terminal for row in rows)
        )
        if planned is not None
        else None,
    }
    return result


def summarize(source: dict) -> dict:
    if (
        source.get("split") not in {"test", "calibration"}
        or not source.get("stages")
        or not isinstance(source.get("operations"), list)
    ):
        raise ValueError("invalid evaluation report")
    stages = []
    for stage in source["stages"]:
        size = stage["gallery_size_planned"]
        rows = [
            row
            for row in source["operations"]
            if row.get("stage") == size
            and row.get("purpose") == "identify"
            and row.get("status") in {"succeeded", "failed"}
        ]
        expected = sum(stage["counts"][kind + "_planned"] for kind in ("known", "unknown"))
        complete = len(rows) == expected
        stages.append(
            {
                "gallery_size_planned": size,
                "gallery_size_enrolled": stage["gallery_size_enrolled"],
                "enrollment_failed": stage["enrollment_failed"],
                "counts": numeric_mapping(stage["counts"]),
                "rates": numeric_mapping(stage["rates"]),
                "all_planned_probes_terminal": complete,
                "by_source_split": {
                    split: subset_counts([row for row in rows if row["source_split"] == split])
                    for split in (
                        "dev-clean",
                        "dev-other",
                        "test-clean",
                        "test-other",
                        "train-clean-100",
                    )
                    if any(row["source_split"] == split for row in rows)
                }
                if complete
                else None,
                "error_counts": dict(
                    Counter(
                        row.get("error_code") or "unspecified"
                        for row in rows
                        if row["status"] == "failed"
                    )
                ),
                "speaker_cluster_intervals": {
                    "DIR": cluster_interval(rows, "known", "correct") if complete else None,
                    "FPIR_observed_lower_bound": cluster_interval(rows, "unknown", "false_accept")
                    if complete
                    else None,
                },
                "execution": timing(rows, "execution_seconds"),
                "queue": timing(rows, "queue_seconds"),
            }
        )
    returns = source.get("return_phase", [])
    return {
        "schema_version": 1,
        "status": source["status"],
        "split": source["split"],
        "manifest_sha256": source.get("binding", {}).get("manifest_sha256"),
        "model_id": source.get("model_id"),
        "model_revision": source.get("model_revision"),
        "policy": numeric_mapping(source.get("frozen_policy", {})),
        "operation_count": len(source["operations"]),
        "job_status_counts": dict(Counter(row["status"] for row in source["operations"])),
        "preprocessing_version_counts": preprocessing_counts(source["operations"]),
        "device_counts": dict(
            Counter(
                row["result"]["device"]
                for row in source["operations"]
                if row.get("result") and row["result"].get("device")
            )
        ),
        "stages": stages,
        "return_phase": return_counts(returns, source.get("return_phase_planned")),
        "limitations": [
            "English read speech; source chapters are separate, actual days and microphones are unverified.",
            "Prepared utterance joins are artificial; mixed speakers, long meetings and Turkish remain untested.",
            "All scheduled known probes stay in DIR denominator, including quality failures.",
            "Unknown failures are not successful rejections. Observed FPIR and worst-case bounds must be read together.",
            "Speaker-cluster bootstrap is descriptive; zero observed false accepts is not a population guarantee.",
            "Nested galleries reuse probes and are not independent replications.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metrics-protocol", choices=["voiceup-open-set-v1"])
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if bool(args.metrics_protocol) != bool(args.manifest):
        parser.error("--metrics-protocol and --manifest must be supplied together")
    if (
        args.input.resolve() == args.output.resolve()
        or args.output.exists()
        or args.manifest
        and args.manifest.resolve() == args.output.resolve()
    ):
        raise SystemExit("Refusing to overwrite an existing input or report")
    with args.input.open("rb") as stream:
        payload = stream.read(16 * 1024 * 1024 + 1)
    if len(payload) > 16 * 1024 * 1024:
        raise SystemExit("Input report exceeds limit")
    if args.metrics_protocol:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "voiceup_speaker_metrics", Path(__file__).with_name("speaker_metrics.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with args.manifest.open("rb") as stream:
            manifest_payload = stream.read(4 * 1024 * 1024 + 1)
        if len(manifest_payload) > 4 * 1024 * 1024:
            raise SystemExit("Manifest exceeds limit")
        try:
            report = module.summarize_metrics(
                module.strict_json(payload), module.strict_json(manifest_payload)
            )
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            raise SystemExit("Invalid manifest-bound metrics evidence") from None
    else:
        report = summarize(json.loads(payload))
    report["private_source_report_sha256"] = hashlib.sha256(payload).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print("Aggregate evidence written without audio or profile identities")


if __name__ == "__main__":
    main()
