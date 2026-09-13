"""Paired lexical scores; individual edit precision is reference-relative, not human judgment."""

from __future__ import annotations

import math
from statistics import median

from voiceup.meeting_metrics import score_transcript, tokenize


def require(condition):
    if not condition:
        raise ValueError("invalid_review_evidence")


def cost(reference, hypothesis):
    return score_transcript(
        {"reference": reference}, {"hypothesis": hypothesis}, normalization="turkish-words-v1"
    )["cpwer"]["errors"]


def words(text):
    return tokenize(text, normalization="turkish-words-v1")


def ratio(top, bottom):
    return top / bottom if bottom else None


def summarize(rows):
    require(isinstance(rows, list) and 1 <= len(rows) <= 5000)
    metrics = dict.fromkeys(
        (
            "planned_rows",
            "completed_rows",
            "failed_rows",
            "reference_words",
            "raw_errors",
            "corrected_errors",
            "changed_rows",
            "improved_rows",
            "worsened_rows",
            "clean_rows",
            "damaged_clean_rows",
            "accepted_edits",
            "beneficial_edits",
            "harmful_edits",
            "neutral_edits",
            "rejected_edits",
        ),
        0,
    )
    elapsed = []
    for row in rows:
        require(
            all(
                isinstance(row.get(key), str) and len(row[key]) <= 4096
                for key in ("reference", "original", "suggested")
            )
        )
        ref, original, suggested = (row[key] for key in ("reference", "original", "suggested"))
        support = len(words(ref))
        require(support > 0 and type(row.get("completed")) is bool)
        duration = row.get("elapsed_seconds")
        require(type(duration) in (int, float) and math.isfinite(duration) and duration >= 0)
        elapsed.append(duration)
        edits = row.get("edits")
        require(isinstance(edits, list) and len(edits) <= 3)
        require(row["completed"] or (suggested == original and not edits))
        rejected = row.get("rejected_count")
        require(type(rejected) is int and 0 <= rejected <= 3)
        require(len(edits) + rejected <= 3 and (row["completed"] or rejected == 0))
        before, after = cost(ref, original), cost(ref, suggested)
        metrics["planned_rows"] += 1
        metrics["completed_rows" if row["completed"] else "failed_rows"] += 1
        metrics["reference_words"] += support
        metrics["raw_errors"] += before
        metrics["corrected_errors"] += after
        metrics["changed_rows"] += words(original) != words(suggested)
        metrics["improved_rows"] += after < before
        metrics["worsened_rows"] += after > before
        metrics["clean_rows"] += before == 0
        metrics["damaged_clean_rows"] += before == 0 and after > 0
        metrics["rejected_edits"] += rejected
        reconstructed, cursor = "", 0
        for edit in edits:
            require(
                isinstance(edit, dict)
                and set(edit) == {"start_char", "end_char", "original", "replacement"}
            )
            start, end = edit["start_char"], edit["end_char"]
            require(
                type(start) is int and type(end) is int and cursor <= start < end <= len(original)
            )
            require(
                original[start:end] == edit["original"]
                and isinstance(edit["replacement"], str)
                and 0 < len(edit["replacement"]) <= 64
            )
            reconstructed += original[cursor:start] + edit["replacement"]
            cursor = end
            standalone = original[:start] + edit["replacement"] + original[end:]
            delta = cost(ref, standalone) - before
            metrics["accepted_edits"] += 1
            metrics[
                "beneficial_edits"
                if delta < 0
                else "harmful_edits"
                if delta > 0
                else "neutral_edits"
            ] += 1
        require(reconstructed + original[cursor:] == suggested)
    metrics.update(
        raw_wer=ratio(metrics["raw_errors"], metrics["reference_words"]),
        corrected_wer=ratio(metrics["corrected_errors"], metrics["reference_words"]),
        edit_precision=ratio(metrics["beneficial_edits"], metrics["accepted_edits"]),
        clean_damage_rate=ratio(metrics["damaged_clean_rows"], metrics["clean_rows"]),
        completion_coverage=ratio(metrics["completed_rows"], metrics["planned_rows"]),
        change_coverage=ratio(metrics["changed_rows"], metrics["planned_rows"]),
        elapsed_seconds=sum(elapsed),
        latency_median_seconds=median(elapsed),
        latency_max_seconds=max(elapsed),
    )
    return metrics
