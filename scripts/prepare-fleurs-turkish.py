"""Prepare the complete, pinned FLEURS Turkish test split without audio conversion.

This read-speech ASR benchmark has no stable speaker/session labels. All 743
test rows are labelled MALE; sentence IDs must never become speaker IDs.
Network access is an explicit preparation operation, never model inference.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import struct
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"
BASE_URL = f"https://huggingface.co/datasets/google/fleurs/resolve/{REVISION}/data/tr_tr"
ARCHIVE_BYTES = 464259241
ARCHIVE_SHA256 = "a7db7a681e4460d2922626bf2037ddc1a9146efba27d78bfc9543250eabc3a09"
TSV_BYTES = 447909
TSV_SHA256 = "52adb452a258976a2428da88fe7ac4d9bce27d4c10f9358ba3acf48a9b59577a"
PROTOCOL = "voiceup-fleurs-tr-test-v1"
MAX_FRAMES = 16000 * 60
MAX_WAV_BYTES = MAX_FRAMES * 4 + 65536


def safe_path(path):
    path = Path(path).absolute()
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            raise ValueError("linked_source_path")
    if path.exists() and path.is_file() and path.stat().st_nlink != 1:
        raise ValueError("linked_source_path")
    return path


def digest(path):
    with safe_path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def publish(temporary, target):
    target = safe_path(target)
    try:
        os.link(temporary, target)
    except FileExistsError:
        if (
            not target.is_file()
            or target.stat().st_size != temporary.stat().st_size
            or digest(target) != digest(temporary)
        ):
            raise ValueError("existing_output_conflict") from None


def write_once(target, payload):
    target = safe_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".fleurs-", suffix=".partial", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        publish(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def validate_url(url):
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not (host == "huggingface.co" or host.endswith(".hf.co"))
    ):
        raise ValueError("untrusted_download_url")


class SourceRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def verify_source(path, size, sha256):
    path = safe_path(path)
    if not path.is_file() or path.stat().st_size != size:
        raise ValueError("source_size_mismatch")
    if digest(path) != sha256:
        raise ValueError("source_hash_mismatch")


def fetch_source(path, url, size, sha256, *, download, opener=None):
    path = safe_path(path)
    if path.exists():
        verify_source(path, size, sha256)
        return
    if not download:
        raise ValueError("explicit_download_required")
    validate_url(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".fleurs-", suffix=".partial", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            request = Request(url, headers={"User-Agent": "VoiceUp-dataset-preparation/1"})
            with (opener or build_opener(SourceRedirects())).open(request, timeout=60) as response:
                validate_url(response.geturl())
                total = 0
                while chunk := response.read(min(1024 * 1024, size - total + 1)):
                    total += len(chunk)
                    if total > size:
                        raise ValueError("source_size_mismatch")
                    stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        verify_source(temporary, size, sha256)
        publish(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_tsv(payload, *, expected_count=743):
    if len(payload) > TSV_BYTES:
        raise ValueError("source_metadata_limit")
    try:
        text = payload.decode("utf-8")
        rows = list(csv.reader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE))
    except (UnicodeError, csv.Error) as error:
        raise ValueError("invalid_source_metadata") from error
    if len(rows) != expected_count:
        raise ValueError("source_clip_count_mismatch")
    result, names = [], set()
    for fields in rows:
        if len(fields) != 7:
            raise ValueError("invalid_source_metadata")
        identity, filename, raw, reference, _unused, samples, gender = fields
        if (
            not re.fullmatch(r"[0-9]{1,10}", identity)
            or not re.fullmatch(r"[0-9]{1,24}\.wav", filename)
            or filename in names
            or not re.fullmatch(r"[0-9]{1,7}", samples)
            or not 0 < int(samples) <= MAX_FRAMES
            or not raw.strip()
            or not reference.strip()
            or len(raw) > 10000
            or len(reference) > 10000
            or any(ord(c) < 32 for c in reference)
            or gender != "MALE"
        ):
            raise ValueError("invalid_source_metadata")
        names.add(filename)
        result.append(
            {
                "text_id": identity,
                "filename": filename,
                "reference": reference.strip(),
                "num_samples": int(samples),
                "gender": gender,
            }
        )
    return result


def validate_wav(payload, *, expected_frames):
    def reject():
        raise ValueError("invalid_source_audio")

    if (
        not 0 < expected_frames <= MAX_FRAMES
        or not 44 <= len(payload) <= MAX_WAV_BYTES
        or payload[:4] != b"RIFF"
        or payload[8:12] != b"WAVE"
        or struct.unpack_from("<I", payload, 4)[0] != len(payload) - 8
    ):
        reject()
    offset, chunks = 12, {}
    while offset + 8 <= len(payload):
        name, size = struct.unpack_from("<4sI", payload, offset)
        start, end = offset + 8, offset + 8 + size
        if (
            name in chunks
            or end + size % 2 > len(payload)
            or name not in {b"fmt ", b"fact", b"data"}
        ):
            reject()
        chunks[name] = payload[start:end]
        offset = end + size % 2
    if offset != len(payload) or set(chunks) != {b"fmt ", b"fact", b"data"}:
        reject()
    if len(chunks[b"fmt "]) != 18 or struct.unpack("<HHIIHHH", chunks[b"fmt "]) != (
        3,
        1,
        16000,
        64000,
        4,
        32,
        0,
    ):
        reject()
    if (
        len(chunks[b"fact"]) != 4
        or struct.unpack("<I", chunks[b"fact"])[0] != expected_frames
        or len(chunks[b"data"]) != expected_frames * 4
        or any(not math.isfinite(v[0]) for v in struct.iter_unpack("<f", chunks[b"data"]))
    ):
        reject()
    return expected_frames


def extract_clips(archive_path, root, rows):
    root = safe_path(root)
    expected = {row["filename"]: row for row in rows}
    found, hashes = {}, set()
    members, directory_seen = 0, False
    with tarfile.open(safe_path(archive_path), "r:gz") as archive:
        for member in archive:
            members += 1
            if members > len(rows) + 1:
                raise ValueError("source_member_limit")
            if member.isdir() and member.name.rstrip("/") == "test":
                if directory_seen:
                    raise ValueError("unexpected_archive_member")
                directory_seen = True
                continue
            match = re.fullmatch(r"test/([0-9]{1,24}\.wav)", member.name)
            if not match or not member.isfile() or not 44 <= member.size <= MAX_WAV_BYTES:
                raise ValueError("unsafe_archive_member")
            filename = match.group(1)
            if filename not in expected or filename in found:
                raise ValueError("unexpected_archive_member")
            row = expected[filename]
            payload = archive.extractfile(member).read(member.size + 1)
            if len(payload) != member.size:
                raise ValueError("source_size_mismatch")
            validate_wav(payload, expected_frames=row["num_samples"])
            audio_hash = hashlib.sha256(payload).hexdigest()
            if audio_hash in hashes:
                raise ValueError("duplicate_source_audio")
            hashes.add(audio_hash)
            clip_id = "fleurs_" + filename.removesuffix(".wav")
            audio = f"clips/{clip_id}.wav"
            reference_file = f"clips/{clip_id}.txt"
            reference_bytes = (row["reference"] + "\n").encode()
            write_once(root / audio, payload)
            write_once(root / reference_file, reference_bytes)
            found[filename] = {
                "clip_id": clip_id,
                "audio": audio,
                "reference_file": reference_file,
                "audio_sha256": audio_hash,
                "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
                "reference": row["reference"],
            }
    if set(found) != set(expected):
        raise ValueError("missing_source_audio")
    return [found[row["filename"]] for row in rows]


def source_manifest(rows):
    return {
        "schema_version": 1,
        "repository": "google/fleurs",
        "revision": REVISION,
        "language": "tr",
        "split": "test",
        "license": "cc-by-4.0",
        "reference_column": "transcription",
        "reference_quality": "source-human-transcribed",
        "audio_policy": "original-mono-16000hz-float32-wav-unchanged",
        "speaker_session_labels_available": False,
        "scope": "read-speech-asr-only-no-speaker-identity-claim",
        "gender_counts": {"MALE": len(rows)},
        "unique_text_ids": len({row["text_id"] for row in rows}),
        "clips": len(rows),
        "samples": sum(row["num_samples"] for row in rows),
        "sample_rate": 16000,
        "files": [
            {
                "url": BASE_URL + "/audio/test.tar.gz",
                "bytes": ARCHIVE_BYTES,
                "sha256": ARCHIVE_SHA256,
                "hash_authority": "publisher-lfs-sha256",
            },
            {
                "url": BASE_URL + "/test.tsv",
                "bytes": TSV_BYTES,
                "sha256": TSV_SHA256,
                "hash_authority": "observed-pinned-official-https-bytes",
            },
        ],
    }


def prepare(root, *, download):
    root = safe_path(root)
    archive_path, tsv_path = root / "test.tar.gz", root / "test.tsv"
    fetch_source(tsv_path, BASE_URL + "/test.tsv", TSV_BYTES, TSV_SHA256, download=download)
    rows = parse_tsv(tsv_path.read_bytes())
    if (
        len({row["text_id"] for row in rows}) != 329
        or sum(row["num_samples"] for row in rows) != 150083520
    ):
        raise ValueError("source_scope_changed")
    fetch_source(
        archive_path,
        BASE_URL + "/audio/test.tar.gz",
        ARCHIVE_BYTES,
        ARCHIVE_SHA256,
        download=download,
    )
    source_payload = json_bytes(source_manifest(rows))
    clips = extract_clips(archive_path, root, rows)
    manifest = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "language": "tr",
        "role": "frozen-test",
        "dataset": "FLEURS-TR",
        "dataset_revision": REVISION,
        "source_sha256": hashlib.sha256(source_payload).hexdigest(),
        "reference_quality": "source-human-transcribed",
        "speaker_session_labels_available": False,
        "selection": "official-test-split-source-order",
        "exclusion_manifest_sha256": None,
        "clips": clips,
    }
    write_once(root / "source-manifest.json", source_payload)
    write_once(root / "manifest.json", json_bytes(manifest))
    print(
        json.dumps(
            {
                "status": "prepared",
                "clips": len(clips),
                "seconds": 9380.22,
                "manifest_sha256": digest(root / "manifest.json"),
                "source_sha256": manifest["source_sha256"],
            }
        ),
        flush=True,
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/turkish/fleurs-tr-test-v1"))
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    prepare(args.root, download=args.download)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, tarfile.TarError):
        raise SystemExit(
            "FLEURS preparation incomplete; original sources and existing outputs preserved."
        ) from None
