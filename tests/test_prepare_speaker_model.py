"""Build-time model acquisition preserves existing files and verifies pinned bytes."""

import hashlib
import importlib.util
import io
from pathlib import Path
from unittest.mock import Mock
from urllib.request import OpenerDirector

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare-speaker-model.py"


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("prepare_speaker_model", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verified_existing_file_uses_no_network(helper, tmp_path):
    target = tmp_path / "model.ckpt"
    target.write_bytes(b"verified fixture")
    opener = Mock(spec_set=OpenerDirector)
    helper.fetch_model(
        "https://huggingface.co/fixture",
        target,
        hashlib.sha256(target.read_bytes()).hexdigest(),
        opener=opener,
    )
    opener.open.assert_not_called()


def test_existing_invalid_file_is_preserved(helper, tmp_path):
    target = tmp_path / "model.ckpt"
    target.write_bytes(b"user content")
    opener = Mock(spec_set=OpenerDirector)
    with pytest.raises(ValueError, match="existing_model_hash_mismatch"):
        helper.fetch_model("https://huggingface.co/fixture", target, "0" * 64, opener=opener)
    assert target.read_bytes() == b"user content"
    opener.open.assert_not_called()


def test_download_published_only_after_hash_verification(helper, tmp_path):
    target = tmp_path / "model.ckpt"
    opener = Mock(spec_set=OpenerDirector)
    opener.open.return_value = io.BytesIO(b"wrong bytes")
    with pytest.raises(ValueError, match="downloaded_model_hash_mismatch"):
        helper.fetch_model("https://huggingface.co/fixture", target, "0" * 64, opener=opener)
    assert not target.exists()
    assert not list(tmp_path.glob("*.partial"))


def test_verified_download_is_atomic_and_reusable(helper, tmp_path):
    payload = b"pinned model fixture"
    target = tmp_path / "model.ckpt"
    opener = Mock(spec_set=OpenerDirector)
    opener.open.return_value = io.BytesIO(payload)
    helper.fetch_model(
        "https://huggingface.co/fixture", target, hashlib.sha256(payload).hexdigest(), opener=opener
    )
    assert target.read_bytes() == payload
    assert not list(tmp_path.glob("*.partial"))


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/file",
        "https://example.com/file",
        "https://user:password@huggingface.co/file",
        "https://huggingface.co:444/file",
        "https://evil.huggingface.co/file",
    ],
)
def test_untrusted_model_redirect_is_rejected(helper, url):
    with pytest.raises(ValueError, match="untrusted_model_url"):
        helper.validate_model_url(url)


@pytest.mark.parametrize(
    "host", ["us.aws.cdn.hf.co", "us.gcp.cdn.hf.co", "cdn-lfs-us-1.hf.co", "cdn-lfs-eu-1.hf.co"]
)
def test_official_model_storage_redirects_are_supported(helper, host):
    helper.validate_model_url(f"https://{host}/fixture?signature=public-test-fixture")


def test_download_size_is_bounded(helper, tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "MAX_MODEL_BYTES", 4)
    target = tmp_path / "model.ckpt"
    opener = Mock(spec_set=OpenerDirector)
    opener.open.return_value = io.BytesIO(b"exceeds limit")
    with pytest.raises(ValueError, match="model_download_too_large"):
        helper.fetch_model("https://huggingface.co/fixture", target, "0" * 64, opener=opener)
    assert not target.exists()


def test_existing_bundle_is_verified_without_acquisition(helper, tmp_path, monkeypatch):
    output = tmp_path / "models/speaker-pilot"
    output.mkdir(parents=True)
    verify = Mock(spec_set=helper.verify_bundle, side_effect=ValueError("invalid_bundle"))
    fetch = Mock(spec_set=helper.fetch_model)
    monkeypatch.setattr(helper, "verify_bundle", verify)
    monkeypatch.setattr(helper, "fetch_model", fetch)
    with pytest.raises(ValueError, match="invalid_bundle"):
        helper.prepare(tmp_path)
    fetch.assert_not_called()


def test_jit_publication_is_verified_reusable_and_atomic(helper, tmp_path):
    payload = b"verified jit fixture"
    path = tmp_path / "model.jit"
    digest = hashlib.sha256(payload).hexdigest()
    helper.publish_model_bytes(path, payload, digest)
    helper.publish_model_bytes(path, payload, digest)
    assert path.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [path]


def test_jit_publication_refuses_invalid_source_and_preserves_existing(helper, tmp_path):
    path = tmp_path / "model.jit"
    with pytest.raises(ValueError):
        helper.publish_model_bytes(path, b"untrusted", "0" * 64)
    assert not path.exists()
    path.write_bytes(b"existing different file")
    payload = b"verified fixture"
    with pytest.raises(ValueError):
        helper.publish_model_bytes(path, payload, hashlib.sha256(payload).hexdigest())
    assert path.read_bytes() == b"existing different file"


def test_jit_publication_refuses_directory(helper, tmp_path):
    path = tmp_path / "model.jit"
    path.mkdir()
    with pytest.raises(ValueError):
        helper.publish_model_bytes(path, b"fixture", hashlib.sha256(b"fixture").hexdigest())
    assert path.is_dir()
