"""Fail-closed contracts for the external Agent Control Registry verifier port."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from kt_scaffold.agent_platform.registry import (
    DetachedSignature,
    OnlineRevocationChecker,
    OnlineRevocationStatus,
    RegistryProvenance,
    RegistryReasonCode,
    RegistryRecord,
    RegistryVerificationError,
    RevocationState,
    RiskTier,
    SignatureAlgorithm,
    SignedRegistryRecord,
    SignedRevocationState,
    VerifiedRegistryReceipt,
    VerifiedRegistryResolution,
    canonical_registry_bytes,
    canonical_registry_sha256,
    verify_registry_record,
)

NOW = datetime(2026, 8, 18, 10, 0, 0, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64


def _signature_value(content: bytes) -> str:
    return hashlib.sha256(b"test-verifier-only\0" + content).hexdigest()


def _signature_for(value: RegistryRecord | RevocationState) -> DetachedSignature:
    return DetachedSignature(
        key_id="key:registry-test",
        algorithm=SignatureAlgorithm.ED25519,
        value=_signature_value(canonical_registry_bytes(value)),
    )


def _signature_verifier(content: bytes, signature: DetachedSignature) -> bool:
    return signature.value == _signature_value(content)


def _record(
    *,
    risk_tier: RiskTier = RiskTier.R1,
    release_epoch: int = 7,
    reference: str = "tool:workspace-read",
    issued_at: datetime = NOW - timedelta(hours=1),
    expires_at: datetime = NOW + timedelta(days=1),
    payload: dict[str, Any] | None = None,
    publisher: str = "team:registry-release",
    reviewers: tuple[str, ...] = ("team:registry-review",),
) -> RegistryRecord:
    return RegistryRecord(
        reference=reference,
        release_epoch=release_epoch,
        version="1.2.3",
        owner="team:tool-platform",
        schema_digest=SHA_A,
        risk_tier=risk_tier,
        scopes=("workspace:read",),
        issued_at=issued_at,
        expires_at=expires_at,
        provenance=RegistryProvenance(
            source_digest=SHA_B,
            publisher=publisher,
            reviewers=reviewers,
            release_id="registry-release:2026-08-18",
        ),
        payload=payload or {"capability_handle": reference, "mode": "read-only"},
    )


def _signed_record(record: RegistryRecord) -> SignedRegistryRecord:
    return SignedRegistryRecord(
        record=record,
        digest=canonical_registry_sha256(record),
        signature=_signature_for(record),
    )


def _revocation(
    record: RegistryRecord,
    *,
    epoch: int = 11,
    issued_at: datetime = NOW - timedelta(minutes=1),
    next_update: datetime | None = None,
    revoked: tuple[str, ...] = (),
) -> SignedRevocationState:
    if next_update is None:
        next_update = issued_at + (
            timedelta(minutes=15) if record.risk_tier == RiskTier.R2 else timedelta(hours=4)
        )
    state = RevocationState(
        risk_tier=record.risk_tier,
        epoch=epoch,
        issued_at=issued_at,
        next_update=next_update,
        revoked_record_digests=revoked,
    )
    return SignedRevocationState(
        state=state,
        digest=canonical_registry_sha256(state),
        signature=_signature_for(state),
    )


def _resolve(
    record: RegistryRecord,
    *,
    now: datetime = NOW,
    signed_revocation: SignedRevocationState | None = None,
    online_checker: OnlineRevocationChecker | None = None,
    previous_receipt: VerifiedRegistryReceipt | None = None,
    expected_version: str | None = None,
    expected_schema_digest: str | None = None,
    requested_scopes: tuple[str, ...] | None = None,
    effective_risk_tier: RiskTier | None = None,
) -> VerifiedRegistryResolution:
    return verify_registry_record(
        _signed_record(record),
        expected_reference=record.reference,
        expected_version=expected_version if expected_version is not None else record.version,
        expected_schema_digest=(
            expected_schema_digest if expected_schema_digest is not None else record.schema_digest
        ),
        requested_scopes=requested_scopes if requested_scopes is not None else record.scopes,
        effective_risk_tier=(
            effective_risk_tier if effective_risk_tier is not None else record.risk_tier
        ),
        now=now,
        signature_verifier=_signature_verifier,
        signed_revocation=signed_revocation,
        online_revocation_checker=online_checker,
        previous_receipt=previous_receipt,
    )


def _assert_code(
    exc: pytest.ExceptionInfo[RegistryVerificationError], code: RegistryReasonCode
) -> None:
    assert exc.value.code is code


def test_signed_record_and_revocation_produce_content_bound_receipt() -> None:
    record = _record()
    revocation = _revocation(record)

    resolution = _resolve(record, signed_revocation=revocation)
    receipt = resolution.receipt

    assert resolution.record == record
    assert receipt.record_digest == canonical_registry_sha256(record)
    assert receipt.record_epoch == record.release_epoch
    assert receipt.revocation_state_digest == canonical_registry_sha256(revocation.state)
    assert receipt.revocation_epoch == revocation.state.epoch
    assert receipt.checked_at == NOW
    assert receipt.next_update == revocation.state.next_update
    assert receipt.revocation_source == "signed-state"
    assert receipt.signature_key_id == "key:registry-test"
    assert receipt.record_version == record.version
    assert receipt.schema_digest == record.schema_digest
    assert receipt.scopes == record.scopes
    assert receipt.authority_granted is False
    assert receipt.runtime_admission == "not-evaluated"
    assert receipt.evidence_scope == "registry-record-verification"
    assert canonical_registry_bytes(record).endswith(b"\n")


def test_declared_digest_is_checked_before_signature_verifier() -> None:
    record = _record()
    envelope = SignedRegistryRecord(
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

    with pytest.raises(RegistryVerificationError) as exc:
        verify_registry_record(
            envelope,
            expected_reference=record.reference,
            expected_version=record.version,
            expected_schema_digest=record.schema_digest,
            requested_scopes=record.scopes,
            effective_risk_tier=record.risk_tier,
            now=NOW,
            signature_verifier=verifier,
            signed_revocation=_revocation(record),
        )

    _assert_code(exc, RegistryReasonCode.DIGEST_MISMATCH)
    assert calls == 0


@pytest.mark.parametrize("raises", (False, True))
def test_invalid_or_unavailable_detached_signature_fails_closed(raises: bool) -> None:
    record = _record()

    def verifier(content: bytes, signature: DetachedSignature) -> bool:
        del content, signature
        if raises:
            raise RuntimeError("external verifier unavailable")
        return False

    with pytest.raises(RegistryVerificationError) as exc:
        verify_registry_record(
            _signed_record(record),
            expected_reference=record.reference,
            expected_version=record.version,
            expected_schema_digest=record.schema_digest,
            requested_scopes=record.scopes,
            effective_risk_tier=record.risk_tier,
            now=NOW,
            signature_verifier=verifier,
            signed_revocation=_revocation(record),
        )

    _assert_code(exc, RegistryReasonCode.SIGNATURE_INVALID)


@pytest.mark.parametrize(
    ("record", "code"),
    (
        (_record(issued_at=NOW + timedelta(seconds=1)), RegistryReasonCode.NOT_YET_VALID),
        (_record(expires_at=NOW), RegistryReasonCode.EXPIRED),
    ),
)
def test_record_validity_has_no_grace_period(
    record: RegistryRecord, code: RegistryReasonCode
) -> None:
    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(record, signed_revocation=_revocation(record))
    _assert_code(exc, code)


@pytest.mark.parametrize(
    ("risk_tier", "interval"),
    (
        (RiskTier.R0, timedelta(hours=4, seconds=1)),
        (RiskTier.R1, timedelta(hours=4, seconds=1)),
        (RiskTier.R2, timedelta(minutes=15, seconds=1)),
    ),
)
def test_signed_revocation_freshness_cannot_exceed_risk_bound(
    risk_tier: RiskTier, interval: timedelta
) -> None:
    record = _record(risk_tier=risk_tier)
    issued_at = NOW - timedelta(seconds=1)
    revocation = _revocation(
        record,
        issued_at=issued_at,
        next_update=issued_at + interval,
    )

    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(record, signed_revocation=revocation)
    _assert_code(exc, RegistryReasonCode.REVOCATION_STALE)


@pytest.mark.parametrize(
    ("risk_tier", "bound"),
    (
        (RiskTier.R0, timedelta(hours=4)),
        (RiskTier.R1, timedelta(hours=4)),
        (RiskTier.R2, timedelta(minutes=15)),
    ),
)
def test_signed_revocation_accepts_exact_risk_bound(risk_tier: RiskTier, bound: timedelta) -> None:
    record = _record(risk_tier=risk_tier)
    revocation = _revocation(record, issued_at=NOW, next_update=NOW + bound)

    resolution = _resolve(record, signed_revocation=revocation)

    assert resolution.receipt.next_update == NOW + bound


def test_signed_revocation_is_stale_at_next_update_without_grace() -> None:
    record = _record()
    revocation = _revocation(
        record,
        issued_at=NOW - timedelta(hours=1),
        next_update=NOW,
    )

    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(record, signed_revocation=revocation)
    _assert_code(exc, RegistryReasonCode.REVOCATION_STALE)


def test_revoked_record_digest_fails_closed() -> None:
    record = _record()
    revocation = _revocation(record, revoked=(canonical_registry_sha256(record),))

    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(record, signed_revocation=revocation)
    _assert_code(exc, RegistryReasonCode.REVOKED)


def test_r3_requires_a_non_reusable_online_check() -> None:
    record = _record(risk_tier=RiskTier.R3)

    def online_checker(
        *, reference: str, record_digest: str, checked_at: datetime
    ) -> OnlineRevocationStatus:
        assert reference == record.reference
        assert record_digest == canonical_registry_sha256(record)
        return OnlineRevocationStatus(
            risk_tier=RiskTier.R3,
            epoch=21,
            checked_at=checked_at,
            next_update=checked_at,
            revoked_record_digests=(),
        )

    resolution = _resolve(record, online_checker=online_checker)

    assert resolution.receipt.revocation_source == "online"
    assert resolution.receipt.revocation_epoch == 21
    assert resolution.receipt.checked_at == resolution.receipt.next_update == NOW


def test_r3_rejects_signed_state_and_reusable_online_status() -> None:
    record = _record(risk_tier=RiskTier.R3)
    with pytest.raises(RegistryVerificationError) as offline_exc:
        _resolve(record, signed_revocation=_revocation(record))
    _assert_code(offline_exc, RegistryReasonCode.REVOCATION_REQUIRED)

    def reusable_status(
        *, reference: str, record_digest: str, checked_at: datetime
    ) -> OnlineRevocationStatus:
        del reference, record_digest
        return OnlineRevocationStatus(
            risk_tier=RiskTier.R3,
            epoch=21,
            checked_at=checked_at,
            next_update=checked_at + timedelta(seconds=1),
            revoked_record_digests=(),
        )

    with pytest.raises(RegistryVerificationError) as reusable_exc:
        _resolve(record, online_checker=reusable_status)
    _assert_code(reusable_exc, RegistryReasonCode.REVOCATION_STALE)


def test_unavailable_online_revocation_port_fails_closed() -> None:
    record = _record(risk_tier=RiskTier.R3)

    def unavailable(
        *, reference: str, record_digest: str, checked_at: datetime
    ) -> OnlineRevocationStatus:
        del reference, record_digest, checked_at
        raise RuntimeError("network unavailable")

    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(record, online_checker=unavailable)
    _assert_code(exc, RegistryReasonCode.REVOCATION_REQUIRED)


def test_ambiguous_or_missing_revocation_authority_fails_without_workspace_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _record()
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agent-control-registry.json").write_text("untrusted workspace fallback\n")

    with pytest.raises(RegistryVerificationError) as missing_exc:
        _resolve(record)
    _assert_code(missing_exc, RegistryReasonCode.REVOCATION_REQUIRED)

    def online_checker(
        *, reference: str, record_digest: str, checked_at: datetime
    ) -> OnlineRevocationStatus:
        del reference, record_digest
        return OnlineRevocationStatus(
            risk_tier=RiskTier.R1,
            epoch=11,
            checked_at=checked_at,
            next_update=checked_at + timedelta(hours=4),
            revoked_record_digests=(),
        )

    with pytest.raises(RegistryVerificationError) as ambiguous_exc:
        _resolve(
            record,
            signed_revocation=_revocation(record),
            online_checker=online_checker,
        )
    _assert_code(ambiguous_exc, RegistryReasonCode.REVOCATION_REQUIRED)


def test_record_and_revocation_epoch_rollback_fail_closed() -> None:
    current = _record(release_epoch=8)
    previous = _resolve(current, signed_revocation=_revocation(current, epoch=12)).receipt

    older_record = _record(release_epoch=7)
    with pytest.raises(RegistryVerificationError) as record_exc:
        _resolve(
            older_record,
            signed_revocation=_revocation(older_record, epoch=13),
            previous_receipt=previous,
        )
    _assert_code(record_exc, RegistryReasonCode.ROLLBACK)

    with pytest.raises(RegistryVerificationError) as state_exc:
        _resolve(
            current,
            signed_revocation=_revocation(current, epoch=11),
            previous_receipt=previous,
        )
    _assert_code(state_exc, RegistryReasonCode.ROLLBACK)

    changed_same_epoch = _revocation(current, epoch=12, revoked=("f" * 64,))
    with pytest.raises(RegistryVerificationError) as equivocation_exc:
        _resolve(
            current,
            signed_revocation=changed_same_epoch,
            previous_receipt=previous,
        )
    _assert_code(equivocation_exc, RegistryReasonCode.ROLLBACK)


def test_risk_tier_change_requires_new_validation_chain() -> None:
    current = _record(risk_tier=RiskTier.R1)
    previous = _resolve(current, signed_revocation=_revocation(current)).receipt
    changed = _record(risk_tier=RiskTier.R2, release_epoch=8)

    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(
            changed,
            signed_revocation=_revocation(changed, epoch=12),
            previous_receipt=previous,
        )
    _assert_code(exc, RegistryReasonCode.RISK_TIER_CHANGED)


@pytest.mark.parametrize(
    ("overrides", "code"),
    (
        ({"expected_version": "latest"}, RegistryReasonCode.PIN_MISMATCH),
        ({"expected_version": "9.9.9"}, RegistryReasonCode.PIN_MISMATCH),
        ({"expected_schema_digest": "f" * 64}, RegistryReasonCode.PIN_MISMATCH),
        ({"requested_scopes": ("workspace:write",)}, RegistryReasonCode.SCOPE_MISMATCH),
        ({"requested_scopes": ()}, RegistryReasonCode.SCOPE_MISMATCH),
        ({"effective_risk_tier": RiskTier.R2}, RegistryReasonCode.RISK_TIER_MISMATCH),
    ),
)
def test_external_version_schema_scope_and_risk_pins_must_match_exactly(
    overrides: dict[str, Any], code: RegistryReasonCode
) -> None:
    record = _record()

    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(record, signed_revocation=_revocation(record), **overrides)
    _assert_code(exc, code)


@pytest.mark.parametrize(
    "payload",
    (
        {"token": "opaque"},
        {"tokens": ["opaque"]},
        {"secrets": ["opaque"]},
        {"Authorization": "opaque"},
        {"private-key": "opaque"},
        {"nested": {"../secret": "opaque"}},
        {"endpoint": "Bearer raw-token-value"},
        {"endpoint": "https://user:password@example.invalid/api"},
        {"value": "-----BEGIN PRIVATE KEY-----"},
    ),
)
def test_raw_secret_token_and_unsafe_payload_keys_are_rejected(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _record(payload=payload)


def test_symbolic_secret_broker_handle_is_allowed_without_raw_secret() -> None:
    record = _record(
        reference="secret:model-access",
        payload={
            "broker_handle": "secret:model-access",
            "metadata": {"rotation_policy": "broker-owned"},
        },
    )

    resolution = _resolve(record, signed_revocation=_revocation(record))

    assert resolution.record.payload["broker_handle"] == "secret:model-access"


def test_empty_payload_invalid_revocation_digest_and_missing_maker_checker_are_rejected() -> None:
    raw_record = _record().model_dump()
    raw_record["payload"] = {}
    with pytest.raises(ValidationError):
        RegistryRecord.model_validate(raw_record)

    with pytest.raises(ValidationError):
        RevocationState(
            risk_tier=RiskTier.R1,
            epoch=1,
            issued_at=NOW,
            next_update=NOW + timedelta(hours=1),
            revoked_record_digests=("not-a-digest",),
        )

    with pytest.raises(ValidationError, match="maker-checker"):
        _record(
            risk_tier=RiskTier.R2,
            publisher="team:same-owner",
            reviewers=("team:same-owner",),
        )


def test_strict_models_reject_coercion_unknown_fields_and_unsafe_signature_algorithm() -> None:
    record = _record()
    raw = record.model_dump()
    raw["release_epoch"] = "7"
    with pytest.raises(ValidationError):
        RegistryRecord.model_validate(raw)

    raw = record.model_dump()
    raw["workspace_fallback"] = True
    with pytest.raises(ValidationError):
        RegistryRecord.model_validate(raw)

    with pytest.raises(ValidationError):
        DetachedSignature.model_validate(
            {"key_id": "key:test", "algorithm": "none", "value": "a" * 64}
        )


def test_reference_mismatch_and_revocation_signature_digest_fail_closed() -> None:
    record = _record()
    with pytest.raises(RegistryVerificationError) as reference_exc:
        verify_registry_record(
            _signed_record(record),
            expected_reference="tool:isolated-test-observation",
            expected_version=record.version,
            expected_schema_digest=record.schema_digest,
            requested_scopes=record.scopes,
            effective_risk_tier=record.risk_tier,
            now=NOW,
            signature_verifier=_signature_verifier,
            signed_revocation=_revocation(record),
        )
    _assert_code(reference_exc, RegistryReasonCode.REFERENCE_MISMATCH)

    revocation = _revocation(record)
    bad_revocation = SignedRevocationState(
        state=revocation.state,
        digest="f" * 64,
        signature=revocation.signature,
    )
    with pytest.raises(RegistryVerificationError) as digest_exc:
        _resolve(record, signed_revocation=bad_revocation)
    _assert_code(digest_exc, RegistryReasonCode.DIGEST_MISMATCH)


@pytest.mark.parametrize(
    ("updates", "requested_scopes"),
    (
        ({"expires_at": NOW + timedelta(days=1)}, ("workspace:read",)),
        ({"scopes": ("workspace:write",)}, ("workspace:write",)),
    ),
)
def test_record_model_dump_shadow_cannot_bypass_signed_expiry_or_scope(
    updates: dict[str, object],
    requested_scopes: tuple[str, ...],
) -> None:
    signed_record = _signed_record(_record(expires_at=NOW))
    shadowed_record = signed_record.record.model_copy(
        update={**updates, "model_dump": signed_record.record.model_dump}
    )
    shadowed_envelope = signed_record.model_copy(update={"record": shadowed_record})

    with pytest.raises(RegistryVerificationError) as exc:
        verify_registry_record(
            shadowed_envelope,
            expected_reference=shadowed_record.reference,
            expected_version=shadowed_record.version,
            expected_schema_digest=shadowed_record.schema_digest,
            requested_scopes=requested_scopes,
            effective_risk_tier=shadowed_record.risk_tier,
            now=NOW,
            signature_verifier=_signature_verifier,
            signed_revocation=_revocation(shadowed_record),
        )

    _assert_code(exc, RegistryReasonCode.DIGEST_MISMATCH)


def test_signed_revocation_model_dump_shadow_cannot_replace_epoch_or_revoked_list() -> None:
    record = _record()
    record_digest = canonical_registry_sha256(record)
    signed_revocation = _revocation(record, epoch=10, revoked=(record_digest,))
    shadowed_state = signed_revocation.state.model_copy(
        update={
            "epoch": 99,
            "revoked_record_digests": (),
            "model_dump": signed_revocation.state.model_dump,
        }
    )
    shadowed_envelope = signed_revocation.model_copy(update={"state": shadowed_state})

    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(record, signed_revocation=shadowed_envelope)

    _assert_code(exc, RegistryReasonCode.DIGEST_MISMATCH)


def test_online_status_model_dump_shadow_cannot_replace_epoch_or_revoked_list() -> None:
    record = _record(risk_tier=RiskTier.R3)

    def checker(
        *, reference: str, record_digest: str, checked_at: datetime
    ) -> OnlineRevocationStatus:
        del reference
        signed_status = OnlineRevocationStatus(
            risk_tier=RiskTier.R3,
            epoch=10,
            checked_at=checked_at,
            next_update=checked_at,
            revoked_record_digests=(record_digest,),
        )
        return signed_status.model_copy(
            update={
                "epoch": 99,
                "revoked_record_digests": (),
                "model_dump": signed_status.model_dump,
            }
        )

    with pytest.raises(RegistryVerificationError) as exc:
        _resolve(record, online_checker=checker)

    _assert_code(exc, RegistryReasonCode.REVOCATION_INVALID)
