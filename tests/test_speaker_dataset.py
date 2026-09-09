"""Dataset bookkeeping and real file decoding; synthetic fixtures are not speech evidence."""

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def validator():
    path = Path(__file__).resolve().parents[1] / "scripts" / "validate-speaker-dataset.py"
    spec = importlib.util.spec_from_file_location("speaker_dataset_validator", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def dataset(tmp_path):
    rows = []

    def add(speaker, role, session, suffix):
        recording_id = f"{speaker}_{suffix}"
        rows.append(
            {
                "id": recording_id,
                "speaker_id": speaker,
                "role": role,
                "session_id": session,
                "source_recording_id": recording_id,
                "path": f"{recording_id}.wav",
                "natural_single_speaker": True,
            }
        )

    for index in range(1, 6):
        speaker = f"P{index:02d}"
        add(speaker, "enrollment", "A", "enrollment")
        for query in range(1, 4):
            add(speaker, "known_query", "B", f"query_{query}")
    for speaker in ("U01", "U02"):
        for query in range(1, 6):
            add(speaker, "unknown_query", "B", f"unknown_{query}")
    add("U01", "new_enrollment", "C", "new_enrollment")
    add("U01", "return_query", "D", "return")
    for index, row in enumerate(rows):
        seconds = 10 if row["role"] in {"enrollment", "new_enrollment"} else 3
        sf.write(tmp_path / row["path"], np.full(seconds * 8000, (index + 1) / 100), 8000)
    return {"schema_version": 1, "dataset_id": "test-data", "language": "tr", "recordings": rows}


def codes(report):
    return {item["code"] for item in report["errors"]}


def test_complete_initial_and_return_phases_are_ready(validator, dataset, tmp_path):
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["status"] == "ready"
    assert report["initial_baseline_ready"] is True
    assert report["return_phase_ready"] is True
    assert report["accuracy_evidence"] is False
    assert report["model_executed"] is False
    assert report["counts"]["files_checked"] == 32
    assert len(report["files"]) == 32


@pytest.mark.parametrize("field", ["session_id", "source_recording_id"])
def test_enrollment_query_leakage_is_not_ready(validator, dataset, tmp_path, field):
    dataset["recordings"][1][field] = dataset["recordings"][0][field]
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["initial_baseline_ready"] is False
    assert "split_leakage" in codes(report)


def test_later_enrollment_requires_independent_initial_unknown_and_return(
    validator, dataset, tmp_path
):
    dataset["recordings"][-1]["source_recording_id"] = dataset["recordings"][-2][
        "source_recording_id"
    ]
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["initial_baseline_ready"] is True
    assert report["return_phase_ready"] is False
    assert "split_leakage" in codes(report)


def test_original_source_cannot_cross_roles_under_another_speaker_id(validator, dataset, tmp_path):
    dataset["recordings"][5]["source_recording_id"] = dataset["recordings"][0][
        "source_recording_id"
    ]
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["initial_baseline_ready"] is False
    assert "split_leakage" in codes(report)


@pytest.mark.parametrize("duplicate_kind", ["path", "bytes", "decoded_pcm"])
def test_duplicate_audio_cannot_inflate_trials(validator, dataset, tmp_path, duplicate_kind):
    original, duplicate = dataset["recordings"][:2]
    source = tmp_path / original["path"]
    if duplicate_kind == "path":
        duplicate["path"] = original["path"]
    elif duplicate_kind == "bytes":
        (tmp_path / duplicate["path"]).write_bytes(source.read_bytes())
    else:
        audio, rate = sf.read(source, dtype="int16")
        duplicate["path"] = "same-pcm.flac"
        sf.write(tmp_path / duplicate["path"], audio, rate, format="FLAC", subtype="PCM_16")
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["status"] == "not_ready"
    assert {"duplicate_path", "duplicate_bytes", "duplicate_pcm"} & codes(report)
    if duplicate_kind == "decoded_pcm":
        assert "duplicate_pcm" in codes(report)
        assert "duplicate_bytes" not in codes(report)


@pytest.mark.parametrize("duplicate_kind", ["path", "bytes", "decoded_pcm"])
def test_later_first_duplicate_cannot_hide_initial_duplicates(
    validator, dataset, tmp_path, duplicate_kind
):
    later = dataset["recordings"].pop(-2)
    dataset["recordings"].insert(0, later)
    queries = [row for row in dataset["recordings"] if row["role"] == "known_query"][:2]
    source = tmp_path / later["path"]
    for index, row in enumerate(queries):
        if duplicate_kind == "path":
            row["path"] = later["path"]
        elif duplicate_kind == "bytes":
            (tmp_path / row["path"]).write_bytes(source.read_bytes())
        else:
            samples, rate = sf.read(source)
            row["path"] = f"duplicate-{index}.flac" if index == 0 else "duplicate-1.wav"
            sf.write(
                tmp_path / row["path"], samples, rate, subtype="PCM_16" if index == 0 else "PCM_24"
            )
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["initial_baseline_ready"] is False
    assert report["return_phase_ready"] is False


def test_missing_return_audio_keeps_initial_phase_ready(validator, dataset, tmp_path):
    dataset["recordings"][-1]["path"] = "not-supplied.wav"
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["initial_baseline_ready"] is True
    assert report["return_phase_ready"] is False
    assert "missing_file" in codes(report)


def test_counts_and_unknown_identity_overlap_are_rejected(validator, dataset, tmp_path):
    dataset["recordings"] = dataset["recordings"][4:]
    dataset["recordings"][16]["speaker_id"] = "P02"
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["status"] == "not_ready"
    assert {"insufficient_enrolled_speakers", "unknown_is_enrolled"} <= codes(report)


def test_missing_return_phase_is_not_overall_ready(validator, dataset, tmp_path):
    dataset["recordings"] = dataset["recordings"][:-2]
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["initial_baseline_ready"] is True
    assert report["return_phase_ready"] is False
    assert report["status"] == "not_ready"


@pytest.mark.parametrize("role", ["known_query", "unknown_query"])
def test_minimum_query_counts_are_required(validator, dataset, tmp_path, role):
    index = next(index for index, row in enumerate(dataset["recordings"]) if row["role"] == role)
    dataset["recordings"].pop(index)
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["initial_baseline_ready"] is False
    expected = (
        "insufficient_known_queries" if role == "known_query" else "insufficient_unknown_queries"
    )
    assert expected in codes(report)


@pytest.mark.parametrize("invalid_path", ["../outside.wav", "/outside.wav", "C:/outside.wav"])
def test_paths_cannot_escape_dataset_root(validator, dataset, tmp_path, invalid_path):
    dataset["recordings"][0]["path"] = invalid_path
    report = validator.validate_dataset(dataset, tmp_path)
    assert "unsafe_path" in codes(report)


def test_header_limits_and_actual_format_are_checked(validator, dataset, tmp_path):
    first = tmp_path / dataset["recordings"][0]["path"]
    sf.write(first, np.zeros(9 * 8000), 8000)
    second = tmp_path / dataset["recordings"][1]["path"]
    sf.write(second, np.zeros(121 * 8000), 8000)
    third = tmp_path / dataset["recordings"][2]["path"]
    sf.write(third, np.zeros(3 * 8000), 8000, format="AIFF")
    report = validator.validate_dataset(dataset, tmp_path)
    assert {"duration_too_short", "audio_limit", "unsupported_audio"} <= codes(report)


@pytest.mark.parametrize(
    "rate,channels,amplitude",
    [(1000, 1, 0.1), (200000, 1, 0.1), (8000, 9, 0.1), (8000, 1, 1.5), (8000, 1, 1.0)],
)
def test_static_inference_compatibility_is_checked(
    validator, dataset, tmp_path, rate, channels, amplitude
):
    source = tmp_path / dataset["recordings"][1]["path"]
    sf.write(source, np.full((rate * 3, channels), amplitude), rate, subtype="FLOAT")
    report = validator.validate_dataset(dataset, tmp_path)
    assert report["initial_baseline_ready"] is False
    assert {"invalid_audio", "clipped_audio"} & codes(report)


def test_compressed_decoded_sample_limit_is_checked(validator, dataset, tmp_path):
    dataset["recordings"][1]["path"] = "too-many-samples.flac"
    remaining = 12_000_001
    block = np.zeros((65536, 2), dtype="int16")
    with sf.SoundFile(
        tmp_path / "too-many-samples.flac", "w", samplerate=192000, channels=2
    ) as target:
        while remaining:
            amount = min(remaining, len(block))
            target.write(block[:amount])
            remaining -= amount
    report = validator.validate_dataset(dataset, tmp_path)
    assert "audio_limit" in codes(report)


def test_manifest_row_limit_is_checked_before_audio(validator, dataset, tmp_path):
    dataset["recordings"] = [dataset["recordings"][0]] * 501
    report = validator.validate_dataset(dataset, tmp_path)
    assert "manifest_recording_limit" in codes(report)
    assert report["files"] == []


def test_truncated_diagnostics_do_not_hide_invalid_return_phase(validator, dataset, tmp_path):
    dataset["recordings"][-1]["path"] = "missing-return.wav"
    for index in range(200):
        original = dataset["recordings"][index % 2]
        dataset["recordings"].append(
            {
                **original,
                "id": f"extra-{index}",
                "source_recording_id": "shared-original",
                "path": f"missing-{index}.wav",
            }
        )
    report = validator.validate_dataset(dataset, tmp_path)
    assert len(report["errors"]) == 1000
    assert report["errors_total"] > 1000
    assert report["errors_truncated"] is True
    assert report["initial_baseline_ready"] is False
    assert report["return_phase_ready"] is False


def test_duplicate_ids_and_missing_human_assertion_are_rejected(validator, dataset, tmp_path):
    dataset["recordings"][1]["id"] = dataset["recordings"][0]["id"]
    dataset["recordings"][2]["natural_single_speaker"] = False
    report = validator.validate_dataset(dataset, tmp_path)
    assert {"duplicate_recording_id", "single_speaker_assertion_required"} <= codes(report)


def test_cli_missing_files_writes_not_ready_without_modifying_inputs(validator, dataset, tmp_path):
    manifest = tmp_path / "dataset.json"
    before = json.dumps(dataset)
    manifest.write_text(before, encoding="utf-8")
    empty = tmp_path / "empty-audio"
    empty.mkdir()
    output = tmp_path / "report.json"
    assert (
        validator.main(
            ["--manifest", str(manifest), "--audio-root", str(empty), "--output", str(output)]
        )
        == 1
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "not_ready"
    assert report["accuracy_evidence"] is False
    assert manifest.read_text(encoding="utf-8") == before
    assert list(empty.iterdir()) == []


def test_oversized_file_is_rejected_before_decoding(validator, dataset, tmp_path):
    with (tmp_path / dataset["recordings"][0]["path"]).open("wb") as source:
        source.truncate(50 * 1024 * 1024 + 1)
    report = validator.validate_dataset(dataset, tmp_path)
    assert "audio_limit" in codes(report)


def test_cli_invalid_recordings_shape_still_writes_not_ready(validator, tmp_path):
    manifest = tmp_path / "dataset.json"
    manifest.write_text('{"recordings": null}', encoding="utf-8")
    output = tmp_path / "report.json"
    assert (
        validator.main(
            ["--manifest", str(manifest), "--audio-root", str(tmp_path), "--output", str(output)]
        )
        == 1
    )
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "not_ready"


def test_cli_manifest_byte_limit_is_checked(validator, tmp_path):
    manifest = tmp_path / "too-large.json"
    manifest.write_bytes(b" " * (1024 * 1024 + 1))
    output = tmp_path / "report.json"
    assert (
        validator.main(
            ["--manifest", str(manifest), "--audio-root", str(tmp_path), "--output", str(output)]
        )
        == 1
    )
    assert "manifest_size_limit" in codes(json.loads(output.read_text(encoding="utf-8")))


@pytest.mark.parametrize("target", ["manifest", "audio", "hardlink"])
def test_cli_cannot_overwrite_source_inputs(validator, dataset, tmp_path, target):
    manifest = tmp_path / "dataset.json"
    manifest.write_text(json.dumps(dataset), encoding="utf-8")
    source = manifest if target == "manifest" else tmp_path / dataset["recordings"][0]["path"]
    output = source
    if target == "hardlink":
        output = tmp_path / "aliased-audio.json"
        output.hardlink_to(source)
    before = source.read_bytes()
    assert (
        validator.main(
            ["--manifest", str(manifest), "--audio-root", str(tmp_path), "--output", str(output)]
        )
        == 1
    )
    assert source.read_bytes() == before


def test_template_declares_32_expected_files_and_no_audio():
    path = Path(__file__).resolve().parents[1] / "examples" / "speaker-dataset.example.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    rows = manifest["recordings"]
    assert len(rows) == 32
    assert {row["speaker_id"] for row in rows if row["role"] == "enrollment"} == {
        f"P{i:02d}" for i in range(1, 6)
    }
    assert len([row for row in rows if row["role"] == "known_query"]) == 15
    assert len([row for row in rows if row["role"] == "unknown_query"]) == 10
    assert all(row["natural_single_speaker"] is False for row in rows)
