"""Pinned model preparation uses real files and parsed HTTP response boundaries."""

import copy
import hashlib
import http.client
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.request import OpenerDirector, Request

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare-diarization-model.py"
REVISION = "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
PATHS = (
    "README.md",
    "config.yaml",
    "embedding/README.md",
    "plda/README.md",
    "embedding/pytorch_model.bin",
    "plda/plda.npz",
    "plda/xvec_transform.npz",
    "segmentation/pytorch_model.bin",
)


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("prepare_diarization_model", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def manifest():
    return {
        "schema_version": 1,
        "repository": "pyannote/speaker-diarization-community-1",
        "revision": REVISION,
        "license": "cc-by-4.0",
        "files": [
            {
                "path": name,
                "size_bytes": len(name.encode()),
                "sha256": hashlib.sha256(name.encode()).hexdigest(),
            }
            for name in PATHS
        ],
    }


def write_manifest(tmp_path, manifest):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def parsed_response(body):
    raw = f"HTTP/1.1 200 OK\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body
    response = http.client.HTTPResponse(SimpleNamespace(makefile=lambda mode: io.BytesIO(raw)))
    response.begin()
    return response


def output_path(root):
    return root / "models/diarization-community-1" / REVISION


def populate(root, manifest):
    output = output_path(root)
    for row in manifest["files"]:
        path = output / row["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(row["path"].encode())
    return output


def test_committed_manifest_pins_complete_offline_inventory(helper):
    document = helper.load_manifest()
    assert document["repository"] == "pyannote/speaker-diarization-community-1"
    assert document["revision"] == REVISION
    assert document["license"] == "cc-by-4.0"
    assert {row["path"] for row in document["files"]} == set(PATHS)
    assert sum(row["size_bytes"] for row in document["files"]) == 32832557
    assert next(row for row in document["files"] if row["path"] == "config.yaml") == {
        "path": "config.yaml",
        "size_bytes": 444,
        "sha256": "5ce2bfa9a938dc132cec1172592d65173cbb8f444ea1e4133f10f9391de155be",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository", "other/model"),
        ("revision", "main"),
        ("license", "unknown"),
        ("schema_version", 2),
    ],
)
def test_manifest_rejects_unpinned_identity(helper, manifest, tmp_path, field, value):
    manifest[field] = value
    with pytest.raises(ValueError, match="invalid_manifest"):
        helper.load_manifest(write_manifest(tmp_path, manifest))


@pytest.mark.parametrize(
    "value",
    [
        "../config.yaml",
        "/config.yaml",
        "C:/config.yaml",
        "embedding\\README.md",
        "embedding/../config.yaml",
        "config.yaml:stream",
        "config.yaml\n",
    ],
)
def test_manifest_refuses_unsafe_paths(helper, manifest, tmp_path, value):
    manifest["files"][0]["path"] = value
    with pytest.raises(ValueError, match="invalid_manifest"):
        helper.load_manifest(write_manifest(tmp_path, manifest))


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "size_zero", "size_bool", "size_large", "hash", "extra_url"]
)
def test_manifest_refuses_incomplete_or_unbounded_files(helper, manifest, tmp_path, change):
    if change == "missing":
        manifest["files"].pop()
    elif change == "duplicate":
        manifest["files"][1] = copy.deepcopy(manifest["files"][0])
    elif change.startswith("size_"):
        manifest["files"][0]["size_bytes"] = {
            "size_zero": 0,
            "size_bool": True,
            "size_large": 2**40,
        }[change]
    elif change == "hash":
        manifest["files"][0]["sha256"] = "not-a-digest"
    else:
        manifest["files"][0]["url"] = "https://example.com/model"
    with pytest.raises(ValueError, match="invalid_manifest"):
        helper.load_manifest(write_manifest(tmp_path, manifest))


