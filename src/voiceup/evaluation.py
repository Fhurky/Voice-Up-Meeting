"""Probe-level, open-set identification metrics for already produced decisions.

This module uses only the standard library. It does not run models, fit decision
thresholds, align diarization segments, or compute duration-weighted errors.
"""

from __future__ import annotations

import math

_STATUSES = ("recognized", "unknown", "ambiguous", "new")
_REQUIRED_KEYS = {"ground_truth", "predicted_id", "status"}


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate_decisions(records: list[dict]) -> dict:
    """Evaluate decisions against persistent speaker identities without remapping.

    Each record requires ``ground_truth`` (nonempty speaker ID or None for a
    person absent from the gallery), ``predicted_id``, and ``status``. Only a
    ``recognized`` decision may carry a predicted ID, and it must carry one.
    ``unknown``, ``ambiguous``, and ``new`` all reject a known-identity match.

    Optional ``duration_seconds`` must be a finite positive number. It is
    descriptive metadata only: every record contributes one probe. Additional
    metadata keys are allowed. Invalid input raises ValueError; inputs are not
    modified. Empty denominators produce None, which serializes to JSON null.
    """
    if not isinstance(records, list):
        raise ValueError("records must be a list of decision objects")

    counts = {
        "total": len(records),
        "known": 0,
        "unknown": 0,
        "recognized": 0,
        "correct_known": 0,
        "wrong_known": 0,
        "rejected_known": 0,
        "false_accepted_unknown": 0,
    }
    status_counts = dict.fromkeys(_STATUSES, 0)

    for index, record in enumerate(records):
        prefix = f"record {index}"
        if not isinstance(record, dict):
            raise ValueError(f"{prefix} must be a decision object")
        missing = _REQUIRED_KEYS.difference(record)
        if missing:
            raise ValueError(f"{prefix} is missing required keys: {', '.join(sorted(missing))}")

        actual = record["ground_truth"]
        predicted = record["predicted_id"]
        status = record["status"]
        if actual is not None and not _valid_id(actual):
            raise ValueError(f"{prefix} ground_truth must be a nonempty string or None")
        if not isinstance(status, str) or status not in _STATUSES:
            raise ValueError(f"{prefix} status must be one of: {', '.join(_STATUSES)}")
        if status == "recognized":
            if not _valid_id(predicted):
                raise ValueError(f"{prefix} recognized decision requires a nonempty predicted_id")
        elif predicted is not None:
            raise ValueError(f"{prefix} predicted_id must be None unless status is recognized")

        if "duration_seconds" in record:
            duration = record["duration_seconds"]
            try:
                valid_duration = (
                    isinstance(duration, (int, float))
                    and not isinstance(duration, bool)
                    and math.isfinite(duration)
                    and duration > 0
                )
            except (OverflowError, TypeError, ValueError):
                valid_duration = False
            if not valid_duration:
                raise ValueError(f"{prefix} duration_seconds must be a finite positive number")

        status_counts[status] += 1
        recognized = status == "recognized"
        counts["recognized"] += int(recognized)
        if actual is None:
            counts["unknown"] += 1
            counts["false_accepted_unknown"] += int(recognized)
        else:
            counts["known"] += 1
            if not recognized:
                counts["rejected_known"] += 1
            elif predicted == actual:
                counts["correct_known"] += 1
            else:
                counts["wrong_known"] += 1

    return {
        "counts": counts,
        "status_counts": status_counts,
        "rates": {
            "DIR": _ratio(counts["correct_known"], counts["known"]),
            "known_misidentification": _ratio(counts["wrong_known"], counts["known"]),
            "known_rejection": _ratio(counts["rejected_known"], counts["known"]),
            "FPIR": _ratio(counts["false_accepted_unknown"], counts["unknown"]),
        },
        "note": (
            "Probe-level gallery-search metrics, not pairwise FAR or EER. "
            "DIR is correct known identifications / all known probes; FPIR is unknown "
            "probes accepted as any gallery identity / all unknown probes. "
            "Rejections include unknown, ambiguous, and new decisions. "
            "Rates are fractions from 0 to 1; undefined rates are null. "
            "Optional durations do not weight these metrics. No calibration is performed."
        ),
    }
