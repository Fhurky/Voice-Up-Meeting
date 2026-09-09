"""Replay scaffold answers while preserving every project-owned edit."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, cast

import yaml

from kt_scaffold import __version__
from kt_scaffold.fsops import apply_file_set, preview
from kt_scaffold.models import Answers, Change, ToolResult
from kt_scaffold.project import render_project
from kt_scaffold.safety import resolved_root, safe_join


def load_answers(root: Path) -> Answers:
    path = root / ".kt-scaffold" / "answers.yml"
    if not path.is_file():
        raise ValueError(f"{root} is not a scaffolded project")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Answers.model_validate(payload)


def load_manifest(root: Path) -> dict[str, Any]:
    path = root / ".kt-scaffold" / "manifest.json"
    if not path.is_file():
        raise ValueError("scaffold manifest is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("scaffold manifest is malformed")
    if not isinstance(payload.get("managed"), dict):
        raise ValueError("scaffold manifest is malformed")
    return cast(dict[str, Any], payload)


def scaffold_update(
    target_dir: str | Path,
    *,
    answer_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    root = resolved_root(target_dir)
    answers = load_answers(root)
    before_answers = answers.model_dump(mode="json")
    if answer_overrides and "generator_version" in answer_overrides:
        raise ValueError("generator_version is owned by the installed kt-scaffold package")
    if answer_overrides and "agent_clients" in answer_overrides:
        raise ValueError(
            "agent_clients is immutable project desired state; use a governed migration operation"
        )
    installed_release = tuple(int(part) for part in __version__.split("-", 1)[0].split("."))
    recorded_release = tuple(
        int(part) for part in answers.generator_version.split("-", 1)[0].split(".")
    )
    if recorded_release > installed_release:
        raise ValueError(
            "refusing to update a project produced by newer kt-scaffold "
            f"{answers.generator_version} with installed {__version__}"
        )
    candidate_answers = {**before_answers, **(answer_overrides or {})}
    candidate_answers["generator_version"] = __version__
    answers = Answers.model_validate(candidate_answers)
    stage = Path(tempfile.mkdtemp(prefix=f".{root.name}.kt-update-", dir=root.parent))
    try:
        prospective = render_project(stage, answers)
        old_manifest = load_manifest(root)
        old: dict[str, str] = old_manifest["managed"]
        new: dict[str, str] = prospective["managed"]
        changes: list[Change] = []
        conflicts: list[str] = []
        resulting = dict(old)
        proposed_writes: dict[str, bytes] = {}

        for relative, new_digest in sorted(new.items()):
            source = stage / relative
            destination = safe_join(root, relative)
            proposed = source.read_bytes()
            if not destination.exists():
                changes.append(Change(path=relative, action="create"))
                resulting[relative] = new_digest
                proposed_writes[relative] = proposed
                continue
            current = destination.read_bytes()
            current_digest = hashlib.sha256(current).hexdigest()
            if relative not in old:
                changes.append(
                    Change(
                        path=relative,
                        action="conflict",
                        diff_preview=preview(current, proposed, relative),
                    )
                )
                conflicts.append(relative)
                continue
            if current_digest != old[relative]:
                changes.append(
                    Change(
                        path=relative,
                        action="conflict",
                        diff_preview=preview(current, proposed, relative),
                    )
                )
                conflicts.append(relative)
                continue
            if current_digest == new_digest:
                changes.append(Change(path=relative, action="skip"))
                resulting[relative] = new_digest
                continue
            changes.append(Change(path=relative, action="update"))
            resulting[relative] = new_digest
            proposed_writes[relative] = proposed

        removed = sorted(set(old) - set(new))
        manual_steps = [
            f"Corpus no longer emits {path}; review it manually (never auto-deleted)."
            for path in removed
        ]
        final_manifest = {
            "format": 1,
            "generator_version": answers.generator_version,
            "managed": resulting,
        }
        manifest_bytes = (json.dumps(final_manifest, indent=2, sort_keys=True) + "\n").encode()

        # Update is a single transaction. A conflict anywhere means no generated file,
        # answer or manifest is touched; the caller can resolve it and replay safely.
        if not conflicts:
            manifest_path = safe_join(root, ".kt-scaffold/manifest.json")
            if manifest_path.read_bytes() != manifest_bytes:
                proposed_writes[".kt-scaffold/manifest.json"] = manifest_bytes
            if proposed_writes:
                apply_file_set(
                    root,
                    proposed_writes,
                    allow_updates=set(proposed_writes),
                )
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    result = ToolResult(
        ok=not conflicts,
        changes=changes,
        warnings=[f"{len(conflicts)} edited generated file(s) left untouched"] if conflicts else [],
        next_steps=["Resolve conflicts manually, then rerun kt-scaffold update"]
        if conflicts
        else ["scripts/quality-gate.sh all"],
    ).as_dict()
    result.update(
        {
            "applied": (
                []
                if conflicts
                else [item.path for item in changes if item.action in {"create", "update"}]
            ),
            "conflicts": conflicts,
            "answers_diff": {
                key: {"before": before_answers.get(key), "after": value}
                for key, value in answers.model_dump(mode="json").items()
                if before_answers.get(key) != value
            },
            "manual_steps": manual_steps,
        }
    )
    return result
