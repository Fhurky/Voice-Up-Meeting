"""Pinned Turkish fixtures preserve source integrity, timeline and weak references."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import wave
from array import array
from pathlib import Path
from unittest.mock import create_autospec
from urllib.request import OpenerDirector

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare-turkish-meeting-evaluation.py"


def module():
    spec = importlib.util.spec_from_file_location("prepare_turkish_meetings", SCRIPT)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def source_row(payload: bytes, name: str = "rec01/rec01__text.csv") -> dict:
    blob = b"blob " + str(len(payload)).encode() + b"\0" + payload
    return {
        "path": name,
        "size_bytes": len(payload),
        "upstream_algorithm": "git-blob-sha1",
        "upstream_digest": hashlib.sha1(blob).hexdigest(),
    }


def opener(payload: bytes):
    result = create_autospec(OpenerDirector, instance=True)
    response = io.BytesIO(payload)
    response.geturl = lambda: "https://huggingface.co/datasets/example/file"
    result.open.return_value = response
    return result


def write_references(root: Path) -> tuple[Path, Path]:
    activity = root / "activity.csv"
    activity.write_text(
        "recording,frame,t_sec,person,speaking\n"
        + "".join(
            f"rec01,{frame},{frame / 16},{speaker},{int(active)}\n"
            for frame in range(16)
            for speaker, active in (
                ("p06", frame < 8),
                ("p03", frame >= 4),
            )
        ),
        encoding="utf-8",
    )
    text = root / "text.csv"
    text.write_text(
        "start_time,end_time,speaker,text\n"
        "00:00:00.000,00:00:00.500,p06,İlk söz.\n"
        "00:00:00.250,00:00:00.900,p03,İkinci söz.\n"
        "00:00:00.900,00:00:01.100,p03,Sınırı aşar.\n"
        "00:00:02.000,00:00:03.000,p06,Dışarıda.\n",
        encoding="utf-8",
    )
    return activity, text


def test_pinned_inventory_is_selective_and_complete() -> None:
    producer = module()
    rows = producer.source_inventory()
    assert len(rows) == 25
    assert sum(row["size_bytes"] for row in rows) == 244_542_070
    assert len({row["path"] for row in rows}) == 25
    assert not any(row["path"].endswith((".mp4", "__video_features.csv")) for row in rows)
    assert producer.REVISION == "db8f20f6eb6b215ec75fb466374fc5cc861b91df"


def test_download_checks_git_blob_hash_and_records_content_sha256(tmp_path: Path) -> None:
    producer = module()
    payload = "speaker,text\np06,İstanbul\n".encode()
    connection = opener(payload)
    row = producer.fetch_source(source_row(payload), tmp_path, opener=connection)
    assert (tmp_path / row["path"]).read_bytes() == payload
    assert row["sha256"] == hashlib.sha256(payload).hexdigest()
    assert row["upstream_algorithm"] == "git-blob-sha1"
    request = connection.open.call_args.args[0]
    assert producer.REVISION in request.full_url
    assert request.get_header("Authorization") is None


@pytest.mark.parametrize("payload", [b"bad", b"corrupt", b"correct-but-overlong"])
def test_download_rejects_corruption_without_publishing(tmp_path: Path, payload: bytes) -> None:
    producer = module()
    with pytest.raises(ValueError, match="source_(size|hash)_mismatch"):
        producer.fetch_source(source_row(b"correct"), tmp_path, opener=opener(payload))
    assert not (tmp_path / "rec01/rec01__text.csv").exists()
    assert not list(tmp_path.rglob("*.partial"))


def test_existing_conflict_is_preserved_without_network(tmp_path: Path) -> None:
    producer = module()
    target = tmp_path / "rec01/rec01__text.csv"
    target.parent.mkdir()
    target.write_bytes(b"user data")
    connection = opener(b"correct")
    with pytest.raises(ValueError, match="source_size_mismatch"):
        producer.fetch_source(source_row(b"correct"), tmp_path, opener=connection)
    assert target.read_bytes() == b"user data"
    connection.open.assert_not_called()


@pytest.mark.parametrize("name", ["../outside", "/absolute", "rec01/../../outside", "a\\b"])
def test_source_paths_cannot_escape_explicit_root(tmp_path: Path, name: str) -> None:
    producer = module()
    with pytest.raises(ValueError, match="unsafe_source_path"):
        producer.fetch_source(source_row(b"data", name), tmp_path, opener=opener(b"data"))


def test_source_reference_preserves_overlap_and_counts_crossing_text(tmp_path: Path) -> None:
    producer = module()
    activity, text = write_references(tmp_path)
    intervals, reference, dropped = producer.read_references(
        activity, text, "rec01", ("p06", "p03"), 1.0
    )
    assert intervals == [
        {"speaker_id": "p06", "start_seconds": 0.0, "end_seconds": 0.5},
        {"speaker_id": "p03", "start_seconds": 0.25, "end_seconds": 1.0},
    ]
    assert reference == [
        {"speaker_id": "p06", "text": "İlk söz."},
        {"speaker_id": "p03", "text": "İkinci söz."},
    ]
    assert dropped == 1


def test_missing_activity_frame_is_not_filled_with_invented_reference(tmp_path: Path) -> None:
    producer = module()
    activity, text = write_references(tmp_path)
    content = activity.read_text(encoding="utf-8")
    activity.write_text(content.replace("rec01,3,0.1875,p06,1\n", ""), encoding="utf-8")
    with pytest.raises(ValueError, match="activity_timeline_mismatch"):
        producer.read_references(activity, text, "rec01", ("p06", "p03"), 1.0)


def test_unknown_reference_identity_is_rejected(tmp_path: Path) -> None:
    producer = module()
    activity, text = write_references(tmp_path)
    text.write_text(text.read_text(encoding="utf-8").replace("p06", "p99"), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_transcript_reference"):
        producer.read_references(activity, text, "rec01", ("p06", "p03"), 1.0)


def test_half_sum_keeps_silence_timing_overlap_and_pcm_limits(tmp_path: Path) -> None:
    producer = module()
    output = tmp_path / "mix.wav"
    left = array("h", [0, 32767, 32767, -32768, 0])
    right = array("h", [0, 0, 32767, -32768, -100])
    producer.write_mixture(left, right, output)
    with wave.open(str(output), "rb") as reader:
        assert reader.getparams()[:3] == (1, 2, 16000)
        samples = array("h", reader.readframes(5))
    if sys.byteorder != "little":
        samples.byteswap()
    assert samples.tolist() == [0, 16383, 32767, -32768, -50]
    assert producer.write_mixture(left, right, output) == producer.digest(output)
    with pytest.raises(FileExistsError, match="existing_output_conflict"):
        producer.write_mixture(right, right, output)


def test_manifest_verification_rejects_incomplete_inventory(tmp_path: Path) -> None:
    producer = module()
    manifest = {
        "schema_version": 1,
        "repository": producer.REPOSITORY,
        "revision": producer.REVISION,
        "license": "apache-2.0",
        "files": [],
    }
    (tmp_path / "source_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_source_manifest"):
        producer.verify_sources(tmp_path)


def test_timeline_audit_rejects_invalid_frames_without_partial_state() -> None:
    producer = module()
    for start, samples, rate in ((float("nan"), 2, 16000), (0, 0, 16000), (0, 2, 0)):
        state = producer.new_timeline_audit()
        with pytest.raises(ValueError, match="invalid_source_audio_timeline"):
            producer.audit_source_frame(state, start, samples, sample_rate=rate)
        assert state == producer.new_timeline_audit()


def test_sample_clock_keeps_all_audio_across_duplicate_and_jumping_timestamps() -> None:
    producer = module()
    destination = array("h", [0]) * 5
    state = {"output_samples": 0}
    audit = producer.new_timeline_audit()
    for start, samples in ((0.0, [7, 8]), (4.0, [9, 10]), (4.0, [11, 12])):
        producer.audit_source_frame(audit, start, 2, sample_rate=16000)
        producer.append_pcm(destination, array("h", samples), state)
    assert destination.tolist() == [7, 8, 9, 10, 11]
    assert state["output_samples"] == 6
    assert audit["source_samples"] == 6
    assert audit["timestamp_repeated_count"] == 1
    assert audit["timestamp_gap_count"] == 1
    assert audit["timestamp_overlap_count"] == 1
    assert audit["max_abs_pts_sample_clock_delta_seconds"] == 3.999875


def test_reference_end_audit_keeps_per_speaker_duration(tmp_path: Path) -> None:
    producer = module()
    activity, text = write_references(tmp_path)
    assert producer.reference_ends(activity, text, ("p06", "p03")) == {
        "p06": {"activity_end_seconds": 1.0, "transcript_end_seconds": 3.0},
        "p03": {"activity_end_seconds": 1.0, "transcript_end_seconds": 1.1},
    }


def test_offset_reference_clips_activity_and_omits_both_crossing_text_edges(tmp_path: Path):
    producer = module()
    activity, text = write_references(tmp_path)
    intervals, reference, crossing = producer.read_references(
        activity, text, "rec01", ("p06", "p03"), 0.5, start_seconds=0.25
    )
    assert intervals == [
        {"speaker_id": "p03", "start_seconds": 0.0, "end_seconds": 0.5},
        {"speaker_id": "p06", "start_seconds": 0.0, "end_seconds": 0.25},
    ]
    assert reference == [{"speaker_id": person, "text": ""} for person in ("p06", "p03")]
    assert crossing == 2


def test_offset_reference_requires_actual_source_coverage(tmp_path: Path):
    producer = module()
    activity, text = write_references(tmp_path)
    with pytest.raises(ValueError, match="activity_coverage_incomplete"):
        producer.read_references(activity, text, "rec01", ("p06", "p03"), 0.75, start_seconds=0.5)


def test_pcm_selection_uses_decoded_sample_order_across_chunk_edges():
    producer = module()
    target = array("h", [0]) * 4
    state = {"output_samples": 0, "selection_start_samples": 3}
    for chunk in ([1, 2], [3, 4, 5], [6, 7, 8], [9]):
        producer.append_pcm(target, array("h", chunk), state)
    assert target.tolist() == [4, 5, 6, 7]
    assert state["output_samples"] == 9


@pytest.mark.parametrize("preset,start", [("window300", 300), ("window600", 600)])
def test_new_presets_are_fixed_and_disjoint_from_development(preset, start):
    producer = module()
    selection = producer.resolve_selection(preset)
    assert selection == (f"voiceup-real-turnturk-{preset}-v1", start, 300)
    assert selection[1] >= 180
    assert producer.resolve_selection("development") == (producer.PROTOCOL, 0, 180)
    assert producer.resolve_selection("development", 1.0) == (producer.PROTOCOL, 0, 1.0)
    with pytest.raises(ValueError, match="invalid_excerpt_selection"):
        producer.resolve_selection(preset, 180)


@pytest.mark.parametrize("preset,duration", [("unknown", None), ("development", 181)])
def test_invalid_selection_is_rejected_before_any_source_or_output_operation(
    tmp_path, preset, duration
):
    producer = module()
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="invalid_excerpt"):
        producer.prepare(tmp_path / "missing", output, preset=preset, duration=duration)
    assert not output.exists()
