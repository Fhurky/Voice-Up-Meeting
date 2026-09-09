"""Fixed evidence report generation and validation."""

from __future__ import annotations

import re
from typing import Any

LABELS = {
    "en": {
        "title": "Run report",
        "result": "Result",
        "ran": "Ran",
        "items": "Items",
        "groups": ["DEFECT", "TRAP", "OBSERVATION", "OPEN", "SIDE-EFFECT"],
        "none": "— none",
        "decision": "← DECISION",
        "local_verification": "local · verification",
        "unit": "unit",
        "browser": "browser",
        "passed": "passed",
        "skipped": "skipped",
        "awaiting_decision": "awaiting decision",
        "decision_none": "none",
    },
    "tr": {
        "title": "Koşum raporu",
        "result": "Sonuç",
        "ran": "Koşulan",
        "items": "Maddeler",
        "groups": ["KUSUR", "TUZAK", "GÖZLEM", "AÇIK", "YAN-ETKİ"],
        "none": "— yok",
        "decision": "← KARAR",
        "local_verification": "yerel · doğrulama",
        "unit": "birim",
        "browser": "tarayıcı",
        "passed": "başarılı",
        "skipped": "atlanan",
        "awaiting_decision": "karar bekleyen",
        "decision_none": "yok",
    },
}
TIER_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


def label_set(locale: str) -> dict[str, Any]:
    return LABELS.get(locale.split("-")[0], LABELS["en"])


def report_skeleton(
    *,
    locale: str,
    verdict: str,
    ran: list[str],
    counts: dict[str, int],
    defects: list[str] | None = None,
    open_items: list[str] | None = None,
) -> str:
    labels = label_set(locale)
    defects = defects or []
    open_items = open_items or []
    decision_items = [item for item in defects + open_items if labels["decision"] in item]
    decision_ids = [
        f"M{index}"
        for index, item in enumerate(defects + open_items, 1)
        if labels["decision"] in item
    ]
    decision_summary = (
        f"{len(decision_items)} ({', '.join(decision_ids)})"
        if decision_items
        else labels["decision_none"]
    )
    lines = [
        f"# {labels['title']} — {labels['local_verification']}",
        "",
        f"1. {labels['result']}: {verdict} — {labels['unit']} {counts.get('unit', 0)} "
        f"{labels['passed']} / {labels['browser']} {counts.get('browser', 0)} "
        f"{labels['passed']} / {labels['skipped']} {counts.get('skipped', 0)}; "
        f"{labels['awaiting_decision']}: {decision_summary}.",
        f"2. {labels['ran']}: " + ("; ".join(ran) if ran else labels["none"]),
        f"3. {labels['items']}:",
    ]
    number = 1
    for group_index, group in enumerate(labels["groups"]):
        lines.append(f"   **{group}**")
        items = defects if group_index == 0 else open_items if group_index == 3 else []
        if not items:
            lines.append(f"   {labels['none']}")
            continue
        for item in items:
            lines.append(f"   M{number} {item}")
            number += 1
    return "\n".join(lines) + "\n"


def validate_report(text: str, locale: str = "en") -> list[str]:
    labels = label_set(locale)
    errors: list[str] = []
    positions = [text.find(f"**{group}**") for group in labels["groups"]]
    if any(position < 0 for position in positions):
        errors.append("one or more fixed group labels are missing")
    elif positions != sorted(positions):
        errors.append("fixed group labels are out of order")
    known_headings = {f"**{group}**" for group in labels["groups"]}
    actual_headings = set(re.findall(r"^\s*(\*\*[^*]+\*\*)\s*$", text, flags=re.MULTILINE))
    if actual_headings - known_headings:
        errors.append("an unknown sixth group label is present")
    numbers = [int(value) for value in re.findall(r"^\s*M(\d+)\s", text, flags=re.MULTILINE)]
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        errors.append("item numbering must be continuous")
    return errors
