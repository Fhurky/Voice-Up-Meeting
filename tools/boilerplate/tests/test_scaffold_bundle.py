"""Deterministic bundle and transactional local-applicator contracts."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from kt_scaffold.applicator import apply_scaffold_bundle
from kt_scaffold.bundle import create_scaffold_bundle, observed_tree_digest
from kt_scaffold.cli import main
from kt_scaffold.models import Answers, ScaffoldBundleDescriptor
from kt_scaffold.project import project_init
from kt_scaffold.safety import SafetyError


def _answers(**overrides: object) -> Answers:
    values: dict[str, object] = {
        "project_intent": "Create a deterministic financial audit MCP scaffold.",
        "primary_domain": "audit",
        "product_name": "Financial Audit Lab",
        "product_slug": "financial-audit-lab",
        "locales": ["tr", "en"],
        "observability": False,
    }
    values.update(overrides)
    return Answers.model_validate(values)


def _write_archive(root: Path, payload: bytes) -> Path:
    archive = root / "scaffold.tar.gz"
    archive.write_bytes(payload)
    return archive


def test_bundle_is_reproducible_and_matches_project_init(tmp_path: Path) -> None:
    answers = _answers()
    first, first_payload = create_scaffold_bundle(answers)
    second, second_payload = create_scaffold_bundle(answers)
    assert first == second
    assert first_payload == second_payload
    assert hashlib.sha256(first_payload).hexdigest() == first.archive.sha256
    assert first.patch_set.file_count > 300
    assert first.patch_set.entry_count > first.patch_set.file_count

    cli_project = tmp_path / "cli-project"
    project_init(cli_project, answers)
    assert observed_tree_digest(cli_project) == first.tree_digest

    archive = _write_archive(tmp_path, first_payload)
    bundle_project = tmp_path / "bundle-project"
    receipt = apply_scaffold_bundle(archive, bundle_project, first)
    assert receipt.status == "created"
    assert receipt.observed_tree_digest == first.tree_digest

    cli_entries = {
        path.relative_to(cli_project): (path.stat().st_mode & 0o777, path.read_bytes())
        for path in cli_project.rglob("*")
        if path.is_file()
    }
    bundle_entries = {
        path.relative_to(bundle_project): (path.stat().st_mode & 0o777, path.read_bytes())
        for path in bundle_project.rglob("*")
        if path.is_file()
    }
    assert bundle_entries == cli_entries


def test_applicator_exact_retry_is_unchanged(tmp_path: Path) -> None:
    descriptor, payload = create_scaffold_bundle(_answers())
    archive = _write_archive(tmp_path, payload)
    target = tmp_path / "project"
    assert apply_scaffold_bundle(archive, target, descriptor).status == "created"
    assert apply_scaffold_bundle(archive, target, descriptor).status == "unchanged"


def test_applicator_rejects_tampering_and_conflicts(tmp_path: Path) -> None:
    descriptor, payload = create_scaffold_bundle(_answers())
    archive = _write_archive(tmp_path, payload)
    archive.write_bytes(payload[:-1] + bytes([payload[-1] ^ 1]))
    with pytest.raises(SafetyError, match="digest"):
        apply_scaffold_bundle(archive, tmp_path / "tampered", descriptor)

    archive.write_bytes(payload)
    conflict = tmp_path / "conflict"
    conflict.mkdir()
    (conflict / "owned.txt").write_text("project-owned\n", encoding="utf-8")
    with pytest.raises(SafetyError, match="non-empty"):
        apply_scaffold_bundle(archive, conflict, descriptor)
    assert (conflict / "owned.txt").read_text(encoding="utf-8") == "project-owned\n"


def test_applicator_rejects_modified_descriptor_and_rolls_back(tmp_path: Path) -> None:
    descriptor, payload = create_scaffold_bundle(_answers())
    archive = _write_archive(tmp_path, payload)
    modified = descriptor.model_copy(update={"tree_digest": "0" * 64})
    with pytest.raises(SafetyError, match="tree digest"):
        apply_scaffold_bundle(archive, tmp_path / "modified", modified)

    target = tmp_path / "rollback"
    target.mkdir()
    with pytest.raises(RuntimeError, match="injected publish failure"):
        apply_scaffold_bundle(
            archive,
            target,
            descriptor,
            inject_publish_failure=True,
        )
    assert target.is_dir()
    assert list(target.iterdir()) == []


def test_descriptor_is_strict_and_serializable() -> None:
    descriptor, _ = create_scaffold_bundle(_answers())
    payload = descriptor.model_dump(mode="json")
    assert ScaffoldBundleDescriptor.model_validate(payload) == descriptor
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="Extra inputs"):
        ScaffoldBundleDescriptor.model_validate(payload)


def test_observability_choice_changes_content_address() -> None:
    disabled, _ = create_scaffold_bundle(_answers(observability=False))
    enabled, _ = create_scaffold_bundle(_answers(observability=True))
    assert disabled.answers_digest != enabled.answers_digest
    assert disabled.tree_digest != enabled.tree_digest
    assert disabled.bundle_id != enabled.bundle_id


def test_bundle_does_not_depend_on_temporary_root() -> None:
    answers = _answers()
    with tempfile.TemporaryDirectory(prefix="first-root-"):
        first, first_payload = create_scaffold_bundle(answers)
    with tempfile.TemporaryDirectory(prefix="second-root-"):
        second, second_payload = create_scaffold_bundle(answers)
    assert json.dumps(first.model_dump(mode="json"), sort_keys=True) == json.dumps(
        second.model_dump(mode="json"), sort_keys=True
    )
    assert first_payload == second_payload


def test_cli_and_turkish_alias_apply_the_same_bundle(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    descriptor, payload = create_scaffold_bundle(_answers())
    archive = _write_archive(tmp_path, payload)
    descriptor_path = tmp_path / "descriptor.json"
    descriptor_path.write_text(
        json.dumps(descriptor.model_dump(mode="json", exclude_none=True)),
        encoding="utf-8",
    )
    target = tmp_path / "project"
    arguments = [
        "--archive",
        str(archive),
        "--descriptor",
        str(descriptor_path),
        "--target-dir",
        str(target),
    ]
    assert main(["apply-bundle", *arguments]) == 0
    english = json.loads(capsys.readouterr().out)
    assert english["receipt"]["status"] == "created"
    assert main(["paketi-uygula", *arguments]) == 0
    turkish = json.loads(capsys.readouterr().out)
    assert turkish["receipt"]["status"] == "unchanged"
    assert english["receipt"]["bundle_id"] == turkish["receipt"]["bundle_id"]
