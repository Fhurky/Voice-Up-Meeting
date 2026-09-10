"""Real filesystem verification with parsed HTTP response fixtures; no network downloads."""

import hashlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def downloader():
    path = Path(__file__).resolve().parents[1] / "scripts" / "prepare-spark-wheelhouse.py"
    spec = importlib.util.spec_from_file_location("spark_wheelhouse", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def artifact():
    body = b"a deterministic wheel fixture"
    return {
        "filename": "fixture-1.0-py3-none-any.whl",
        "url": "https://files.pythonhosted.org/packages/fixture-1.0-py3-none-any.whl",
        "sha256": hashlib.sha256(body).hexdigest(),
        "size_bytes": len(body),
    }


def parsed_response(body, status=200):
    raw = f"HTTP/1.1 {status} Test\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body
    response = http.client.HTTPResponse(SimpleNamespace(makefile=lambda mode: io.BytesIO(raw)))
    response.begin()
    return response


def manifest_file(tmp_path, artifact):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"artifacts": [artifact]}), encoding="utf-8")
    return path


def transport(monkeypatch, downloader, body=b"a deterministic wheel fixture"):
    calls = []

    def open_request(request, *, timeout):
        calls.append((request.full_url, timeout))
        return parsed_response(body)

    monkeypatch.setattr(
        downloader, "build_opener", lambda handler: SimpleNamespace(open=open_request)
    )
    return calls


def test_download_is_verified_reusable_and_leaves_unrelated_files(
    downloader, artifact, tmp_path, monkeypatch, capsys
):
    calls = transport(monkeypatch, downloader)
    directory = tmp_path / "wheels"
    directory.mkdir()
    (directory / "notes.txt").write_text("keep")
    manifest = manifest_file(tmp_path, artifact)
    downloader.prepare(manifest, directory)
    downloader.prepare(manifest, directory)
    assert len(calls) == 1
    assert (directory / artifact["filename"]).read_bytes() == b"a deterministic wheel fixture"
    assert (directory / "notes.txt").read_text() == "keep"
    assert sorted(p.name for p in directory.iterdir()) == [artifact["filename"], "notes.txt"]
    output = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row["status"] for row in output] == ["downloaded", "reused"]
    assert all(set(row) == {"filename", "status", "bytes"} for row in output)


@pytest.mark.parametrize("body", [b"short", b"X" * 29, b"X" * 28])
def test_wrong_size_or_hash_leaves_no_artifact_or_temp(
    downloader, artifact, tmp_path, monkeypatch, body
):
    transport(monkeypatch, downloader, body)
    directory = tmp_path / "wheels"
    with pytest.raises(downloader.WheelhouseError):
        downloader.prepare(manifest_file(tmp_path, artifact), directory)
    assert not list(directory.iterdir())


def test_corrupt_existing_file_is_preserved_and_never_downloaded(
    downloader, artifact, tmp_path, monkeypatch
):
    calls = transport(monkeypatch, downloader)
    directory = tmp_path / "wheels"
    directory.mkdir()
    target = directory / artifact["filename"]
    target.write_bytes(b"corrupt user-owned content")
    with pytest.raises(downloader.WheelhouseError, match="existing_artifact_mismatch"):
        downloader.prepare(manifest_file(tmp_path, artifact), directory)
    assert target.read_bytes() == b"corrupt user-owned content"
    assert calls == []


@pytest.mark.parametrize(
    "filename",
    [
        "../escape.whl",
        "sub/file.whl",
        "sub\\file.whl",
        "C:evil.whl",
        "CON.whl",
        "a\n.whl",
        "not-a-wheel.txt",
    ],
)
def test_unsafe_filenames_fail_before_directory_creation(downloader, artifact, tmp_path, filename):
    artifact["filename"] = filename
    with pytest.raises(downloader.WheelhouseError, match="invalid_filename"):
        downloader.prepare(manifest_file(tmp_path, artifact), tmp_path / "wheels")
    assert not (tmp_path / "wheels").exists()


