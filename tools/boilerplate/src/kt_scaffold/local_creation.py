"""Trusted local MCP creation bound to one explicit workspace root."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Literal

from kt_scaffold import __version__
from kt_scaffold.bundle import collect_entries, tree_digest
from kt_scaffold.models import Answers, LocalMcpCreationReceipt, ToolResult
from kt_scaffold.project import project_init, render_project
from kt_scaffold.safety import SafetyError
from kt_scaffold.update import load_answers, load_manifest


def validate_local_workspace_root(value: str | Path) -> Path:
    """Bind a local MCP process to a real, narrow, non-symlink workspace root."""

    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        raise SafetyError("workspace root must be an explicit absolute path")
    if candidate.is_symlink():
        raise SafetyError("workspace root may not be a symbolic link")
    if not candidate.exists() or not candidate.is_dir():
        raise SafetyError("workspace root must be an existing directory")
    resolved = candidate.resolve(strict=True)
    if resolved == Path(resolved.anchor):
        raise SafetyError("filesystem root is not a valid workspace root")
    if resolved == Path.home().resolve(strict=True):
        raise SafetyError("user home is not a valid workspace root")
    return resolved


def _expected_tree_digest(answers: Answers) -> str:
    with tempfile.TemporaryDirectory(prefix="kt-scaffold-expected-") as temporary:
        expected_root = Path(temporary) / "project"
        expected_root.mkdir()
        render_project(expected_root, answers)
        return tree_digest(collect_entries(expected_root))


def _assert_exact_completed_retry(root: Path, answers: Answers) -> str:
    try:
        recorded_answers = load_answers(root)
        manifest = load_manifest(root)
    except (OSError, ValueError) as exc:
        raise SafetyError("workspace is non-empty and is not a complete scaffold") from exc
    if recorded_answers.model_dump(mode="json") != answers.model_dump(mode="json"):
        raise SafetyError("workspace contains a scaffold created from different answers")
    managed = manifest["managed"]
    expected_files = set(managed) | {".kt-scaffold/manifest.json"}
    actual_files: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise SafetyError(f"completed scaffold contains a symbolic link: {relative}")
        if path.is_file():
            actual_files.add(relative)
    if actual_files != expected_files:
        raise SafetyError("workspace is partial, edited, or contains unowned files")
    for relative, expected_digest in managed.items():
        path = root / relative
        if not path.is_file():
            raise SafetyError(f"completed scaffold is missing managed file: {relative}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected_digest:
            raise SafetyError(f"completed scaffold has an edited managed file: {relative}")
    expected_digest = _expected_tree_digest(answers)
    if tree_digest(collect_entries(root)) != expected_digest:
        raise SafetyError("completed scaffold differs from the installed deterministic generator")
    return expected_digest


def project_create_operation(root: Path, answers: Answers) -> dict[str, object]:
    """Create or recognize one exact scaffold without executing external code."""

    workspace = validate_local_workspace_root(root)
    status: Literal["created", "unchanged"] = "created"
    if any(workspace.iterdir()):
        expected = _assert_exact_completed_retry(workspace, answers)
        status = "unchanged"
    else:
        project_init(workspace, answers)
        expected = _expected_tree_digest(answers)

    entries = collect_entries(workspace)
    observed = tree_digest(entries)
    if observed != expected:
        raise SafetyError("created scaffold differs from the installed deterministic generator")
    receipt = LocalMcpCreationReceipt(
        generator_version=__version__,
        status=status,
        expected_tree_digest=expected,
        observed_tree_digest=observed,
        file_count=sum(entry.kind == "file" for entry in entries),
        entry_count=len(entries),
    )
    result = ToolResult(
        ok=True,
        next_steps=["Run the generated local quality gate before product adaptation."],
    ).as_dict()
    result["receipt"] = receipt.model_dump(mode="json")
    return result


__all__ = ["project_create_operation", "validate_local_workspace_root"]
