#!/usr/bin/env python3
"""Prepare the pinned public Whisper package without reading any credentials."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts/asr-model-manifest.json"
REPOSITORY = "Systran/faster-whisper-large-v3"
REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
FILE_PATHS = frozenset(
    {
        "README.md",
        "config.json",
        "model.bin",
        "preprocessor_config.json",
        "tokenizer.json",
        "vocabulary.json",
    }
)
MAX_FILE_BYTES = 4 * 1024**3
RANGE_BYTES = 16 * 1024**2
COMMON = runpy.run_path(str(ROOT / "scripts/prepare-diarization-model.py"))
WHEELHOUSE = COMMON["WHEELHOUSE"]
checked_path = COMMON["checked_path"]
verify_package = COMMON["verify_package"]
publish_directory = COMMON["publish_directory"]


def load_manifest(path: Path = MANIFEST) -> dict:
    path = checked_path(path)
    if not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("invalid_manifest")
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "repository", "revision", "license", "files"}
        or type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or document["repository"] != REPOSITORY
        or document["revision"] != REVISION
        or document["license"] != "mit"
        or not isinstance(document["files"], list)
        or len(document["files"]) != len(FILE_PATHS)
    ):
        raise ValueError("invalid_manifest")
    seen = set()
    for row in document["files"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"path", "size_bytes", "sha256"}
            or not isinstance(row["path"], str)
            or row["path"] not in FILE_PATHS
            or row["path"] in seen
            or type(row["size_bytes"]) is not int
            or not 0 < row["size_bytes"] <= MAX_FILE_BYTES
            or not isinstance(row["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
        ):
            raise ValueError("invalid_manifest")
        seen.add(row["path"])
    return document


def fetch_file(row: dict, target: Path, *, opener=None) -> None:
    target = checked_path(target)
    WHEELHOUSE["directory_path"](target.parent)
    url = f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{row['path']}"
    COMMON["validate_model_url"](url)
    descriptor, name = tempfile.mkstemp(suffix=".partial", dir=target.parent)
    temporary = Path(name)

    def read_range(offset):
        end = min(row["size_bytes"], offset + RANGE_BYTES) - 1
        headers = {"User-Agent": "VoiceUp-model-preparation/1"}
        ranged = row["size_bytes"] > RANGE_BYTES
        if ranged:
            headers["Range"] = f"bytes={offset}-{end}"
        connection = opener or build_opener(COMMON["ModelRedirects"]())
        with connection.open(Request(url, headers=headers), timeout=60) as response:
            if ranged and (
                response.status != 206
                or response.headers.get("Content-Range")
                != f"bytes {offset}-{end}/{row['size_bytes']}"
            ):
                raise ValueError("downloaded_model_range_mismatch")
            received = bytearray()
            expected = end - offset + 1
            while chunk := response.read(min(1024 * 1024, expected - len(received) + 1)):
                received.extend(chunk)
                if len(received) > expected:
                    raise ValueError("downloaded_model_size_mismatch")
            if len(received) != expected:
                raise ValueError("downloaded_model_size_mismatch")
        return offset, received

    try:
        with os.fdopen(descriptor, "wb") as stream:
            # Four bounded 16 MiB range tasks run per batch. Each range writes
            # only its verified offset; the complete file is hashed below.
            with ThreadPoolExecutor(max_workers=4) as executor:
                for first in range(0, row["size_bytes"], 4 * RANGE_BYTES):
                    offsets = range(
                        first, min(row["size_bytes"], first + 4 * RANGE_BYTES), RANGE_BYTES
                    )
                    futures = [executor.submit(read_range, offset) for offset in offsets]
                    for future in as_completed(futures):
                        offset, received = future.result()
                        stream.seek(offset)
                        stream.write(received)
                    stream.flush()
            stream.flush()
            os.fsync(stream.fileno())
        size = temporary.stat().st_size
        with temporary.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if size != row["size_bytes"] or digest != row["sha256"]:
            raise ValueError("downloaded_model_hash_mismatch")
        WHEELHOUSE["publish"](
            temporary, target, size, row["sha256"], "existing_model_hash_mismatch"
        )
    finally:
        temporary.unlink(missing_ok=True)


def prepare(root: Path = ROOT, *, manifest_path: Path = MANIFEST, verify_only=False, opener=None):
    manifest = load_manifest(manifest_path)
    output = checked_path(root / "models/asr-large-v3" / REVISION)
    status = "verified" if verify_only else "reused"
    if verify_only or output.exists():
        verify_package(output, manifest)
    else:
        parent = WHEELHOUSE["directory_path"](output.parent)
        with tempfile.TemporaryDirectory(prefix=".asr-", dir=parent) as temporary:
            staged = Path(temporary) / "package"
            for row in manifest["files"]:
                fetch_file(row, staged / row["path"], opener=opener)
            verify_package(staged, manifest)
            try:
                publish_directory(staged, output)
            except OSError:
                if not output.exists():
                    raise
                verify_package(output, manifest)
            verify_package(output, manifest)
        status = "prepared"
    return {
        "status": status,
        "directory": str(output),
        "files": len(manifest["files"]),
        "revision": REVISION,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--verify", action="store_true")
    arguments = parser.parse_args()
    try:
        result = prepare(arguments.root, verify_only=arguments.verify)
    except (Exception, KeyboardInterrupt):
        print(
            json.dumps({"status": "failed", "code": "asr_model_preparation_failed"}),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
