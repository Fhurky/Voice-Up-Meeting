import json

import pytest

from voiceup.cli import main


def test_demo_reopens_memory_and_adds_sixth(capsys):
    assert main(["demo"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["synthetic_demo"] is True
    assert result["passed"] is True
    assert result["total_profiles"] == 6
    assert [p["status"] for p in result["meeting_2_after_reopen"]] == ["recognized"] * 5 + ["new"]


def test_demo_writes_json_artifact(tmp_path, capsys):
    path = tmp_path / "results" / "demo.json"
    assert main(["demo", "--output", str(path)]) == 0
    assert json.loads(path.read_text(encoding="utf-8"))["passed"] is True
    assert capsys.readouterr().out == ""


def test_evaluate_cli(tmp_path, capsys):
    path = tmp_path / "decisions.json"
    path.write_text(
        json.dumps(
            [
                {"ground_truth": "a", "predicted_id": "a", "status": "recognized"},
                {"ground_truth": None, "predicted_id": None, "status": "unknown"},
            ]
        )
    )
    assert main(["evaluate", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["rates"]["DIR"] == 1


@pytest.mark.parametrize("content", ["not JSON", "{}", '[{"status": "recognized"}]'])
def test_evaluate_errors_are_actionable(tmp_path, capsys, content):
    path = tmp_path / "bad.json"
    path.write_text(content)
    assert main(["evaluate", str(path)]) == 2
    assert "Hata:" in capsys.readouterr().err


def test_profiles_do_not_load_model(tmp_path, capsys, monkeypatch):
    from voiceup.backends import SpeechBrainEmbedder

    def fail(*args, **kwargs):
        pytest.fail("Listing profiles must not load neural models")

    monkeypatch.setattr(SpeechBrainEmbedder, "_load", fail)
    assert main(["profiles", "--db", str(tmp_path / "profiles.db"), "list"]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_invalid_matching_policy_fails_before_audio_loading(tmp_path, capsys):
    assert main(["identify", str(tmp_path / "absent.wav"), "--match-threshold", "nan"]) == 2
    assert "policy" in capsys.readouterr().err
