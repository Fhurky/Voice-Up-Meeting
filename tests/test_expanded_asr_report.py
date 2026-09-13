"""Public ASR diagnostics preserve word-weighted errors and disclose sampling limits."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location(
        "expanded_report", ROOT / "scripts/report-expanded-turkish-asr.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def report():
    from voiceup.meeting_metrics import score_transcript

    clips = []
    for index, (reference, hypothesis) in enumerate(
        (("bir iki üç dört", "bir iki üç dört"), ("beş", "altı yedi sekiz"))
    ):
        clips.append(
            {
                "source_sha256": str(index) * 64,
                "duration_seconds": 2.0,
                "reference": reference,
                "hypothesis": hypothesis,
                "metrics": score_transcript(
                    {"r": reference}, {"h": hypothesis}, normalization="turkish-words-v1"
                ),
            }
        )
    return {
        "status": "complete",
        "protocol": "voiceup-fleurs-tr-test-v1",
        "planned_clips": 2,
        "manifest_sha256": "a" * 64,
        "source_sha256": "b" * 64,
        "clips": clips,
    }


def test_word_weighting_buckets_and_bootstrap_are_deterministic():
    source = report()
    result = module().summarize(source)
    assert result["wer"] == 3 / 5
    assert result["clips"] == 2
    assert result["zero_error_clips"] == 1
    assert result["clip_wer_over_one"] == 1
    assert result["duration_seconds"] == 4
    assert result["bootstrap_95"]["lower"] == 0
    assert result["bootstrap_95"]["upper"] == 3
    assert result == module().summarize(source)
    serialized = json.dumps(result)
    assert "bir iki" not in serialized
    assert "altı" not in serialized


@pytest.mark.parametrize(
    "change", ["incomplete", "missing", "duplicate", "metric", "duration", "metric_shape", "tokens"]
)
def test_bad_or_partial_evidence_is_not_summarized_as_success(change):
    source = report()
    if change == "incomplete":
        source["status"] = "incomplete"
    elif change == "missing":
        source["planned_clips"] = 3
    elif change == "duplicate":
        source["clips"][1]["source_sha256"] = source["clips"][0]["source_sha256"]
    elif change == "metric":
        source["clips"][1]["metrics"]["cpwer"]["errors"] = 0
    elif change == "metric_shape":
        source["clips"][1]["metrics"]["counts"] = []
    elif change == "tokens":
        source["clips"][1]["reference"] = "kelime " * 2001
    else:
        source["clips"][1]["duration_seconds"] = float("nan")
    with pytest.raises(ValueError, match="transcript_token_limit" if change == "tokens" else None):
        module().summarize(source)


def test_real_cli_creates_only_aggregate_and_refuses_existing_output(tmp_path):
    source, output = tmp_path / "private.json", tmp_path / "public.json"
    source.write_text(json.dumps(report()), encoding="utf-8")
    original = source.read_bytes()
    command = [
        sys.executable,
        str(ROOT / "scripts/report-expanded-turkish-asr.py"),
        "--input",
        str(source),
        "--output",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    public = json.loads(output.read_text())
    assert public["wer"] == 0.6
    assert public["private_report_sha256"]
    again = subprocess.run(command, capture_output=True, text=True)
    assert again.returncode != 0
    assert source.read_bytes() == original
