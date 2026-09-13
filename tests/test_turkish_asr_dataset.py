"""MediaSpeech extraction uses regular bounded files and frozen clip selection."""

import importlib.util
import io
import json
import os
import subprocess
import sys
from argparse import Namespace
from uuid import UUID
import tarfile
from pathlib import Path

import pytest


@pytest.fixture
def script():
    spec = importlib.util.spec_from_file_location(
        "turkish_asr", Path(__file__).parents[1] / "scripts/evaluate-turkish-asr.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_member_path_cannot_escape_or_link(script):
    for name in ("../escape.txt", "/TR/a.txt", "TR/../../a.flac", "TR/a.wav", "TR/a/b.txt"):
        member = tarfile.TarInfo(name)
        member.size = 10
        with pytest.raises(ValueError):
            script.member_identity(member)
    member = tarfile.TarInfo("TR/" + "a" * 36 + ".flac")
    member.type = tarfile.SYMTYPE
    with pytest.raises(ValueError):
        script.member_identity(member)


def test_duplicate_archive_reference_is_refused(script, tmp_path):
    path = tmp_path / "TR.tgz"
    with tarfile.open(path, "w:gz") as archive:
        for _ in range(2):
            member = tarfile.TarInfo("TR/00000000-0000-4000-8000-000000000001.txt")
            member.size = 1
            archive.addfile(member, io.BytesIO(b"a"))
    with pytest.raises(ValueError, match="duplicate"):
        script.index_archive(path)


def test_selection_is_reproducible_and_clip_disjoint(script):
    identities = [str(index) for index in range(100)]
    a, b = script.select_clips(identities, 10)
    assert (a, b) == script.select_clips(list(reversed(identities)), 10)
    assert len(a) == len(b) == 10
    assert not set(a) & set(b)


def test_existing_files_are_never_overwritten(script, tmp_path):
    target = tmp_path / "file.txt"
    script.immutable_write(target, b"original")
    script.immutable_write(target, b"original")
    with pytest.raises(ValueError, match="conflict"):
        script.immutable_write(target, b"replacement")
    assert target.read_bytes() == b"original"


def test_aggregate_sums_clip_edits_without_cross_clip_permutation(script):
    report = {
        "status": "complete",
        "manifest_sha256": "a" * 64,
        "archive_sha256": "b" * 64,
        "planned_clips": 2,
        "clips": [
            {
                "metrics": {
                    "counts": {"reference_words": 10, "hypothesis_words": 11},
                    "cpwer": {"errors": 3, "substitutions": 2, "deletions": 0, "insertions": 1},
                }
            },
            {
                "metrics": {
                    "counts": {"reference_words": 20, "hypothesis_words": 19},
                    "cpwer": {"errors": 1, "substitutions": 0, "deletions": 1, "insertions": 0},
                }
            },
        ],
    }
    result = script.aggregate(report)
    assert result["wer"] == pytest.approx(4 / 30)
    assert result["reference_words"] == 30
    assert "speaker" not in str(result)
    assert "clips" not in result
    report["status"] = "incomplete"
    assert script.aggregate(report)["wer"] is None


def manifest_fixture(script, tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    identities = [str(UUID(int=i)) for i in range(1, 5)]
    dev, test = script.select_clips(identities, 2)
    rows = [
        {
            "clip_id": value,
            "role": "calibration" if value in dev else "frozen-test",
            "flac_sha256": f"{index:064x}",
            "txt_sha256": "b" * 64,
            "reference": "özel metin",
        }
        for index, value in enumerate(dev + test, 1)
    ]
    value = {
        "schema_version": 1,
        "protocol": script.SEED,
        "language": "tr",
        "source_url": script.URL,
        "archive_sha256": script.ARCHIVE_SHA256,
        "archive_bytes": script.ARCHIVE_BYTES,
        "reference_quality": "source-human-transcribed",
        "selection": "sha256-seed-order-clip-disjoint",
        "speaker_session_labels_available": False,
        "clips": rows,
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return root, path, value


def test_manifest_hash_binds_exact_bounded_file_bytes(script, tmp_path):
    root, path, value = manifest_fixture(script, tmp_path)
    document, observed_hash = script.load_manifest(root)
    assert document == value
    assert observed_hash == script.digest(path)


@pytest.mark.parametrize(
    "change", ["duplicate_id", "duplicate_audio", "role", "boolean_version", "order"]
)
def test_entire_manifest_validates_both_roles_before_selection(script, tmp_path, change):
    root, path, value = manifest_fixture(script, tmp_path)
    if change == "duplicate_id":
        value["clips"][2]["clip_id"] = value["clips"][0]["clip_id"]
    elif change == "duplicate_audio":
        value["clips"][2]["flac_sha256"] = value["clips"][0]["flac_sha256"]
    elif change == "role":
        value["clips"][2]["role"] = "calibration"
    elif change == "boolean_version":
        value["schema_version"] = True
    else:
        value["clips"] = list(reversed(value["clips"]))
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError):
        script.load_manifest(root)


def test_manifest_rejects_duplicate_fields_and_oversized_files(script, tmp_path, monkeypatch):
    root, path, _ = manifest_fixture(script, tmp_path)
    path.write_text('{"schema_version": 1, "schema_version": 1}')
    with pytest.raises(ValueError, match="duplicate"):
        script.load_manifest(root)
    monkeypatch.setattr(script, "MAX_MANIFEST_BYTES", 16)
    with pytest.raises(ValueError, match="limit"):
        script.load_manifest(root)


def test_output_alias_and_model_descendants_are_rejected_before_writes(script, tmp_path):
    root, manifest_path, _ = manifest_fixture(script, tmp_path)
    models = tmp_path / "models"
    models.mkdir()
    model_manifest = tmp_path / "model-manifest.json"
    model_manifest.write_text("preserved")
    output = tmp_path / "result.json"
    os.link(model_manifest, output)
    args = Namespace(
        root=root,
        output=output,
        model_dir=models,
        model_manifest=model_manifest,
        results_md=tmp_path / "results.md",
    )
    with pytest.raises(ValueError):
        script.evaluation_paths(args, [])
    args.output = models / "new-file.json"
    with pytest.raises(ValueError):
        script.evaluation_paths(args, [])
    assert model_manifest.read_text() == "preserved"
    assert manifest_path.is_file()
    assert not args.output.exists()


def test_bounded_decoder_rejects_long_audio_before_allocating_samples(script, tmp_path):
    import soundfile as sf
    import numpy as np

    path = tmp_path / "too-long.flac"
    with sf.SoundFile(
        path, "w", samplerate=16000, channels=1, format="FLAC", subtype="PCM_16"
    ) as audio:
        for _ in range(61):
            audio.write(np.zeros(16000, dtype="float32"))
    with pytest.raises(ValueError, match="invalid_audio"):
        script.read_audio(path)


def test_bounded_decoder_preserves_original_float32_samples(script, tmp_path):
    import soundfile as sf
    import numpy as np

    path = tmp_path / "short.flac"
    samples = np.linspace(-0.5, 0.5, 16000, dtype="float32")
    sf.write(path, samples, 16000, subtype="PCM_16")
    expected, expected_rate = sf.read(path, dtype="float32")
    actual, rate = script.read_audio(path)
    assert rate == expected_rate == 16000
    np.testing.assert_array_equal(actual, expected)


def test_unique_atomic_checkpoint_preserves_old_partial_name(script, tmp_path):
    output = tmp_path / "run.json"
    stale = tmp_path / "run.partial.json"
    stale.write_text("user-owned")
    script.save_checkpoint(output, {"status": "incomplete"})
    script.save_checkpoint(output, {"status": "complete"})
    assert json.loads(output.read_text()) == {"status": "complete"}
    assert stale.read_text() == "user-owned"
    assert not list(tmp_path.glob("*.tmp"))


def test_real_process_lock_rejects_second_evaluation_before_model_import(script, tmp_path):
    root, _, _ = manifest_fixture(script, tmp_path)
    output, public = tmp_path / "run.json", tmp_path / "run.aggregate.json"
    arguments = [
        sys.executable,
        script.__file__,
        "evaluate",
        "--root",
        str(root),
        "--output",
        str(output),
        "--model-dir",
        str(tmp_path / "models"),
        "--model-manifest",
        str(tmp_path / "model.json"),
        "--experiment-id",
        "lock-test",
        "--results-md",
        str(tmp_path / "results.md"),
    ]
    with script.evaluation_lock(output, public):
        result = subprocess.run(arguments, text=True, capture_output=True, timeout=15)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert not output.exists()
    assert not public.exists()


def test_pinned_archive_change_fails_before_extracting(script, tmp_path, monkeypatch):
    archive = tmp_path / "TR.tgz"
    archive.write_bytes(b"changed")
    monkeypatch.setattr(script, "ARCHIVE_BYTES", 7)
    with pytest.raises(ValueError, match="archive_revision_changed"):
        script.prepare(tmp_path, download=False, count=1)
    assert not (tmp_path / "clips").exists()
    assert not (tmp_path / "manifest.json").exists()


def test_orchestration_freezes_source_and_manifest_hash_before_model_work(
    script, tmp_path, monkeypatch
):
    root, manifest_path, _ = manifest_fixture(script, tmp_path)
    expected_script, expected_manifest = (
        script.digest(Path(script.__file__)),
        script.digest(manifest_path),
    )
    args = Namespace(
        root=root,
        output=tmp_path / "run.json",
        model_dir=tmp_path / "models",
        model_manifest=tmp_path / "model.json",
        results_md=tmp_path / "results.md",
        role="frozen-test",
        language="tr",
    )
    from unittest.mock import create_autospec

    def inspect(_args, _root, _manifest, manifest_hash, output, _public, source_hash):
        # An edit after validation cannot relabel the bytes whose model work was requested.
        manifest_path.write_text("edited after validation")
        script.save_checkpoint(output, {"source": source_hash, "manifest": manifest_hash})

    delegate = create_autospec(script._evaluate, side_effect=inspect)
    monkeypatch.setattr(script, "_evaluate", delegate)
    script.evaluate(args)
    report = json.loads(args.output.read_text())
    assert report == {"source": expected_script, "manifest": expected_manifest}
