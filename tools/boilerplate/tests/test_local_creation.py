"""Trusted-local project creation safety, determinism and desired-state contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from kt_scaffold.bundle import observed_tree_digest
from kt_scaffold.cli import main
from kt_scaffold.local_creation import project_create_operation, validate_local_workspace_root
from kt_scaffold.models import Answers
from kt_scaffold.safety import SafetyError
from kt_scaffold.update import scaffold_update


def test_local_creation_matches_cli_and_persists_selected_clients(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    local_root = tmp_path / "local"
    cli_root = tmp_path / "cli"
    local_root.mkdir()
    answers = answers_factory(agent_clients=["github-copilot-vscode"])

    local = project_create_operation(local_root, answers)
    assert local["receipt"]["status"] == "created"
    cli_args = [
        "init",
        "--target-dir",
        str(cli_root),
        "--intent",
        answers.project_intent,
        "--primary-domain",
        answers.primary_domain,
        "--product-name",
        answers.product_name,
        "--product-slug",
        answers.product_slug,
        "--env-prefix",
        str(answers.env_prefix),
        "--api-prefix",
        str(answers.api_prefix),
        "--tenant-header",
        answers.tenant_header,
        "--locales",
        ",".join(answers.locales),
        "--agent-client",
        "github-copilot-vscode",
    ]
    if not answers.observability:
        cli_args.append("--no-observability")
    assert main(cli_args) == 0

    assert observed_tree_digest(local_root) == observed_tree_digest(cli_root)
    persisted = yaml.safe_load(
        (local_root / ".kt-scaffold/answers.yml").read_text(encoding="utf-8")
    )
    assert persisted["agent_clients"] == ["github-copilot-vscode"]
    projections = local_root / ".kt-scaffold/agent-projections"
    assert len(list(projections.glob(".github/agents/*.agent.md"))) == 4
    assert not list(projections.glob(".claude/agents/*.md"))


def test_local_creation_exact_retry_and_divergence_fail_closed(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    answers = answers_factory(agent_clients=["github-copilot-vscode"])
    first = project_create_operation(root, answers)
    repeated = project_create_operation(root, answers)
    assert first["receipt"]["status"] == "created"
    assert repeated["receipt"]["status"] == "unchanged"
    assert repeated["receipt"]["observed_tree_digest"] == first["receipt"]["observed_tree_digest"]

    (root / "README.md").write_text("edited\n", encoding="utf-8")
    with pytest.raises(SafetyError, match="edited managed file"):
        project_create_operation(root, answers)


def test_local_creation_rejects_forged_manifest_and_matching_edited_file(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    answers = answers_factory(agent_clients=["github-copilot-vscode"])
    project_create_operation(root, answers)

    edited = b"forged but internally consistent\n"
    (root / "README.md").write_bytes(edited)
    manifest_path = root / ".kt-scaffold/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["managed"]["README.md"] = hashlib.sha256(edited).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SafetyError, match="installed deterministic generator"):
        project_create_operation(root, answers)


def test_local_creation_rejects_unowned_and_unsafe_roots(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    unowned = tmp_path / "unowned"
    unowned.mkdir()
    (unowned / "sentinel").write_text("keep", encoding="utf-8")
    with pytest.raises(SafetyError, match="not a complete scaffold"):
        project_create_operation(unowned, answers_factory())
    assert (unowned / "sentinel").read_text(encoding="utf-8") == "keep"

    with pytest.raises(SafetyError, match="absolute"):
        validate_local_workspace_root("relative")
    with pytest.raises(SafetyError, match="user home"):
        validate_local_workspace_root(Path.home())
    with pytest.raises(SafetyError, match="filesystem root"):
        validate_local_workspace_root(Path(Path.cwd().anchor))
    linked = tmp_path / "linked"
    linked.symlink_to(unowned, target_is_directory=True)
    with pytest.raises(SafetyError, match="symbolic link"):
        validate_local_workspace_root(linked)


def test_agent_client_selection_is_immutable_during_ordinary_update(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    project_create_operation(
        root,
        answers_factory(agent_clients=["github-copilot-vscode"]),
    )
    with pytest.raises(ValueError, match="immutable project desired state"):
        scaffold_update(root, answer_overrides={"agent_clients": ["codex"]})


def test_local_creation_implementation_has_no_download_or_process_execution() -> None:
    source = Path("src/kt_scaffold/local_creation.py").read_text(encoding="utf-8")
    for forbidden in (
        "subprocess",
        "os.system",
        "requests",
        "urllib",
        "standalone_applicator",
        "apply_bundle",
        "curl",
    ):
        assert forbidden not in source