def test_token_environment_precedes_file_without_reading_it(helper, tmp_path):
    (tmp_path / ".env").mkdir()
    assert helper.load_token(tmp_path, {"HF_TOKEN": "hf_environment123"}) == "hf_environment123"


@pytest.mark.parametrize(
    "line",
    [
        "HF_TOKEN=hf_fixture123",
        " HF_TOKEN = 'hf_fixture123' ",
        'export HF_TOKEN="hf_fixture123"',
        "HF_TOKEN=hf_fixture123 # local setup",
    ],
)
def test_token_parser_reads_only_literal_hf_assignment(helper, tmp_path, line):
    (tmp_path / ".env").write_text("GITHUB_TOKEN=unrelated\n" + line + "\n", encoding="utf-8")
    assert helper.load_token(tmp_path, {}) == "hf_fixture123"


@pytest.mark.parametrize(
    "content",
    [
        "HF_TOKEN=\n",
        "HF_TOKEN=hf_one\nHF_TOKEN=hf_two",
        'HF_TOKEN="hf_missing_quote',
        "HF_TOKEN=$(print-secret)",
        "GITHUB_TOKEN=unrelated",
    ],
)
def test_missing_or_ambiguous_token_fails_safely(helper, tmp_path, content):
    (tmp_path / ".env").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        helper.load_token(tmp_path, {})
    assert str(error.value) == "invalid_token_configuration"


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/file",
        "https://example.com/file",
        "https://evil.huggingface.co/file",
        "https://user:password@huggingface.co/file",
        "https://huggingface.co:444/file",
    ],
)
def test_untrusted_redirect_is_rejected_before_request(helper, url):
    request = Request("https://huggingface.co/model")
    request.add_unredirected_header("Authorization", "Bearer hf_fixture123")
    with pytest.raises(ValueError, match="untrusted_model_url"):
        helper.ModelRedirects().redirect_request(request, None, 302, "Found", {}, url)


@pytest.mark.parametrize("normal_header", [False, True])
@pytest.mark.parametrize("header_name", ["Authorization", "Proxy-Authorization"])
def test_cross_origin_redirect_never_forwards_bearer(helper, normal_header, header_name):
    request = Request("https://huggingface.co/model")
    add = request.add_header if normal_header else request.add_unredirected_header
    add(header_name, "Bearer hf_fixture123")
    redirected = helper.ModelRedirects().redirect_request(
        request, None, 302, "Found", {}, "https://cas-bridge.xethub.hf.co/model?signature=test"
    )
    assert not any(
        name.lower() in {"authorization", "proxy-authorization"}
        for name, _ in redirected.header_items()
    )
    assert "hf_fixture123" not in redirected.full_url


def test_same_origin_authentication_remains_unredirected(helper):
    request = Request("https://huggingface.co/model")
    request.add_unredirected_header("Authorization", "Bearer hf_fixture123")
    redirected = helper.ModelRedirects().redirect_request(
        request, None, 307, "Found", {}, "https://huggingface.co/api/resolve-cache/model"
    )
    assert redirected.get_header("Authorization") == "Bearer hf_fixture123"
    assert "Authorization" not in redirected.headers


def test_download_uses_pinned_url_and_header_then_reuses_verified_file(helper, manifest, tmp_path):
    row = manifest["files"][0]
    target = tmp_path / row["path"]
    opener = Mock(spec_set=OpenerDirector)
    opener.open.return_value = parsed_response(row["path"].encode())
    helper.fetch_file(row, target, "hf_fixture123", opener=opener)
    helper.fetch_file(row, target, "hf_fixture123", opener=opener)
    request = opener.open.call_args.args[0]
    assert (
        request.full_url
        == f"https://huggingface.co/pyannote/speaker-diarization-community-1/resolve/{REVISION}/README.md"
    )
    assert request.get_header("Authorization") == "Bearer hf_fixture123"
    assert "Authorization" not in request.headers
    assert opener.open.call_count == 1
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("body", [b"short", b"X" * 9, b"X" * 10])
def test_wrong_size_or_hash_never_publishes_file(helper, manifest, tmp_path, body):
    opener = Mock(spec_set=OpenerDirector)
    opener.open.return_value = parsed_response(body)
    with pytest.raises(ValueError):
        helper.fetch_file(
            manifest["files"][0], tmp_path / "README.md", "hf_fixture123", opener=opener
        )
    assert list(tmp_path.iterdir()) == []


