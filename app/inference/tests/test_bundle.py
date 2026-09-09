"""Real filesystem tests for pinned package rejection, without model downloads."""

import importlib.util
import json
from pathlib import Path

import pytest

from voiceup_inference.model_bundle import BundleError, manifest, verify_bundle


def test_missing_package_rejected(tmp_path):
    with pytest.raises(BundleError, match="missing or unreadable"):
        verify_bundle(tmp_path / "missing")


def test_manifest_cannot_admit_modified_hashes_or_revision(tmp_path):
    for key, value in (("model_revision", "untrusted"), ("files", {"custom.py": "00"})):
        data = manifest()
        data[key] = value
        (tmp_path / "manifest.json").write_text(json.dumps(data))
        with pytest.raises(BundleError, match="metadata"):
            verify_bundle(tmp_path)


def test_valid_metadata_without_files_is_not_ready(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(manifest()))
    with pytest.raises(BundleError, match="missing or non-regular"):
        verify_bundle(tmp_path)


def test_modified_file_is_rejected_against_compiled_allowlist(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(manifest()))
    (tmp_path / "ecapa").mkdir()
    (tmp_path / "ecapa" / "hyperparams.yaml").write_text("untrusted: content")
    with pytest.raises(BundleError, match="content hash"):
        verify_bundle(tmp_path)


def test_oversized_or_invalid_manifest_is_rejected(tmp_path):
    for value in ("x" * 16385, "{broken json"):
        (tmp_path / "manifest.json").write_text(value)
        with pytest.raises(BundleError):
            verify_bundle(tmp_path)


def test_packager_rejects_unverified_source_before_creating_output(tmp_path):
    script = Path(__file__).resolve().parents[3] / "scripts" / "package-speaker-model.py"
    spec = importlib.util.spec_from_file_location("package_speaker_model", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source"
    source.mkdir()
    (source / "hyperparams.yaml").write_text("untrusted: content")
    output = tmp_path / "package"
    with pytest.raises(BundleError):
        module.package_model(source, tmp_path / "silero.jit", output)
    assert not output.exists()


def test_packager_never_overwrites_existing_output(tmp_path):
    script = Path(__file__).resolve().parents[3] / "scripts" / "package-speaker-model.py"
    spec = importlib.util.spec_from_file_location("package_speaker_model", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    preserved = tmp_path / "keep.txt"
    preserved.write_text("preserved")
    with pytest.raises(ValueError, match="already exists"):
        module.package_model(tmp_path, tmp_path / "missing.jit", tmp_path)
    assert preserved.read_text() == "preserved"
