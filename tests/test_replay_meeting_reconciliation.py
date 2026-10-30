"""The replay tool must reuse the product's clustering and select thresholds from dev data only."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "replay_reconciliation", ROOT / "scripts/replay-meeting-reconciliation.py"
)
replay = importlib.util.module_from_spec(spec)
sys.modules["replay_reconciliation"] = replay
spec.loader.exec_module(replay)


def row(dev: float, test: float = 99.0) -> dict:
    return {"dev": {"der": dev}, "test": {"der": test}}


def voice(first: float, second: float) -> list[float]:
    return [first, second] + [0.0] * 254


def chunk(index: int, tracks: list[tuple[str, list[float], float, float]]) -> dict:
    start = index * 300.0
    return {
        "index": index,
        "context_start": max(0.0, start - 5),
        "core_start": start,
        "core_end": start + 300.0,
        "turns": [
            {"start": turn_start, "end": turn_end, "speaker": label}
            for label, _, turn_start, turn_end in tracks
        ],
        "tracks": [
            {"speaker": label, "status": "inconsistent_audio", "embedding": None, "tracking": vector}
            for label, vector, _, _ in tracks
        ],
    }


def test_selection_takes_the_highest_threshold_within_tolerance_of_every_condition() -> None:
    grid = {
        0.4: {"a": row(20.0), "b": row(30.0)},
        0.6: {"a": row(20.9), "b": row(30.5)},
        0.7: {"a": row(21.5), "b": row(30.2)},
    }
    assert replay.select_threshold(grid) == 0.6


def test_selection_ignores_held_out_test_data() -> None:
    grid = {0.4: {"a": row(20.0, 10.0)}, 0.6: {"a": row(20.5, 90.0)}}
    assert replay.select_threshold(grid) == 0.6


def test_one_voice_across_chunks_scores_as_one_speaker() -> None:
    chunks = [
        chunk(0, [("x", voice(1.0, 0.0), 10.0, 100.0)]),
        chunk(1, [("y", voice(1.0, 0.01), 10.0, 100.0)]),
    ]
    clusters = replay.cluster(chunks, 0.6, replay.domain())
    assert clusters == {(0, "x"): 0, (1, "y"): 0}
    turns = replay.hypothesis(chunks, clusters)
    assert {turn["speaker_public_id"] for turn in turns} == {"s0"}


def test_overlapping_tracks_of_one_chunk_stay_apart_and_touching_tracks_can_merge() -> None:
    same = voice(1.0, 0.0)
    overlapping = [chunk(0, [("x", same, 10.0, 50.0), ("y", same, 40.0, 90.0)])]
    assert replay.cluster(overlapping, 0.6, replay.domain()) == {(0, "x"): 0, (0, "y"): 1}
    separate = [chunk(0, [("x", same, 10.0, 50.0), ("y", same, 60.0, 90.0)])]
    assert replay.cluster(separate, 0.6, replay.domain()) == {(0, "x"): 0, (0, "y"): 0}


def test_export_reads_only_and_quotes_identifiers() -> None:
    sql = replay.export_sql(["a'b", "c"])
    assert sql.startswith("select ") and "'a''b','c'" in sql
    assert not any(word in sql.lower() for word in ("update ", "delete ", "insert ", "drop "))
