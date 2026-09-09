"""Signed disposable-conformance grant contracts and fail-closed bindings."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from kt_scaffold.agent_platform.activation import (
    ActivationReasonCode,
    AgentActivationError,
    AgentActivationLock,
    ConformanceGrantReasonCode,
    ConformanceGrantVerificationError,
    ConformanceWorkspaceGrant,
    EffectiveRuntimeSnapshot,
    ProjectionDigest,
    SignedConformanceWorkspaceGrant,
    VerifiedConformanceWorkspaceGrant,
    activate_admitted_client,
    activation_lock_sha256,
    activation_state_path,
    assert_verified_grant_binding,
    canonical_conformance_grant_bytes,
    canonical_conformance_grant_sha256,
    consume_verified_grant,
    deactivate_client,
    effective_runtime_sha256,
    result_projection_digests,
    verify_conformance_workspace_grant,
)
from kt_scaffold.agent_platform.admission import (
    AdmissionAction,
    AdmissionAuthorityScope,
    AdmissionPinSet,
    AdmissionRecord,
    AdmissionRevocationChecker,
    AdmissionRevocationStatus,
    CanonicalContractDigest,
    ClientId,
    ClientRuntimePin,
    ExecutionMode,
    ProjectionArtifactDigest,
    ProjectionPins,
    RevocationSource,
    RuntimeEvidencePins,
    SignedAdmissionRecord,
    canonical_admission_bytes,
    canonical_admission_sha256,
    verify_admission_record,
)
from kt_scaffold.agent_platform.compiler import compile_agent_projections
from kt_scaffold.agent_platform.models import CompilationResult
from kt_scaffold.agent_platform.registry import (
    DetachedSignature,
    RiskTier,
    SignatureAlgorithm,
)
from kt_scaffold.models import Change

NOW = datetime(2026, 8, 18, 10, 0, 0, tzinfo=UTC)
ENVIRONMENT_ID = "environment:conformance-test"
PROJECT_ID = "project:activation-test"
ENVIRONMENT_DIGEST = "e" * 64
RUNTIME_DIGEST = "d" * 64
CANONICAL_AGENT_IDS = (
    "application-security",
    "code-review",
    "requirements-scope",
    "test-automation",
)


def _signature(content: bytes) -> DetachedSignature:
    return DetachedSignature(
        key_id="key:conformance-test",
        algorithm=SignatureAlgorithm.ED25519,
        value=hashlib.sha256(b"test-only\0" + content).hexdigest(),
    )


def _verifier(content: bytes, signature: DetachedSignature) -> bool:
    return signature.value == hashlib.sha256(b"test-only\0" + content).hexdigest()


def _grant(
    result: CompilationResult,
    *,
    client_id: str = "codex",
    environment_id: str = ENVIRONMENT_ID,
    issued_at: datetime = NOW - timedelta(minutes=1),
    expires_at: datetime = NOW + timedelta(minutes=10),
) -> ConformanceWorkspaceGrant:
    return ConformanceWorkspaceGrant(
        grant_id="conformance-grant:test-1",
        nonce="test-nonce-00000001",
        client_id=client_id,
        risk_tier="R0",
        environment_id=environment_id,
        issuer="team:ai-governance",
        compiler_lock_sha256=result.lock_sha256,
        projections=result_projection_digests(result, client_id),
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _envelope(grant: ConformanceWorkspaceGrant) -> SignedConformanceWorkspaceGrant:
    content = canonical_conformance_grant_bytes(grant)
    return SignedConformanceWorkspaceGrant(
        grant=grant,
        digest=canonical_conformance_grant_sha256(grant),
        signature=_signature(content),
    )


def _verify(
    result: CompilationResult,
    *,
    grant: ConformanceWorkspaceGrant | None = None,
    client_id: str = "codex",
    environment_id: str = ENVIRONMENT_ID,
) -> VerifiedConformanceWorkspaceGrant:
    selected = grant or _grant(result, client_id=client_id, environment_id=environment_id)
    return verify_conformance_workspace_grant(
        _envelope(selected),
        result=result,
        client_id=client_id,
        environment_id=environment_id,
        now=NOW,
        signature_verifier=_verifier,
    )


def _assert_code(
    caught: pytest.ExceptionInfo[ConformanceGrantVerificationError],
    code: ConformanceGrantReasonCode,
) -> None:
    assert caught.value.code is code


def test_verified_grant_binds_exact_compilation_without_admission() -> None:
    result = compile_agent_projections()
    verified = _verify(result)

    assert verified.client_id == "codex"
    assert verified.compiler_lock_sha256 == result.lock_sha256
    assert verified.projections == result_projection_digests(result, "codex")
    assert verified.persistent_activation is False
    assert verified.runtime_admission is False
    assert verified.verified_at == NOW
    assert canonical_conformance_grant_bytes(_grant(result)).endswith(b"\n")


@pytest.mark.parametrize("failure", ("digest", "signature", "verifier-error"))
def test_digest_and_external_signature_fail_closed(failure: str) -> None:
    result = compile_agent_projections()
    grant = _grant(result)
    envelope = _envelope(grant)
    verifier = _verifier
    if failure == "digest":
        envelope = envelope.model_copy(update={"digest": "f" * 64})
    elif failure == "signature":
        bad = envelope.signature.model_copy(update={"value": "f" * 64})
        envelope = envelope.model_copy(update={"signature": bad})
    else:

        def unavailable(content: bytes, signature: DetachedSignature) -> bool:
            del content, signature
            raise RuntimeError("external verifier unavailable")

        verifier = unavailable

    with pytest.raises(ConformanceGrantVerificationError) as caught:
        verify_conformance_workspace_grant(
            envelope,
            result=result,
            client_id="codex",
            environment_id=ENVIRONMENT_ID,
            now=NOW,
            signature_verifier=verifier,
        )

    expected = (
        ConformanceGrantReasonCode.DIGEST_MISMATCH
        if failure == "digest"
        else ConformanceGrantReasonCode.SIGNATURE_INVALID
    )
    _assert_code(caught, expected)


@pytest.mark.parametrize(
    ("issued_at", "expires_at", "code"),
    (
        (
            NOW + timedelta(seconds=1),
            NOW + timedelta(minutes=5),
            ConformanceGrantReasonCode.NOT_YET_VALID,
        ),
        (
            NOW - timedelta(minutes=5),
            NOW,
            ConformanceGrantReasonCode.EXPIRED,
        ),
    ),
)
def test_grant_window_has_no_grace(
    issued_at: datetime,
    expires_at: datetime,
    code: ConformanceGrantReasonCode,
) -> None:
    result = compile_agent_projections()
    grant = _grant(result, issued_at=issued_at, expires_at=expires_at)

    with pytest.raises(ConformanceGrantVerificationError) as caught:
        _verify(result, grant=grant)

    _assert_code(caught, code)


def test_ttl_path_and_unknown_fields_are_strict() -> None:
    result = compile_agent_projections()
    raw: dict[str, Any] = _grant(result).model_dump()
    raw["expires_at"] = raw["issued_at"] + timedelta(minutes=15, seconds=1)
    with pytest.raises(ValidationError, match="15-minute"):
        ConformanceWorkspaceGrant.model_validate(raw)

    with pytest.raises(ValidationError, match="normalized and relative"):
        ProjectionDigest(relative_path="../escape.toml", sha256="a" * 64)

    raw = _grant(result).model_dump()
    raw["workspace_fallback"] = True
    with pytest.raises(ValidationError):
        ConformanceWorkspaceGrant.model_validate(raw)


@pytest.mark.parametrize("mismatch", ("client", "environment", "lock", "projection"))
def test_exact_binding_mismatch_fails_closed(mismatch: str) -> None:
    result = compile_agent_projections()
    grant = _grant(result)
    client_id = "codex"
    environment_id = ENVIRONMENT_ID
    if mismatch == "client":
        client_id = "claude-code"
    elif mismatch == "environment":
        environment_id = "environment:different"
    elif mismatch == "lock":
        grant = grant.model_copy(update={"compiler_lock_sha256": "f" * 64})
    else:
        projections = list(grant.projections)
        projections[0] = projections[0].model_copy(update={"sha256": "f" * 64})
        grant = grant.model_copy(update={"projections": tuple(projections)})

    with pytest.raises(ConformanceGrantVerificationError) as caught:
        _verify(
            result,
            grant=grant,
            client_id=client_id,
            environment_id=environment_id,
        )

    _assert_code(caught, ConformanceGrantReasonCode.BINDING_MISMATCH)


def test_verified_grant_rechecks_expiry_and_requires_external_single_use_consumer() -> None:
    result = compile_agent_projections()
    verified = _verify(result)

    with pytest.raises(ConformanceGrantVerificationError) as expired:
        assert_verified_grant_binding(
            verified,
            result=result,
            client_id="codex",
            environment_id=ENVIRONMENT_ID,
            now=verified.expires_at,
        )
    _assert_code(expired, ConformanceGrantReasonCode.EXPIRED)

    consume_verified_grant(verified, lambda grant_id, nonce: bool(grant_id and nonce))
    with pytest.raises(ConformanceGrantVerificationError, match="already used or unavailable"):
        consume_verified_grant(verified, lambda grant_id, nonce: False)


def _admission_pins(
    result: CompilationResult,
    *,
    agent_ids: tuple[str, ...] = CANONICAL_AGENT_IDS,
    risk_tier: RiskTier = RiskTier.R0,
) -> AdmissionPinSet:
    artifacts = {
        item.agent_id: item for item in result.artifacts if item.client_id == ClientId.CODEX.value
    }
    canonical = tuple(
        CanonicalContractDigest(
            agent_id=agent_id,
            sha256=next(
                source.sha256
                for source in artifacts[agent_id].inputs
                if source.path == f"agents/{agent_id}/agent.yml"
            ),
        )
        for agent_id in CANONICAL_AGENT_IDS
    )
    projections = tuple(
        ProjectionArtifactDigest(
            agent_id=agent_id,
            relative_path=artifacts[agent_id].relative_path,
            sha256=artifacts[agent_id].sha256,
        )
        for agent_id in CANONICAL_AGENT_IDS
    )
    sample = artifacts[CANONICAL_AGENT_IDS[0]]
    return AdmissionPinSet(
        client=ClientRuntimePin(
            client_id=ClientId.CODEX,
            version="0.147.0",
            build_id="codex-build:stable",
            runtime_artifact_digest=RUNTIME_DIGEST,
        ),
        canonical_contracts=canonical,
        projection=ProjectionPins(lock_digest=result.lock_sha256, artifacts=projections),
        runtime_evidence=RuntimeEvidencePins(
            adapter_id=sample.adapter_id,
            adapter_version=sample.adapter_version,
            adapter_digest="a" * 64,
            resolved_model_id="model:approved",
            model_revision="revision:2026-08-18",
            model_digest="b" * 64,
            tool_registry_digest="c" * 64,
            mcp_registry_digest="d" * 64,
            policy_digest="e" * 64,
            approval_policy_digest="f" * 64,
            identity_scope_digest="1" * 64,
            environment_digest=ENVIRONMENT_DIGEST,
            dataset_digest="2" * 64,
            conformance_evidence_digest="3" * 64,
        ),
        risk_tier=risk_tier,
        owner="person:risk-owner",
        authority_scope=AdmissionAuthorityScope(
            project_id=PROJECT_ID,
            environment_id=ENVIRONMENT_ID,
            agent_ids=agent_ids,
            actions=(AdmissionAction.READ,),
            resources=("workspace:read",),
            execution_mode=ExecutionMode.ADVISORY,
        ),
    )


AdmissionAuthorization = tuple[
    SignedAdmissionRecord,
    AdmissionPinSet,
    AdmissionRevocationChecker,
]


def _signed_admission(
    result: CompilationResult,
    *,
    agent_ids: tuple[str, ...] = CANONICAL_AGENT_IDS,
    release_epoch: int = 3,
    risk_tier: RiskTier = RiskTier.R0,
    revocation_epoch: int = 7,
    revocation_source_digest: str = "4" * 64,
) -> AdmissionAuthorization:
    pins = _admission_pins(result, agent_ids=agent_ids, risk_tier=risk_tier)
    record = AdmissionRecord(
        admission_id="admission:activation-test",
        release_epoch=release_epoch,
        pins=pins,
        reviewers=("person:security-reviewer",),
        issued_at=NOW - timedelta(hours=1),
        not_before=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(days=1),
    )
    content = canonical_admission_bytes(record)
    envelope = SignedAdmissionRecord(
        record=record,
        digest=canonical_admission_sha256(record),
        signature=_signature(content),
    )

    def revocation(
        *, admission_id: str, admission_digest: str, checked_at: datetime
    ) -> AdmissionRevocationStatus:
        assert admission_id == record.admission_id
        assert admission_digest == canonical_admission_sha256(record)
        return AdmissionRevocationStatus(
            source=RevocationSource.SIGNED_STATE,
            source_digest=revocation_source_digest,
            risk_tier=risk_tier,
            epoch=revocation_epoch,
            checked_at=checked_at,
            next_update=checked_at + timedelta(hours=4),
            revoked_admission_digests=(),
        )

    return envelope, pins, revocation


def _effective_runtime(authorization: AdmissionAuthorization) -> EffectiveRuntimeSnapshot:
    _, pins, _ = authorization
    return EffectiveRuntimeSnapshot(client=pins.client, runtime_evidence=pins.runtime_evidence)


def _activate(
    root: Path,
    result: CompilationResult,
    authorization: AdmissionAuthorization,
    **kwargs: Any,
) -> tuple[list[Change], list[dict[str, str]], AgentActivationLock]:
    envelope, pins, revocation_checker = authorization
    return activate_admitted_client(
        root,
        result,
        envelope,
        expected_admission_id=kwargs.pop("expected_admission_id", envelope.record.admission_id),
        expected_pins=kwargs.pop("expected_pins", pins),
        effective_risk_tier=kwargs.pop("effective_risk_tier", pins.risk_tier),
        signature_verifier=kwargs.pop("signature_verifier", _verifier),
        revocation_checker=kwargs.pop("revocation_checker", revocation_checker),
        effective_runtime=kwargs.pop("effective_runtime", _effective_runtime(authorization)),
        project_id=kwargs.pop("project_id", PROJECT_ID),
        environment_id=kwargs.pop("environment_id", ENVIRONMENT_ID),
        now=kwargs.pop("now", NOW),
        **kwargs,
    )


def test_receipt_gated_activation_is_scoped_owned_and_reversible(tmp_path: Path) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(
        result,
        agent_ids=("application-security", "requirements-scope"),
    )

    changes, drift, state = _activate(tmp_path, result, authorization)

    assert len([item for item in changes if item.action == "create"]) == 3
    assert len(drift) == 3
    assert [item.agent_id for item in state.artifacts] == [
        "application-security",
        "requirements-scope",
    ]
    assert state.authority_intersection_required is True
    assert state.effective_runtime_sha256 == effective_runtime_sha256(
        _effective_runtime(authorization)
    )
    assert state.risk_tier is RiskTier.R0
    assert state.revocation_source is RevocationSource.SIGNED_STATE
    assert state.revocation_epoch == 7
    assert state.revocation_source_digest == "4" * 64
    assert (tmp_path / activation_state_path(ClientId.CODEX)).is_file()
    assert (tmp_path / ".codex/agents/application-security.toml").is_file()
    assert (tmp_path / ".codex/agents/requirements-scope.toml").is_file()
    assert not (tmp_path / ".codex/agents/code-review.toml").exists()

    with pytest.raises(AgentActivationError) as unbound_state:
        _activate(tmp_path, result, authorization, mode="check")
    assert unbound_state.value.code is ActivationReasonCode.STATE_INVALID

    with pytest.raises(AgentActivationError) as missing_receipt:
        _activate(
            tmp_path,
            result,
            authorization,
            previous_state_sha256=activation_lock_sha256(state),
            mode="check",
        )
    assert missing_receipt.value.code is ActivationReasonCode.AUTHORIZATION_INVALID

    wrong_receipt = state.admission_receipt.model_copy(
        update={"next_update": state.admission_receipt.next_update + timedelta(seconds=1)}
    )
    with pytest.raises(AgentActivationError) as mismatched_receipt:
        _activate(
            tmp_path,
            result,
            authorization,
            previous_state_sha256=activation_lock_sha256(state),
            previous_receipt=wrong_receipt,
            mode="check",
        )
    assert mismatched_receipt.value.code is ActivationReasonCode.AUTHORIZATION_INVALID

    checked, checked_drift, _ = _activate(
        tmp_path,
        result,
        authorization,
        previous_state_sha256=activation_lock_sha256(state),
        previous_receipt=state.admission_receipt,
        mode="check",
    )
    assert {item.action for item in checked} == {"skip"}
    assert checked_drift == []

    with pytest.raises(AgentActivationError) as wrong_state:
        deactivate_client(
            tmp_path,
            ClientId.CODEX,
            expected_state_sha256="f" * 64,
        )
    assert wrong_state.value.code is ActivationReasonCode.STATE_INVALID

    deleted, delete_drift = deactivate_client(
        tmp_path,
        ClientId.CODEX,
        expected_state_sha256=activation_lock_sha256(state),
    )
    assert len([item for item in deleted if item.action == "delete"]) == 3
    assert len(delete_drift) == 3
    assert not (tmp_path / ".codex/agents/application-security.toml").exists()
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()


def test_activation_refuses_unowned_edited_and_symlink_paths(tmp_path: Path) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)
    unowned = tmp_path / ".codex/agents/application-security.toml"
    unowned.parent.mkdir(parents=True)
    unowned.write_text("unowned\n", encoding="utf-8")

    with pytest.raises(AgentActivationError) as unowned_error:
        _activate(tmp_path, result, authorization)
    assert unowned_error.value.code is ActivationReasonCode.OWNERSHIP_CONFLICT
    assert unowned.read_text(encoding="utf-8") == "unowned\n"

    unowned.unlink()
    _, _, state = _activate(tmp_path, result, authorization)
    activated = tmp_path / ".codex/agents/application-security.toml"
    activated.write_text("edited\n", encoding="utf-8")
    with pytest.raises(AgentActivationError) as edited_error:
        deactivate_client(
            tmp_path,
            ClientId.CODEX,
            expected_state_sha256=activation_lock_sha256(state),
        )
    assert edited_error.value.code is ActivationReasonCode.OWNERSHIP_CONFLICT
    assert activated.read_text(encoding="utf-8") == "edited\n"

    outside = tmp_path / "outside"
    outside.mkdir()
    fresh = tmp_path / "symlink-project"
    fresh.mkdir()
    (fresh / ".codex").symlink_to(outside, target_is_directory=True)
    with pytest.raises(AgentActivationError) as symlink_error:
        _activate(fresh, result, authorization)
    assert symlink_error.value.code is ActivationReasonCode.STATE_INVALID


def test_reactivation_deletes_only_unchanged_owned_stale_agent(tmp_path: Path) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    full = _signed_admission(result)
    _, _, full_state = _activate(tmp_path, result, full)
    narrower = _signed_admission(
        result,
        agent_ids=("requirements-scope",),
        release_epoch=4,
    )

    changes, drift, state = _activate(
        tmp_path,
        result,
        narrower,
        previous_state_sha256=activation_lock_sha256(full_state),
        previous_receipt=full_state.admission_receipt,
    )

    assert [item.agent_id for item in state.artifacts] == ["requirements-scope"]
    assert len([item for item in changes if item.action == "delete"]) == 3
    assert len([item for item in drift if item["reason"] == "stale activated projection"]) == 3
    assert not (tmp_path / ".codex/agents/application-security.toml").exists()


@pytest.mark.parametrize(
    ("agent_ids", "release_epoch"),
    (
        (CANONICAL_AGENT_IDS, 3),
        (("requirements-scope",), 4),
    ),
)
def test_reactivation_rejects_release_rollback_or_same_epoch_rewrite(
    tmp_path: Path,
    agent_ids: tuple[str, ...],
    release_epoch: int,
) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    current = _signed_admission(result, release_epoch=4)
    _, _, current_state = _activate(tmp_path, result, current)
    replacement = _signed_admission(
        result,
        agent_ids=agent_ids,
        release_epoch=release_epoch,
    )

    with pytest.raises(AgentActivationError) as caught:
        _activate(
            tmp_path,
            result,
            replacement,
            previous_state_sha256=activation_lock_sha256(current_state),
            previous_receipt=current_state.admission_receipt,
        )

    assert caught.value.code is ActivationReasonCode.AUTHORIZATION_INVALID


@pytest.mark.parametrize(
    "replacement_kwargs",
    (
        {"release_epoch": 5, "revocation_epoch": 6},
        {
            "release_epoch": 5,
            "revocation_epoch": 7,
            "revocation_source_digest": "5" * 64,
        },
        {"release_epoch": 5, "revocation_epoch": 8, "risk_tier": RiskTier.R1},
    ),
)
def test_reactivation_rejects_revocation_or_risk_history_rollback(
    tmp_path: Path,
    replacement_kwargs: dict[str, Any],
) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    current = _signed_admission(result, release_epoch=4)
    _, _, current_state = _activate(tmp_path, result, current)
    replacement = _signed_admission(result, **replacement_kwargs)

    with pytest.raises(AgentActivationError) as caught:
        _activate(
            tmp_path,
            result,
            replacement,
            previous_state_sha256=activation_lock_sha256(current_state),
            previous_receipt=current_state.admission_receipt,
        )

    assert caught.value.code is ActivationReasonCode.AUTHORIZATION_INVALID


def test_activation_and_deactivation_roll_back_injected_partial_failure(tmp_path: Path) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)

    with pytest.raises(AgentActivationError):
        _activate(tmp_path, result, authorization, inject_failure_after=1)
    assert not (tmp_path / ".codex/agents/application-security.toml").exists()
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()

    _, _, state = _activate(tmp_path, result, authorization)
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    with pytest.raises(AgentActivationError):
        deactivate_client(
            tmp_path,
            ClientId.CODEX,
            expected_state_sha256=activation_lock_sha256(state),
            inject_failure_after=1,
        )
    after = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before


@pytest.mark.parametrize(
    "overrides",
    (
        {"project_id": "project:different"},
        {"environment_id": "environment:different"},
        {"now": NOW + timedelta(days=1)},
    ),
)
def test_activation_rechecks_external_scope_and_current_admission(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)

    with pytest.raises(AgentActivationError) as caught:
        _activate(tmp_path, result, authorization, **overrides)

    assert caught.value.code is ActivationReasonCode.AUTHORIZATION_INVALID
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()


@pytest.mark.parametrize(
    ("component", "field", "value"),
    (
        ("client", "client_id", ClientId.CLAUDE_CODE),
        ("client", "version", "0.148.0"),
        ("client", "build_id", "codex-build:different"),
        ("client", "runtime_artifact_digest", "9" * 64),
        ("runtime_evidence", "adapter_id", "adapter:different"),
        ("runtime_evidence", "adapter_version", "9.9.9"),
        ("runtime_evidence", "adapter_digest", "9" * 64),
        ("runtime_evidence", "resolved_model_id", "model:different"),
        ("runtime_evidence", "model_revision", "revision:different"),
        ("runtime_evidence", "model_digest", "9" * 64),
        ("runtime_evidence", "tool_registry_digest", "9" * 64),
        ("runtime_evidence", "mcp_registry_digest", "9" * 64),
        ("runtime_evidence", "policy_digest", "9" * 64),
        ("runtime_evidence", "approval_policy_digest", "9" * 64),
        ("runtime_evidence", "identity_scope_digest", "9" * 64),
        ("runtime_evidence", "environment_digest", "9" * 64),
        ("runtime_evidence", "dataset_digest", "9" * 64),
        ("runtime_evidence", "conformance_evidence_digest", "9" * 64),
    ),
)
def test_activation_rejects_every_effective_runtime_tuple_drift(
    tmp_path: Path,
    component: str,
    field: str,
    value: object,
) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)
    raw = _effective_runtime(authorization).model_dump()
    raw[component][field] = value
    effective_runtime = EffectiveRuntimeSnapshot.model_validate(raw)

    with pytest.raises(AgentActivationError) as caught:
        _activate(
            tmp_path,
            result,
            authorization,
            effective_runtime=effective_runtime,
        )

    assert caught.value.code is ActivationReasonCode.AUTHORIZATION_INVALID
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()


def test_activation_requires_complete_live_snapshot_and_reverifies_signature(
    tmp_path: Path,
) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)

    with pytest.raises(AgentActivationError) as missing_snapshot:
        _activate(
            tmp_path,
            result,
            authorization,
            effective_runtime=cast(EffectiveRuntimeSnapshot, None),
        )
    assert missing_snapshot.value.code is ActivationReasonCode.AUTHORIZATION_INVALID

    snapshot = _effective_runtime(authorization)
    shadowed_snapshot = snapshot.model_copy(
        update={"model_dump": lambda **_: snapshot.model_dump(mode="python")}
    )
    with pytest.raises(AgentActivationError) as invalid_snapshot:
        _activate(
            tmp_path,
            result,
            authorization,
            effective_runtime=shadowed_snapshot,
        )
    assert invalid_snapshot.value.code is ActivationReasonCode.AUTHORIZATION_INVALID

    envelope, pins, revocation_checker = authorization
    invalid_signature = envelope.signature.model_copy(update={"value": "9" * 64})
    tampered = envelope.model_copy(update={"signature": invalid_signature})
    with pytest.raises(AgentActivationError) as bad_signature:
        _activate(
            tmp_path,
            result,
            (tampered, pins, revocation_checker),
        )
    assert bad_signature.value.code is ActivationReasonCode.AUTHORIZATION_INVALID
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()


def test_activation_rejects_shadowed_signed_admission_payload(tmp_path: Path) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)
    envelope, pins, revocation_checker = authorization
    original = envelope.record
    forged = original.model_copy(
        update={
            "expires_at": NOW + timedelta(days=2),
            "model_dump": lambda **_: original.model_dump(mode="python"),
        }
    )
    tampered_envelope = envelope.model_copy(update={"record": forged})

    with pytest.raises(AgentActivationError) as caught:
        _activate(
            tmp_path,
            result,
            (tampered_envelope, pins, revocation_checker),
            now=NOW + timedelta(days=1, hours=1),
        )

    assert caught.value.code is ActivationReasonCode.AUTHORIZATION_INVALID
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()


def test_activation_rejects_shadowed_revocation_status(tmp_path: Path) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)
    envelope, pins, revocation_checker = authorization

    def shadowed_revocation(
        *, admission_id: str, admission_digest: str, checked_at: datetime
    ) -> AdmissionRevocationStatus:
        status = revocation_checker(
            admission_id=admission_id,
            admission_digest=admission_digest,
            checked_at=checked_at,
        )
        return status.model_copy(
            update={"model_dump": lambda **_: status.model_dump(mode="python")}
        )

    with pytest.raises(AgentActivationError) as caught:
        _activate(
            tmp_path,
            result,
            (envelope, pins, shadowed_revocation),
        )

    assert caught.value.code is ActivationReasonCode.AUTHORIZATION_INVALID
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()


def test_activation_revalidates_model_copy_artifact_content(tmp_path: Path) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)
    malicious = result.artifacts[0].model_copy(update={"content": "MALICIOUS\n"})
    tampered_result = result.model_copy(update={"artifacts": (malicious, *result.artifacts[1:])})

    with pytest.raises(AgentActivationError) as caught:
        _activate(tmp_path, tampered_result, authorization)

    assert caught.value.code is ActivationReasonCode.AUTHORIZATION_INVALID
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()
    assert not (tmp_path / ".codex/agents/application-security.toml").exists()


def test_activation_rejects_a_preconstructed_verified_admission(tmp_path: Path) -> None:
    result = compile_agent_projections(client_ids=("codex",))
    authorization = _signed_admission(result)
    envelope, pins, revocation_checker = authorization
    verified = verify_admission_record(
        envelope,
        expected_admission_id=envelope.record.admission_id,
        expected_pins=pins,
        effective_risk_tier=RiskTier.R0,
        now=NOW,
        signature_verifier=_verifier,
        revocation_checker=revocation_checker,
    )

    with pytest.raises(AgentActivationError) as caught:
        activate_admitted_client(
            tmp_path,
            result,
            cast(SignedAdmissionRecord, verified),
            expected_admission_id=envelope.record.admission_id,
            expected_pins=pins,
            effective_risk_tier=RiskTier.R0,
            signature_verifier=_verifier,
            revocation_checker=revocation_checker,
            effective_runtime=_effective_runtime(authorization),
            project_id=PROJECT_ID,
            environment_id=ENVIRONMENT_ID,
            now=NOW,
        )

    assert caught.value.code is ActivationReasonCode.AUTHORIZATION_INVALID
    assert not (tmp_path / activation_state_path(ClientId.CODEX)).exists()