def test_existing_different_file_is_preserved(helper, manifest, tmp_path):
    target = tmp_path / "README.md"
    target.write_bytes(b"user-owned bytes")
    opener = Mock(spec_set=OpenerDirector)
    with pytest.raises(ValueError):
        helper.fetch_file(manifest["files"][0], target, "hf_fixture123", opener=opener)
    assert target.read_bytes() == b"user-owned bytes"
    opener.open.assert_not_called()


def test_verified_bundle_and_verify_mode_need_neither_token_nor_network(
    helper, manifest, tmp_path, monkeypatch
):
    populate(tmp_path, manifest)
    manifest_path = write_manifest(tmp_path, manifest)
    token = Mock(spec_set=helper.load_token, side_effect=AssertionError("must not read secrets"))
    opener = Mock(spec_set=helper.build_opener, side_effect=AssertionError("must not open network"))
    monkeypatch.setattr(helper, "load_token", token)
    monkeypatch.setattr(helper, "build_opener", opener)
    helper.prepare(tmp_path, manifest_path=manifest_path, verify_only=True)
    helper.prepare(tmp_path, manifest_path=manifest_path)
    token.assert_not_called()
    opener.assert_not_called()


def test_verify_missing_package_does_not_create_directories(helper, manifest, tmp_path):
    manifest_path = write_manifest(tmp_path, manifest)
    with pytest.raises(ValueError):
        helper.prepare(tmp_path, manifest_path=manifest_path, verify_only=True)
    assert not (tmp_path / "models").exists()


@pytest.mark.parametrize("defect", ["missing", "changed", "extra"])
def test_invalid_existing_bundle_is_preserved_without_network(helper, manifest, tmp_path, defect):
    output = populate(tmp_path, manifest)
    if defect == "missing":
        (output / "config.yaml").unlink()
    elif defect == "changed":
        (output / "config.yaml").write_bytes(b"user content")
    else:
        (output / "notes.txt").write_bytes(b"user content")
    before = {
        p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob("*") if p.is_file()
    }
    opener = Mock(spec_set=OpenerDirector)
    with pytest.raises(ValueError):
        helper.prepare(tmp_path, manifest_path=write_manifest(tmp_path, manifest), opener=opener)
    assert before == {
        p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob("*") if p.is_file()
    }
    opener.open.assert_not_called()


@pytest.mark.parametrize("fail_last", [False, True])
def test_package_published_only_after_every_file_verified(
    helper, manifest, tmp_path, monkeypatch, fail_last
):
    monkeypatch.setenv("HF_TOKEN", "hf_fixture123")
    output = output_path(tmp_path)
    calls = []
    opener = Mock(spec_set=OpenerDirector)

    def download(request, *, timeout):
        assert not output.exists()
        name = request.full_url.split(f"/{REVISION}/", 1)[1]
        calls.append(name)
        return parsed_response(b"broken" if fail_last and name == PATHS[-1] else name.encode())

    opener.open.side_effect = download
    if fail_last:
        with pytest.raises(ValueError):
            helper.prepare(
                tmp_path, manifest_path=write_manifest(tmp_path, manifest), opener=opener
            )
        assert not output.exists()
    else:
        helper.prepare(tmp_path, manifest_path=write_manifest(tmp_path, manifest), opener=opener)
        assert len(list(output.rglob("*.bin"))) == 2
        helper.verify_package(output, manifest)
    assert calls == list(PATHS)
    assert not list(output.parent.glob(".community-*"))


