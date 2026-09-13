"""Publish bounded, anonymous diagnostics from a complete Turkish ASR experiment.

The bootstrap interval describes clip resampling only; it is not a confidence
interval for independent speakers, sessions or the full Turkish population.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from pathlib import Path

from voiceup.meeting_metrics import score_transcript, tokenize

PROTOCOLS = {"voiceup-mediaspeech-tr-expanded-v1", "voiceup-fleurs-tr-test-v1"}
MAX_BYTES = 32 * 1024 * 1024


def require(condition, message="invalid_complete_asr_evidence"):
    if not condition:
        raise ValueError(message)


def checked_path(path):
    path = Path(path).absolute()
    require(
        not any(
            p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)
        ),
        "linked_path",
    )
    require(not path.exists() or (path.is_file() and path.stat().st_nlink == 1), "linked_path")
    return path


def quantile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    return ordered[left] + (ordered[right] - ordered[left]) * (position - left)


def summarize(report):
    require(
        isinstance(report, dict)
        and report.get("status") == "complete"
        and report.get("protocol") in PROTOCOLS
    )
    rows = report.get("clips")
    require(
        isinstance(rows, list)
        and 1 <= len(rows) <= 5000
        and type(report.get("planned_clips")) is int
        and report["planned_clips"] == len(rows)
    )
    for key in ("manifest_sha256", "source_sha256"):
        require(isinstance(report.get(key), str) and re.fullmatch(r"[0-9a-f]{64}", report[key]))
    durations, pairs, rates, seen = [], [], [], set()
    totals = dict(
        reference_words=0, hypothesis_words=0, errors=0, substitutions=0, deletions=0, insertions=0
    )
    for row in rows:
        require(isinstance(row, dict))
        source = row.get("source_sha256")
        require(
            isinstance(source, str) and re.fullmatch(r"[0-9a-f]{64}", source) and source not in seen
        )
        seen.add(source)
        duration = row.get("duration_seconds")
        require(type(duration) in (int, float) and math.isfinite(duration) and 0 < duration <= 60)
        durations.append(duration)
        require(
            all(
                isinstance(row.get(key), str) and len(row[key]) <= 100000
                for key in ("reference", "hypothesis")
            )
        )
        require(
            all(
                len(tokenize(row[key], normalization="turkish-words-v1")) <= 2000
                for key in ("reference", "hypothesis")
            ),
            "transcript_token_limit",
        )
        measured = score_transcript(
            {"reference": row["reference"]},
            {"hypothesis": row["hypothesis"]},
            normalization="turkish-words-v1",
        )
        supplied = row.get("metrics")
        require(
            isinstance(supplied, dict)
            and supplied.get("normalization") == "turkish-words-v1"
            and all(isinstance(supplied.get(key), dict) for key in ("counts", "cpwer"))
        )
        for key in totals:
            group = "counts" if key.endswith("words") else "cpwer"
            observed = supplied.get(group, {}).get(key)
            require(
                type(observed) is int and observed == measured[group][key],
                "private_metric_mismatch",
            )
            totals[key] += observed
        errors, words = measured["cpwer"]["errors"], measured["counts"]["reference_words"]
        pairs.append((errors, words))
        if words:
            rates.append(errors / words)
    require(totals["reference_words"] > 0 and rates)
    rng = random.Random("voiceup-clip-bootstrap-v1")
    bootstrap = []
    for _ in range(2000):
        selected = rng.choices(pairs, k=len(pairs))
        errors, words = map(sum, zip(*selected, strict=True))
        if words:
            bootstrap.append(errors / words)
    return {
        "schema_version": 1,
        "protocol": report["protocol"],
        "status": "complete",
        "normalization": "turkish-words-v1",
        "manifest_sha256": report["manifest_sha256"],
        "source_sha256": report["source_sha256"],
        "clips": len(rows),
        "duration_seconds": sum(durations),
        "duration_min_seconds": min(durations),
        "duration_max_seconds": max(durations),
        **totals,
        "wer": totals["errors"] / totals["reference_words"],
        "zero_error_clips": sum(errors == 0 for errors, _ in pairs),
        "zero_reference_word_clips": sum(words == 0 for _, words in pairs),
        "clip_wer_median": quantile(rates, 0.5),
        "clip_wer_p90": quantile(rates, 0.9),
        "clip_wer_p95": quantile(rates, 0.95),
        "clip_wer_over_half": sum(rate > 0.5 for rate in rates),
        "clip_wer_over_one": sum(rate > 1 for rate in rates),
        "bootstrap_95": {
            "method": "percentile-word-weighted-ratio-from-clip-resampling",
            "seed": "voiceup-clip-bootstrap-v1",
            "resamples": 2000,
            "defined_resamples": len(bootstrap),
            "lower": quantile(bootstrap, 0.025),
            "upper": quantile(bootstrap, 0.975),
            "scope": "conditional-on-clips-not-independent-speakers-sessions-or-population",
        },
    }


def unique_fields(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate_json_field")
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError("invalid_json_number")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, output = checked_path(args.input), checked_path(args.output)
    require(
        source.resolve() != output.resolve() and not output.exists(), "existing_or_aliased_output"
    )
    with source.open("rb") as stream:
        payload = stream.read(MAX_BYTES + 1)
    require(len(payload) <= MAX_BYTES, "input_limit")
    report = json.loads(payload, object_pairs_hook=unique_fields, parse_constant=reject_constant)
    public = summarize(report)
    public["private_report_sha256"] = hashlib.sha256(payload).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(public, allow_nan=False, indent=2) + "\n")
    print(f"Published aggregate diagnostics for {public['clips']} clips; private text excluded.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise SystemExit(
            "ASR diagnostics refused invalid, partial or conflicting evidence."
        ) from None
