"""Expanded frozen cohorts preserve old data and resume exact completed clips."""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import create_autospec

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def script(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "expanded_asr", Path(__file__).parents[1] / "scripts/evaluate-expanded-turkish-asr.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cohort(script, tmp_path, count=3):
    root = tmp_path / "data"
    (root / "clips").mkdir(parents=True)
    rows = []
    for index in range(count):
        identity = f"sample_{index}"
        audio = root / "clips" / (identity + ".wav")
        reference = root / "clips" / (identity + ".txt")
        sf.write(audio, np.full(1600, 0.1 + index / 10), 16000)
        reference.write_text("İstanbul güzel bir şehir", encoding="utf-8")
        rows.append(
            dict(
                clip_id=identity,
                audio=f"clips/{identity}.wav",
                reference_file=f"clips/{identity}.txt",
                audio_sha256=script.base.digest(audio),
                reference_sha256=script.base.digest(reference),
                reference=reference.read_text(encoding="utf-8"),
            )
        )
    manifest = dict(
        schema_version=1,
        protocol="voiceup-fleurs-tr-test-v1",
        language="tr",
        role="frozen-test",
        dataset="FLEURS-TR",
        dataset_revision="a" * 40,
        source_sha256="b" * 64,
        reference_quality="source-human-transcribed",
        speaker_session_labels_available=False,
        selection="official-test-split-source-order",
        exclusion_manifest_sha256=None,
        clips=rows,
    )
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    script.MANIFEST_SHA256[manifest["protocol"]] = script.base.digest(root / "manifest.json")
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    model_manifest = tmp_path / "model.json"
    model_manifest.write_text("{}")
    args = Namespace(
        root=root,
        output=tmp_path / "run.private.json",
        model_dir=model_dir,
        model_manifest=model_manifest,
        experiment_id="expanded-test",
        results_md=tmp_path / "results.md",
        resume=False,
    )
    return args, manifest


@pytest.mark.parametrize("change", ["duplicate_audio", "escape", "protocol", "role", "extra"])
def test_manifest_refuses_invalid_contract(script, tmp_path, change):
    args, manifest = cohort(script, tmp_path)
    if change == "duplicate_audio":
        manifest["clips"][1]["audio_sha256"] = manifest["clips"][0]["audio_sha256"]
    elif change == "escape":
        manifest["clips"][0]["audio"] = "../escape.wav"
    elif change == "extra":
        manifest["credentials"] = "forbidden"
    else:
        manifest[change] = "unknown"
    (args.root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        script.load_manifest(args.root)


def test_manifest_odd_cohort_and_exact_hash(script, tmp_path):
    args, manifest = cohort(script, tmp_path)
    actual, digest = script.load_manifest(args.root)
    assert actual == manifest
    assert digest == script.base.digest(args.root / "manifest.json")


def test_source_change_fails_before_model_loading(script, tmp_path, monkeypatch):
    args, manifest = cohort(script, tmp_path)
    (args.root / manifest["clips"][2]["reference_file"]).write_text("changed")
    model = create_autospec(script.load_model)
    monkeypatch.setattr(script, "load_model", model)
    with pytest.raises(ValueError, match="source_changed"):
        script.evaluate(args)
    model.assert_not_called()
    assert not args.output.exists()


def test_output_protects_source_and_model_files(script, tmp_path):
    args, _ = cohort(script, tmp_path)
    args.output = args.root / "new.json"
    with pytest.raises(ValueError):
        script.evaluate(args)
    assert not args.output.exists()


def install_model(script, monkeypatch, fail_at=None):
    calls = []
    if not hasattr(script, "original_model_functions"):
        script.original_model_functions = (script.load_model, script.transcribe, script.publish)
    original_load, original_transcribe, original_publish = script.original_model_functions

    def infer(_model, _samples):
        calls.append(len(calls))
        if fail_at is not None and len(calls) == fail_at:
            raise RuntimeError("simulated_inference_interruption")
        return "İstanbul güzel bir kent", "tr"

    monkeypatch.setattr(script, "load_model", create_autospec(original_load, return_value=object()))
    monkeypatch.setattr(
        script, "transcribe", create_autospec(original_transcribe, side_effect=infer)
    )
    monkeypatch.setattr(script, "publish", create_autospec(original_publish))
    return calls


def test_interrupted_resume_skips_exact_durable_clips(script, tmp_path, monkeypatch):
    args, _ = cohort(script, tmp_path)
    calls = install_model(script, monkeypatch, fail_at=2)
    with pytest.raises(RuntimeError):
        script.evaluate(args)
    partial = json.loads(args.output.read_text(encoding="utf-8"))
    assert partial["status"] == "incomplete"
    assert len(partial["clips"]) == 1
    assert len(calls) == 2
    assert script.aggregate(partial)["wer"] is None
    args.resume = True
    calls = install_model(script, monkeypatch)
    script.evaluate(args)
    complete = json.loads(args.output.read_text(encoding="utf-8"))
    assert len(calls) == 2
    assert complete["status"] == "complete"
    assert script.aggregate(complete)["wer"] == pytest.approx(3 / 12)
    assert len(complete["clips"]) == 3
    before = args.output.read_bytes()
    script.evaluate(args)
    assert args.output.read_bytes() == before
    assert len(calls) == 2


@pytest.mark.parametrize("change", ["manifest", "experiment_id", "model_manifest", "ledger"])
def test_resume_rejects_changed_binding(script, tmp_path, monkeypatch, change):
    args, manifest = cohort(script, tmp_path)
    install_model(script, monkeypatch, fail_at=2)
    with pytest.raises(RuntimeError):
        script.evaluate(args)
    args.resume = True
    if change == "manifest":
        manifest["selection"] = "changed-selection"
        (args.root / "manifest.json").write_text(json.dumps(manifest))
    elif change == "model_manifest":
        args.model_manifest.write_text('{"changed":true}')
    elif change == "ledger":
        args.results_md = tmp_path / "other.md"
    else:
        args.experiment_id = "other-run"
    install_model(script, monkeypatch)
    with pytest.raises(ValueError, match="binding"):
        script.evaluate(args)
    script.load_model.assert_not_called()


def test_resume_rejects_tampered_cached_metrics(script, tmp_path, monkeypatch):
    args, _ = cohort(script, tmp_path)
    install_model(script, monkeypatch, fail_at=2)
    with pytest.raises(RuntimeError):
        script.evaluate(args)
    cache = script.paths(args)[2]
    row_path = cache / "000000.json"
    row = json.loads(row_path.read_text(encoding="utf-8"))
    row["metrics"]["cpwer"]["errors"] = 0
    row_path.write_text(json.dumps(row))
    args.resume = True
    install_model(script, monkeypatch)
    with pytest.raises(ValueError, match="checkpoint"):
        script.evaluate(args)
    script.load_model.assert_not_called()


def test_existing_state_requires_explicit_resume(script, tmp_path, monkeypatch):
    args, _ = cohort(script, tmp_path)
    install_model(script, monkeypatch)
    script.evaluate(args)
    before = args.output.read_bytes()
    with pytest.raises(ValueError, match="resume"):
        script.evaluate(args)
    assert args.output.read_bytes() == before


def test_aggregate_never_exposes_text_or_clip_identity(script, tmp_path, monkeypatch):
    args, _ = cohort(script, tmp_path)
    install_model(script, monkeypatch)
    script.evaluate(args)
    result = script.aggregate(json.loads(args.output.read_text(encoding="utf-8")))
    assert result["protocol"] == "voiceup-fleurs-tr-test-v1"
    assert result["reference_words"] == 12
    assert "İstanbul" not in json.dumps(result)
    assert "sample_0" not in json.dumps(result)


def test_exclusion_uses_ids_and_hashes_without_reassigning_old_roles(script):
    source = [
        dict(clip_id="a", audio_sha256="1"),
        dict(clip_id="b", audio_sha256="2"),
        dict(clip_id="c", audio_sha256="3"),
    ]
    old = [dict(clip_id="a", flac_sha256="2", role="calibration")]
    assert script.exclude_previous(source, old) == [source[2]]
    assert old[0]["role"] == "calibration"


def test_recovery_preserves_stale_atomic_temporary_file(script, tmp_path, monkeypatch):
    args, _ = cohort(script, tmp_path)
    install_model(script, monkeypatch, fail_at=2)
    with pytest.raises(RuntimeError):
        script.evaluate(args)
    cache = script.paths(args)[2]
    stale = cache / ("000001.json." + "a" * 32 + ".tmp")
    stale.write_text("partial interrupted write")
    args.resume = True
    install_model(script, monkeypatch)
    script.evaluate(args)
    assert stale.read_text() == "partial interrupted write"


def test_checkpoint_duration_is_bound_to_actual_audio(script, tmp_path, monkeypatch):
    args, _ = cohort(script, tmp_path)
    install_model(script, monkeypatch, fail_at=2)
    with pytest.raises(RuntimeError):
        script.evaluate(args)
    row_path = script.paths(args)[2] / "000000.json"
    row = json.loads(row_path.read_text(encoding="utf-8"))
    row["duration_seconds"] = 59.0
    row_path.write_text(json.dumps(row))
    args.resume = True
    install_model(script, monkeypatch)
    with pytest.raises(ValueError, match="checkpoint"):
        script.evaluate(args)


def test_success_and_incomplete_publish_through_real_ledger(script, tmp_path, monkeypatch):
    args, _ = cohort(script, tmp_path)
    install_model(script, monkeypatch, fail_at=2)
    monkeypatch.setattr(script, "publish", script.original_model_functions[2])
    with pytest.raises(RuntimeError):
        script.evaluate(args)
    partial = args.results_md.read_text(encoding="utf-8")
    assert '"status":"incomplete"' in partial
    args.resume = True
    install_model(script, monkeypatch)
    monkeypatch.setattr(script, "publish", script.original_model_functions[2])
    script.evaluate(args)
    complete = args.results_md.read_text(encoding="utf-8")
    assert '"status":"complete"' in complete
    assert "İstanbul" not in complete
    script.evaluate(args)
    assert args.results_md.read_text(encoding="utf-8") == complete


def test_model_loading_failure_keeps_full_planned_denominator(script, tmp_path, monkeypatch):
    args, _ = cohort(script, tmp_path)
    install_model(script, monkeypatch)
    script.load_model.side_effect = RuntimeError("unavailable GPU")
    with pytest.raises(RuntimeError):
        script.evaluate(args)
    report = json.loads(args.output.read_text(encoding="utf-8"))
    assert script.aggregate(report)["planned_clips"] == 3
    assert script.aggregate(report)["observed_clips"] == 0
    assert script.aggregate(report)["wer"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("protocol", "voiceup-mediaspeech-tr-expanded-v1"),
        ("source_sha256", "c" * 64),
        ("model_id", "other/model"),
    ],
)
def test_completed_report_cannot_relabel_cached_inference(
    script, tmp_path, monkeypatch, field, value
):
    args, _ = cohort(script, tmp_path)
    install_model(script, monkeypatch)
    script.evaluate(args)
    report = json.loads(args.output.read_text(encoding="utf-8"))
    report[field] = value
    args.output.write_text(json.dumps(report))
    args.resume = True
    with pytest.raises(ValueError, match="checkpoint"):
        script.evaluate(args)


def test_destination_hardlink_is_refused_before_mutation(script, tmp_path):
    import os

    args, _ = cohort(script, tmp_path)
    original = args.model_manifest.read_bytes()
    os.link(args.model_manifest, args.output)
    with pytest.raises(ValueError):
        script.evaluate(args)
    assert args.model_manifest.read_bytes() == original


def test_cli_model_runtime_error_is_sanitized_and_records_incomplete(script, tmp_path):
    import subprocess
    import sys

    args, manifest = cohort(script, tmp_path)
    command = """
import importlib.util,sys
from pathlib import Path
from unittest.mock import create_autospec
path=Path(sys.argv.pop(1))
sys.path.insert(0,str(path.parent))
spec=importlib.util.spec_from_file_location('expanded_cli_test',path)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
root=Path(sys.argv[sys.argv.index('--root')+1])
module.MANIFEST_SHA256['voiceup-fleurs-tr-test-v1']=module.base.digest(root/'manifest.json')
module.load_model=create_autospec(module.load_model,side_effect=RuntimeError('PRIVATE_MODEL_ERROR'))
module.cli()
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            command,
            script.__file__,
            "evaluate",
            "--root",
            str(args.root),
            "--output",
            str(args.output),
            "--model-dir",
            str(args.model_dir),
            "--model-manifest",
            str(args.model_manifest),
            "--experiment-id",
            args.experiment_id,
            "--results-md",
            str(args.results_md),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Expanded Turkish ASR incomplete" in result.stderr
    assert "PRIVATE_MODEL_ERROR" not in result.stderr
    assert "Traceback" not in result.stderr
    report = json.loads(args.output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert report["planned_clips"] == len(manifest["clips"])
    assert '"status":"incomplete"' in args.results_md.read_text(encoding="utf-8")


def test_missing_model_directory_fails_before_sources_or_lock_files(script, tmp_path):
    args, manifest = cohort(script, tmp_path)
    args.model_dir = tmp_path / "mistyped-model-directory"
    (args.root / manifest["clips"][0]["reference_file"]).write_text("changed source")
    with pytest.raises(ValueError, match="model_directory_missing"):
        script.evaluate(args)
    assert not args.output.with_suffix(".json.lock").exists()


@pytest.mark.parametrize("kind", ["source_file", "source_parent"])
def test_linked_source_path_is_refused(script, tmp_path, kind):
    args, manifest = cohort(script, tmp_path)
    if kind == "source_file":
        target = args.root / manifest["clips"][0]["audio"]
        original = tmp_path / "original-audio.wav"
    else:
        target = args.root / "clips"
        original = tmp_path / "original-clips"
    target.rename(original)
    try:
        target.symlink_to(original, target_is_directory=kind == "source_parent")
    except OSError:
        pytest.skip("Local Windows account cannot create symbolic links")
    with pytest.raises(ValueError, match="linked"):
        script.evaluate(args)
    assert not args.output.exists()
