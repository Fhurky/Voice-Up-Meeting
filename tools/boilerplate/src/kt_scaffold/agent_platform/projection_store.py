"""Inert projection storage and disposable real-client conformance materialization."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from kt_scaffold.agent_platform.activation import (
    SignedConformanceWorkspaceGrant,
    assert_verified_grant_binding,
    consume_verified_grant,
    verify_conformance_workspace_grant,
)
from kt_scaffold.agent_platform.manifest import canonical_json
from kt_scaffold.agent_platform.models import (
    CompilationResult,
    ProjectionManifest,
    revalidate_compilation_result,
)
from kt_scaffold.agent_platform.registry import DetachedSignatureVerifier
from kt_scaffold.fsops import apply_file_set
from kt_scaffold.models import Change
from kt_scaffold.safety import SafetyError, atomic_write, safe_join

INERT_PROJECTION_ROOT = PurePosixPath(".kt-scaffold/agent-projections")
INERT_LOCK_PATH = (INERT_PROJECTION_ROOT / "PROJECTIONS.lock.json").as_posix()


class AgentProjectionStoreError(ValueError):
    """An inert projection inventory is unsafe, edited, or malformed."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inert_projection_path(native_path: str) -> str:
    path = PurePosixPath(native_path)
    if (
        path.is_absolute()
        or path.as_posix() != native_path
        or any(part in {"", ".", ".."} for part in path.parts)
        or "\\" in native_path
    ):
        raise AgentProjectionStoreError(f"unsafe native projection path: {native_path}")
    return (INERT_PROJECTION_ROOT / path).as_posix()


def inert_projection_files(result: CompilationResult) -> dict[str, bytes]:
    try:
        result = revalidate_compilation_result(result)
    except (AttributeError, TypeError, ValueError) as exc:
        raise AgentProjectionStoreError("compiled projection result failed validation") from exc
    files = {
        inert_projection_path(artifact.relative_path): artifact.content.encode("utf-8")
        for artifact in result.artifacts
    }
    files[INERT_LOCK_PATH] = result.lock_content.encode("utf-8")
    return files


def _load_existing_manifest(root: Path) -> tuple[ProjectionManifest, bytes] | None:
    lock = safe_join(root, INERT_LOCK_PATH)
    if not lock.exists():
        return None
    if lock.is_symlink() or not lock.is_file():
        raise AgentProjectionStoreError("inert projection lock is missing or unsafe")
    content = lock.read_bytes()
    try:
        manifest = ProjectionManifest.model_validate_json(content)
    except (UnicodeDecodeError, ValidationError) as exc:
        raise AgentProjectionStoreError("inert projection lock is malformed") from exc
    canonical = canonical_json(manifest.model_dump(mode="json")).encode("utf-8")
    if content != canonical:
        raise AgentProjectionStoreError("inert projection lock is not canonical generated JSON")
    return manifest, content


def _artifact_digests(manifest: ProjectionManifest) -> dict[str, str]:
    digests: dict[str, str] = {}
    for artifact in manifest.artifacts:
        relative = inert_projection_path(artifact.relative_path)
        if relative in digests:
            raise AgentProjectionStoreError(f"duplicate inert projection path: {relative}")
        digests[relative] = artifact.sha256
    return digests


