"""Fixture assembly keeps identity/source chronology without repeating evidence."""

import importlib.util
import sys
import wave
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare-meeting-evaluation.py"


def module():
    spec = importlib.util.spec_from_file_location("meeting_evaluation", SCRIPT)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def test_round_robin_never_repeats_source_frames(tmp_path: Path) -> None:
    producer = module()
    sources = []
    for index in range(2):
        path = tmp_path / f"{index}.wav"
        with wave.open(str(path), "wb") as target:
            target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            target.writeframes(bytes([index + 1, 0]) * (16000 * 3))
        sources.append((str(index), path))
    result = producer.assemble(sources, tmp_path / "mixed.wav", excerpt_seconds=2, gap_seconds=0.25)
    assert result["source_audio_seconds"] == 6
    assert result["duration_seconds"] == 6.75
    for identity in ("0", "1"):
        ranges = [row for row in result["intervals"] if row["speaker_id"] == identity]
        assert [(r["source_start_frame"], r["source_end_frame"]) for r in ranges] == [
            (0, 32000),
            (32000, 48000),
        ]
    assert result["sha256"] and len(result["sha256"]) == 64


def test_existing_output_is_not_overwritten(tmp_path: Path) -> None:
    producer = module()
    path = tmp_path / "owned.wav"
    path.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        producer.assemble([], path)
    assert path.read_bytes() == b"keep"
