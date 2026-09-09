"""Deterministic, content-addressed scaffold bundle construction."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import stat
import tarfile
import tempfile
from pathlib import Path
from typing import Literal

from kt_scaffold import __version__
from kt_scaffold.models import (
    Answers,
    ProjectMetadata,
    ScaffoldArchive,
    ScaffoldBundleDescriptor,
    ScaffoldEntry,
    ScaffoldPatchSet,
)
from kt_scaffold.project import render_project

MAX_ENTRIES = 2048
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TREE_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def answers_digest(answers: Answers) -> str:
    """Bind a bundle to the complete normalized answer object."""
    return _sha256(_canonical_json(answers.model_dump(mode="json")))


def collect_entries(root: Path) -> list[ScaffoldEntry]:
    """Describe a rendered tree using normalized paths, modes and file digests."""
    entries: list[ScaffoldEntry] = []
    total_bytes = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if len(relative.encode("utf-8")) > 240:
            raise ValueError(f"scaffold entry path exceeds 240 UTF-8 bytes: {relative}")
        if path.is_symlink():
            raise ValueError(f"scaffold bundle cannot contain symbolic links: {relative}")
        mode = stat.S_IMODE(path.stat().st_mode)
        normalized_mode: Literal["0644", "0755"] = "0755" if mode & 0o111 else "0644"
        if path.is_dir():
            entries.append(
                ScaffoldEntry(
                    path=relative,
                    kind="directory",
                    mode="0755",
                    bytes=0,
                )
            )
            continue
        if not path.is_file():
            raise ValueError(f"unsupported scaffold entry type: {relative}")
        content = path.read_bytes()
        if len(content) > MAX_FILE_BYTES:
            raise ValueError(f"scaffold file exceeds {MAX_FILE_BYTES} bytes: {relative}")
        total_bytes += len(content)
        if total_bytes > MAX_TREE_BYTES:
            raise ValueError(f"scaffold tree exceeds {MAX_TREE_BYTES} bytes")
        entries.append(
            ScaffoldEntry(
                path=relative,
                kind="file",
                mode=normalized_mode,
                bytes=len(content),
                sha256=_sha256(content),
            )
        )
    if not entries:
        raise ValueError("scaffold bundle cannot be empty")
    if len(entries) > MAX_ENTRIES:
        raise ValueError(f"scaffold bundle exceeds {MAX_ENTRIES} entries")
    return entries


def tree_digest(entries: list[ScaffoldEntry]) -> str:
    """Return the canonical digest of the complete path/mode/content inventory."""
    payload = [entry.model_dump(mode="json", exclude_none=True) for entry in entries]
    return _sha256(_canonical_json(payload))


def observed_tree_digest(root: Path) -> str:
    """Calculate a tree digest with the same rules used during bundle creation."""
    return tree_digest(collect_entries(root))


def _descriptor_identity_payload(descriptor: ScaffoldBundleDescriptor) -> dict[str, object]:
    return {
        "generator_version": descriptor.generator_version,
        "answers_digest": descriptor.answers_digest,
        "tree_digest": descriptor.tree_digest,
        "archive": descriptor.archive.model_dump(mode="json"),
        "patch_set": descriptor.patch_set.model_dump(mode="json"),
        "project_manifest": descriptor.project_manifest.model_dump(mode="json"),
    }


def validate_descriptor_integrity(descriptor: ScaffoldBundleDescriptor) -> None:
    """Reject descriptor fields that do not agree with their content-addressed identity."""
    observed_tree = tree_digest(descriptor.patch_set.entries)
    if observed_tree != descriptor.tree_digest:
        raise ValueError("scaffold descriptor tree digest does not match its patch set")
    observed_id = _sha256(_canonical_json(_descriptor_identity_payload(descriptor)))
    if observed_id != descriptor.bundle_id:
        raise ValueError("scaffold descriptor bundle id does not match its content")


def _archive_bytes(root: Path, entries: list[ScaffoldEntry]) -> bytes:
    output = io.BytesIO()
    with (
        gzip.GzipFile(
            fileobj=output,
            mode="wb",
            compresslevel=9,
            mtime=0,
            filename="",
        ) as zipped,
        tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive,
    ):
        for entry in entries:
            info = tarfile.TarInfo(entry.path)
            info.mode = int(entry.mode, 8)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            if entry.kind == "directory":
                info.type = tarfile.DIRTYPE
                info.size = 0
                archive.addfile(info)
                continue
            content = (root / entry.path).read_bytes()
            info.type = tarfile.REGTYPE
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    result = output.getvalue()
    if len(result) > MAX_ARCHIVE_BYTES:
        raise ValueError(f"scaffold archive exceeds {MAX_ARCHIVE_BYTES} bytes")
    return result


def create_scaffold_bundle(answers: Answers) -> tuple[ScaffoldBundleDescriptor, bytes]:
    """Render once and return a deterministic descriptor plus opaque archive bytes."""
    if answers.generator_version != __version__:
        raise ValueError("generator_version is owned by the installed kt-scaffold package")
    collisions = sorted(key for key in os.environ if key.startswith(str(answers.env_prefix)))
    if collisions:
        raise ValueError(
            f"environment prefix {answers.env_prefix} collides with current process keys: "
            + ", ".join(collisions)
        )
    with tempfile.TemporaryDirectory(prefix="kt-scaffold-bundle-") as temporary:
        root = Path(temporary) / "project"
        root.mkdir()
        render_project(root, answers)
        entries = collect_entries(root)
        archive_bytes = _archive_bytes(root, entries)
        manifest = ProjectMetadata.model_validate_json(
            (root / ".kt-scaffold/project-manifest.json").read_text(encoding="utf-8")
        )

    patch_set = ScaffoldPatchSet(
        entry_count=len(entries),
        file_count=sum(entry.kind == "file" for entry in entries),
        uncompressed_bytes=sum(entry.bytes for entry in entries if entry.kind == "file"),
        entries=entries,
    )
    archive = ScaffoldArchive(sha256=_sha256(archive_bytes), bytes=len(archive_bytes))
    digest = tree_digest(entries)
    descriptor_payload: dict[str, object] = {
        "generator_version": __version__,
        "answers_digest": answers_digest(answers),
        "tree_digest": digest,
        "archive": archive.model_dump(mode="json"),
        "patch_set": patch_set.model_dump(mode="json"),
        "project_manifest": manifest.model_dump(mode="json"),
    }
    bundle_id = _sha256(_canonical_json(descriptor_payload))
    descriptor = ScaffoldBundleDescriptor(
        bundle_id=bundle_id,
        generator_version=__version__,
        answers_digest=answers_digest(answers),
        tree_digest=digest,
        archive=archive,
        patch_set=patch_set,
        project_manifest=manifest,
    )
    validate_descriptor_integrity(descriptor)
    return descriptor, archive_bytes
