#!/usr/bin/env python3
"""Prepare an immutable Community-1 package; verification never needs network or secrets.

This build-time tool installs no dependencies and does not change model settings.
The complete, verified staging directory is published only after all files pass.
Existing packages are verified in place and are never repaired or overwritten.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import runpy
import sys
import tempfile
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts/diarization-model-manifest.json"
REPOSITORY = "pyannote/speaker-diarization-community-1"
REVISION = "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee"
FILE_PATHS = frozenset(
    {
        "README.md",
        "config.yaml",
        "embedding/README.md",
        "plda/README.md",
        "embedding/pytorch_model.bin",
        "plda/plda.npz",
        "plda/xvec_transform.npz",
        "segmentation/pytorch_model.bin",
    }
)
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_ENV_BYTES = 64 * 1024
CHUNK_BYTES = 1024 * 1024
PUBLIC_MODEL = runpy.run_path(str(ROOT / "scripts/prepare-speaker-model.py"))
WHEELHOUSE = PUBLIC_MODEL["WHEELHOUSE"]
validate_model_url = PUBLIC_MODEL["validate_model_url"]
checked_path = WHEELHOUSE["checked_path"]


def load_manifest(path: Path = MANIFEST) -> dict:
    path = checked_path(path)
    if not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("invalid_manifest")
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "repository", "revision", "license", "files"}
        or type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or document["repository"] != REPOSITORY
        or document["revision"] != REVISION
        or document["license"] != "cc-by-4.0"
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


def load_token(root: Path, environ=None) -> str:
    environment = os.environ if environ is None else environ
    if "HF_TOKEN" in environment:
        token = environment["HF_TOKEN"].strip()
    else:
        path = checked_path(root / ".env")
        if not path.is_file() or path.stat().st_size > MAX_ENV_BYTES:
            raise ValueError("invalid_token_configuration")
        values = []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].lstrip()
            name, separator, value = line.partition("=")
            if not separator or name.strip() != "HF_TOKEN":
                continue
            value = value.strip()
            if value.startswith(("'", '"')):
                if len(value) < 2 or value[-1] != value[0]:
                    raise ValueError("invalid_token_configuration")
                value = value[1:-1]
            else:
                value = value.split(" #", 1)[0].rstrip()
            values.append(value)
        if len(values) != 1:
            raise ValueError("invalid_token_configuration")
        token = values[0]
    if re.fullmatch(r"hf_[A-Za-z0-9]{1,256}", token) is None:
        raise ValueError("invalid_token_configuration")
    return token


class ModelRedirects(HTTPRedirectHandler):
    """Allow official HTTPS targets; never forward credentials across origins."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_model_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        redirected.remove_header("Authorization")
        redirected.remove_header("Proxy-authorization")
        # Gated same-origin resolve-cache requests can still require the token.
        # It remains unredirected, so each subsequent hop rechecks its origin.
        if urlsplit(req.full_url).netloc == urlsplit(newurl).netloc == "huggingface.co":
            authorization = req.get_header("Authorization")
            if authorization:
                redirected.add_unredirected_header("Authorization", authorization)
        return redirected


