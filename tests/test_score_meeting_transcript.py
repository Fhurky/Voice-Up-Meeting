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


def run(tmp_path, value):
    source, output = tmp_path / "input.json", tmp_path / "output.json"
    payload = json.dumps(value).encode()
    source.write_bytes(payload)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output)],
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
