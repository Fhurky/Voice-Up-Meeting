"""Filesystem sandbox and atomic write primitives."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path


class SafetyError(ValueError):
    """An operation would escape or weaken the managed filesystem boundary."""


def resolved_root(path: str | Path, *, require_empty: bool = False) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise SafetyError("target root may not be a symbolic link")
    absolute = candidate.absolute()
    if absolute == Path(absolute.anchor):
        raise SafetyError("filesystem root is not a valid target")
    if candidate.exists() and not candidate.is_dir():
        raise SafetyError("target must be a directory")
    if require_empty and candidate.exists() and any(candidate.iterdir()):
        raise SafetyError("project_init requires an empty target directory")
    return absolute.resolve(strict=False)


def safe_relative(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute() or any(part in {"..", ""} for part in path.parts):
        raise SafetyError(f"unsafe relative path: {value}")
    return path


def safe_join(root: Path, relative: str | Path, *, reject_symlinks: bool = True) -> Path:
    rel = safe_relative(relative)
    root = root.resolve(strict=False)
    current = root
    for part in rel.parts:
        current = current / part
        if reject_symlinks and current.exists() and current.is_symlink():
            raise SafetyError(f"symbolic-link component rejected: {current}")
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SafetyError(f"path escapes target root: {relative}") from exc
    return resolved


def atomic_write(root: Path, relative: str | Path, content: bytes) -> None:
    destination = safe_join(root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(destination.stat().st_mode) if destination.exists() else 0o644
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        os.chmod(destination, mode)
    finally:
        temporary.unlink(missing_ok=True)


def publish_staged_tree(stage: Path, target: Path, *, fail_after_swap: bool = False) -> None:
    """Publish a validated tree atomically and restore an empty target on failure."""

    target = resolved_root(target, require_empty=True)
    stage = stage.resolve(strict=True)
    if stage.parent != target.parent:
        raise SafetyError("staging directory must be a sibling of target")

    original: Path | None = None
    if target.exists():
        original = target.with_name(f".{target.name}.kt-original-{os.getpid()}")
        if original.exists():
            raise SafetyError(f"publish recovery path already exists: {original}")
        os.replace(target, original)

    try:
        os.replace(stage, target)
        if fail_after_swap:
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


def make_stage(target: Path) -> Path:
    target = resolved_root(target, require_empty=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{target.name}.kt-stage-", dir=target.parent))
