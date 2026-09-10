#!/usr/bin/env python3
"""Verify generated agent-client projections without a local generator install."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "rules"
LOCK = RULES / "GENERATED.lock"
AGENT_PLATFORM = ROOT / "agent-platform"
PROJECTION_ROOT = ROOT / ".kt-scaffold" / "agent-projections"
PROJECTION_LOCK = PROJECTION_ROOT / "PROJECTIONS.lock.json"


def digest_corpus() -> str:
    digest = hashlib.sha256()
    # Preserve the recorded case-insensitive order independently of the host OS.
    for path in sorted(RULES.glob("*"), key=lambda path: (path.name.casefold(), path.name)):
        if path.is_file() and path.name != "GENERATED.lock":
            digest.update(path.name.encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def safe_relative(value: object, label: str) -> Path:
    if not isinstance(value, str):
        raise SystemExit(f"{label} path is not a string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise SystemExit(f"unsafe {label} path: {value}")
    return path


def verify_agent_projections() -> int:
    if not PROJECTION_LOCK.is_file() or PROJECTION_LOCK.is_symlink():
        raise SystemExit("agent projection lock is missing or unsafe")
    payload = json.loads(PROJECTION_LOCK.read_text(encoding="utf-8"))
    if payload.get("kind") != "AgentProjectionLock":
        raise SystemExit("agent projection lock kind is invalid")
    if payload.get("generation_status") != "generated":
        raise SystemExit("agent projection lock does not record generated state")
    if payload.get("activation_status") != "not_activated":
        raise SystemExit("inert agent projection lock claims activation")
    if payload.get("runtime_conformance") != "not_run":
        raise SystemExit("inert agent projection lock claims runtime conformance")

    inputs = payload.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise SystemExit("agent projection lock has no canonical input inventory")
    for item in inputs:
        if not isinstance(item, dict):
            raise SystemExit("agent projection input entry is malformed")
        relative = safe_relative(item.get("path"), "agent-platform input")
        source = AGENT_PLATFORM / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"canonical agent-platform input is missing or unsafe: {relative}")
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != item.get("sha256"):
            raise SystemExit(f"canonical agent-platform input drifted: {relative}")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise SystemExit("agent projection lock has no artifact inventory")
    expected_files = {PROJECTION_LOCK.relative_to(PROJECTION_ROOT).as_posix()}
    seen: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            raise SystemExit("agent projection artifact entry is malformed")
        relative = safe_relative(item.get("relative_path"), "agent projection")
        normalized = relative.as_posix()
        if normalized in seen:
            raise SystemExit(f"duplicate agent projection path: {normalized}")
        seen.add(normalized)
        expected_files.add(normalized)
        destination = PROJECTION_ROOT / relative
        if not destination.is_file() or destination.is_symlink():
            raise SystemExit(f"inert agent projection is missing or unsafe: {normalized}")
        actual = hashlib.sha256(destination.read_bytes()).hexdigest()
        if actual != item.get("sha256"):
            raise SystemExit(f"inert agent projection drifted: {normalized}")

    actual_files: set[str] = set()
    for path in PROJECTION_ROOT.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"symbolic link in inert projection tree: {path}")
        if path.is_file():
            actual_files.add(path.relative_to(PROJECTION_ROOT).as_posix())
    extra = sorted(actual_files - expected_files)
    if extra:
        raise SystemExit(f"unowned stale inert agent projections: {', '.join(extra)}")
    return len(artifacts)


def main() -> int:
    if not LOCK.is_file() or LOCK.is_symlink():
        raise SystemExit("governance lock is missing or unsafe")
    payload = json.loads(LOCK.read_text(encoding="utf-8"))
    if payload.get("corpus_digest") != digest_corpus():
        raise SystemExit("canonical rule corpus differs from its generated projection lock")
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise SystemExit("governance lock has no generated file inventory")
    for relative, expected in sorted(files.items()):
        path = safe_relative(relative, "governance lock")
        destination = ROOT / path
        if not destination.is_file() or destination.is_symlink():
            raise SystemExit(f"generated governance file is missing or unsafe: {relative}")
        actual = hashlib.sha256(destination.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"generated governance file drifted: {relative}")
    agent_count = verify_agent_projections()
    print(f"governance projections current: {len(files)} files")
    print(f"inert agent projections current: {agent_count} files; activation not claimed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
