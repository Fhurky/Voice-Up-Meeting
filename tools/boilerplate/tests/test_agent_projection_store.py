"""Inert projection storage, ownership, and disposable activation boundaries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from kt_scaffold.agent_platform.activation import (
    ConformanceGrantVerificationError,
    ConformanceWorkspaceGrant,
    SignedConformanceWorkspaceGrant,
    canonical_conformance_grant_bytes,
    canonical_conformance_grant_sha256,
    result_projection_digests,
    verify_conformance_workspace_grant,
)
from kt_scaffold.agent_platform.compiler import compile_agent_projections
from kt_scaffold.agent_platform.models import CompilationResult
from kt_scaffold.agent_platform.projection_store import (
    INERT_LOCK_PATH,
    AgentProjectionStoreError,
    inert_projection_path,
    materialize_conformance_client,
    render_inert_projections,
)
from kt_scaffold.agent_platform.registry import DetachedSignature, SignatureAlgorithm
from kt_scaffold.models import Answers
from kt_scaffold.project import project_init

LIVE_DISCOVERY_ROOTS = (
    ".codex/agents",
    ".claude/agents",
    ".github/agents",
    ".cursor/agents",
)
NOW = datetime(2026, 8, 18, 10, 0, 0, tzinfo=UTC)


def _verifier(content: bytes, signature: DetachedSignature) -> bool:
    return signature.value == hashlib.sha256(b"test-only\0" + content).hexdigest()


def _signed_conformance_grant(
    result: CompilationResult,
    client_id: str,
    environment_id: str,
) -> SignedConformanceWorkspaceGrant:
    grant = ConformanceWorkspaceGrant(
        grant_id="conformance-grant:test-1",
        nonce="test-nonce-00000001",
        client_id=client_id,
        risk_tier="R0",
        environment_id=environment_id,
        issuer="team:ai-governance",
        compiler_lock_sha256=result.lock_sha256,
        projections=result_projection_digests(result, client_id),
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=10),
    )
    content = canonical_conformance_grant_bytes(grant)
    signature = DetachedSignature(
        key_id="key:conformance-test",
        algorithm=SignatureAlgorithm.ED25519,
        value=hashlib.sha256(b"test-only\0" + content).hexdigest(),
    )
    return SignedConformanceWorkspaceGrant(
        grant=grant,
        digest=canonical_conformance_grant_sha256(grant),
        signature=signature,
    )


def test_inert_store_writes_all_four_clients_without_live_activation(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    result = compile_agent_projections()

    changes, drift = render_inert_projections(root, result, mode="write")
    checked, checked_drift = render_inert_projections(root, result, mode="check")

    assert len(result.artifacts) == 16
    assert len([item for item in changes if item.action == "create"]) == 17
    assert len(drift) == 17
    assert {item.action for item in checked} == {"skip"}
    assert checked_drift == []
    assert (root / INERT_LOCK_PATH).is_file()
    assert all(not (root / path).exists() for path in LIVE_DISCOVERY_ROOTS)
    for artifact in result.artifacts:
        inert = root / inert_projection_path(artifact.relative_path)
        assert inert.read_text(encoding="utf-8") == artifact.content


def test_inert_store_refuses_edited_generated_or_stale_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    full = compile_agent_projections()
    render_inert_projections(root, full, mode="write")
    edited_artifact = next(item for item in full.artifacts if item.client_id == "claude-code")
    edited_path = root / inert_projection_path(edited_artifact.relative_path)
    edited_path.write_text("user edit\n", encoding="utf-8")
    before_lock = (root / INERT_LOCK_PATH).read_bytes()

    subset = compile_agent_projections(client_ids=("codex",))
    changes, drift = render_inert_projections(root, subset, mode="write")

    assert any(item.path == edited_path.relative_to(root).as_posix() for item in changes)
    assert any(item["reason"] == "edited stale projection" for item in drift)
    assert edited_path.read_text(encoding="utf-8") == "user edit\n"
    assert (root / INERT_LOCK_PATH).read_bytes() == before_lock
    projection_root = root / ".kt-scaffold/agent-projections"
    assert sum(path.is_file() for path in projection_root.rglob("*")) == 17


def test_inert_store_deletes_only_unchanged_owned_stale_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    full = compile_agent_projections()
    render_inert_projections(root, full, mode="write")

    subset = compile_agent_projections(client_ids=("codex",))
    changes, _drift = render_inert_projections(root, subset, mode="write")
    lock = json.loads((root / INERT_LOCK_PATH).read_text(encoding="utf-8"))

    assert len([item for item in changes if item.action == "delete"]) == 12
    assert len(lock["artifacts"]) == 4
    assert all(
        (root / inert_projection_path(item.relative_path)).exists() for item in subset.artifacts
    )
    assert all(
        not (root / inert_projection_path(item.relative_path)).exists()
        for item in full.artifacts
        if item.client_id != "codex"
    )


def test_conformance_materialization_is_client_scoped_and_always_destroyed() -> None:
    result = compile_agent_projections()
    workspace: Path
    environment_id = "environment:disposable-test"
    authorization = _signed_conformance_grant(result, "codex", environment_id)
    consumed: set[str] = set()

    def consume(grant_id: str, nonce: str) -> bool:
        identity = f"{grant_id}:{nonce}"
        if identity in consumed:
            return False
        consumed.add(identity)
        return True

    with materialize_conformance_client(
        result,
        "codex",
        authorization=authorization,
        environment_id=environment_id,
        now=NOW,
        signature_verifier=_verifier,
        consume_grant=consume,
    ) as workspace:
        assert workspace.is_dir()
        assert len(list((workspace / ".codex/agents").glob("*.toml"))) == 4
        assert all(
            not (workspace / path).exists()
            for path in LIVE_DISCOVERY_ROOTS
            if path != ".codex/agents"
        )
        assert (workspace / ".kt-scaffold/PROJECTIONS.lock.json").is_file()

    assert not workspace.exists()
    with (
        pytest.raises(ValueError, match="already used or unavailable"),
        materialize_conformance_client(
            result,
            "codex",
            authorization=authorization,
            environment_id=environment_id,
            now=NOW,
            signature_verifier=_verifier,
            consume_grant=consume,
        ),
    ):
        pass


def test_conformance_materialization_rejects_a_preconstructed_verified_grant() -> None:
    result = compile_agent_projections(client_ids=("codex",))
    environment_id = "environment:disposable-test"
    envelope = _signed_conformance_grant(result, "codex", environment_id)
    verified = verify_conformance_workspace_grant(
        envelope,
        result=result,
        client_id="codex",
        environment_id=environment_id,
        now=NOW,
        signature_verifier=_verifier,
    )
    consumed = False

    def consume(grant_id: str, nonce: str) -> bool:
        nonlocal consumed
        consumed = bool(grant_id and nonce)
        return True

    with (
        pytest.raises(ConformanceGrantVerificationError, match="signed grant envelope"),
        materialize_conformance_client(
            result,
            "codex",
            authorization=cast(SignedConformanceWorkspaceGrant, verified),
            environment_id=environment_id,
            now=NOW,
            signature_verifier=_verifier,
            consume_grant=consume,
        ),
    ):
        pass

    assert consumed is False


def test_conformance_materialization_rejects_shadowed_signed_grant_payload() -> None:
    result = compile_agent_projections(client_ids=("codex",))
    environment_id = "environment:disposable-test"
    envelope = _signed_conformance_grant(result, "codex", environment_id)
    original = envelope.grant
    forged = original.model_copy(
        update={
            "expires_at": NOW + timedelta(minutes=20),
            "model_dump": lambda **_: original.model_dump(mode="python"),
        }
    )
    tampered_envelope = envelope.model_copy(update={"grant": forged})
    consumed = False

    def consume(grant_id: str, nonce: str) -> bool:
        nonlocal consumed
        consumed = bool(grant_id and nonce)
        return True

    with (
        pytest.raises(ConformanceGrantVerificationError, match="canonical signed grant"),
        materialize_conformance_client(
            result,
            "codex",
            authorization=tampered_envelope,
            environment_id=environment_id,
            now=NOW + timedelta(minutes=11),
            signature_verifier=_verifier,
            consume_grant=consume,
        ),
    ):
        pass

    assert consumed is False


def test_conformance_materialization_revalidates_model_copy_artifact_content() -> None:
    result = compile_agent_projections(client_ids=("codex",))
    environment_id = "environment:disposable-test"
    authorization = _signed_conformance_grant(result, "codex", environment_id)
    malicious = result.artifacts[0].model_copy(update={"content": "MALICIOUS\n"})
    tampered_result = result.model_copy(update={"artifacts": (malicious, *result.artifacts[1:])})
    consumed = False

    def consume(grant_id: str, nonce: str) -> bool:
        nonlocal consumed
        consumed = bool(grant_id and nonce)
        return True

    with (
        pytest.raises(AgentProjectionStoreError, match="failed validation"),
        materialize_conformance_client(
            tampered_result,
            "codex",
            authorization=authorization,
            environment_id=environment_id,
            now=NOW,
            signature_verifier=_verifier,
            consume_grant=consume,
        ),
    ):
        pass

    assert consumed is False


def test_project_init_manages_inert_projection_bundle_only(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    manifest = json.loads((target / ".kt-scaffold/manifest.json").read_text(encoding="utf-8"))

    assert INERT_LOCK_PATH in manifest["managed"]
    assert (
        len(
            [
                path
                for path in manifest["managed"]
                if path.startswith(".kt-scaffold/agent-projections/")
            ]
        )
        == 17
    )
    assert all(not (target / path).exists() for path in LIVE_DISCOVERY_ROOTS)
