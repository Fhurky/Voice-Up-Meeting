"""Public ASR model packages use immutable bytes and require no credentials."""

import copy
import hashlib
import http.client
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.request import OpenerDirector

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare-asr-model.py"
REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
PATHS = (
    "README.md",
    "config.json",
    "model.bin",
    "preprocessor_config.json",
    "tokenizer.json",
    "vocabulary.json",
)


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("prepare_asr_model", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def manifest():
    return {
        "schema_version": 1,
        "repository": "Systran/faster-whisper-large-v3",
        "revision": REVISION,
        "license": "mit",
        "files": [
            {
                "path": name,
                "size_bytes": len(name),
                "sha256": hashlib.sha256(name.encode()).hexdigest(),
            }
            for name in PATHS
        ],
    }


def write_manifest(root, document):
    path = root / "manifest.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def parsed_response(body, *, status=200, content_range=None):
    headers = f"Content-Length: {len(body)}\r\n"
    if content_range:
        headers += f"Content-Range: {content_range}\r\n"
    raw = f"HTTP/1.1 {status} OK\r\n{headers}\r\n".encode() + body
    response = http.client.HTTPResponse(SimpleNamespace(makefile=lambda mode: io.BytesIO(raw)))
    response.begin()
    return response


def populate(root, document):
    target = root / "models/asr-large-v3" / REVISION
    target.mkdir(parents=True)
    for row in document["files"]:
        (target / row["path"]).write_bytes(row["path"].encode())
    return target


def test_committed_inventory_pins_selected_model_and_all_runtime_files(helper):
    document = helper.load_manifest()
    assert document["revision"] == REVISION
    assert document["repository"] == "Systran/faster-whisper-large-v3"
    assert document["license"] == "mit"
    assert {r["path"] for r in document["files"]} == set(PATHS)
    assert sum(r["size_bytes"] for r in document["files"]) == 3090837754


@pytest.mark.parametrize(
    "change", ["revision", "repository", "license", "path", "size", "hash", "missing", "duplicate"]
)
def test_unpinned_or_unsafe_manifest_rejected(helper, manifest, tmp_path, change):
    if change in {"revision", "repository", "license"}:
        manifest[change] = "untrusted"
    elif change == "path":
        manifest["files"][0]["path"] = "../outside"
    elif change == "size":
        manifest["files"][0]["size_bytes"] = 2**40
    elif change == "hash":
        manifest["files"][0]["sha256"] = "no"
    elif change == "missing":
        manifest["files"].pop()
    else:
        manifest["files"][1] = copy.deepcopy(manifest["files"][0])
    with pytest.raises(ValueError, match="invalid_manifest"):
        helper.load_manifest(write_manifest(tmp_path, manifest))


@pytest.mark.parametrize("verify_only", [False, True])
def test_existing_package_reuses_without_network_or_token(
    helper, manifest, tmp_path, monkeypatch, verify_only
):
    target = populate(tmp_path, manifest)
    (tmp_path / ".env").mkdir()
    monkeypatch.setenv("HF_TOKEN", "must-not-be-read")
    opener = Mock(spec_set=OpenerDirector)
    opener.open.side_effect = AssertionError("network attempted")
    result = helper.prepare(
        tmp_path,
        manifest_path=write_manifest(tmp_path, manifest),
        verify_only=verify_only,
        opener=opener,
    )
    assert Path(result["directory"]) == target
    assert result["files"] == 6
    opener.open.assert_not_called()


def test_public_download_sends_no_token_and_publishes_only_verified_package(
    helper, manifest, tmp_path, monkeypatch
):
    monkeypatch.setenv("HF_TOKEN", "must-not-be-forwarded")
    (tmp_path / ".env").mkdir()
    requested = []

    def open_response(request, timeout):
        assert timeout == 60
        assert not any("authorization" in key.lower() for key, _ in request.header_items())
        assert request.full_url.startswith(
            f"https://huggingface.co/Systran/faster-whisper-large-v3/resolve/{REVISION}/"
        )
        name = request.full_url.rsplit("/", 1)[1]
        requested.append(name)
        return parsed_response(name.encode())

    opener = Mock(spec_set=OpenerDirector)
    opener.open.side_effect = open_response
    result = helper.prepare(
        tmp_path, manifest_path=write_manifest(tmp_path, manifest), opener=opener
    )
    assert result["status"] == "prepared"
    assert requested == list(PATHS)
    helper.verify_package(Path(result["directory"]), manifest)


@pytest.mark.parametrize("body", [b"", b"wrong-data", b"x" * 100])
def test_corrupt_download_never_publishes_package(helper, manifest, tmp_path, body):
    opener = Mock(spec_set=OpenerDirector)
    opener.open.return_value = parsed_response(body)
    with pytest.raises(ValueError, match="downloaded_model"):
        helper.prepare(tmp_path, manifest_path=write_manifest(tmp_path, manifest), opener=opener)
    assert not (tmp_path / "models/asr-large-v3" / REVISION).exists()


@pytest.mark.parametrize("change", ["corrupt", "missing", "extra"])
def test_existing_different_package_is_preserved(helper, manifest, tmp_path, change):
    target = populate(tmp_path, manifest)
    if change == "corrupt":
        (target / "config.json").write_bytes(b"altered")
    elif change == "missing":
        (target / "config.json").unlink()
    else:
        (target / "unexpected").write_bytes(b"extra")
    before = {p.name: p.read_bytes() for p in target.iterdir()}
    with pytest.raises(ValueError):
        helper.prepare(tmp_path, manifest_path=write_manifest(tmp_path, manifest))
    assert {p.name: p.read_bytes() for p in target.iterdir()} == before


def test_large_file_uses_exact_ranges_and_verifies_whole_file(helper, tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "RANGE_BYTES", 4)
    body = b"large-model"
    row = {"path": "model.bin", "size_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    requested = []

    def open_range(request, timeout):
        value = request.get_header("Range")
        requested.append(value)
        start, end = map(int, value.removeprefix("bytes=").split("-"))
        return parsed_response(
            body[start : end + 1], status=206, content_range=f"bytes {start}-{end}/{len(body)}"
        )

    opener = Mock(spec_set=OpenerDirector)
    opener.open.side_effect = open_range
    helper.fetch_file(row, tmp_path / "model.bin", opener=opener)
    assert (tmp_path / "model.bin").read_bytes() == body
    assert set(requested) == {"bytes=0-3", "bytes=4-7", "bytes=8-10"}


@pytest.mark.parametrize("content_range", [None, "bytes 1-4/11", "bytes 0-3/12"])
def test_large_file_rejects_wrong_or_missing_range(helper, tmp_path, monkeypatch, content_range):
    monkeypatch.setattr(helper, "RANGE_BYTES", 4)
    row = {
        "path": "model.bin",
        "size_bytes": 11,
        "sha256": hashlib.sha256(b"large-model").hexdigest(),
    }
    opener = Mock(spec_set=OpenerDirector)
    opener.open.side_effect = lambda request, timeout: parsed_response(
        b"larg", status=206, content_range=content_range
    )
    with pytest.raises(ValueError, match="downloaded_model_range_mismatch"):
        helper.fetch_file(row, tmp_path / "model.bin", opener=opener)
    assert not (tmp_path / "model.bin").exists()
