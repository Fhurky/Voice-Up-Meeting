#!/usr/bin/env python3
"""Replay meeting-end speaker reconciliation over stored chunk results (PRD 021).

No GPU and no writes: `sql` prints a read-only export of the chunk results of one finished AMI
run for psql, and `replay` clusters those tracks with the product's own domain function at each
threshold, scores them against the human references and applies the dev-only selection rule.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
NEW_THRESHOLD = 0.45
DEV_TOLERANCE_POINTS = 1.0
LONG_SPEAKER_SECONDS = 30.0
PURE_SHARE = 0.8


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def domain() -> Any:
    return _load(
        "voiceup_reconciliation", ROOT / "app/backend/app/domain/meeting_reconciliation.py"
    )


def ami() -> Any:
    return _load("voiceup_ami_runner", ROOT / "scripts/run-ami-evaluation.py")


def export_sql(public_ids: list[str]) -> str:
    identifiers = ",".join("'" + value.replace("'", "''") + "'" for value in sorted(public_ids))
    return (
        "select jsonb_build_object('public_id', m.public_id, 'index', c.index, "
        "'context_start', c.context_start, 'core_start', c.core_start, 'core_end', c.core_end, "
        "'turns', c.result->'provider'->'turns', 'tracks', (select jsonb_agg(jsonb_build_object("
        "'speaker', t->>'speaker', 'status', t->>'status', 'embedding', t->'embedding', "
        "'tracking', t->'tracking'->'embedding')) "
        "from jsonb_array_elements(c.result->'provider'->'tracks') t))::text "
        "from meeting_chunk c join meeting m on m.meeting_id = c.meeting_id "
        f"where m.public_id in ({identifiers}) and c.is_deleted = false "
        "order by m.public_id, c.index;"
    )


def _spans(chunk: dict, label: str) -> list[tuple[float, float]]:
    offset = float(chunk["context_start"])
    spans = sorted(
        (offset + turn["start"], offset + turn["end"])
        for turn in chunk["turns"] or []
        if turn["speaker"] == label
    )
    merged: list[tuple[float, float]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _meet(first: list[tuple[float, float]], second: list[tuple[float, float]]) -> bool:
    return any(max(a, c) < min(b, d) for a, b in first for c, d in second)


def _different(left: dict, right: dict) -> bool:
    if left["status"] != "usable" or right["status"] != "usable":
        return False
    if left["embedding"] is None or right["embedding"] is None:
        return False
    return sum(a * b for a, b in zip(left["embedding"], right["embedding"], strict=True)) < (
        NEW_THRESHOLD
    )


def cluster(chunks: list[dict], threshold: float, reconciliation: Any) -> dict[tuple[int, str], int]:
    """Mirror MeetingChunkPersistence.reconcile: same inputs, same conflicts, same function."""
    tracks, conflicts = [], []
    for chunk in chunks:
        core = (float(chunk["core_start"]), float(chunk["core_end"]))
        rows = chunk["tracks"] or []
        speech = {row["speaker"]: _spans(chunk, row["speaker"]) for row in rows}
        for position, row in enumerate(rows):
            owned = sum(
                max(0.0, min(end, core[1]) - max(start, core[0]))
                for start, end in speech[row["speaker"]]
            )
            for other in rows[:position]:
                if _meet(speech[row["speaker"]], speech[other["speaker"]]) or _different(row, other):
                    conflicts.append(
                        ((chunk["index"], other["speaker"]), (chunk["index"], row["speaker"]))
                    )
            tracks.append(
                reconciliation.ReconciliationTrack(
                    chunk["index"],
                    row["speaker"],
                    owned,
                    tuple(row["tracking"]) if row["tracking"] is not None else None,
                )
            )
    return reconciliation.reconcile_tracks(tracks, threshold, NEW_THRESHOLD, conflicts).clusters


def hypothesis(chunks: list[dict], clusters: dict[tuple[int, str], int]) -> list[dict]:
    turns = []
    final = max(chunk["index"] for chunk in chunks)
    for chunk in chunks:
        start = max(0.0, float(chunk["core_start"]) - 5)
        end = float(chunk["core_end"]) if chunk["index"] == final else float(chunk["core_end"]) - 5
        for turn in chunk["turns"] or []:
            a = max(start, float(chunk["context_start"]) + turn["start"])
            b = min(end, float(chunk["context_start"]) + turn["end"])
            if a < b:
                turns.append(
                    {
                        "start_seconds": a,
                        "end_seconds": b,
                        "speaker_public_id": f"s{clusters[(chunk['index'], turn['speaker'])]}",
                    }
                )
    return turns


def pool(rows: list[dict[str, float]]) -> dict[str, float]:
    totals: Counter[str] = Counter()
    for row in rows:
        totals.update(row)
    reference = totals["total"] or 1.0
    errors = totals["missed"] + totals["false_alarm"] + totals["confusion"]
    return {
        "der": round(100 * errors / reference, 2),
        "confusion": round(100 * totals["confusion"] / reference, 2),
    }


def select_threshold(
    grid: dict[float, dict[str, dict]], tolerance: float = DEV_TOLERANCE_POINTS
) -> float:
    """Highest threshold within tolerance of the best dev DER in every audio condition."""
    conditions = {condition for row in grid.values() for condition in row}
    best = {
        condition: min(row[condition]["dev"]["der"] for row in grid.values())
        for condition in conditions
    }
    eligible = [
        threshold
        for threshold, row in grid.items()
        if all(row[condition]["dev"]["der"] <= best[condition] + tolerance for condition in row)
    ]
    return max(eligible)


def replay(args: argparse.Namespace) -> dict:
    runner, reconciliation = ami(), domain()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    meetings = {item["meeting"]: item for item in protocol["meetings"]}
    corpus: dict[str, dict[str, list[dict]]] = {}
    for condition, state_path, chunks_path in args.run:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
        names = {value["public_id"]: name for name, value in state["meetings"].items()}
        grouped: dict[str, list[dict]] = defaultdict(list)
        for line in Path(chunks_path).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            grouped[names[row["public_id"]]].append(row)
        corpus[condition] = grouped
    grid: dict[float, dict[str, dict]] = {}
    for threshold in args.thresholds:
        grid[threshold] = {}
        for condition, grouped in corpus.items():
            scored: dict[str, list] = {"dev": [], "test": []}
            counts, long_counts, long_total, mixed = [], [], 0, 0
            for meeting, chunks in sorted(grouped.items()):
                chunks = sorted(chunks, key=lambda chunk: chunk["index"])
                item = meetings[meeting]
                reference = runner.read_rttm(args.protocol.parent / item["rttm"], meeting)
                uem = (float(item["uem"][0]), float(item["uem"][1]))
                turns = hypothesis(chunks, cluster(chunks, threshold, reconciliation))
                scored[item["split"]].append(runner.der_components(turns, reference, uem, 0.0))
                seconds: Counter[str] = Counter()
                for turn in turns:
                    seconds[turn["speaker_public_id"]] += turn["end_seconds"] - turn["start_seconds"]
                long = {key for key, value in seconds.items() if value >= LONG_SPEAKER_SECONDS}
                dominance = runner.dominant_people(turns, reference, uem)
                counts.append(len(seconds))
                long_counts.append(len(long))
                long_total += len(long)
                mixed += sum(dominance.get(key, (None, 0.0))[1] < PURE_SHARE for key in long)
            grid[threshold][condition] = {
                "dev": pool(scored["dev"]),
                "test": pool(scored["test"]),
                "speakers_median": statistics.median(counts),
                "long_speakers_median": statistics.median(long_counts),
                "long_speakers": long_total,
                "mixed_long_speakers": mixed,
            }
    return {"selected_threshold": select_threshold(grid), "grid": grid}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    sql = commands.add_parser("sql")
    sql.add_argument("--state", type=Path, required=True)
    run = commands.add_parser("replay")
    run.add_argument("--protocol", type=Path, required=True)
    run.add_argument(
        "--run", nargs=3, action="append", required=True, metavar=("CONDITION", "STATE", "CHUNKS")
    )
    run.add_argument(
        "--thresholds", type=float, nargs="+", default=[0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]
    )
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "sql":
        state = json.loads(args.state.read_text(encoding="utf-8"))
        print(export_sql([value["public_id"] for value in state["meetings"].values()]))
        return
    report = replay(args)
    if not all(math.isfinite(key) for key in report["grid"]):
        raise SystemExit("invalid_threshold")
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"selected_threshold": report["selected_threshold"]}))


if __name__ == "__main__":
    main()