@pytest.mark.parametrize(
    "url",
    [
        "http://files.pythonhosted.org/a.whl",
        "https://files.pythonhosted.org.evil.test/a.whl",
        "https://download.pytorch.org@evil.test/a.whl",
        "https://secret@download.pytorch.org/a.whl",
        "https://download.pytorch.org:444/a.whl",
        "https://download.pytorch.org/a.whl?token=secret",
        "https://download.pytorch.org/a.whl#secret",
        "https://download.pytorch.org/different.whl",
    ],
)
def test_unapproved_or_ambiguous_urls_are_rejected(downloader, artifact, tmp_path, url):
    artifact["url"] = url
    with pytest.raises(downloader.WheelhouseError, match="invalid_url"):
        downloader.prepare(manifest_file(tmp_path, artifact), tmp_path / "wheels")


@pytest.mark.parametrize(
    "key,value",
    [
        ("size_bytes", True),
        ("size_bytes", 0),
        ("size_bytes", 2**40),
        ("sha256", "bad"),
        ("sha256", "F" * 64),
    ],
)
def test_invalid_metadata_is_rejected(downloader, artifact, tmp_path, key, value):
    artifact[key] = value
    with pytest.raises(downloader.WheelhouseError):
        downloader.prepare(manifest_file(tmp_path, artifact), tmp_path / "wheels")


def test_manifest_duplicates_and_size_are_bounded(downloader, artifact, tmp_path):
    manifest = manifest_file(tmp_path, artifact)
    duplicate = {**artifact, "filename": artifact["filename"].upper()}
    manifest.write_text(json.dumps({"artifacts": [artifact, duplicate]}))
    with pytest.raises(downloader.WheelhouseError):
        downloader.prepare(manifest, tmp_path / "wheels")
    manifest.write_bytes(b" " * (downloader.MAX_MANIFEST_BYTES + 1))
    with pytest.raises(downloader.WheelhouseError, match="manifest_too_large"):
        downloader.prepare(manifest, tmp_path / "wheels")


