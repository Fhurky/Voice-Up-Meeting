"""The offline controller binds inputs and keeps transcript-bearing files private."""

import hashlib
import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import create_autospec

import pytest


@pytest.fixture
def controller(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "review_controller", root / "scripts/evaluate-transcript-review.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


def configuration(controller, tmp_path):
    source = b"fixture source"
    for name in ("infrastructure/ollama_correction.py", "domain/transcript_correction.py"):
        path = tmp_path / "app/backend/app" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source)
    manifest = {
        "protocol": "voiceup-context-review-v1",
        "reference_quality": "synthetic-authored",
        "cases": [
            {
                "id": "case-1",
                "original": "Clean text.",
                "reference": "Clean text.",
                "before": [],
                "after": [],
            }
        ],
    }
    input_path = tmp_path / "outputs/manifest.private.json"
    input_path.parent.mkdir(parents=True)
    input_path.write_text(json.dumps(manifest), encoding="utf-8")
    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    source_hash = hashlib.sha256(source * 2).hexdigest()
    metadata = {
        "experiment_id": "review-test",
        "date": "2026-09-13",
        "dataset": "review-test",
        "dataset_revision": input_hash,
        "language": "tr",
        "role": "regression",
        "pipeline": "transcript-review",
        "models": [{"id": "ollama/test", "revision": "a" * 64}],
        "protocol_sha256": input_hash,
        "configuration_sha256": source_hash,
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    args = Namespace(
        input=input_path,
        output=tmp_path / "outputs/run",
        experiment_metadata=metadata_path,
        results_md=tmp_path / "results.md",
        bash="bash",
    )
    result = {
        "completed": True,
        "suggested": "Clean text.",
        "status": "unchanged",
        "edits": [],
        "rejected_count": 0,
        "model_name": "test",
        "model_digest": "a" * 64,
        "policy_version": "tr-context-words-v1",
        "source_code_sha256": source_hash,
    }
    return args, manifest, metadata, result


def test_private_output_must_be_inside_repository_outputs_before_a_model_call(
    controller, tmp_path, monkeypatch
):
    args, _, _, _ = configuration(controller, tmp_path)
    args.output = tmp_path / "docs/private-results"
    process = create_autospec(controller.subprocess.run)
    monkeypatch.setattr(controller.subprocess, "run", process)
    with pytest.raises(ValueError, match="private_output_required"):
        controller.run(args)
    process.assert_not_called()
    assert not args.output.exists()


def test_prepare_refuses_public_output_even_for_authored_inputs(controller, tmp_path):
    args, _, _, _ = configuration(controller, tmp_path)
    with pytest.raises(ValueError, match="private_output_required"):
        controller.prepare(
            Namespace(
                fixture=args.input,
                corpus=None,
                output=tmp_path / "docs/fixture.json",
                per_stratum=1,
            )
        )


def test_private_path_resolves_parent_traversal_before_confinement(controller, tmp_path):
    with pytest.raises(ValueError, match="private_output_required"):
        controller.private_path(tmp_path / "outputs/../docs/private.json")
    assert (
        controller.private_path(tmp_path / "outputs/run/row.private.json")
        == (tmp_path / "outputs/run/row.private.json").resolve()
    )


def test_input_metadata_mismatch_fails_before_model_or_output(controller, tmp_path, monkeypatch):
    args, _, metadata, _ = configuration(controller, tmp_path)
    metadata["dataset_revision"] = "b" * 64
    args.experiment_metadata.write_text(json.dumps(metadata), encoding="utf-8")
    process = create_autospec(controller.subprocess.run)
    monkeypatch.setattr(controller.subprocess, "run", process)
    with pytest.raises(ValueError, match="input_changed"):
        controller.run(args)
    process.assert_not_called()
    assert not args.output.exists()


def test_unknown_case_fields_are_not_copied_into_private_observations(
    controller, tmp_path, monkeypatch
):
    args, manifest, _, _ = configuration(controller, tmp_path)
    manifest["cases"][0]["private_prompt"] = "UNEXPECTED"
    args.input.write_text(json.dumps(manifest), encoding="utf-8")
    process = create_autospec(controller.subprocess.run)
    monkeypatch.setattr(controller.subprocess, "run", process)
    with pytest.raises(ValueError):
        controller.run(args)
    process.assert_not_called()


@pytest.mark.parametrize("key", ["source_code_sha256", "model_digest"])
def test_worker_identity_mismatch_remains_a_failed_row(controller, tmp_path, monkeypatch, key):
    args, _, _, result = configuration(controller, tmp_path)
    result[key] = "b" * 64
    process = create_autospec(
        controller.subprocess.run, return_value=CompletedProcess([], 0, json.dumps(result), "")
    )
    monkeypatch.setattr(controller.subprocess, "run", process)
    controller.run(args)
    aggregate = json.loads((args.output / "aggregate.json").read_text(encoding="utf-8"))
    assert aggregate["metrics"]["planned_rows"] == aggregate["metrics"]["failed_rows"] == 1
    assert aggregate["metrics"]["completed_rows"] == 0


def test_recording_uses_frozen_input_and_metadata_when_disk_files_change(
    controller, tmp_path, monkeypatch
):
    args, _, metadata, result = configuration(controller, tmp_path)

    def changed_files(*_args, **_kwargs):
        args.input.write_text("{}", encoding="utf-8")
        args.experiment_metadata.write_text("{}", encoding="utf-8")
        return CompletedProcess([], 0, json.dumps(result), "")

    process = create_autospec(controller.subprocess.run, side_effect=changed_files)
    monkeypatch.setattr(controller.subprocess, "run", process)
    controller.run(args)
    aggregate = json.loads((args.output / "aggregate.json").read_text(encoding="utf-8"))
    assert aggregate["input_sha256"] == metadata["dataset_revision"]
    assert aggregate["metrics"]["completed_rows"] == 1
    assert metadata["dataset_revision"] in args.results_md.read_text(encoding="utf-8")
    command = process.call_args.args[0]
    assert command[:2] == ["bash", str(tmp_path / "scripts/stack.sh")]
    assert process.call_args.kwargs["timeout"] == 115
    assert process.call_args.kwargs["encoding"] == "utf-8"


def visible_configuration(controller, tmp_path):
    args, manifest, metadata, result = configuration(controller, tmp_path)
    args.visible_model = "test:local"
    path = tmp_path / "app/backend/app/domain/transcript_suggestions.py"
    path.write_bytes(b"visible source")
    source_hash = hashlib.sha256(b"fixture source" * 2 + b"visible source").hexdigest()
    metadata["models"][0]["id"] = "ollama/test-local"
    metadata["configuration_sha256"] = source_hash
    args.experiment_metadata.write_text(json.dumps(metadata), encoding="utf-8")
    result.update(
        model_name="test:local",
        policy_version="tr-context-words-v2",
        source_code_sha256=source_hash,
        model_output='{"edits":[]}',
        model_output_truncated=False,
        saveable=False,
        review_required_count=0,
    )
    return args, manifest, metadata, result


def test_visible_mode_preserves_all_mapped_edits_and_separates_protocol(
    controller, tmp_path, monkeypatch
):
    args, _, _, result = visible_configuration(controller, tmp_path)
    result.update(
        status="suggested",
        suggested="Clean word.",
        edits=[dict(start_char=6, end_char=10, original="text", replacement="word")],
        saveable=True,
        review_required_count=1,
    )
    process = create_autospec(
        controller.subprocess.run, return_value=CompletedProcess([], 0, json.dumps(result), "")
    )
    monkeypatch.setattr(controller.subprocess, "run", process)
    controller.run(args)
    payload = json.loads(process.call_args.kwargs["input"])
    assert payload["model_name"] == "test:local"
    report = json.loads((args.output / "aggregate.json").read_text(encoding="utf-8"))
    assert report["protocol"] == "voiceup-context-review-visible-v1"
    assert report["policy_version"] == "tr-context-words-v2"
    assert report["metrics"]["damaged_clean_rows"] == 1
    assert report["review_required_edits"] == 1
    assert report["saveable_rows"] == 1
    assert "model_output" not in report
    assert "tr-context-words-v2" in args.results_md.read_text(encoding="utf-8")


def test_visible_mode_does_not_accept_a_different_selected_model(controller, tmp_path, monkeypatch):
    args, _, _, result = visible_configuration(controller, tmp_path)
    result["model_name"] = "other:local"
    process = create_autospec(
        controller.subprocess.run, return_value=CompletedProcess([], 0, json.dumps(result), "")
    )
    monkeypatch.setattr(controller.subprocess, "run", process)
    controller.run(args)
    report = json.loads((args.output / "aggregate.json").read_text(encoding="utf-8"))
    assert report["metrics"]["failed_rows"] == 1
    assert report["metrics"]["corrected_errors"] == report["metrics"]["raw_errors"]


def test_visible_raw_reply_is_retained_privately_when_it_cannot_be_mapped(
    controller, tmp_path, monkeypatch
):
    args, _, _, result = visible_configuration(controller, tmp_path)
    result.update(status="invalid_output", model_output="Raw model answer")
    process = create_autospec(
        controller.subprocess.run, return_value=CompletedProcess([], 0, json.dumps(result), "")
    )
    monkeypatch.setattr(controller.subprocess, "run", process)
    controller.run(args)
    report = json.loads((args.output / "aggregate.json").read_text(encoding="utf-8"))
    row = json.loads((args.output / "row-001.private.json").read_text(encoding="utf-8"))
    assert row["model_output"] == "Raw model answer"
    assert report["visible_status_counts"]["invalid_output"] == 1
    assert report["metrics"]["changed_rows"] == 0


@pytest.mark.parametrize(
    "status,truncated,unmapped", [("unmapped", False, 1), ("invalid_output", True, 0)]
)
def test_unsaveable_projection_is_visible_but_scored_with_unchanged_source(
    controller, tmp_path, monkeypatch, status, truncated, unmapped
):
    args, _, _, result = visible_configuration(controller, tmp_path)
    result.update(
        status=status,
        model_output_truncated=truncated,
        suggested="Clean word.",
        edits=[dict(start_char=6, end_char=10, original="text", replacement="word")],
        rejected_count=unmapped,
    )
    process = create_autospec(
        controller.subprocess.run, return_value=CompletedProcess([], 0, json.dumps(result), "")
    )
    monkeypatch.setattr(controller.subprocess, "run", process)
    controller.run(args)
    report = json.loads((args.output / "aggregate.json").read_text(encoding="utf-8"))
    row = json.loads((args.output / "row-001.private.json").read_text(encoding="utf-8"))
    assert report["metrics"]["corrected_errors"] == report["metrics"]["raw_errors"] == 0
    assert report["metrics"]["accepted_edits"] == 0
    assert row["visible_suggested"] == "Clean word."
    assert row["visible_edits"] == result["edits"]
    assert row["suggested"] == row["original"]
