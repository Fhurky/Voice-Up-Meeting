"""Conflict-aware multi-file changes with rollback for generator operations."""

from __future__ import annotations

import difflib
import hashlib
from pathlib import Path

from kt_scaffold.models import Change
from kt_scaffold.safety import atomic_write, safe_join


def preview(current: bytes, proposed: bytes, path: str) -> str:
    before = current.decode("utf-8", errors="replace").splitlines(keepends=True)
    after = proposed.decode("utf-8", errors="replace").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(before, after, fromfile=f"a/{path}", tofile=f"b/{path}", n=3)
    )[:8000]


def apply_file_set(
    root: Path,
    proposed: dict[str, bytes],
    *,
    allow_updates: set[str] | None = None,
    owned_updates: dict[str, str] | None = None,
    owned_deletes: dict[str, str] | None = None,
    inject_failure_after: int | None = None,
) -> list[Change]:
    """Preflight owned writes/deletes, then apply all or restore the original bytes."""

    allow_updates = allow_updates or set()
    owned_updates = owned_updates or {}
    owned_deletes = owned_deletes or {}
    ambiguous_updates = sorted(set(allow_updates) & set(owned_updates))
    if ambiguous_updates:
        raise ValueError(
            "paths cannot use both unpinned and digest-owned updates: "
            f"{', '.join(ambiguous_updates)}"
        )
    overlap = sorted(set(proposed) & set(owned_deletes))
    if overlap:
        raise ValueError(f"paths cannot be both written and deleted: {', '.join(overlap)}")
    changes: list[Change] = []
    originals: dict[str, bytes | None] = {}
    conflicts: list[Change] = []
    for relative, content in sorted(proposed.items()):
        destination = safe_join(root, relative)
        if not destination.exists():
            originals[relative] = None
            changes.append(Change(path=relative, action="create"))
            continue
        current = destination.read_bytes()
        originals[relative] = current
        if current == content:
            changes.append(Change(path=relative, action="skip"))
        elif relative in owned_updates:
            current_digest = hashlib.sha256(current).hexdigest()
            if current_digest != owned_updates[relative]:
                conflicts.append(
                    Change(
                        path=relative,
                        action="conflict",
                        diff_preview="owned generated file was edited; refusing update",
                    )
                )
            else:
                changes.append(
                    Change(
                        path=relative,
                        action="update",
                        diff_preview=preview(current, content, relative),
                    )
                )
        elif relative in allow_updates:
            changes.append(
                Change(
                    path=relative,
                    action="update",
                    diff_preview=preview(current, content, relative),
                )
            )
        else:
            conflicts.append(
                Change(
                    path=relative,
                    action="conflict",
                    diff_preview=preview(current, content, relative),
                )
            )
    for relative, expected_digest in sorted(owned_deletes.items()):
        destination = safe_join(root, relative)
        if not destination.exists():
            originals[relative] = None
            changes.append(Change(path=relative, action="skip"))
            continue
        current = destination.read_bytes()
        originals[relative] = current
        current_digest = hashlib.sha256(current).hexdigest()
        if current_digest != expected_digest:
            conflicts.append(
                Change(
                    path=relative,
                    action="conflict",
                    diff_preview="owned stale file was edited; refusing deletion",
                )
            )
        else:
            changes.append(Change(path=relative, action="delete"))
    if conflicts:
        return conflicts + [item for item in changes if item.action == "skip"]

    written: list[str] = []
    deleted: list[str] = []
    try:
        for relative, content in sorted(proposed.items()):
            destination = safe_join(root, relative)
            if destination.exists() and destination.read_bytes() == content:
                continue
            owned_update_digest = owned_updates.get(relative)
            if owned_update_digest is not None and (
                not destination.exists()
                or hashlib.sha256(destination.read_bytes()).hexdigest() != owned_update_digest
            ):
                raise RuntimeError(f"owned update changed during transaction: {relative}")
            atomic_write(root, relative, content)
            written.append(relative)
            if inject_failure_after is not None and len(written) >= inject_failure_after:
                raise RuntimeError("injected generator write failure")
        for relative in sorted(owned_deletes):
            destination = safe_join(root, relative)
            if not destination.exists():
                continue
            if hashlib.sha256(destination.read_bytes()).hexdigest() != owned_deletes[relative]:
                raise RuntimeError(f"owned delete changed during transaction: {relative}")
            destination.unlink()
            deleted.append(relative)
            if (
                inject_failure_after is not None
                and len(written) + len(deleted) >= inject_failure_after
            ):
                raise RuntimeError("injected generator write failure")
    except BaseException:
        for relative in reversed(deleted):
            original = originals[relative]
            if original is not None:
                atomic_write(root, relative, original)
        for relative in reversed(written):
            destination = safe_join(root, relative)
            original = originals[relative]
            if original is None:
                destination.unlink(missing_ok=True)
            else:
                atomic_write(root, relative, original)
        raise
    return changes
