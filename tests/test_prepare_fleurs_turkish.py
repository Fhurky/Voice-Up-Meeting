"""Original FLEURS sources remain bounded, immutable and correctly attributed."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import struct
import tarfile
from pathlib import Path
from unittest.mock import create_autospec
from urllib.request import OpenerDirector

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare-fleurs-turkish.py"


def module():
    spec = importlib.util.spec_from_file_location("prepare_fleurs_turkish", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def wav(frames=16, *, rate=16000, sample=0.125):
    fmt = struct.pack("<HHIIHHH", 3, 1, rate, rate * 4, 4, 32, 0)
    data = struct.pack("<f", sample) * frames
    body = b"WAVEfmt " + struct.pack("<I", len(fmt)) + fmt
    body += b"fact" + struct.pack("<II", 4, frames)
    body += b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


def tsv(*rows):
    return "".join(
        f"{text_id}\t{filename}\tÖzgün metin.\tışık güzel\tunused\t{frames}\tMALE\n"
        for text_id, filename, frames in rows
    ).encode()


def archive(path, entries):
    with tarfile.open(path, "w:gz") as stream:
        for name, content, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(content) if kind == tarfile.REGTYPE else 0
            info.linkname = "outside.wav" if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ""
            stream.addfile(info, io.BytesIO(content) if info.size else None)


def test_source_pins_and_metadata_meaning():
    producer = module()
    assert producer.REVISION == "70bb2e84b976b7e960aa89f1c648e09c59f894dd"
    assert producer.ARCHIVE_BYTES == 464259241
    assert (
        producer.ARCHIVE_SHA256
        == "a7db7a681e4460d2922626bf2037ddc1a9146efba27d78bfc9543250eabc3a09"
    )
    rows = producer.parse_tsv(tsv((1, "123.wav", 16), (1, "456.wav", 32)), expected_count=2)
    assert rows[0] == {
        "text_id": "1",
        "filename": "123.wav",
        "reference": "ışık güzel",
        "num_samples": 16,
        "gender": "MALE",
    }
    assert rows[1]["text_id"] == rows[0]["text_id"]


@pytest.mark.parametrize(
    "payload",
    [
        b"bad",
        tsv((1, "../123.wav", 16)),
        tsv((1, "123.wav", 0)),
        tsv((1, "123.wav", 960001)),
        tsv((1, "123.wav", 16)).replace(b"MALE", b"UNKNOWN"),
        tsv((1, "123.wav", 16)).replace("ışık güzel".encode(), b""),
        tsv((1, "123.wav", 16), (2, "123.wav", 32)),
        b"\xff",
    ],
)
def test_bad_metadata_is_rejected(payload):
    with pytest.raises(ValueError):
        module().parse_tsv(payload, expected_count=1)


def test_float_audio_preserved_and_sample_count_verified():
    producer = module()
    assert producer.validate_wav(wav(), expected_frames=16) == 16
    with pytest.raises(ValueError, match="invalid_source_audio"):
        producer.validate_wav(wav(), expected_frames=17)


@pytest.mark.parametrize(
    "payload",
    [
        wav(rate=48000),
        wav(sample=float("nan")),
        wav(sample=float("inf")),
        wav() + b"junk",
        wav()[:-1],
        b"RIFF" + b"\0" * 80,
    ],
)
def test_malformed_audio_is_rejected(payload):
    with pytest.raises(ValueError, match="invalid_source_audio"):
        module().validate_wav(payload, expected_frames=16)


def test_extraction_matches_metadata_order_and_preserves_original_bytes(tmp_path):
    producer = module()
    rows = producer.parse_tsv(tsv((1, "123.wav", 16), (1, "456.wav", 32)), expected_count=2)
    source = tmp_path / "source.tar.gz"
    archive(
        source,
        [("test/456.wav", wav(32), tarfile.REGTYPE), ("test/123.wav", wav(), tarfile.REGTYPE)],
    )
    clips = producer.extract_clips(source, tmp_path / "destination", rows)
    assert [r["clip_id"] for r in clips] == ["fleurs_123", "fleurs_456"]
    assert (tmp_path / "destination" / clips[0]["audio"]).read_bytes() == wav()
    assert clips[0]["audio_sha256"] == hashlib.sha256(wav()).hexdigest()
    assert clips[0]["reference"] == "ışık güzel"
    assert producer.extract_clips(source, tmp_path / "destination", rows) == clips


@pytest.mark.parametrize(
    "entries",
    [
        [("../123.wav", wav(), tarfile.REGTYPE)],
        [("test/123.wav", b"", tarfile.SYMTYPE)],
        [("test/123.wav", b"", tarfile.LNKTYPE)],
        [("test/999.wav", wav(), tarfile.REGTYPE)],
        [("test/123.wav", wav(), tarfile.REGTYPE)] * 2,
        [],
    ],
)
def test_unsafe_missing_extra_duplicate_archive_members_rejected(tmp_path, entries):
    producer = module()
    source = tmp_path / "source.tar.gz"
    archive(source, entries)
    rows = producer.parse_tsv(tsv((1, "123.wav", 16)), expected_count=1)
    with pytest.raises(ValueError):
        producer.extract_clips(source, tmp_path / "destination", rows)


def test_existing_conflict_and_hardlink_are_preserved(tmp_path):
    producer = module()
    destination = tmp_path / "existing.txt"
    destination.write_bytes(b"owner content")
    with pytest.raises(ValueError, match="existing_output_conflict"):
        producer.write_once(destination, b"different")
    assert destination.read_bytes() == b"owner content"
    linked = tmp_path / "linked.txt"
    linked.hardlink_to(destination)
    with pytest.raises(ValueError, match="linked_source_path"):
        producer.write_once(linked, b"owner content")


def test_source_manifest_scope_and_digest_are_deterministic():
    producer = module()
    rows = producer.parse_tsv(tsv((1, "123.wav", 16)), expected_count=1)
    source = producer.source_manifest(rows)
    assert source["speaker_session_labels_available"] is False
    assert source["gender_counts"] == {"MALE": 1}
    assert source["unique_text_ids"] == 1
    assert source["license"] == "cc-by-4.0"
    assert producer.json_bytes(source) == producer.json_bytes(
        json.loads(producer.json_bytes(source))
    )


def test_missing_source_requires_explicit_download(tmp_path):
    with pytest.raises(ValueError, match="explicit_download_required"):
        module().prepare(tmp_path, download=False)


def connection(payload, url="https://huggingface.co/datasets/google/fleurs/source"):
    value = create_autospec(OpenerDirector, instance=True)
    response = io.BytesIO(payload)
    response.geturl = lambda: url
    value.open.return_value = response
    return value


def test_explicit_download_hashes_bytes_and_reuses_without_network(tmp_path):
    producer = module()
    payload = b"pinned official bytes"
    path = tmp_path / "source"
    client = connection(payload)
    producer.fetch_source(
        path,
        producer.BASE_URL + "/test.tsv",
        len(payload),
        hashlib.sha256(payload).hexdigest(),
        download=True,
        opener=client,
    )
    assert path.read_bytes() == payload
    request = client.open.call_args.args[0]
    assert producer.REVISION in request.full_url
    assert request.get_header("Authorization") is None
    client.open.reset_mock()
    producer.fetch_source(
        path,
        producer.BASE_URL + "/test.tsv",
        len(payload),
        hashlib.sha256(payload).hexdigest(),
        download=False,
        opener=client,
    )
    client.open.assert_not_called()


@pytest.mark.parametrize("payload", [b"sho", b"wr0ng", b"too-long"])
def test_corrupt_download_never_publishes(tmp_path, payload):
    producer = module()
    path = tmp_path / "source"
    with pytest.raises(ValueError, match="source_(size|hash)_mismatch"):
        producer.fetch_source(
            path,
            producer.BASE_URL + "/test.tsv",
            5,
            hashlib.sha256(b"right").hexdigest(),
            download=True,
            opener=connection(payload),
        )
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/file",
        "https://example.com/file",
        "https://user:secret@huggingface.co/file",
        "https://huggingface.co:444/file",
        "https://huggingface.co.attacker.invalid/file",
    ],
)
def test_download_rejects_untrusted_redirects(url):
    with pytest.raises(ValueError, match="untrusted_download_url"):
        module().validate_url(url)


def test_preparation_refuses_changed_full_corpus_scope(tmp_path, monkeypatch):
    producer = module()
    payload = tsv(*[(i % 329, f"{i}.wav", 16) for i in range(743)])
    root = tmp_path / "prepared"
    root.mkdir()
    (root / "test.tsv").write_bytes(payload)
    monkeypatch.setattr(producer, "TSV_BYTES", len(payload))
    monkeypatch.setattr(producer, "TSV_SHA256", hashlib.sha256(payload).hexdigest())
    with pytest.raises(ValueError, match="source_scope_changed"):
        producer.prepare(root, download=False)
    assert not (root / "manifest.json").exists()
