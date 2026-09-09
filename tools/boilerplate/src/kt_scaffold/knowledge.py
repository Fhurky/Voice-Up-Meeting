"""Workspace-independent blueprint and governance knowledge-plane operations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, cast

from kt_scaffold import __version__
from kt_scaffold.corpus import generator_corpus_dir, load_rules, public_rule
from kt_scaffold.models import (
    Answers,
    ArtifactAuthority,
    ArtifactKind,
    GovernanceArtifactRef,
    GovernanceUpdateItem,
    GovernanceUpdateProposal,
    ProjectMetadata,
    ReconciliationDecision,
    RuleScope,
    ToolResult,
)
from kt_scaffold.render import COMMAND_SCOPES, COMMANDS, TURKISH_COMMANDS, render_skill

DIRECTORY_CONTRACT = [
    {"path": "specs/<domain>/PRDs/<capability>/", "purpose": "accepted product intent"},
    {"path": "app/backend/", "purpose": "profile-native backend implementation"},
    {"path": "app/frontend/", "purpose": "typed localized user interface"},
    {"path": "schema/", "purpose": "desired-state persistence authority"},
    {"path": "rules/", "purpose": "locally reconciled governance corpus"},
    {"path": "plans/", "purpose": "architecture exploration outside accepted PRDs"},
    {"path": "e2e/", "purpose": "permanent live acceptance scenarios"},
]


CanonicalArtifact = tuple[GovernanceArtifactRef, str, dict[str, Any]]


def _artifact_reference(
    artifact_id: str,
    kind: ArtifactKind,
    authority: ArtifactAuthority,
    content: str,
) -> GovernanceArtifactRef:
    return GovernanceArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        authority=authority,
        version=__version__,
        sha256=hashlib.sha256(content.encode()).hexdigest(),
    )


def _canonical_artifacts() -> dict[str, CanonicalArtifact]:
    root = generator_corpus_dir()
    artifacts: dict[str, CanonicalArtifact] = {}
    for rule in load_rules(root):
        content = rule.source.read_text(encoding="utf-8")
        artifact_id = f"rule:{rule.id}"
        reference = _artifact_reference(artifact_id, "rule", rule.authority, content)
        artifacts[artifact_id] = (reference, content, public_rule(rule))
    for command in COMMANDS:
        for language, cli in (("en", command.cli), ("tr", TURKISH_COMMANDS[command.cli][0])):
            content = render_skill(command, language=language)
            artifact_id = f"skill:kt-{cli}"
            reference = _artifact_reference(artifact_id, "skill", "recommended", content)
            title = command.description if language == "en" else TURKISH_COMMANDS[command.cli][1]
            artifacts[artifact_id] = (
                reference,
                content,
                {
                    "id": f"kt-{cli}",
                    "title": title,
                    "scope": COMMAND_SCOPES[command.cli],
                    "authority": "recommended",
                    "trigger": "on-demand",
                    "applies_to": [],
                    "priority": 100,
                    "clients": ["claude", "codex"],
                    "gate": command.name,
                    "language": language,
                },
            )
    guidance_root = Path(__file__).with_name("governance")
    for source in sorted(guidance_root.glob("*.md")):
        content = source.read_text(encoding="utf-8")
        artifact_id = f"guidance:{source.stem}"
        title = next(
            (line.removeprefix("# ") for line in content.splitlines() if line.startswith("# ")),
            source.stem.replace("-", " ").title(),
        )
        reference = _artifact_reference(artifact_id, "guidance", "mandatory", content)
        artifacts[artifact_id] = (
            reference,
            content,
            {
                "id": source.stem,
                "title": title,
                "scope": "governance",
                "authority": "mandatory",
                "trigger": "on-demand",
                "applies_to": [],
                "priority": 10,
                "clients": ["agents", "claude", "codex", "cursor"],
                "gate": "governance_update_check",
                "language": "en",
            },
        )
    return artifacts


def governance_digest(artifacts: Mapping[str, CanonicalArtifact] | None = None) -> str:
    """Digest every canonical rule, skill and guidance reference in stable order."""
    current = artifacts if artifacts is not None else _canonical_artifacts()
    digest = hashlib.sha256()
    for artifact_id, (reference, _content, _metadata) in sorted(current.items()):
        digest.update(artifact_id.encode())
        digest.update(b"\0")
        digest.update(reference.kind.encode())
        digest.update(b"\0")
        digest.update(reference.authority.encode())
        digest.update(b"\0")
        digest.update(reference.sha256.encode())
        digest.update(b"\0")
    return digest.hexdigest()


def project_metadata(answers: Answers) -> ProjectMetadata:
    canonical = _canonical_artifacts()
    artifacts = [item[0] for item in canonical.values()]
    return ProjectMetadata(
        blueprint_version=__version__,
        project_intent=answers.project_intent,
        primary_domain=answers.primary_domain,
        backend_profile=answers.backend_profile,
        persistence_profile=answers.persistence_profile,
        locales=answers.locales,
        governance_version=__version__,
        governance_digest=governance_digest(canonical),
        artifacts=artifacts,
    )


def project_blueprint_operation(**payload: Any) -> dict[str, object]:
    """Return architectural intent and inventory; never inspect or mutate a workspace."""
    answers = Answers.model_validate(payload)
    metadata = project_metadata(answers)
    result = ToolResult(
        ok=True,
        next_steps=[
            "Local agent creates and adapts the workspace from this blueprint.",
            "Persist project_manifest as .kt-scaffold/project-manifest.json.",
            "Run the locally selected walking skeleton and acceptance gates.",
        ],
    ).as_dict()
    result.update(
        {
            "project_manifest": metadata.model_dump(mode="json"),
            "architecture": {
                "delivery": "spec-first-domain-first",
                "dependency_direction": "delivery -> application -> domain",
                "local_agent_owns": [
                    "workspace creation and edits",
                    "implementation within the fixed Python/FastAPI profile",
                    "tests, local database and evidence",
                    "semantic reconciliation of governance updates",
                ],
                "mcp_owns": [
                    "blueprint intent",
                    "canonical governance artifacts",
                    "authority classification",
                    "versioned update proposals",
                ],
            },
            "directories": DIRECTORY_CONTRACT,
            "acceptance": [
                "accepted PRD precedes business implementation",
                "JWT plus RBAC baseline remains explicit",
                "desired-state schema owns generated migrations",
                "local quality gate and live scenario evidence are recorded",
            ],
        }
    )
    return result


def governance_catalog_operation(
    *,
    kind: ArtifactKind | None = None,
    authority: ArtifactAuthority | None = None,
    scope: RuleScope | None = None,
) -> dict[str, object]:
    artifacts = _canonical_artifacts()
    listed: list[dict[str, Any]] = []
    for reference, _content, metadata in artifacts.values():
        if kind and reference.kind != kind:
            continue
        if authority and reference.authority != authority:
            continue
        if scope and metadata["scope"] != scope:
            continue
        listed.append({**reference.model_dump(mode="json"), **metadata})
    result = ToolResult(ok=True).as_dict()
    result["artifacts"] = listed
    return result


def governance_artifacts_get_operation(ids: list[str]) -> dict[str, object]:
    if not ids:
        raise ValueError("at least one governance artifact id is required")
    if len(ids) != len(set(ids)):
        raise ValueError("governance artifact ids must be unique")
    artifacts = _canonical_artifacts()
    missing = sorted(set(ids) - set(artifacts))
    if missing:
        raise ValueError(f"unknown governance artifact ids: {', '.join(missing)}")
    result = ToolResult(ok=True).as_dict()
    result["artifacts"] = [
        {
            **artifacts[artifact_id][0].model_dump(mode="json"),
            **artifacts[artifact_id][2],
            "content": artifacts[artifact_id][1],
        }
        for artifact_id in ids
    ]
    return result


def _proposal_id(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def governance_update_check_operation(metadata: ProjectMetadata) -> dict[str, object]:
    canonical = _canonical_artifacts()
    current = {item.artifact_id: item for item in metadata.artifacts}
    items: list[GovernanceUpdateItem] = []
    unchanged = 0
    for artifact_id, (target, _content, public) in canonical.items():
        installed = current.get(artifact_id)
        if installed and installed == target:
            unchanged += 1
            continue
        action: Literal["add", "align", "review", "preserve", "deprecate"]
        if installed is None:
            action = "add"
        elif target.authority == "mandatory":
            action = "align"
        else:
            action = "review"
        required = [public["title"]] if target.authority == "mandatory" else []
        instruction = (
            "Preserve this required behavior; local wording and additional constraints may vary."
            if target.authority == "mandatory"
            else "Compare with the local copy and adapt, defer or reject with a recorded rationale."
        )
        items.append(
            GovernanceUpdateItem(
                artifact=target,
                action=action,
                intent=f"Align local governance with: {public['title']}",
                required_behaviors=required,
                local_instruction=instruction,
            )
        )
    for artifact_id, installed in current.items():
        if artifact_id not in canonical:
            if installed.authority != "project-owned":
                raise ValueError(
                    f"unknown non-project-owned artifact cannot be reconciled: {artifact_id}"
                )
            items.append(
                GovernanceUpdateItem(
                    artifact=installed,
                    action="preserve",
                    intent="Preserve project-owned local governance.",
                    local_instruction="The central MCP does not alter project-owned artifacts.",
                )
            )
    base: dict[str, object] = {
        "blueprint_id": metadata.blueprint_id,
        "from_governance_version": metadata.governance_version,
        "to_governance_version": __version__,
        "target_governance_digest": governance_digest(canonical),
        "items": [item.model_dump(mode="json") for item in items],
        "unchanged": unchanged,
    }
    proposal = GovernanceUpdateProposal(
        proposal_id=_proposal_id(base),
        blueprint_id=metadata.blueprint_id,
        from_governance_version=metadata.governance_version,
        to_governance_version=__version__,
        target_governance_digest=cast(str, base["target_governance_digest"]),
        items=items,
        unchanged=unchanged,
    )
    result = ToolResult(
        ok=True,
        next_steps=[
            "Fetch only proposal artifacts that the local agent needs to compare.",
            "Reconcile locally, run local validation, then record decisions.",
        ],
    ).as_dict()
    result["proposal"] = proposal.model_dump(mode="json")
    return result


def reconciliation_validate_operation(
    proposal: GovernanceUpdateProposal,
    decisions: list[ReconciliationDecision],
) -> dict[str, object]:
    proposal_payload: dict[str, object] = {
        "blueprint_id": proposal.blueprint_id,
        "from_governance_version": proposal.from_governance_version,
        "to_governance_version": proposal.to_governance_version,
        "target_governance_digest": proposal.target_governance_digest,
        "items": [item.model_dump(mode="json") for item in proposal.items],
        "unchanged": proposal.unchanged,
    }
    if proposal.proposal_id != _proposal_id(proposal_payload):
        raise ValueError("governance proposal content does not match its proposal id")
    expected = {item.artifact.artifact_id: item for item in proposal.items}
    supplied = {item.artifact_id: item for item in decisions}
    if len(supplied) != len(decisions):
        raise ValueError("reconciliation decisions contain duplicate artifact ids")
    unknown = sorted(set(supplied) - set(expected))
    if unknown:
        raise ValueError(f"decisions reference unknown proposal artifacts: {', '.join(unknown)}")
    unresolved: list[str] = []
    for artifact_id, item in expected.items():
        decision = supplied.get(artifact_id)
        if decision is None:
            unresolved.append(artifact_id)
            continue
        missing_mandatory_behavior = decision.decision == "adapted" and not set(
            item.required_behaviors
        ) <= set(decision.preserved_behaviors)
        if item.artifact.authority == "mandatory" and (
            decision.decision not in {"accepted", "adapted"} or missing_mandatory_behavior
        ):
            unresolved.append(artifact_id)
    receipt_payload: dict[str, object] = {
        "proposal_id": proposal.proposal_id,
        "decisions": [item.model_dump(mode="json") for item in decisions],
        "unresolved": sorted(unresolved),
    }
    result = ToolResult(
        ok=not unresolved,
        warnings=["Reconciliation is an attestation, not remote workspace verification."],
        next_steps=["Persist this receipt beside the local project manifest and run local gates."],
    ).as_dict()
    result.update(
        {
            "aligned": not unresolved,
            "unresolved": sorted(unresolved),
            "receipt": {
                **receipt_payload,
                "receipt_id": _proposal_id(receipt_payload),
                "provenance": "local-agent-attested",
            },
        }
    )
    return result
