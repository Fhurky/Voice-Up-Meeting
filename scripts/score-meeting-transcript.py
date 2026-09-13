"""Score complete per-speaker reference/hypothesis streams without model or network calls.

Input JSON has schema_version=1, source_sha256, reference_complete=true, and
reference/hypothesis arrays of {speaker_id, text}. Each speaker occurs once with
all its words in chronological order. Only hypotheses may use a null speaker.
The aggregate report includes input/audio hashes, never text or speaker labels.
Pass --normalization turkish-words-v1 for Turkish case matching. Optional
--experiment-metadata records aggregate success/incomplete evidence in results.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from voiceup.meeting_metrics import NORMALIZATION, NORMALIZATIONS, score_transcript

MAX_INPUT_BYTES = 16 * 1024 * 1024


def unique_fields(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate_json_field")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("invalid_json_constant")


def streams(rows):
    if not isinstance(rows, list) or len(rows) > 200:
        raise ValueError("invalid_streams")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"speaker_id", "text"}:
            raise ValueError("invalid_stream")
        identity = row["speaker_id"]
        if identity is not None and not isinstance(identity, str):
            raise ValueError("invalid_speaker_id")
        if identity in result:
            raise ValueError("duplicate_speaker_stream")
        result[identity] = row["text"]
    return result


def checked_path(path):
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("symlink_refused")
    return path


def record_report(args, report):
    if args.experiment_metadata is None:
        return
    from experiment_ledger import record_from_metadata_file

    ledger = args.results_md or Path(__file__).resolve().parents[1] / "results.md"
    if ledger.resolve() in {args.input.resolve(), args.output.resolve()}:
        raise ValueError("ledger_evidence_path_conflict")
    record_from_metadata_file(
        ledger, args.experiment_metadata, report=report, kind="transcript", evidence=None
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--normalization", choices=NORMALIZATIONS, default=NORMALIZATION)
    parser.add_argument("--experiment-metadata", type=Path)
    parser.add_argument("--results-md", type=Path)
    args = parser.parse_args()
    if args.results_md is not None and args.experiment_metadata is None:
        parser.error("--results-md requires --experiment-metadata")
    try:
        source = checked_path(args.input.absolute())
        output = checked_path(args.output.absolute())
        if output.exists() or output.resolve() == source.resolve():
            raise ValueError("output_exists")
        with source.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
        if len(payload) > MAX_INPUT_BYTES:
            raise ValueError("input_limit")
        value = json.loads(payload, object_pairs_hook=unique_fields, parse_constant=reject_constant)
        if (
            not isinstance(value, dict)
            or set(value)
            != {"schema_version", "source_sha256", "reference_complete", "reference", "hypothesis"}
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or value["reference_complete"] is not True
            or not isinstance(value["source_sha256"], str)
            or re.fullmatch("[0-9a-f]{64}", value["source_sha256"]) is None
        ):
            raise ValueError("invalid_complete_reference_document")
        report = score_transcript(
            streams(value["reference"]),
            streams(value["hypothesis"]),
            normalization=args.normalization,
        )
        for metric in ("cpwer", "assigned_only"):
            report[metric].pop("assignment")
        report.update(
            {
                "input_sha256": hashlib.sha256(payload).hexdigest(),
                "source_sha256": value["source_sha256"],
                "schema_version": 1,
            }
        )
        encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as target:
            target.write(encoded)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        try:
            record_report(args, {"status": "incomplete"})
        except (OSError, ValueError, TypeError, OverflowError, RecursionError):
            raise SystemExit(
                "Transcript scoring failed and the experiment was not recorded; "
                "check reference input, experiment metadata and ledger path."
            ) from None
        raise SystemExit(
            "Transcript scoring failed; check complete references, input limits and output path."
        ) from None
    try:
        record_report(args, report)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        raise SystemExit(
            "Transcript metrics were saved but the experiment was not recorded; "
            "check experiment metadata and record the existing report."
        ) from None
    print("Aggregate transcription metrics written; all reference and hypothesis words counted.")


if __name__ == "__main__":
    main()
