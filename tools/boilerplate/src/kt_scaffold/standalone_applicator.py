"""Standard-library-only verified applicator for URL-only MCP bootstrap."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import stat
import sys
import tarfile
import tempfile
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_TREE_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ENTRIES = 2048
ALLOWED_MODES = {"0644", "0755"}


class ApplicationError(ValueError):
    """The prepared payload or selected target violates the application contract."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ApplicationError("descriptor contains an unsafe entry path")
    if len(value.encode("utf-8")) > 240 or unicodedata.normalize("NFC", value) != value:
        raise ApplicationError("descriptor contains a non-canonical entry path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ApplicationError("descriptor contains an unsafe entry path")
    if path.as_posix() != value:
        raise ApplicationError("descriptor entry path is not normalized POSIX")
    return value


def _normalized_entries(descriptor: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    patch_set = descriptor.get("patch_set")
    if not isinstance(patch_set, dict) or patch_set.get("operation") != "create":
        raise ApplicationError("descriptor patch_set is invalid")
    raw_entries = patch_set.get("entries")
    if not isinstance(raw_entries, list) or not 1 <= len(raw_entries) <= MAX_ENTRIES:
        raise ApplicationError("descriptor entry count is invalid")
    entries: list[dict[str, Any]] = []
    paths: set[str] = set()
    folded_paths: set[str] = set()
    file_count = 0
    total_bytes = 0
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ApplicationError("descriptor entry must be an object")
        path = _safe_path(raw.get("path"))
        folded = path.casefold()
        if path in paths or folded in folded_paths:
            raise ApplicationError("descriptor contains duplicate or case-colliding paths")
        paths.add(path)
        folded_paths.add(folded)
        kind = raw.get("kind")
        mode = raw.get("mode")
        size = raw.get("bytes")
        digest = raw.get("sha256")
        if kind not in {"file", "directory"} or mode not in ALLOWED_MODES:
            raise ApplicationError(f"descriptor entry type or mode is invalid: {path}")
        if not isinstance(size, int) or isinstance(size, bool) or not 0 <= size <= MAX_FILE_BYTES:
            raise ApplicationError(f"descriptor entry size is invalid: {path}")
        normalized: dict[str, Any] = {
            "path": path,
            "kind": kind,
            "mode": mode,
            "bytes": size,
        }
        if kind == "directory":
            if size != 0 or digest is not None or mode != "0755":
                raise ApplicationError(f"descriptor directory metadata is invalid: {path}")
            normalized["sha256"] = None
        else:
            if not isinstance(digest, str) or len(digest) != 64:
                raise ApplicationError(f"descriptor file digest is invalid: {path}")
            if any(character not in "0123456789abcdef" for character in digest):
                raise ApplicationError(f"descriptor file digest is invalid: {path}")
            normalized["sha256"] = digest
            file_count += 1
            total_bytes += size
        entries.append(normalized)
    if total_bytes > MAX_TREE_BYTES:
        raise ApplicationError("descriptor tree exceeds the uncompressed size limit")
    if patch_set.get("entry_count") != len(entries):
        raise ApplicationError("descriptor entry_count does not match entries")
    if patch_set.get("file_count") != file_count:
        raise ApplicationError("descriptor file_count does not match entries")
    if patch_set.get("uncompressed_bytes") != total_bytes:
        raise ApplicationError("descriptor uncompressed_bytes does not match entries")
    return entries, file_count


def _validate_descriptor(descriptor: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    if descriptor.get("format") != 1:
        raise ApplicationError("unsupported scaffold descriptor format")
    entries, file_count = _normalized_entries(descriptor)
    tree_payload = [
        {key: value for key, value in entry.items() if value is not None} for entry in entries
    ]
    observed_tree = _sha256(_canonical_json(tree_payload))
    if observed_tree != descriptor.get("tree_digest"):
        raise ApplicationError("scaffold descriptor tree digest does not match its patch set")
    archive = descriptor.get("archive")
    if not isinstance(archive, dict):
        raise ApplicationError("scaffold descriptor archive metadata is missing")
    if archive.get("media_type") != "application/vnd.kt-scaffold.project+tar.gzip":
        raise ApplicationError("unsupported scaffold archive media type")
    archive_size = archive.get("bytes")
    archive_digest = archive.get("sha256")
    if (
        not isinstance(archive_size, int)
        or isinstance(archive_size, bool)
        or not 1 <= archive_size <= MAX_ARCHIVE_BYTES
    ):
        raise ApplicationError("scaffold descriptor archive size is invalid")
    if not isinstance(archive_digest, str) or len(archive_digest) != 64:
        raise ApplicationError("scaffold descriptor archive digest is invalid")
    patch_set = {
        "operation": "create",
        "entry_count": len(entries),
        "file_count": file_count,
        "uncompressed_bytes": sum(entry["bytes"] for entry in entries if entry["kind"] == "file"),
        "entries": entries,
    }
    identity = {
        "generator_version": descriptor.get("generator_version"),
        "answers_digest": descriptor.get("answers_digest"),
        "tree_digest": descriptor.get("tree_digest"),
        "archive": archive,
        "patch_set": patch_set,
        "project_manifest": descriptor.get("project_manifest"),
    }
    if _sha256(_canonical_json(identity)) != descriptor.get("bundle_id"):
        raise ApplicationError("scaffold descriptor bundle id does not match its content")
    return entries, file_count


def _collect_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = _safe_path(path.relative_to(root).as_posix())
        if path.is_symlink():
            raise ApplicationError(f"observed tree contains a symbolic link: {relative}")
        if path.is_dir():
            entries.append({"path": relative, "kind": "directory", "mode": "0755", "bytes": 0})
            continue
        if not path.is_file():
            raise ApplicationError(f"observed tree contains an unsupported entry: {relative}")
        content = path.read_bytes()
        total_bytes += len(content)
        if len(content) > MAX_FILE_BYTES or total_bytes > MAX_TREE_BYTES:
            raise ApplicationError("observed tree exceeds the size limit")
        mode = "0755" if stat.S_IMODE(path.stat().st_mode) & 0o111 else "0644"
        entries.append(
            {
                "path": relative,
                "kind": "file",
                "mode": mode,
                "bytes": len(content),
                "sha256": _sha256(content),
            }
        )
    if not 1 <= len(entries) <= MAX_ENTRIES:
        raise ApplicationError("observed tree entry count is invalid")
    return entries


def _tree_digest(root: Path) -> str:
    return _sha256(_canonical_json(_collect_entries(root)))


def _safe_join(root: Path, relative: str) -> Path:
    candidate = root.joinpath(*PurePosixPath(_safe_path(relative)).parts)
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ApplicationError(f"symbolic-link component rejected: {relative}")
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise ApplicationError(f"entry escapes target root: {relative}") from exc
    return candidate


def _target(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise ApplicationError("target root may not be a symbolic link")
    absolute = candidate.absolute()
    if absolute == Path(absolute.anchor) or absolute.resolve(strict=False) == Path.home().resolve():
        raise ApplicationError("filesystem root and user home are not valid scaffold targets")
    if candidate.exists() and not candidate.is_dir():
        raise ApplicationError("target must be a directory")
    return absolute.resolve(strict=False)


def _archive_content(path: str | Path, descriptor: dict[str, Any]) -> bytes:
    archive = Path(path)
    if archive.is_symlink() or not archive.is_file():
        raise ApplicationError("scaffold archive must be a regular non-symlink file")
    content = archive.read_bytes()
    metadata = descriptor["archive"]
    if len(content) != metadata["bytes"] or len(content) > MAX_ARCHIVE_BYTES:
        raise ApplicationError("scaffold archive size does not match its descriptor")
    if _sha256(content) != metadata["sha256"]:
        raise ApplicationError("scaffold archive digest does not match its descriptor")
    return content


def _write_file(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _extract(
    content: bytes,
    stage: Path,
    expected_entries: list[dict[str, Any]],
) -> None:
    expected = {entry["path"]: entry for entry in expected_entries}
    observed: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) > MAX_ENTRIES:
            raise ApplicationError("archive exceeds the entry-count limit")
        for member in members:
            name = _safe_path(member.name)
            if name in observed:
                raise ApplicationError(f"duplicate archive entry: {name}")
            observed.add(name)
            entry = expected.get(name)
            if entry is None:
                raise ApplicationError(f"archive contains an undeclared entry: {name}")
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise ApplicationError(f"archive contains an unsafe entry type: {name}")
            if member.mode != int(entry["mode"], 8):
                raise ApplicationError(f"archive mode differs from descriptor: {name}")
            destination = _safe_join(stage, name)
            if entry["kind"] == "directory":
                if not member.isdir():
                    raise ApplicationError(f"archive entry kind differs from descriptor: {name}")
                destination.mkdir(parents=True, exist_ok=True)
                destination.chmod(int(entry["mode"], 8))
                continue
            if not member.isfile() or member.size != entry["bytes"]:
                raise ApplicationError(f"archive file metadata differs from descriptor: {name}")
            source = archive.extractfile(member)
            if source is None:
                raise ApplicationError(f"archive file cannot be read: {name}")
            data = source.read(entry["bytes"] + 1)
            if len(data) != entry["bytes"] or _sha256(data) != entry["sha256"]:
                raise ApplicationError(f"archive file digest differs from descriptor: {name}")
            _write_file(destination, data, int(entry["mode"], 8))
    if observed != set(expected):
        raise ApplicationError("archive is missing declared entries")


def _publish(stage: Path, target: Path, *, inject_publish_failure: bool = False) -> None:
    if target.is_symlink() or (target.exists() and any(target.iterdir())):
        raise ApplicationError("target changed after applicator preflight")
    original: Path | None = None
    if target.exists():
        original = target.with_name(f".{target.name}.kt-original-{os.getpid()}")
        if original.exists():
            raise ApplicationError("publish recovery path already exists")
        os.replace(target, original)
    try:
        os.replace(stage, target)
        if inject_publish_failure:
            raise RuntimeError("injected publish failure")
        if original is not None:
            original.rmdir()
    except BaseException:
        if target.exists() and target != stage:
            failed = target.with_name(f".{target.name}.kt-failed-{os.getpid()}")
            os.replace(target, failed)
            if original is not None and original.exists():
                os.replace(original, target)
            shutil.rmtree(failed, ignore_errors=True)
        elif original is not None and original.exists():
            os.replace(original, target)
        raise


def apply_bundle(
    archive_path: str | Path,
    target_dir: str | Path,
    descriptor: dict[str, Any],
    *,
    expected_bundle_id: str,
    inject_publish_failure: bool = False,
) -> dict[str, Any]:
    """Validate and transactionally materialize one prepared scaffold bundle."""
    entries, file_count = _validate_descriptor(descriptor)
    if descriptor["bundle_id"] != expected_bundle_id:
        raise ApplicationError("descriptor does not match the expected MCP bundle id")
    target = _target(target_dir)
    if target.exists() and any(target.iterdir()):
        if _tree_digest(target) != descriptor["tree_digest"]:
            raise ApplicationError("target is non-empty and differs from the prepared bundle")
        status = "unchanged"
    else:
        content = _archive_content(archive_path, descriptor)
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.kt-stage-", dir=target.parent))
        try:
            _extract(content, stage, entries)
            observed = _tree_digest(stage)
            if observed != descriptor["tree_digest"]:
                raise ApplicationError("staged tree digest does not match its descriptor")
            _publish(stage, target, inject_publish_failure=inject_publish_failure)
        except BaseException:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)
            raise
        status = "created"
    return {
        "format": 1,
        "provenance": "local-applicator-observed",
        "bundle_id": descriptor["bundle_id"],
        "archive_sha256": descriptor["archive"]["sha256"],
        "expected_tree_digest": descriptor["tree_digest"],
        "observed_tree_digest": descriptor["tree_digest"],
        "status": status,
        "file_count": file_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kt-scaffold-apply")
    parser.add_argument("--archive", required=True)
    parser.add_argument("--descriptor", required=True)
    parser.add_argument("--expected-bundle-id", required=True)
    parser.add_argument("--target-dir", required=True)
    namespace = parser.parse_args(argv)
    try:
        descriptor = json.loads(Path(namespace.descriptor).read_text(encoding="utf-8"))
        if not isinstance(descriptor, dict):
            raise ApplicationError("descriptor must contain a JSON object")
        receipt = apply_bundle(
            namespace.archive,
            namespace.target_dir,
            descriptor,
            expected_bundle_id=namespace.expected_bundle_id,
        )
    except (ApplicationError, OSError, json.JSONDecodeError, tarfile.TarError) as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True) + "\n")
        return 2
    sys.stdout.write(json.dumps({"ok": True, "receipt": receipt}, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