def render_inert_projections(
    root: str | Path,
    result: CompilationResult,
    *,
    mode: str = "write",
) -> tuple[list[Change], list[dict[str, str]]]:
    """Write/check compiler outputs below an inert root without activating client discovery."""

    if mode not in {"write", "check"}:
        raise ValueError("mode must be write or check")
    try:
        result = revalidate_compilation_result(result)
    except (AttributeError, TypeError, ValueError) as exc:
        raise AgentProjectionStoreError("compiled projection result failed validation") from exc
    project_root = Path(root).resolve(strict=True)
    expected = inert_projection_files(result)
    current_manifest = _load_existing_manifest(project_root)
    old_digests = _artifact_digests(current_manifest[0]) if current_manifest else {}
    new_digests = _artifact_digests(result.manifest)
    changes: list[Change] = []
    drift: list[dict[str, str]] = []
    conflicts: list[Change] = []
    allow_updates: set[str] = set()

    for relative, proposed in sorted(expected.items()):
        destination = safe_join(project_root, relative)
        if not destination.exists():
            changes.append(Change(path=relative, action="create"))
            drift.append({"path": relative, "reason": "missing"})
            continue
        if destination.is_symlink() or not destination.is_file():
            raise AgentProjectionStoreError(f"unsafe inert projection destination: {relative}")
        current = destination.read_bytes()
        if current == proposed:
            changes.append(Change(path=relative, action="skip"))
            continue
        if relative == INERT_LOCK_PATH:
            if current_manifest is None:
                conflicts.append(Change(path=relative, action="conflict"))
                drift.append({"path": relative, "reason": "unowned lock"})
            else:
                changes.append(Change(path=relative, action="update"))
                allow_updates.add(relative)
                drift.append({"path": relative, "reason": "content differs"})
            continue
        actual = _digest(current)
        owned_digest = old_digests.get(relative)
        if owned_digest is None:
            conflicts.append(Change(path=relative, action="conflict"))
            drift.append({"path": relative, "reason": "unowned destination"})
        elif actual != owned_digest:
            conflicts.append(Change(path=relative, action="conflict"))
            drift.append({"path": relative, "reason": "edited generated projection"})
        else:
            changes.append(Change(path=relative, action="update"))
            allow_updates.add(relative)
            drift.append({"path": relative, "reason": "content differs"})

    owned_deletes: dict[str, str] = {}
    for relative in sorted(set(old_digests) - set(new_digests)):
        destination = safe_join(project_root, relative)
        if not destination.exists():
            changes.append(Change(path=relative, action="skip"))
            continue
        if destination.is_symlink() or not destination.is_file():
            raise AgentProjectionStoreError(f"unsafe stale inert projection: {relative}")
        actual = _digest(destination.read_bytes())
        if actual != old_digests[relative]:
            conflicts.append(Change(path=relative, action="conflict"))
            drift.append({"path": relative, "reason": "edited stale projection"})
        else:
            changes.append(Change(path=relative, action="delete"))
            drift.append({"path": relative, "reason": "stale generated projection"})
            owned_deletes[relative] = old_digests[relative]

    if conflicts:
        return sorted(
            conflicts + [item for item in changes if item.action == "skip"], key=lambda x: x.path
        ), drift
    if mode == "write" and drift:
        try:
            applied = apply_file_set(
                project_root,
                expected,
                allow_updates=allow_updates,
                owned_deletes=owned_deletes,
            )
        except SafetyError as exc:
            raise AgentProjectionStoreError(str(exc)) from exc
        return applied, drift
    return changes, drift


@contextmanager
def materialize_conformance_client(
    result: CompilationResult,
    client_id: str,
    *,
    authorization: SignedConformanceWorkspaceGrant,
    environment_id: str,
    now: datetime,
    signature_verifier: DetachedSignatureVerifier,
    consume_grant: Callable[[str, str], bool],
) -> Iterator[Path]:
    """Reverify a signed grant, then create and destroy one disposable live workspace."""

    try:
        result = revalidate_compilation_result(result)
    except (AttributeError, TypeError, ValueError) as exc:
        raise AgentProjectionStoreError("compiled projection result failed validation") from exc
    artifacts = tuple(item for item in result.artifacts if item.client_id == client_id)
    if not artifacts:
        raise AgentProjectionStoreError(f"compiled result has no client: {client_id}")
    verified_authorization = verify_conformance_workspace_grant(
        authorization,
        result=result,
        client_id=client_id,
        environment_id=environment_id,
        now=now,
        signature_verifier=signature_verifier,
    )
    assert_verified_grant_binding(
        verified_authorization,
        result=result,
        client_id=client_id,
        environment_id=environment_id,
        now=now,
    )
    consume_verified_grant(verified_authorization, consume_grant)
    workspace = Path(tempfile.mkdtemp(prefix=f"kt-agent-conformance-{client_id}-"))
    try:
        for artifact in artifacts:
            atomic_write(workspace, artifact.relative_path, artifact.content.encode("utf-8"))
        atomic_write(
            workspace,
            ".kt-scaffold/PROJECTIONS.lock.json",
            result.lock_content.encode("utf-8"),
        )
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


__all__ = [
    "INERT_LOCK_PATH",
    "INERT_PROJECTION_ROOT",
    "AgentProjectionStoreError",
    "inert_projection_files",
    "inert_projection_path",
    "materialize_conformance_client",
    "render_inert_projections",
]
