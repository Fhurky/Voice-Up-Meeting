"""Filesystem sandbox and rollback guarantees."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from kt_scaffold.fsops import apply_file_set
from kt_scaffold.models import Answers
from kt_scaffold.project import project_init
from kt_scaffold.safety import SafetyError, atomic_write, resolved_root, safe_join, safe_relative


@pytest.mark.parametrize(
    "value",
    ["../escape", "nested/../../escape", "/absolute/path"],
)
def test_relative_paths_cannot_escape_the_sandbox(value: str) -> None:
    with pytest.raises(SafetyError, match="unsafe relative path"):
        safe_relative(value)


def test_symlink_components_and_symlink_roots_are_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    root_link = tmp_path / "root-link"
    root_link.symlink_to(root, target_is_directory=True)

    with pytest.raises(SafetyError, match="symbolic-link component"):
        safe_join(root, "linked/escaped.txt")
    with pytest.raises(SafetyError, match="target root may not be a symbolic link"):
        resolved_root(root_link)


def test_atomic_write_rejects_traversal_without_touching_outside(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("original", encoding="utf-8")

    with pytest.raises(SafetyError):
        atomic_write(root, "../outside.txt", b"changed")

    assert outside.read_text(encoding="utf-8") == "original"
    assert list(root.iterdir()) == []


def test_multi_file_write_rolls_back_every_written_file(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "existing.txt").write_text("before", encoding="utf-8")

    with pytest.raises(RuntimeError, match="injected generator write failure"):
        apply_file_set(
            root,
            {
                "created.txt": b"created",
                "existing.txt": b"after",
            },
            allow_updates={"existing.txt"},
            inject_failure_after=2,
        )

    assert not (root / "created.txt").exists()
    assert (root / "existing.txt").read_text(encoding="utf-8") == "before"


def test_transactional_init_publish_failure_restores_preexisting_empty_target(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    target.mkdir()

    with pytest.raises(RuntimeError, match="injected publish failure"):
        project_init(target, answers_factory(), inject_publish_failure=True)

    assert target.is_dir()
    assert list(target.iterdir()) == []
    assert not list(tmp_path.glob(".project.kt-stage-*"))
    assert not list(tmp_path.glob(".project.kt-failed-*"))
    assert not list(tmp_path.glob(".project.kt-original-*"))


def test_project_publish_failure_removes_new_target(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"

    with pytest.raises(RuntimeError, match="injected publish failure"):
        project_init(target, answers_factory(), inject_publish_failure=True)

    assert not target.exists()
    assert not list(tmp_path.glob(".project.kt-*"))


def test_project_init_refuses_nonempty_target_without_mutation(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    target.mkdir()
    sentinel = target / "owned.txt"
    sentinel.write_text("user-owned", encoding="utf-8")

    with pytest.raises(SafetyError, match="empty target"):
        project_init(target, answers_factory())

    assert sentinel.read_text(encoding="utf-8") == "user-owned"
    assert sorted(path.name for path in target.iterdir()) == ["owned.txt"]
