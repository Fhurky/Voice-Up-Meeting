"""Record validated aggregate evidence, or repeat the explicitly inventoried historical backfill."""

from __future__ import annotations

import argparse
from pathlib import Path

from experiment_ledger import (
    DEFAULT_LEDGER,
    ROOT,
    read_document,
    record_experiment,
    record_from_metadata_file,
)


def metadata(date, dataset, revision, language, role, pipeline, models=None):
    value = {
        "date": date,
        "dataset": dataset,
        "dataset_revision": revision,
        "language": language,
        "role": role,
        "pipeline": pipeline,
    }
    if models:
        value["models"] = models
    return value


def backfill(ledger):
    """Only named, reviewed evidence; never recursively select favorable historical results."""
    added = 0
    for cohort in ("calibration", "historical", "fresh"):
        evidence = f"docs/evidence/2026-09-09-speaker-metrics/{cohort}-summary.json"
        report = read_document(ROOT / evidence)
        added += record_experiment(
            ledger,
            experiment_id=f"history-20260909-ecapa50-{cohort}",
            metadata=metadata(
                "2026-09-09",
                "librispeech",
                report["manifest_sha256"],
                "en",
                "calibration" if cohort == "calibration" else "regression",
                "speaker-pilot",
                [{"id": report["model_id"], "revision": report["model_revision"]}],
            ),
            report=report,
            kind="identity",
            evidence=evidence,
        )

    evidence = "docs/evidence/2026-09-11-accuracy-audit/asr-results.json"
    source = read_document(ROOT / evidence)
    model = [{"id": source["model"]["model_id"], "revision": source["model"]["revision"]}]
    baseline = source["baseline"]
    variants = [
        (
            "baseline",
            baseline["protocol_sha256"],
            baseline["aggregate"]["standard_cpwer"],
            baseline["aggregate"]["constrained_assigned_only_cost"],
            sum(case["unassigned_tokens"] for case in baseline["cases"].values()),
        ),
    ]
    for name, candidate in source["candidates"].items():
        aggregate = candidate["aggregate"].get("candidate", candidate["aggregate"])
        variants.append(
            (
                "rejected-" + name.replace("_", "-"),
                candidate["protocol_sha256"],
                aggregate["cpwer"],
                aggregate["assigned_only"],
                sum(case["unassigned_words"] for case in candidate["cases"].values()),
            )
        )
    for name, protocol, cpwer, assigned, unassigned in variants:
        report = {
            "normalization": "unicode-words-v1",
            "counts": {
                "reference_words": cpwer["reference_words"],
                "hypothesis_words": cpwer["hypothesis_words"],
                "unassigned_words": unassigned,
            },
            "unassigned_word_fraction": unassigned / cpwer["hypothesis_words"],
        }
        for field, cost in (("cpwer", cpwer), ("assigned_only", assigned)):
            report[field] = {
                key: cost[key] for key in ("errors", "substitutions", "deletions", "insertions")
            }
            report[field]["rate"] = cost["error_rate"]
        added += record_experiment(
            ledger,
            experiment_id="history-20260911-asr-" + name,
            metadata=metadata(
                "2026-09-11",
                "librispeech-constructed-abc",
                protocol,
                "en",
                "calibration",
                "meeting-asr",
                model,
            ),
            report=report,
            kind="transcript",
            evidence=evidence,
        )

    for case in ("a", "b", "c"):
        evidence = (
            f"docs/evidence/2026-09-11-accuracy-audit/capacity50-native-{case}-memory-results.json"
        )
        source = read_document(ROOT / evidence)
        observed = source[f"{case}_observation"]
        meta = metadata(
            "2026-09-11",
            "librispeech-constructed-50",
            observed["protocol_sha256"],
            "en",
            "regression",
            "meeting-asr",
        )
        added += record_experiment(
            ledger,
            experiment_id=f"history-20260911-native50-{case}-text",
            metadata=meta,
            report=observed["transcript_metrics"],
            kind="transcript",
            evidence=evidence,
        )
        observations = {
            "planned_people": observed["all_people_denominator"],
            "enrolled_people": observed["gallery_total"],
        }
        if case != "a":
            observations["correct_returns"] = observed["source_mapped_correct_profiles"]
        added += record_experiment(
            ledger,
            experiment_id=f"history-20260911-native50-{case}-memory",
            metadata=meta | {"pipeline": "meeting-memory"},
            report={"status": "unscored", "observations": observations},
            kind="observation",
            evidence=evidence,
        )

    evidence = "docs/evidence/2026-09-10-meeting-delivery/turkish-source-results.json"
    source = read_document(ROOT / evidence)
    added += record_experiment(
        ledger,
        experiment_id="history-20260910-turkish-single-speaker-smoke",
        metadata=metadata(
            "2026-09-10",
            "local-turkish-sample",
            source["source_sha256"],
            "tr",
            "smoke",
            "meeting-memory",
        ),
        report={
            "status": "unscored",
            "source_sha256": source["source_sha256"],
            "observations": {
                "observed_speakers": source["observed_speakers"],
                "transcript_segments": source["transcript_segments"],
            },
        },
        kind="observation",
        evidence=evidence,
    )
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--experiment-metadata", type=Path)
    parser.add_argument(
        "--kind",
        choices=(
            "identity",
            "transcript",
            "meeting_identity",
            "asr_clips",
            "observation",
            "transcript_review",
        ),
    )
    parser.add_argument("--results-md", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--evidence", help="Reviewed repository-relative aggregate JSON under docs/evidence/"
    )
    parser.add_argument("--backfill-reviewed-history", action="store_true")
    args = parser.parse_args()
    if args.backfill_reviewed_history:
        if any((args.input, args.experiment_metadata, args.kind, args.evidence)):
            parser.error("historical backfill cannot be combined with input metadata")
    elif not all((args.input, args.experiment_metadata, args.kind)):
        parser.error("--input, --experiment-metadata and --kind are required")
    try:
        if args.backfill_reviewed_history:
            added = backfill(args.results_md)
        else:
            if args.results_md.resolve() == args.input.resolve():
                raise ValueError("ledger_input_path_conflict")
            added = int(
                record_from_metadata_file(
                    args.results_md,
                    args.experiment_metadata,
                    report=read_document(args.input),
                    kind=args.kind,
                    evidence=args.evidence,
                )
            )
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):
        raise SystemExit(
            "Experiment was not recorded; check aggregate evidence, public metadata and ledger path"
        ) from None
    print(f"Experiment snapshots added: {added}; identical snapshots are unchanged.")


if __name__ == "__main__":
    main()
