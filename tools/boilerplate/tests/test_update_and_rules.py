"""Safe update and rule projection drift contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from functools import partial
from pathlib import Path

import pytest
import yaml

from kt_scaffold import __version__
from kt_scaffold import update as update_module
from kt_scaffold.agent_platform.contracts import AgentPlatformContractError
from kt_scaffold.agent_platform.models import ReasonCode
from kt_scaffold.fsops import apply_file_set
from kt_scaffold.models import Answers
from kt_scaffold.operations import clients_render_operation
from kt_scaffold.project import project_init
from kt_scaffold.update import scaffold_update


def test_update_noop_is_idempotent_and_writes_nothing(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())

    result = scaffold_update(target)

    assert result["ok"] is True
    assert result["conflicts"] == []
    assert result["applied"] == []
    assert {change["action"] for change in result["changes"]} == {"skip"}


def test_update_conflict_preserves_every_file_and_reports_the_edit(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    readme = target / "README.md"
    user_content = readme.read_text(encoding="utf-8") + "\nUser-owned clarification.\n"
    readme.write_text(user_content, encoding="utf-8")
    before = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }

    result = scaffold_update(target, answer_overrides={"product_name": "Renamed Product"})

    assert result["ok"] is False
    assert "README.md" in result["conflicts"]
    assert readme.read_text(encoding="utf-8") == user_content
    readme_change = next(change for change in result["changes"] if change["path"] == "README.md")
    assert readme_change["action"] == "conflict"
    assert "User-owned clarification" in readme_change["diff_preview"]
    after = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert result["applied"] == []
    assert result["answers_diff"]["product_name"] == {
        "before": "Internal Control Surface",
        "after": "Renamed Product",
    }


def test_update_replay_advances_a_historical_generator_version_owned_by_the_tool(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    answers_path = target / ".kt-scaffold/answers.yml"
    manifest_path = target / ".kt-scaffold/manifest.json"
    answers = yaml.safe_load(answers_path.read_text(encoding="utf-8"))
    answers["generator_version"] = "0.0.9"
    historical_answers = yaml.safe_dump(answers, sort_keys=False, allow_unicode=True).encode()
    answers_path.write_bytes(historical_answers)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generator_version"] = "0.0.9"
    manifest["managed"][".kt-scaffold/answers.yml"] = hashlib.sha256(historical_answers).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    result = scaffold_update(target)

    assert result["ok"] is True
    assert result["answers_diff"]["generator_version"] == {
        "before": "0.0.9",
        "after": __version__,
    }
    updated_answers = yaml.safe_load(answers_path.read_text(encoding="utf-8"))
    updated_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert updated_answers["generator_version"] == __version__
    assert updated_manifest["generator_version"] == __version__


def test_update_rejects_a_caller_owned_generator_version(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())

    with pytest.raises(ValueError, match="owned by the installed"):
        scaffold_update(target, answer_overrides={"generator_version": "0.0.9"})


def test_update_rolls_back_every_file_and_manifest_on_write_failure(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    before = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }
    monkeypatch.setattr(
        update_module,
        "apply_file_set",
        partial(apply_file_set, inject_failure_after=2),
    )

    with pytest.raises(RuntimeError, match="injected generator write failure"):
        scaffold_update(target, answer_overrides={"product_name": "Renamed Product"})

    after = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_owned_file_deletion_is_digest_checked_and_transactional(tmp_path: Path) -> None:
    root = tmp_path / "owned-files"
    root.mkdir()
    stale = root / "stale.txt"
    current = root / "current.txt"
    stale.write_text("generated stale\n", encoding="utf-8")
    current.write_text("generated old\n", encoding="utf-8")
    stale_digest = hashlib.sha256(stale.read_bytes()).hexdigest()

    changes = apply_file_set(
        root,
        {"current.txt": b"generated new\n"},
        allow_updates={"current.txt"},
        owned_deletes={"stale.txt": stale_digest},
    )

    assert {(item.path, item.action) for item in changes} == {
        ("current.txt", "update"),
        ("stale.txt", "delete"),
    }
    assert not stale.exists()
    assert current.read_bytes() == b"generated new\n"


def test_owned_file_deletion_refuses_edits_and_rolls_back_on_failure(tmp_path: Path) -> None:
    root = tmp_path / "owned-files"
    root.mkdir()
    stale = root / "stale.txt"
    current = root / "current.txt"
    stale.write_text("edited stale\n", encoding="utf-8")
    current.write_text("generated old\n", encoding="utf-8")

    conflicts = apply_file_set(
        root,
        {"current.txt": b"generated new\n"},
        allow_updates={"current.txt"},
        owned_deletes={"stale.txt": hashlib.sha256(b"generated stale\n").hexdigest()},
    )
    assert [(item.path, item.action) for item in conflicts] == [("stale.txt", "conflict")]
    assert current.read_bytes() == b"generated old\n"

    stale_digest = hashlib.sha256(stale.read_bytes()).hexdigest()
    with pytest.raises(RuntimeError, match="injected generator write failure"):
        apply_file_set(
            root,
            {"current.txt": b"generated new\n"},
            allow_updates={"current.txt"},
            owned_deletes={"stale.txt": stale_digest},
            inject_failure_after=2,
        )
    assert stale.read_bytes() == b"edited stale\n"
    assert current.read_bytes() == b"generated old\n"


def test_update_removal_is_reported_for_manual_review_and_never_deleted(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    retired_path = target / "rules/retired-generated-rule.md"
    retired_path.write_text("retired corpus output\n", encoding="utf-8")
    manifest_path = target / ".kt-scaffold/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["managed"]["rules/retired-generated-rule.md"] = hashlib.sha256(
        retired_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = scaffold_update(target)

    assert result["ok"] is True
    assert retired_path.read_text(encoding="utf-8") == "retired corpus output\n"
    assert result["manual_steps"] == [
        "Corpus no longer emits rules/retired-generated-rule.md; "
        "review it manually (never auto-deleted)."
    ]


def test_rule_render_check_detects_and_repairs_projection_drift(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    agents = target / "AGENTS.md"
    canonical = agents.read_bytes()
    agents.write_text("manual drift\n", encoding="utf-8")

    check = clients_render_operation(str(target), mode="check")

    assert check["ok"] is False
    assert {item["path"] for item in check["drift"]} == {"AGENTS.md"}
    assert agents.read_text(encoding="utf-8") == "manual drift\n"

    write = clients_render_operation(str(target), mode="write")
    final_check = clients_render_operation(str(target), mode="check")

    assert write["ok"] is True
    assert write["lock_updated"] is True
    assert agents.read_bytes() == canonical
    assert final_check["ok"] is True
    assert final_check["drift"] == []


def test_subset_render_preserves_full_governance_lock_inventory(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    lock_path = target / "rules" / "GENERATED.lock"
    complete = json.loads(lock_path.read_text(encoding="utf-8"))

    result = clients_render_operation(str(target), clients=["codex"], mode="write")
    after = json.loads(lock_path.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert after == complete
    assert "AGENTS.md" in after["files"]
    assert ".codex/config.toml" in after["files"]


def test_agent_client_subset_is_inert_and_has_a_coherent_selected_lock(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    governance_lock_path = target / "rules" / "GENERATED.lock"
    governance_lock = governance_lock_path.read_bytes()

    result = clients_render_operation(
        str(target),
        clients=["codex"],
        agent_clients=["codex", "cursor"],
        mode="write",
    )

    projection = result["agent_projection"]
    assert isinstance(projection, dict)
    assert projection["artifact_count"] == 8
    lock_path = target / ".kt-scaffold/agent-projections/PROJECTIONS.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert len(lock["artifacts"]) == 8
    assert {item["client_id"] for item in lock["artifacts"]} == {"codex", "cursor"}
    projection_root = target / ".kt-scaffold/agent-projections"
    assert sum(path.is_file() for path in projection_root.rglob("*")) == 9
    assert governance_lock_path.read_bytes() == governance_lock
    assert not (target / ".codex/agents").exists()
    assert not (target / ".cursor/agents").exists()


def test_unknown_agent_client_fails_before_any_render_write(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    before = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }

    with pytest.raises(AgentPlatformContractError) as caught:
        clients_render_operation(
            str(target),
            agent_clients=["unknown-client"],  # type: ignore[list-item]
            mode="write",
        )

    after = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }
    assert caught.value.code == ReasonCode.ADAPTER_NOT_FOUND
    assert after == before


def test_render_rejects_unknown_governance_client(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())

    with pytest.raises(ValueError, match="unknown governance clients: unknown-client"):
        clients_render_operation(str(target), clients=["unknown-client"], mode="check")


def test_generated_governance_check_needs_no_local_generator(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    script = target / "scripts/check-governance-drift.py"

    passed = subprocess.run(
        ["python3", str(script)],
        cwd=target,
        env={"PATH": "/usr/bin:/bin"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert passed.returncode == 0, passed.stderr
    assert "governance projections current" in passed.stdout
    assert "inert agent projections current: 16 files; activation not claimed" in passed.stdout

    agents = target / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
    failed = subprocess.run(
        ["python3", str(script)],
        cwd=target,
        env={"PATH": "/usr/bin:/bin"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert failed.returncode != 0
    assert "generated governance file drifted: AGENTS.md" in failed.stderr

    clients_render_operation(str(target), mode="write")
    inert = target / ".kt-scaffold/agent-projections/.codex/agents/code-review.toml"
    inert.write_text(inert.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
    projection_failed = subprocess.run(
        ["python3", str(script)],
        cwd=target,
        env={"PATH": "/usr/bin:/bin"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert projection_failed.returncode != 0
    assert "inert agent projection drifted: .codex/agents/code-review.toml" in (
        projection_failed.stderr
    )
