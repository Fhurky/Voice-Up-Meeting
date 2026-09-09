"""Knowledge-plane metadata, proposal and reconciliation contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from kt_scaffold.cli import main
from kt_scaffold.knowledge import (
    governance_artifacts_get_operation,
    governance_catalog_operation,
    governance_update_check_operation,
    project_blueprint_operation,
    reconciliation_validate_operation,
)
from kt_scaffold.mcp_surfaces import _answers
from kt_scaffold.models import (
    GovernanceArtifactRef,
    GovernanceUpdateProposal,
    ProjectMetadata,
    ReconciliationDecision,
)
from kt_scaffold.operations import init_operation


def test_mcp_answer_normalization_treats_empty_optional_prefixes_as_omitted() -> None:
    answers = _answers(
        project_intent="Create a governed developer experience scaffold.",
        primary_domain="developer-experience",
        product_name="AI Lab VS Code Demo",
        product_slug="ai-lab-vscode-demo",
        env_prefix="",
        api_prefix="   ",
        tenant_header="x-tenant-id",
        locales=["en", "tr"],
        observability=True,
        agent_clients=None,
    )

    assert answers.env_prefix == "AI_LAB_VSCODE_DEMO_"
    assert answers.api_prefix == "/api/ai-lab-vscode-demo/v1"


def _blueprint() -> dict[str, object]:
    return project_blueprint_operation(
        project_intent="Audit internal payment controls with an offline LLM harness.",
        primary_domain="payments",
        product_name="Payment Controls",
        product_slug="payment-controls",
        backend_profile="python-fastapi",
        persistence_profile="sqlalchemy-alembic",
        locales=["tr", "en"],
        observability=False,
    )


def _metadata() -> ProjectMetadata:
    return ProjectMetadata.model_validate(_blueprint()["project_manifest"])


def test_blueprint_is_bounded_metadata_not_a_workspace_or_patch() -> None:
    result = _blueprint()
    assert result["ok"] is True
    encoded = json.dumps(result)
    assert "patch_set" not in encoded
    assert "target_dir" not in encoded
    assert "content" not in result["project_manifest"]
    metadata = ProjectMetadata.model_validate(result["project_manifest"])
    assert metadata.primary_domain == "payments"
    assert metadata.locales == ["tr", "en"]
    assert {item.authority for item in metadata.artifacts} == {"mandatory", "recommended"}
    assert len(encoded.encode()) < 256 * 1024


def test_generated_project_persists_and_exports_only_bounded_metadata(tmp_path: Path) -> None:
    target = tmp_path / "project"
    init_operation(
        str(target),
        project_intent="Audit internal payment controls with an offline LLM harness.",
        primary_domain="payments",
        product_slug="payment-controls",
        observability=False,
    )
    manifest_path = target / ".kt-scaffold/project-manifest.json"
    expected = ProjectMetadata.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    process = subprocess.run(
        ["python3", "scripts/export-project-metadata.py"],
        cwd=target,
        text=True,
        capture_output=True,
        check=True,
    )
    assert ProjectMetadata.model_validate_json(process.stdout) == expected
    assert "app/backend" not in process.stdout
    assert "password" not in process.stdout.lower()


def test_turkish_cli_alias_invokes_the_exact_same_local_operation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "project"
    init_operation(
        str(target),
        project_intent="Audit internal payment controls with an offline LLM harness.",
        primary_domain="payments",
        observability=False,
    )
    assert main(["rules", "--target-dir", str(target), "--scope", "governance"]) == 0
    english = capsys.readouterr().out
    assert main(["kurallar", "--target-dir", str(target), "--scope", "governance"]) == 0
    assert capsys.readouterr().out == english


def test_catalog_filters_and_artifact_fetch_is_explicit() -> None:
    mandatory = governance_catalog_operation(authority="mandatory")
    artifacts = mandatory["artifacts"]
    assert artifacts
    assert all(item["authority"] == "mandatory" for item in artifacts)
    assert all("content" not in item for item in artifacts)
    artifact_id = artifacts[0]["artifact_id"]
    fetched = governance_artifacts_get_operation([artifact_id])
    assert fetched["artifacts"][0]["artifact_id"] == artifact_id
    assert fetched["artifacts"][0]["content"].startswith("---\n")
    with pytest.raises(ValueError, match="unknown governance artifact"):
        governance_artifacts_get_operation(["rule:does-not-exist"])
    skills = governance_catalog_operation(kind="skill")["artifacts"]
    assert {item["language"] for item in skills} == {"en", "tr"}
    assert {item["artifact_id"] for item in skills} >= {"skill:kt-init", "skill:kt-baslat"}
    guidance = governance_catalog_operation(kind="guidance")["artifacts"]
    assert {item["artifact_id"] for item in guidance} == {"guidance:local-reconciliation"}
    selected = governance_artifacts_get_operation(
        ["skill:kt-baslat", "guidance:local-reconciliation"]
    )["artifacts"]
    assert "Argümanlar:" in selected[0]["content"]
    assert "workspace source" in selected[1]["content"]
    with pytest.raises(ValueError, match="at least one"):
        governance_artifacts_get_operation([])
    with pytest.raises(ValueError, match="must be unique"):
        governance_artifacts_get_operation([artifact_id, artifact_id])
    assert governance_catalog_operation(scope="schema")["artifacts"]


def test_current_metadata_has_no_update_items_and_proposal_is_deterministic() -> None:
    first = governance_update_check_operation(_metadata())
    second = governance_update_check_operation(_metadata())
    assert first == second
    proposal = GovernanceUpdateProposal.model_validate(first["proposal"])
    assert proposal.items == []
    assert proposal.unchanged == len(_metadata().artifacts)


def test_update_proposal_distinguishes_mandatory_recommended_and_project_owned() -> None:
    metadata = _metadata()
    mandatory = next(item for item in metadata.artifacts if item.authority == "mandatory")
    recommended = next(item for item in metadata.artifacts if item.authority == "recommended")
    local = GovernanceArtifactRef(
        artifact_id="guidance:local-risk-model",
        kind="guidance",
        authority="project-owned",
        version="1.0.0",
        sha256="a" * 64,
    )
    changed = metadata.model_copy(
        update={
            "governance_version": "0.0.1",
            "artifacts": [
                item.model_copy(update={"sha256": "0" * 64})
                if item.artifact_id in {mandatory.artifact_id, recommended.artifact_id}
                else item
                for item in metadata.artifacts
            ]
            + [local],
        }
    )
    proposal = GovernanceUpdateProposal.model_validate(
        governance_update_check_operation(changed)["proposal"]
    )
    indexed = {item.artifact.artifact_id: item for item in proposal.items}
    assert indexed[mandatory.artifact_id].action == "align"
    assert indexed[mandatory.artifact_id].required_behaviors
    assert indexed[recommended.artifact_id].action == "review"
    assert indexed[recommended.artifact_id].required_behaviors == []
    assert indexed[local.artifact_id].action == "preserve"


def test_unknown_central_artifact_cannot_be_disguised_as_local_state() -> None:
    metadata = _metadata()
    unknown = GovernanceArtifactRef(
        artifact_id="rule:unknown-central",
        kind="rule",
        authority="mandatory",
        version="1.0.0",
        sha256="b" * 64,
    )
    with pytest.raises(ValueError, match="unknown non-project-owned"):
        governance_update_check_operation(
            metadata.model_copy(update={"artifacts": [*metadata.artifacts, unknown]})
        )


def test_canonical_artifact_authority_cannot_be_downgraded_with_the_same_digest() -> None:
    metadata = _metadata()
    mandatory = next(item for item in metadata.artifacts if item.authority == "mandatory")
    downgraded = mandatory.model_copy(update={"authority": "project-owned"})
    altered = metadata.model_copy(
        update={
            "artifacts": [
                downgraded if item.artifact_id == mandatory.artifact_id else item
                for item in metadata.artifacts
            ]
        }
    )

    proposal = GovernanceUpdateProposal.model_validate(
        governance_update_check_operation(altered)["proposal"]
    )

    item = next(
        entry for entry in proposal.items if entry.artifact.artifact_id == mandatory.artifact_id
    )
    assert item.action == "align"
    assert item.artifact.authority == "mandatory"


def test_reconciliation_requires_every_mandatory_behavior_but_allows_local_wording() -> None:
    metadata = _metadata()
    mandatory = next(item for item in metadata.artifacts if item.authority == "mandatory")
    changed = metadata.model_copy(
        update={
            "artifacts": [
                item.model_copy(update={"sha256": "0" * 64})
                if item.artifact_id == mandatory.artifact_id
                else item
                for item in metadata.artifacts
            ]
        }
    )
    proposal = GovernanceUpdateProposal.model_validate(
        governance_update_check_operation(changed)["proposal"]
    )
    item = proposal.items[0]
    rejected = reconciliation_validate_operation(
        proposal,
        [
            ReconciliationDecision(
                artifact_id=mandatory.artifact_id,
                decision="deferred",
                rationale="Needs local review.",
            )
        ],
    )
    assert rejected["aligned"] is False
    adapted = reconciliation_validate_operation(
        proposal,
        [
            ReconciliationDecision(
                artifact_id=mandatory.artifact_id,
                decision="adapted",
                rationale="Kept the invariant in project terminology.",
                preserved_behaviors=item.required_behaviors,
            )
        ],
    )
    assert adapted["aligned"] is True
    assert adapted["receipt"]["provenance"] == "local-agent-attested"
    assert adapted["warnings"] == [
        "Reconciliation is an attestation, not remote workspace verification."
    ]


def test_reconciliation_rejects_duplicate_unknown_and_incomplete_decisions() -> None:
    metadata = _metadata()
    altered = metadata.model_copy(
        update={
            "artifacts": [
                item.model_copy(update={"sha256": "f" * 64}) for item in metadata.artifacts[:2]
            ]
        }
    )
    proposal = GovernanceUpdateProposal.model_validate(
        governance_update_check_operation(altered)["proposal"]
    )
    duplicate = ReconciliationDecision(
        artifact_id=proposal.items[0].artifact.artifact_id,
        decision="accepted",
        rationale="Accepted locally.",
    )
    with pytest.raises(ValueError, match="duplicate"):
        reconciliation_validate_operation(proposal, [duplicate, duplicate])
    with pytest.raises(ValueError, match="unknown proposal"):
        reconciliation_validate_operation(
            proposal,
            [duplicate.model_copy(update={"artifact_id": "rule:not-proposed"})],
        )
    incomplete = reconciliation_validate_operation(proposal, [duplicate])
    assert incomplete["aligned"] is False
    assert incomplete["unresolved"]
    tampered = proposal.model_copy(update={"unchanged": proposal.unchanged + 1})
    with pytest.raises(ValueError, match="does not match its proposal id"):
        reconciliation_validate_operation(tampered, [])


def test_project_metadata_rejects_duplicate_artifact_ids() -> None:
    metadata = _metadata()
    payload = metadata.model_dump(mode="json")
    payload["artifacts"].append(payload["artifacts"][0])
    with pytest.raises(ValueError, match="duplicate artifact ids"):
        ProjectMetadata.model_validate(payload)


def test_governance_proposal_rejects_duplicate_artifact_ids() -> None:
    proposal = GovernanceUpdateProposal.model_validate(
        governance_update_check_operation(
            _metadata().model_copy(
                update={
                    "artifacts": [
                        item.model_copy(update={"sha256": "0" * 64})
                        for item in _metadata().artifacts
                    ]
                }
            )
        )["proposal"]
    )
    payload = proposal.model_dump(mode="json")
    payload["items"].append(payload["items"][0])
    with pytest.raises(ValueError, match="duplicate artifact ids"):
        GovernanceUpdateProposal.model_validate(payload)