def test_symlink_target_and_destination_are_rejected(downloader, artifact, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    directory = tmp_path / "wheels"
    try:
        directory.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        if os.name == "nt" and exc.winerror == 1314:
            pytest.skip("Windows account cannot create symlinks; real Linux symlink check required")
        raise
    manifest = manifest_file(tmp_path, artifact)
    with pytest.raises(downloader.WheelhouseError, match="unsafe_path"):
        downloader.prepare(manifest, directory)
    nested = directory / "nested"
    with pytest.raises(downloader.WheelhouseError, match="unsafe_path"):
        downloader.prepare(manifest, nested)
    ordinary = tmp_path / "ordinary"
    ordinary.mkdir()
    victim = outside / "victim"
    victim.write_bytes(b"preserve")
    (ordinary / artifact["filename"]).symlink_to(victim)
    with pytest.raises(downloader.WheelhouseError, match="unsafe_path"):
        downloader.prepare(manifest, ordinary)
    assert victim.read_bytes() == b"preserve"


def test_interruption_cleans_temp_and_next_run_can_retry(
    downloader, artifact, tmp_path, monkeypatch
):
    response = parsed_response(b"a deterministic wheel fixture")
    response.read = lambda amount: (_ for _ in ()).throw(KeyboardInterrupt())

    def interrupted_open(request, *, timeout):
        return response

    monkeypatch.setattr(
        downloader, "build_opener", lambda handler: SimpleNamespace(open=interrupted_open)
    )
    directory = tmp_path / "wheels"
    manifest = manifest_file(tmp_path, artifact)
    with pytest.raises(KeyboardInterrupt):
        downloader.prepare(manifest, directory)
    assert not list(directory.iterdir())
    transport(monkeypatch, downloader)
    downloader.prepare(manifest, directory)
    assert (directory / artifact["filename"]).is_file()


def test_redirect_is_checked_before_following(downloader, artifact):
    handler = downloader.OfficialRedirects(artifact["filename"])
    request = downloader.Request(artifact["url"])
    with pytest.raises(downloader.WheelhouseError, match="invalid_url"):
        handler.redirect_request(request, None, 302, "Found", {}, "https://evil.test/stolen.whl")


def test_stream_reads_are_bounded_and_non200_is_rejected(
    downloader, artifact, tmp_path, monkeypatch
):
    response = parsed_response(b"a deterministic wheel fixture")
    read = response.read
    amounts = []

    def bounded_read(amount):
        amounts.append(amount)
        return read(amount)

    response.read = bounded_read
    monkeypatch.setattr(
        downloader,
        "build_opener",
        lambda handler: SimpleNamespace(open=lambda request, timeout: response),
    )
    downloader.prepare(manifest_file(tmp_path, artifact), tmp_path / "wheels")
    assert amounts and all(0 < n <= downloader.CHUNK_BYTES for n in amounts)
    response = parsed_response(b"a deterministic wheel fixture", status=206)
    with pytest.raises(downloader.WheelhouseError, match="unexpected_http_status"):
        downloader.prepare(manifest_file(tmp_path, artifact), tmp_path / "other")


def test_concurrent_final_file_is_never_overwritten(downloader, artifact, tmp_path, monkeypatch):
    transport(monkeypatch, downloader)
    directory = tmp_path / "wheels"
    real_link = downloader.os.link

    def competing_link(source, target, **kwargs):
        Path(target).write_bytes(b"another publisher")
        return real_link(source, target, **kwargs)

    monkeypatch.setattr(downloader.os, "link", competing_link)
    with pytest.raises(downloader.WheelhouseError, match="existing_artifact_mismatch"):
        downloader.prepare(manifest_file(tmp_path, artifact), directory)
    assert (directory / artifact["filename"]).read_bytes() == b"another publisher"
    assert len(list(directory.iterdir())) == 1


def test_cli_error_never_echoes_manifest_secrets(downloader, artifact, tmp_path, capsys):
    artifact["url"] = "https://secret-token@download.pytorch.org/anything.whl"
    result = downloader.main(
        [
            "--manifest",
            str(manifest_file(tmp_path, artifact)),
            "--directory",
            str(tmp_path / "wheels"),
        ]
    )
    captured = capsys.readouterr()
    assert result == 1
    assert "secret-token" not in captured.out + captured.err
    assert set(json.loads(captured.err)) == {"filename", "status", "bytes"}


def test_lock_generation_is_deterministic_and_does_not_download(
    downloader, artifact, tmp_path, monkeypatch
):
    artifact.update(name="fixture", version="1.0")
    manifest = manifest_file(tmp_path, artifact)
    lock = tmp_path / "requirements.spark.txt"
    calls = transport(monkeypatch, downloader)
    args = ["--manifest", str(manifest), "--write-lock", str(lock)]
    assert downloader.main(args) == 0
    expected = lock.read_bytes()
    assert b"fixture==1.0" in expected
    assert artifact["sha256"].encode() in expected
    assert b"https://" not in expected
    assert downloader.main(args) == 0
    assert lock.read_bytes() == expected
    assert calls == []
    lock.write_bytes(b"existing user content")
    with pytest.raises(downloader.WheelhouseError, match="existing_lock_mismatch"):
        downloader.write_lock(manifest, lock)
    assert lock.read_bytes() == b"existing user content"


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"name": "wrong", "version": "1.0"},
        {"name": "fixture", "version": "2.0"},
        {"name": "fixture\nevil", "version": "1.0"},
        {"name": "fixture", "version": ">=1.0"},
    ],
)
def test_lock_rejects_missing_invalid_or_filename_mismatched_pins(
    downloader, artifact, tmp_path, changes
):
    artifact.update(changes)
    with pytest.raises(downloader.WheelhouseError, match="invalid_pin"):
        downloader.write_lock(manifest_file(tmp_path, artifact), tmp_path / "lock.txt")
    assert not (tmp_path / "lock.txt").exists()