def test_symlink_or_junction_ancestor_is_rejected(helper, manifest, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(linked), str(outside)],
            check=True,
            capture_output=True,
        )
    else:
        linked.symlink_to(outside, target_is_directory=True)
    opener = Mock(spec_set=OpenerDirector)
    with pytest.raises(ValueError, match="unsafe_path"):
        helper.fetch_file(
            manifest["files"][0], linked / "README.md", "hf_fixture123", opener=opener
        )
    assert list(outside.iterdir()) == []
    opener.open.assert_not_called()


def test_cli_failure_never_prints_sensitive_exception(helper, monkeypatch, capsys):
    failure = Mock(
        spec_set=helper.prepare,
        side_effect=OSError("Bearer hf_sentinelSecret https://signed.invalid/token"),
    )
    monkeypatch.setattr(helper, "prepare", failure)
    assert helper.main([]) == 1
    output = capsys.readouterr()
    assert "failed" in output.err.lower()
    assert "hf_sentinelSecret" not in output.err + output.out
    assert "https://" not in output.err + output.out


@pytest.mark.parametrize("existing", ["empty", "different"])
def test_directory_publication_never_replaces_existing_target(helper, tmp_path, existing):
    staged, output = tmp_path / "staged", tmp_path / "published"
    staged.mkdir()
    (staged / "model.bin").write_bytes(b"complete verified staged bytes")
    output.mkdir()
    if existing == "different":
        (output / "keep.txt").write_bytes(b"existing owner bytes")
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    with pytest.raises(FileExistsError):
        helper.publish_directory(staged, output)
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before
    assert (staged / "model.bin").read_bytes() == b"complete verified staged bytes"


def test_directory_publication_moves_complete_package_to_absent_target(helper, tmp_path):
    staged, output = tmp_path / "staged", tmp_path / "published"
    staged.mkdir()
    (staged / "model.bin").write_bytes(b"complete verified staged bytes")
    helper.publish_directory(staged, output)
    assert not staged.exists()
    assert (output / "model.bin").read_bytes() == b"complete verified staged bytes"


def test_directory_publication_fails_closed_on_unsupported_platform(helper, tmp_path, monkeypatch):
    staged, output = tmp_path / "staged", tmp_path / "published"
    staged.mkdir()
    monkeypatch.setattr(helper, "sys", SimpleNamespace(platform="unsupported"))
    with pytest.raises(ValueError, match="atomic_publication_unavailable"):
        helper.publish_directory(staged, output)
    assert staged.is_dir()
    assert not output.exists()


@pytest.mark.parametrize("concurrent", ["same", "empty", "different"])
def test_concurrent_publication_reuses_only_complete_identical_package(
    helper, manifest, tmp_path, monkeypatch, concurrent
):
    monkeypatch.setenv("HF_TOKEN", "hf_fixture123")
    output = output_path(tmp_path)
    publish = helper.publish_directory

    def concurrent_publish(staged, target):
        if concurrent == "same":
            populate(tmp_path, manifest)
        else:
            output.mkdir()
            if concurrent == "different":
                (output / "README.md").write_bytes(b"existing owner bytes")
        publish(staged, target)

    monkeypatch.setattr(helper, "publish_directory", concurrent_publish)
    opener = Mock(spec_set=OpenerDirector)
    opener.open.side_effect = lambda request, timeout: parsed_response(
        request.full_url.split(f"/{REVISION}/", 1)[1].encode()
    )
    path = write_manifest(tmp_path, manifest)
    if concurrent == "same":
        assert helper.prepare(tmp_path, manifest_path=path, opener=opener)["status"] == "reused"
    else:
        with pytest.raises(ValueError):
            helper.prepare(tmp_path, manifest_path=path, opener=opener)
        expected = {} if concurrent == "empty" else {"README.md": b"existing owner bytes"}
        assert {p.name: p.read_bytes() for p in output.iterdir()} == expected
    assert not list(output.parent.glob(".community-*"))
