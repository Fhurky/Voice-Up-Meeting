"""Exact tuple, governance, time, and revocation contracts for runtime admission records."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from kt_scaffold.agent_platform.admission import (
    ADMISSION_TTL_BOUNDS,
    AdmissionAction,
    AdmissionAuthorityScope,
    AdmissionPinSet,
    AdmissionReasonCode,
    AdmissionRecord,
    AdmissionRevocationChecker,
    AdmissionRevocationStatus,
    AdmissionVerificationError,
    CanonicalContractDigest,
    ClientId,
    ClientRuntimePin,
    ExecutionMode,
    ProjectionArtifactDigest,
    ProjectionPins,
    RevocationSource,
    RuntimeEvidencePins,
    SignedAdmissionRecord,
    VerifiedAdmissionReceipt,
    canonical_admission_bytes,
    canonical_admission_sha256,
    verify_admission_record,
)
from kt_scaffold.agent_platform.registry import (
    DetachedSignature,
    RiskTier,
    SignatureAlgorithm,
)

NOW = datetime(2026, 8, 18, 10, 0, 0, tzinfo=UTC)
AGENTS = (
    "application-security",
    "code-review",
    "requirements-scope",
    "test-automation",
)
CLIENT_PATHS = {
    ClientId.CODEX: ".codex/agents/{agent}.toml",
    ClientId.CLAUDE_CODE: ".claude/agents/{agent}.md",
    ClientId.GITHUB_COPILOT_VSCODE: ".github/agents/{agent}.agent.md",
    ClientId.CURSOR: ".cursor/agents/{agent}.md",
}


def _digest(number: int) -> str:
    return f"{number:064x}"


def _signature_value(content: bytes) -> str:
    return hashlib.sha256(b"test-admission-verifier\0" + content).hexdigest()


def _signature_for(record: AdmissionRecord) -> DetachedSignature:
    return DetachedSignature(
        key_id="key:admission-test",
        algorithm=SignatureAlgorithm.ED25519,
        value=_signature_value(canonical_admission_bytes(record)),
    )


def _signature_verifier(content: bytes, signature: DetachedSignature) -> bool:
    return signature.value == _signature_value(content)


def _scope(
    risk_tier: RiskTier,
    *,
    actions: tuple[AdmissionAction, ...] | None = None,
    execution_mode: ExecutionMode | None = None,
    resources: tuple[str, ...] = ("workspace:assigned",),
) -> AdmissionAuthorityScope:
    if actions is None:
        actions = (AdmissionAction.READ, AdmissionAction.SEARCH)
    if execution_mode is None:
        execution_mode = (
            ExecutionMode.ADVISORY if risk_tier == RiskTier.R3 else ExecutionMode.DIRECT
        )
    return AdmissionAuthorityScope(
        project_id="project:lab-sandbox",
        environment_id="environment:macos-arm64-lab",
        agent_ids=AGENTS,
        actions=actions,
        resources=resources,
        execution_mode=execution_mode,
    )


def _runtime_evidence(
    *,
    adapter_version: str = "1.0.0",
    model_revision: str = "2026-08-18",
    model_digest: str | None = None,
) -> RuntimeEvidencePins:
    return RuntimeEvidencePins(
        adapter_id="kt-scaffold:codex-adapter",
        adapter_version=adapter_version,
        adapter_digest=_digest(30),
        resolved_model_id="openai:gpt-5",
        model_revision=model_revision,
        model_digest=model_digest or _digest(31),
        tool_registry_digest=_digest(32),
        mcp_registry_digest=_digest(33),
        policy_digest=_digest(34),
        approval_policy_digest=_digest(35),
        identity_scope_digest=_digest(36),
        environment_digest=_digest(37),
        dataset_digest=_digest(38),
        conformance_evidence_digest=_digest(39),
    )


def _pins(
    *,
    risk_tier: RiskTier = RiskTier.R1,
    client_id: ClientId = ClientId.CODEX,
    client_version: str = "1.2.3",
    build_id: str = "codex-build:20260818.1",
    runtime_artifact_digest: str | None = None,
    scope: AdmissionAuthorityScope | None = None,
    runtime_evidence: RuntimeEvidencePins | None = None,
    contracts: tuple[CanonicalContractDigest, ...] | None = None,
    projection: ProjectionPins | None = None,
) -> AdmissionPinSet:
    if contracts is None:
        contracts = tuple(
            CanonicalContractDigest(agent_id=agent_id, sha256=_digest(index + 1))
            for index, agent_id in enumerate(AGENTS)
        )
    if projection is None:
        projection = ProjectionPins(
            lock_digest=_digest(10),
            artifacts=tuple(
                ProjectionArtifactDigest(
                    agent_id=agent_id,
                    relative_path=CLIENT_PATHS[client_id].format(agent=agent_id),
                    sha256=_digest(index + 20),
                )
                for index, agent_id in enumerate(AGENTS)
            ),
        )
    return AdmissionPinSet(
        client=ClientRuntimePin(
            client_id=client_id,
            version=client_version,
            build_id=build_id,
            runtime_artifact_digest=runtime_artifact_digest or _digest(11),
        ),
        canonical_contracts=contracts,
        projection=projection,
        runtime_evidence=runtime_evidence or _runtime_evidence(),
        risk_tier=risk_tier,
        owner="team:platform-governance-owner",
        authority_scope=scope or _scope(risk_tier),
    )


def _record(
    *,
    pins: AdmissionPinSet | None = None,
    risk_tier: RiskTier = RiskTier.R1,
    release_epoch: int = 7,
    issued_at: datetime = NOW - timedelta(hours=2),
    not_before: datetime = NOW - timedelta(hours=1),
    expires_at: datetime = NOW + timedelta(days=1),
    reviewers: tuple[str, ...] | None = None,
) -> AdmissionRecord:
    selected_pins = pins or _pins(risk_tier=risk_tier)
    if reviewers is None:
        reviewers = (
            ("team:agent-security-owner", "team:ai-risk-owner")
            if selected_pins.risk_tier in {RiskTier.R2, RiskTier.R3}
            else ("team:agent-security-owner",)
        )
    return AdmissionRecord(
        admission_id=f"admission:codex-{selected_pins.risk_tier.value.casefold()}-20260818",
        release_epoch=release_epoch,
        pins=selected_pins,
        reviewers=reviewers,
        issued_at=issued_at,
        not_before=not_before,
        expires_at=expires_at,
    )


def _signed(record: AdmissionRecord) -> SignedAdmissionRecord:
    return SignedAdmissionRecord(
        record=record,
        digest=canonical_admission_sha256(record),
        signature=_signature_for(record),
    )


def _revocation_checker(
    record: AdmissionRecord,
    *,
    epoch: int = 11,
    source: RevocationSource | None = None,
    source_digest: str | None = None,
    next_update_delta: timedelta | None = None,
    revoked: tuple[str, ...] = (),
    status_risk_tier: RiskTier | None = None,
    checked_at_offset: timedelta = timedelta(0),
) -> AdmissionRevocationChecker:
    if source is None:
        source = (
            RevocationSource.ONLINE
            if record.pins.risk_tier == RiskTier.R3
            else RevocationSource.SIGNED_STATE
        )
    if next_update_delta is None:
        next_update_delta = {
            RiskTier.R0: timedelta(hours=4),
            RiskTier.R1: timedelta(hours=4),
            RiskTier.R2: timedelta(minutes=15),
            RiskTier.R3: timedelta(0),
        }[record.pins.risk_tier]

    def checker(
        *, admission_id: str, admission_digest: str, checked_at: datetime
    ) -> AdmissionRevocationStatus:
        assert admission_id == record.admission_id
        assert admission_digest == canonical_admission_sha256(record)
        status_checked_at = checked_at + checked_at_offset
        return AdmissionRevocationStatus(
            source=source,
            source_digest=source_digest or _digest(50),
            risk_tier=status_risk_tier or record.pins.risk_tier,
            epoch=epoch,
            checked_at=status_checked_at,
            next_update=status_checked_at + next_update_delta,
            revoked_admission_digests=revoked,
        )

    return checker


def _resolve(
    record: AdmissionRecord,
    *,
    expected_pins: AdmissionPinSet | None = None,
    effective_risk_tier: RiskTier | None = None,
    now: datetime = NOW,
    revocation_checker: AdmissionRevocationChecker | None = None,
    previous_receipt: VerifiedAdmissionReceipt | None = None,
):
    return verify_admission_record(
        _signed(record),
        expected_admission_id=record.admission_id,
        expected_pins=expected_pins or record.pins,
        effective_risk_tier=effective_risk_tier or record.pins.risk_tier,
        now=now,
        signature_verifier=_signature_verifier,
        revocation_checker=revocation_checker or _revocation_checker(record),
        previous_receipt=previous_receipt,
    )


def _assert_code(
    exc: pytest.ExceptionInfo[AdmissionVerificationError], code: AdmissionReasonCode
) -> None:
    assert exc.value.code is code


def test_verified_receipt_binds_exact_tuple_and_exposes_scope_without_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _record()
    monkeypatch.chdir(tmp_path)

    verified = _resolve(record)
    receipt = verified.receipt

    assert verified.record == record
    assert receipt.record_digest == canonical_admission_sha256(record)
    assert receipt.pinset_digest == canonical_admission_sha256(record.pins)
    assert receipt.client_id == ClientId.CODEX
    assert receipt.client_version == "1.2.3"
    assert receipt.risk_tier == RiskTier.R1
    assert receipt.owner == "team:platform-governance-owner"
    assert receipt.authority_scope == record.pins.authority_scope
    assert receipt.admission_decision == "admitted"
    assert receipt.runtime_authority_effect == "requires-external-policy-intersection"
    assert receipt.activation_performed is False
    assert receipt.execution_performed is False
    assert receipt.revocation_epoch == 11
    assert receipt.checked_at == NOW
    assert not any(tmp_path.iterdir())


def test_digest_mismatch_is_rejected_before_signature_verification() -> None:
    record = _record()
    envelope = SignedAdmissionRecord(
        record=record,
        digest="f" * 64,
        signature=_signature_for(record),
    )
    calls = 0

    def verifier(content: bytes, signature: DetachedSignature) -> bool:
        del content, signature
        nonlocal calls
        calls += 1
        return True

    with pytest.raises(AdmissionVerificationError) as exc:
        verify_admission_record(
            envelope,
            expected_admission_id=record.admission_id,
            expected_pins=record.pins,
            effective_risk_tier=record.pins.risk_tier,
            now=NOW,
            signature_verifier=verifier,
            revocation_checker=_revocation_checker(record),
        )

    _assert_code(exc, AdmissionReasonCode.DIGEST_MISMATCH)
    assert calls == 0


@pytest.mark.parametrize("raises", (False, True))
def test_invalid_or_unavailable_signature_verifier_fails_closed(raises: bool) -> None:
    record = _record()

    def verifier(content: bytes, signature: DetachedSignature) -> bool:
        del content, signature
        if raises:
            raise RuntimeError("external verifier unavailable")
        return False

    with pytest.raises(AdmissionVerificationError) as exc:
        verify_admission_record(
            _signed(record),
            expected_admission_id=record.admission_id,
            expected_pins=record.pins,
            effective_risk_tier=record.pins.risk_tier,
            now=NOW,
            signature_verifier=verifier,
            revocation_checker=_revocation_checker(record),
        )
    _assert_code(exc, AdmissionReasonCode.SIGNATURE_INVALID)


@pytest.mark.parametrize(
    ("record", "code"),
    (
        (_record(not_before=NOW + timedelta(seconds=1)), AdmissionReasonCode.NOT_YET_VALID),
        (_record(expires_at=NOW), AdmissionReasonCode.EXPIRED),
    ),
)
def test_not_before_and_expiry_have_no_grace(
    record: AdmissionRecord, code: AdmissionReasonCode
) -> None:
    with pytest.raises(AdmissionVerificationError) as exc:
        _resolve(record)
    _assert_code(exc, code)


@pytest.mark.parametrize("risk_tier", tuple(RiskTier))
def test_risk_tier_ttl_accepts_exact_bound_and_rejects_one_second_more(
    risk_tier: RiskTier,
) -> None:
    not_before = NOW
    exact = _record(
        risk_tier=risk_tier,
        issued_at=NOW,
        not_before=not_before,
        expires_at=not_before + ADMISSION_TTL_BOUNDS[risk_tier],
    )
    assert exact.expires_at - exact.not_before == ADMISSION_TTL_BOUNDS[risk_tier]

    with pytest.raises(ValidationError, match="TTL"):
        _record(
            risk_tier=risk_tier,
            issued_at=NOW,
            not_before=not_before,
            expires_at=not_before + ADMISSION_TTL_BOUNDS[risk_tier] + timedelta(seconds=1),
        )


def test_exact_pin_and_effective_risk_mismatch_fail_closed() -> None:
    record = _record()
    different_pins = _pins(runtime_artifact_digest="f" * 64)

    with pytest.raises(AdmissionVerificationError) as pin_exc:
        _resolve(record, expected_pins=different_pins)
    _assert_code(pin_exc, AdmissionReasonCode.PIN_MISMATCH)

    with pytest.raises(AdmissionVerificationError) as risk_exc:
        _resolve(record, effective_risk_tier=RiskTier.R2)
    _assert_code(risk_exc, AdmissionReasonCode.RISK_TIER_MISMATCH)


def test_record_and_revocation_epoch_rollback_and_equivocation_fail_closed() -> None:
    current = _record(release_epoch=8)
    previous = _resolve(current, revocation_checker=_revocation_checker(current, epoch=12)).receipt

    older = _record(release_epoch=7)
    with pytest.raises(AdmissionVerificationError) as record_exc:
        _resolve(
            older,
            revocation_checker=_revocation_checker(older, epoch=13),
            previous_receipt=previous,
        )
    _assert_code(record_exc, AdmissionReasonCode.ROLLBACK)

    with pytest.raises(AdmissionVerificationError) as state_exc:
        _resolve(
            current,
            revocation_checker=_revocation_checker(current, epoch=11),
            previous_receipt=previous,
        )
    _assert_code(state_exc, AdmissionReasonCode.ROLLBACK)

    with pytest.raises(AdmissionVerificationError) as equivocation_exc:
        _resolve(
            current,
            revocation_checker=_revocation_checker(
                current,
                epoch=12,
                source_digest="f" * 64,
            ),
            previous_receipt=previous,
        )
    _assert_code(equivocation_exc, AdmissionReasonCode.ROLLBACK)


def test_revoked_digest_and_revocation_port_failures_are_denied() -> None:
    record = _record()
    with pytest.raises(AdmissionVerificationError) as revoked_exc:
        _resolve(
            record,
            revocation_checker=_revocation_checker(
                record,
                revoked=(canonical_admission_sha256(record),),
            ),
        )
    _assert_code(revoked_exc, AdmissionReasonCode.REVOKED)

    def unavailable(
        *, admission_id: str, admission_digest: str, checked_at: datetime
    ) -> AdmissionRevocationStatus:
        del admission_id, admission_digest, checked_at
        raise RuntimeError("status service unavailable")

    with pytest.raises(AdmissionVerificationError) as unavailable_exc:
        _resolve(record, revocation_checker=unavailable)
    _assert_code(unavailable_exc, AdmissionReasonCode.REVOCATION_REQUIRED)


@pytest.mark.parametrize(
    ("kwargs", "code"),
    (
        (
            {"next_update_delta": timedelta(hours=4, seconds=1)},
            AdmissionReasonCode.REVOCATION_STALE,
        ),
        ({"next_update_delta": timedelta(hours=-1)}, AdmissionReasonCode.REVOCATION_INVALID),
        ({"status_risk_tier": RiskTier.R2}, AdmissionReasonCode.REVOCATION_INVALID),
        ({"checked_at_offset": timedelta(seconds=-1)}, AdmissionReasonCode.REVOCATION_INVALID),
    ),
)
def test_stale_or_mismatched_revocation_status_fails_closed(
    kwargs: dict[str, Any], code: AdmissionReasonCode
) -> None:
    record = _record()
    checker = _revocation_checker(record, **kwargs)
    with pytest.raises((AdmissionVerificationError, ValidationError)) as caught:
        _resolve(record, revocation_checker=checker)
    if isinstance(caught.value, AdmissionVerificationError):
        assert caught.value.code is code
    else:
        assert code is AdmissionReasonCode.REVOCATION_INVALID


def test_r3_allows_only_non_reusable_online_read_only_advisory_admission() -> None:
    record = _record(risk_tier=RiskTier.R3)
    receipt = _resolve(record).receipt
    assert receipt.revocation_source == RevocationSource.ONLINE
    assert receipt.checked_at == receipt.next_update == NOW
    assert receipt.authority_scope.execution_mode == ExecutionMode.ADVISORY

    with pytest.raises(ValidationError, match="R3 direct execution"):
        _pins(
            risk_tier=RiskTier.R3,
            scope=_scope(RiskTier.R3, execution_mode=ExecutionMode.DIRECT),
        )
    with pytest.raises(ValidationError, match="R3 direct execution"):
        _pins(
            risk_tier=RiskTier.R3,
            scope=_scope(
                RiskTier.R3,
                actions=(AdmissionAction.READ, AdmissionAction.WORKSPACE_WRITE),
            ),
        )


def test_r3_rejects_cached_or_reusable_revocation_status() -> None:
    record = _record(risk_tier=RiskTier.R3)
    with pytest.raises(AdmissionVerificationError) as cached_exc:
        _resolve(
            record,
            revocation_checker=_revocation_checker(
                record,
                source=RevocationSource.SIGNED_STATE,
            ),
        )
    _assert_code(cached_exc, AdmissionReasonCode.REVOCATION_STALE)

    with pytest.raises(AdmissionVerificationError) as reusable_exc:
        _resolve(
            record,
            revocation_checker=_revocation_checker(
                record,
                next_update_delta=timedelta(seconds=1),
            ),
        )
    _assert_code(reusable_exc, AdmissionReasonCode.REVOCATION_STALE)


@pytest.mark.parametrize(
    "factory",
    (
        lambda: _pins(client_version="1.2.3-alpha.1"),
        lambda: _pins(client_version="latest"),
        lambda: _pins(build_id="codex-build:latest"),
        lambda: _pins(runtime_evidence=_runtime_evidence(adapter_version="1.0.0-rc.1")),
        lambda: _pins(runtime_evidence=_runtime_evidence(model_revision="latest")),
        lambda: _scope(RiskTier.R1, resources=("workspace:*",)),
    ),
)
def test_wildcard_latest_and_prerelease_identity_is_rejected(factory) -> None:
    with pytest.raises(ValidationError):
        factory()


def test_contract_projection_and_client_path_pins_are_exact() -> None:
    contracts = tuple(
        CanonicalContractDigest(agent_id=agent_id, sha256=_digest(index + 1))
        for index, agent_id in enumerate(reversed(AGENTS))
    )
    with pytest.raises(ValidationError, match="four canonical agents"):
        _pins(contracts=contracts)

    projection = ProjectionPins(
        lock_digest=_digest(10),
        artifacts=tuple(
            ProjectionArtifactDigest(
                agent_id=agent_id,
                relative_path=f".claude/agents/{agent_id}.md",
                sha256=_digest(index + 20),
            )
            for index, agent_id in enumerate(AGENTS)
        ),
    )
    with pytest.raises(ValidationError, match="exact admitted client"):
        _pins(client_id=ClientId.CODEX, projection=projection)


def test_owner_reviewer_separation_and_risk_reviewer_count_are_strict() -> None:
    with pytest.raises(ValidationError, match="separated"):
        _record(reviewers=("team:platform-governance-owner",))

    with pytest.raises(ValidationError, match="additional independent reviewers"):
        _record(risk_tier=RiskTier.R2, reviewers=("team:agent-security-owner",))


def test_raw_secret_and_unknown_authority_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="raw secret"):
        _pins(scope=_scope(RiskTier.R1, resources=("sk-super-secret-token",)))

    raw = _record().model_dump()
    raw["token"] = "".join(("raw-", "token"))
    with pytest.raises(ValidationError):
        AdmissionRecord.model_validate(raw)

    raw = _record().model_dump()
    raw["decision"] = "denied"
    with pytest.raises(ValidationError):
        AdmissionRecord.model_validate(raw)


def test_strict_models_reject_scalar_coercion_and_noncanonical_owner() -> None:
    raw = _record().model_dump()
    raw["release_epoch"] = "7"
    with pytest.raises(ValidationError):
        AdmissionRecord.model_validate(raw)

    raw_pins = _pins().model_dump()
    raw_pins["owner"] = "platform-owner"
    with pytest.raises(ValidationError):
        AdmissionPinSet.model_validate(raw_pins)


def test_revocation_port_must_return_strict_status_model() -> None:
    record = _record()

    def invalid_status(
        *, admission_id: str, admission_digest: str, checked_at: datetime
    ) -> AdmissionRevocationStatus:
        del admission_id, admission_digest, checked_at
        return cast(AdmissionRevocationStatus, {"epoch": 1})

    with pytest.raises(AdmissionVerificationError) as exc:
        _resolve(record, revocation_checker=invalid_status)
    _assert_code(exc, AdmissionReasonCode.REVOCATION_INVALID)