def fetch_file(row: dict, target: Path, token: str, *, opener=None) -> None:
    target = checked_path(target)
    if WHEELHOUSE["verify_existing"](
        target, row["size_bytes"], row["sha256"], "existing_model_hash_mismatch"
    ):
        return
    WHEELHOUSE["directory_path"](target.parent)
    url = f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{row['path']}"
    validate_model_url(url)
    request = Request(url, headers={"User-Agent": "VoiceUp-model-preparation/1"})
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    opener = opener or build_opener(ModelRedirects())
    descriptor, temporary_name = tempfile.mkstemp(suffix=".partial", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, opener.open(request, timeout=60) as response:
            digest, size = hashlib.sha256(), 0
            while chunk := response.read(min(CHUNK_BYTES, row["size_bytes"] - size + 1)):
                size += len(chunk)
                if size > row["size_bytes"]:
                    raise ValueError("downloaded_model_size_mismatch")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if size != row["size_bytes"] or digest.hexdigest() != row["sha256"]:
            raise ValueError("downloaded_model_hash_mismatch")
        WHEELHOUSE["publish"](
            temporary, target, size, row["sha256"], "existing_model_hash_mismatch"
        )
    finally:
        temporary.unlink(missing_ok=True)


def verify_package(directory: Path, manifest: dict) -> None:
    directory = checked_path(directory)
    if not directory.is_dir():
        raise ValueError("missing_model_package")
    expected = {row["path"] for row in manifest["files"]}
    actual = set()
    for path in directory.rglob("*"):
        path = checked_path(path)
        if not path.is_dir():
            actual.add(path.relative_to(directory).as_posix())
    if actual != expected:
        raise ValueError("incomplete_model_package")
    for row in manifest["files"]:
        if not WHEELHOUSE["verify_existing"](
            directory / row["path"], row["size_bytes"], row["sha256"], "model_hash_mismatch"
        ):
            raise ValueError("incomplete_model_package")


def publish_directory(staged: Path, output: Path) -> None:
    """Publish without replacing even an empty directory created concurrently.

    Plain POSIX rename replaces empty destinations. Linux RENAME_NOREPLACE and
    Darwin RENAME_EXCL instead fail atomically; Windows rename already does so.
    Unsupported platforms/filesystems fail closed rather than fall back to rename.
    """
    staged, output = checked_path(staged), checked_path(output)
    if sys.platform == "win32":
        staged.rename(output)
        return
    if not (sys.platform.startswith("linux") or sys.platform == "darwin"):
        raise ValueError("atomic_publication_unavailable")
    library = ctypes.CDLL(None, use_errno=True)
    try:
        if sys.platform.startswith("linux"):
            rename = library.renameat2
            rename.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            arguments = (-100, os.fsencode(staged), -100, os.fsencode(output), 1)
        else:
            rename = library.renamex_np
            rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            arguments = (os.fsencode(staged), os.fsencode(output), 4)
    except AttributeError:
        raise ValueError("atomic_publication_unavailable") from None
    rename.restype = ctypes.c_int
    if rename(*arguments) != 0:
        code = ctypes.get_errno()
        raise OSError(code, "atomic_publication_failed")


def prepare(
    root: Path = ROOT,
    *,
    manifest_path: Path = MANIFEST,
    verify_only: bool = False,
    opener=None,
) -> dict:
    manifest = load_manifest(manifest_path)
    output = checked_path(root / "models/diarization-community-1" / REVISION)
    status = "verified" if verify_only else "reused"
    if verify_only or output.exists():
        verify_package(output, manifest)
    else:
        token = load_token(root)
        parent = WHEELHOUSE["directory_path"](output.parent)
        opener = opener or build_opener(ModelRedirects())
        with tempfile.TemporaryDirectory(prefix=".community-", dir=parent) as temporary:
            staged = Path(temporary) / "package"
            for row in manifest["files"]:
                fetch_file(row, staged / row["path"], token, opener=opener)
            verify_package(staged, manifest)
            checked_path(output)
            if output.exists():
                # A concurrent preparer may already have published identical bytes.
                verify_package(output, manifest)
            else:
                try:
                    publish_directory(staged, output)
                except FileExistsError:
                    verify_package(output, manifest)
                else:
                    status = "downloaded"
        verify_package(output, manifest)
    result = {
        "status": status,
        "repository": REPOSITORY,
        "revision": REVISION,
        "files": len(manifest["files"]),
        "bytes": sum(row["size_bytes"] for row in manifest["files"]),
    }
    print(json.dumps(result))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify offline; never read a token")
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="Project root containing models/.env"
    )
    args = parser.parse_args(argv)
    try:
        prepare(args.root, verify_only=args.verify)
    except (ValueError, OSError, HTTPException):
        # HTTP exceptions may embed authorization or signed URLs; never render them.
        print(
            "Model preparation failed: verify setup access, connectivity, space and pinned files; "
            "existing files were preserved",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
