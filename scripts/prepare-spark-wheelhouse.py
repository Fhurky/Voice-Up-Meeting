#!/usr/bin/env python3
"""Download explicit Spark artifacts or deterministically generate their offline hash lock.

This standard-library helper downloads only: it never installs packages, admits a
dependency, or changes the existing x86 wheelhouse. The manifest is the source of
the reviewed artifact coordinates. Runtime compatibility is a separate check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from http.client import HTTPException
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_ARTIFACTS = 512
MAX_ARTIFACT_BYTES = 16 * 1024**3
CHUNK_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 60
ALLOWED_HOSTS = frozenset({"files.pythonhosted.org", "download.pytorch.org"})
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,249}\.whl\Z")
PACKAGE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
VERSION = re.compile(
    r"[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?(?:\.post[0-9]+)?"
    r"(?:\.dev[0-9]+)?(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?\Z",
    re.IGNORECASE,
)


class WheelhouseError(ValueError):
    """A safe error code and optional validated basename, never a source URL."""

    def __init__(self, code: str, filename: str | None = None):
        super().__init__(code)
        self.code = code
        self.filename = filename


def validate_filename(value: object) -> str:
    if not isinstance(value, str) or not FILENAME.fullmatch(value):
        raise WheelhouseError("invalid_filename")
    stem = value.split(".", 1)[0].upper()
    if stem in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?:COM|LPT)[1-9]", stem):
        raise WheelhouseError("invalid_filename")
    return value


def validate_url(value: object, filename: str) -> str:
    try:
        if not isinstance(value, str) or any(ord(char) <= 32 for char in value):
            raise ValueError
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or parsed.query
            or parsed.fragment
            or unquote(parsed.path.rsplit("/", 1)[-1]) != filename
        ):
            raise ValueError
    except ValueError:
        raise WheelhouseError("invalid_url", filename) from None
    return value


class OfficialRedirects(HTTPRedirectHandler):
    """Check every redirect before urllib can make the redirected request."""

    def __init__(self, filename: str):
        self.filename = filename

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.filename)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def checked_path(path: Path) -> Path:
    absolute = Path(os.path.abspath(path.expanduser()))
    for part in [*reversed(absolute.parents), absolute]:
        is_junction = getattr(part, "is_junction", lambda: False)
        if part.is_symlink() or is_junction():
            raise WheelhouseError("unsafe_path")
    return absolute


def read_manifest(path: Path, *, for_lock: bool = False) -> list[dict]:
    path = checked_path(path)
    if not path.is_file():
        raise WheelhouseError("invalid_manifest")
    with path.open("rb") as source:
        raw = source.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise WheelhouseError("manifest_too_large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise WheelhouseError("invalid_manifest") from None
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= MAX_ARTIFACTS:
        raise WheelhouseError("invalid_artifact_count")
    seen = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise WheelhouseError("invalid_artifact")
        filename = validate_filename(artifact.get("filename"))
        if filename.casefold() in seen:
            raise WheelhouseError("duplicate_filename", filename)
        seen.add(filename.casefold())
        validate_url(artifact.get("url"), filename)
        digest, size = artifact.get("sha256"), artifact.get("size_bytes")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise WheelhouseError("invalid_sha256", filename)
        if type(size) is not int or not 1 <= size <= MAX_ARTIFACT_BYTES:
            raise WheelhouseError("invalid_size", filename)
    if for_lock and "direct_pins" in payload:
        direct = payload["direct_pins"]
        if not isinstance(direct, dict) or not direct:
            raise WheelhouseError("invalid_direct_pins")
        names = {
            re.sub(r"[-_.]+", "-", item.get("name", "")).lower(): item.get("version")
            for item in artifacts
            if isinstance(item.get("name"), str)
        }
        seen_direct = set()
        for name, version in direct.items():
            if not isinstance(name, str) or not PACKAGE.fullmatch(name):
                raise WheelhouseError("invalid_direct_pins")
            canonical = re.sub(r"[-_.]+", "-", name).lower()
            if (
                not isinstance(version, str)
                or not VERSION.fullmatch(version)
                or names.get(canonical) != version
                or canonical in seen_direct
            ):
                raise WheelhouseError("invalid_direct_pins")
            seen_direct.add(canonical)
    return artifacts


def directory_path(path: Path) -> Path:
    directory = checked_path(path)
    directory.mkdir(parents=True, exist_ok=True)
    directory = checked_path(directory)
    if not directory.is_dir():
        raise WheelhouseError("unsafe_path")
    return directory


def verify_existing(path: Path, size: int, digest: str, code: str) -> bool:
    path = checked_path(path)
    if not path.exists():
        return False
    if not stat.S_ISREG(path.lstat().st_mode):
        raise WheelhouseError(code, path.name)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != size:
            raise WheelhouseError(code, path.name)
        result = hashlib.sha256()
        total = 0
        while chunk := source.read(CHUNK_BYTES):
            total += len(chunk)
            if total > size:
                raise WheelhouseError(code, path.name)
            result.update(chunk)
    if total != size or result.hexdigest() != digest:
        raise WheelhouseError(code, path.name)
    return True


def publish(temporary: Path, target: Path, size: int, digest: str, code: str) -> bool:
    checked_path(temporary)
    checked_path(target)
    if temporary.parent.resolve() != target.parent.resolve():
        raise WheelhouseError("unsafe_path")
    try:
        # Same-directory hard-link publication is atomic and cannot overwrite a
        # concurrent writer. NTFS and the Spark filesystem support this operation.
        os.link(temporary, target, follow_symlinks=False)
    except FileExistsError:
        verify_existing(target, size, digest, code)
        return False
    return True


def report(filename: str, status: str, size: int, *, error: bool = False) -> None:
    print(
        json.dumps({"filename": filename, "status": status, "bytes": size}),
        file=sys.stderr if error else sys.stdout,
        flush=True,
    )


def download_artifact(artifact: dict, directory: Path) -> None:
    filename, size, digest = (artifact["filename"], artifact["size_bytes"], artifact["sha256"])
    directory = checked_path(directory)
    target = checked_path(directory / filename)
    if target.parent != directory:
        raise WheelhouseError("unsafe_path", filename)
    if verify_existing(target, size, digest, "existing_artifact_mismatch"):
        report(filename, "reused", size)
        return
    descriptor, temporary_name = tempfile.mkstemp(prefix=".wheel-", suffix=".part", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            opener = build_opener(OfficialRedirects(filename))
            request = Request(artifact["url"], headers={"Accept-Encoding": "identity"})
            with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise WheelhouseError("unexpected_http_status", filename)
                result = hashlib.sha256()
                total = 0
                while chunk := response.read(min(CHUNK_BYTES, size - total + 1)):
                    total += len(chunk)
                    if total > size:
                        raise WheelhouseError("size_mismatch", filename)
                    output.write(chunk)
                    result.update(chunk)
                if total != size:
                    raise WheelhouseError("size_mismatch", filename)
                if result.hexdigest() != digest:
                    raise WheelhouseError("sha256_mismatch", filename)
            output.flush()
            os.fsync(output.fileno())
        created = publish(temporary, target, size, digest, "existing_artifact_mismatch")
        report(filename, "downloaded" if created else "reused", size)
    except (OSError, TimeoutError, HTTPException) as exc:
        raise WheelhouseError("download_failed", filename) from exc
    finally:
        temporary.unlink(missing_ok=True)


def prepare(manifest: Path, directory: Path) -> None:
    artifacts = read_manifest(manifest)
    prepare_artifacts(artifacts, directory)


def prepare_artifacts(artifacts: list[dict], directory: Path) -> None:
    destination = directory_path(directory)
    for artifact in artifacts:
        download_artifact(artifact, destination)


def lock_bytes(artifacts: list[dict]) -> bytes:
    pins = {}
    for artifact in artifacts:
        name, version = artifact.get("name"), artifact.get("version")
        if (
            not isinstance(name, str)
            or not PACKAGE.fullmatch(name)
            or not isinstance(version, str)
            or not VERSION.fullmatch(version)
        ):
            raise WheelhouseError("invalid_pin", artifact["filename"])
        canonical = re.sub(r"[-_.]+", "-", name).lower()
        fields = artifact["filename"][:-4].split("-")
        if (
            len(fields) not in {5, 6}
            or re.sub(r"[-_.]+", "-", fields[0]).lower() != canonical
            or fields[1] != version
        ):
            raise WheelhouseError("invalid_pin", artifact["filename"])
        if canonical in pins:
            raise WheelhouseError("duplicate_package", artifact["filename"])
        pins[canonical] = (version, artifact["sha256"])
    lines = [
        "# Generated by scripts/prepare-spark-wheelhouse.py --write-lock.",
        "# Artifact URLs and platform identity are defined by the input manifest.",
        "# Install only from its verified wheelhouse with --no-index --require-hashes.",
    ]
    for name, (version, digest) in sorted(pins.items()):
        lines.append(f"{name}=={version} \\")
        lines.append(f"    --hash=sha256:{digest}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_lock(manifest: Path, target: Path) -> None:
    write_lock_artifacts(read_manifest(manifest, for_lock=True), target)


def write_lock_artifacts(artifacts: list[dict], target: Path) -> None:
    content = lock_bytes(artifacts)
    target = checked_path(target)
    digest = hashlib.sha256(content).hexdigest()
    if verify_existing(target, len(content), digest, "existing_lock_mismatch"):
        report(target.name, "reused", len(content))
        return
    parent = directory_path(target.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".lock-", suffix=".part", dir=parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        created = publish(temporary, target, len(content), digest, "existing_lock_mismatch")
        report(target.name, "written" if created else "reused", len(content))
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--write-lock", type=Path)
    args = parser.parse_args(argv)
    if args.directory is None and args.write_lock is None:
        parser.error("provide --directory or --write-lock")
    try:
        artifacts = read_manifest(args.manifest, for_lock=args.write_lock is not None)
        if args.write_lock is not None:
            write_lock_artifacts(artifacts, args.write_lock)
        if args.directory is not None:
            prepare_artifacts(artifacts, args.directory)
    except WheelhouseError as exc:
        report(exc.filename or "manifest", exc.code, 0, error=True)
        return 1
    except KeyboardInterrupt:
        report("manifest", "interrupted", 0, error=True)
        return 130
    except (OSError, TimeoutError):
        report("manifest", "io_failed", 0, error=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
