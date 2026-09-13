"""The offline scorer binds complete references and never publishes raw text."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "score-meeting-transcript.py"


def document():
    return {
        "schema_version": 1,
        "source_sha256": "a" * 64,
        "reference_complete": True,
        "reference": [{"speaker_id": "alice-private", "text": "hello world"}],
        "hypothesis": [{"speaker_id": None, "text": "hello"}],
    }


def run(tmp_path, value, *arguments):
    source, output = tmp_path / "input.json", tmp_path / "output.json"
    payload = json.dumps(value).encode()
    source.write_bytes(payload)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output), *arguments],
        capture_output=True,
        text=True,
    )
    return result, output, payload


def test_real_file_report_includes_hash_and_all_words_but_no_text_or_identity(tmp_path):
    result, output, payload = run(tmp_path, document())
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["input_sha256"] == hashlib.sha256(payload).hexdigest()
    assert report["source_sha256"] == "a" * 64
    assert report["counts"]["reference_words"] == 2
    assert report["cpwer"]["deletions"] == 1
    assert report["assigned_only"]["errors"] == 3
    assert "hello" not in output.read_text() + result.stdout + result.stderr
    assert "alice-private" not in output.read_text() + result.stdout + result.stderr


def test_turkish_cli_scores_real_unicode_input_without_publishing_text(tmp_path):
    value = document() | {
        "reference": [{"speaker_id": "private-reference", "text": "IŞIK I\u0307ZMİR"}],
        "hypothesis": [{"speaker_id": "private-hypothesis", "text": "ışık izmir"}],
    }
    result, output, payload = run(tmp_path, value, "--normalization", "turkish-words-v1")
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["normalization"] == "turkish-words-v1"
    assert report["cpwer"]["errors"] == 0
    assert report["counts"]["reference_words"] == 2
    assert report["input_sha256"] == hashlib.sha256(payload).hexdigest()
    published = output.read_text() + result.stdout + result.stderr
    assert "private-reference" not in published
    assert "private-hypothesis" not in published
    assert "izmir" not in published


def test_default_cli_report_keeps_existing_normalization_contract(tmp_path):
    result, output, _ = run(tmp_path, document())
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["normalization"] == "unicode-words-v1"
    assert set(report) == {
        "normalization",
        "counts",
        "cpwer",
        "assigned_only",
        "unassigned_word_fraction",
        "note",
        "input_sha256",
        "source_sha256",
        "schema_version",
    }


def test_unknown_normalization_never_creates_evidence(tmp_path):
    result, output, _ = run(tmp_path, document(), "--normalization", "unknown-v1")
    assert result.returncode != 0
    assert not output.exists()


def experiment_metadata(tmp_path):
    metadata = tmp_path / "experiment.json"
    metadata.write_text(
        json.dumps(
            {
                "experiment_id": "tr-cli-001",
                "date": "2026-09-13",
                "dataset": "unit-fixture",
                "dataset_revision": "v1",
                "language": "tr",
                "role": "regression",
                "pipeline": "meeting-asr",
            }
        )
    )
    return metadata


def test_cli_records_aggregate_experiment_after_scoring(tmp_path):
    metadata, ledger = experiment_metadata(tmp_path), tmp_path / "results.md"
    result, output, _ = run(
        tmp_path, document(), "--experiment-metadata", str(metadata), "--results-md", str(ledger)
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()
    published = ledger.read_text(encoding="utf-8")
    assert "tr-cli-001" in published
    assert "unicode-words-v1" in published
    assert "hello" not in published
    assert "alice-private" not in published
    assert str(tmp_path) not in published


def test_cli_records_invalid_reference_as_incomplete_without_scores(tmp_path):
    metadata, ledger = experiment_metadata(tmp_path), tmp_path / "results.md"
    result, output, _ = run(
        tmp_path,
        document() | {"reference_complete": False},
        "--experiment-metadata",
        str(metadata),
        "--results-md",
        str(ledger),
    )
    assert result.returncode != 0
    assert not output.exists()
    published = ledger.read_text(encoding="utf-8")
    assert "tr-cli-001" in published
    assert "incomplete" in published
    assert "hello" not in published
    assert "alice-private" not in published


def test_results_path_requires_explicit_experiment_metadata(tmp_path):
    ledger = tmp_path / "results.md"
    result, output, _ = run(tmp_path, document(), "--results-md", str(ledger))
    assert result.returncode != 0
    assert not output.exists()
    assert not ledger.exists()


@pytest.mark.parametrize(
    "change",
    [
        {"reference_complete": False},
        {"reference_complete": 1},
        {"schema_version": True},
        {"source_sha256": "invalid"},
        {"reference": [{"speaker_id": None, "text": "private text"}]},
        {"hypothesis": [{"speaker_id": None, "text": "one"}, {"speaker_id": None, "text": "two"}]},
    ],
)
def test_incomplete_or_malformed_reference_never_produces_a_score(tmp_path, change):
    value = document() | change
    result, output, _ = run(tmp_path, value)
    assert result.returncode != 0
    assert not output.exists()
    assert "private text" not in result.stderr


def test_existing_evidence_is_not_overwritten(tmp_path):
    output = tmp_path / "output.json"
    output.write_text("preserved")
    result, _, _ = run(tmp_path, document())
    assert result.returncode != 0
    assert output.read_text() == "preserved"


def test_duplicate_json_fields_are_rejected(tmp_path):
    source, output = tmp_path / "input.json", tmp_path / "output.json"
    source.write_text('{"schema_version":1,"schema_version":1}')
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not output.exists()