def test_lock_rejects_duplicate_normalized_package_names(downloader, artifact, tmp_path):
    artifact.update(name="fixture", version="1.0")
    second = {**artifact, "filename": "fixture-1.0-cp313-none-any.whl"}
    second["url"] = "https://files.pythonhosted.org/packages/" + second["filename"]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"artifacts": [artifact, second]}))
    with pytest.raises(downloader.WheelhouseError, match="duplicate_package"):
        downloader.write_lock(path, tmp_path / "lock.txt")


def test_lock_is_sorted_independently_of_manifest_order(downloader, artifact, tmp_path):
    artifact.update(name="fixture", version="1.0")
    second = {**artifact, "name": "another", "filename": "another-1.0-py3-none-any.whl"}
    second["url"] = "https://files.pythonhosted.org/packages/" + second["filename"]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"artifacts": [artifact, second]}))
    downloader.write_lock(path, tmp_path / "first.txt")
    path.write_text(json.dumps({"artifacts": [second, artifact]}))
    downloader.write_lock(path, tmp_path / "second.txt")
    assert (tmp_path / "first.txt").read_bytes() == (tmp_path / "second.txt").read_bytes()


@pytest.mark.parametrize("direct_pins", [{"fixture": "2.0"}, {"missing": "1.0"}, ["fixture==1.0"]])
def test_lock_rejects_inconsistent_direct_pins(downloader, artifact, tmp_path, direct_pins):
    artifact.update(name="fixture", version="1.0")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"artifacts": [artifact], "direct_pins": direct_pins}))
    with pytest.raises(downloader.WheelhouseError, match="invalid_direct_pins"):
        downloader.write_lock(path, tmp_path / "lock.txt")


def test_existing_nonregular_target_is_rejected_without_download(
    downloader, artifact, tmp_path, monkeypatch
):
    calls = transport(monkeypatch, downloader)
    directory = tmp_path / "wheels"
    directory.mkdir()
    (directory / artifact["filename"]).mkdir()
    with pytest.raises(downloader.WheelhouseError, match="existing_artifact_mismatch"):
        downloader.prepare(manifest_file(tmp_path, artifact), directory)
    assert calls == []


def test_committed_lock_and_admission_bind_the_artifact_sources(downloader):
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "app/inference/spark-wheelhouse-manifest.json"
    artifacts = downloader.read_manifest(manifest_path, for_lock=True)
    assert (
        downloader.lock_bytes(artifacts)
        == (root / "app/inference/requirements.spark.txt").read_bytes()
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    direct = {}
    for line in (root / "app/inference/requirements.spark.in").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            name, version = line.split("==")
            direct[name] = version
    assert direct == manifest["direct_pins"]
    decision = json.loads((root / "dependency-admission.json").read_text())["decision"]
    for relative, digest in decision["artifact_bindings"].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest


def test_protocol_failure_is_sanitized_and_cleans_temp(
    downloader, artifact, tmp_path, monkeypatch, capsys
):
    def broken_response(request, *, timeout):
        raise http.client.BadStatusLine("upstream-private-value")

    monkeypatch.setattr(
        downloader, "build_opener", lambda handler: SimpleNamespace(open=broken_response)
    )
    directory = tmp_path / "wheels"
    assert (
        downloader.main(
            ["--manifest", str(manifest_file(tmp_path, artifact)), "--directory", str(directory)]
        )
        == 1
    )
    assert not list(directory.iterdir())
    output = capsys.readouterr()
    assert "upstream-private-value" not in output.out + output.err
    assert json.loads(output.err)["status"] == "download_failed"


@pytest.mark.parametrize("payload", [[], {"artifacts": []}, {"artifacts": [{}] * 513}])
def test_manifest_shape_and_artifact_count_are_bounded(downloader, tmp_path, payload):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload))
    with pytest.raises(downloader.WheelhouseError):
        downloader.prepare(manifest, tmp_path / "wheels")
    assert not (tmp_path / "wheels").exists()
