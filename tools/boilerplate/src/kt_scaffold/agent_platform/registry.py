"""Fail-closed verification port for Agent Control Registry records.

This module owns no signer, key material, trust root, network client, or registry storage. Callers
must inject those external trust decisions. A successful result means only that the injected
verifier and revocation port accepted the exact canonical bytes under the checks implemented here.
"""

from __future__ import annotations

import hashlib
import math
import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal, NoReturn, Protocol, cast

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from kt_scaffold.agent_platform.manifest import canonical_json

SHA256_PATTERN = r"^[0-9a-f]{64}$"
REFERENCE_PATTERN = (
    r"^(?:inference-profile|tool|mcp|egress|secret|approval-policy|eval):"
    r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
)
OWNER_PATTERN = r"^(?:team|person):[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
SAFE_IDENTIFIER_PATTERN = r"^[a-z][a-z0-9]*(?:[-.:/][a-z0-9]+)*$"
EXACT_VERSION_PATTERN = r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9]+(?:[.-][a-z0-9]+)*)?$"
SAFE_PAYLOAD_KEY = re.compile(r"^[a-z][a-z0-9]*(?:[_-][a-z0-9]+)*$")
RAW_SECRET_KEYS = frozenset(
    {
        "api_key",
        "api_keys",
        "apikey",
        "authorization",
        "bearer",
        "cookie",
        "credential",
        "credentials",
        "id_token",
        "password",
        "passwords",
        "passphrase",
        "private_key",
        "private_keys",
        "proxy_authorization",
        "refresh_token",
        "secret",
        "secrets",
        "secret_value",
        "set_cookie",
        "token",
        "tokens",
        "access_token",
    }
)
RAW_SECRET_SUFFIXES = ("_password", "_passphrase", "_private_key", "_secret", "_token")
RAW_SECRET_VALUES = (
    re.compile(r"(?i)^bearer\s+\S+"),
    re.compile(r"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----"),
    re.compile(r"(?i)^(?:sk|ghp|github_pat|xox[baprs])[-_][a-z0-9_-]{8,}$"),
    re.compile(r"^[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}$"),
    re.compile(r"^[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@", re.IGNORECASE),
)
REVOCATION_BOUNDS = {
    "R0": timedelta(hours=4),
    "R1": timedelta(hours=4),
    "R2": timedelta(minutes=15),
}


class RegistryModel(BaseModel):
    """Immutable Pydantic boundary with strict scalar and unknown-field handling."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RegistryReasonCode(StrEnum):
    DIGEST_MISMATCH = "AP_REGISTRY_DIGEST_MISMATCH"
    SIGNATURE_INVALID = "AP_REGISTRY_SIGNATURE_INVALID"
    REFERENCE_MISMATCH = "AP_REGISTRY_REFERENCE_MISMATCH"
    PIN_MISMATCH = "AP_REGISTRY_PIN_MISMATCH"
    SCOPE_MISMATCH = "AP_REGISTRY_SCOPE_MISMATCH"
    RISK_TIER_MISMATCH = "AP_REGISTRY_RISK_TIER_MISMATCH"
    NOT_YET_VALID = "AP_REGISTRY_NOT_YET_VALID"
    EXPIRED = "AP_REGISTRY_EXPIRED"
    REVOCATION_REQUIRED = "AP_REGISTRY_REVOCATION_REQUIRED"
    REVOCATION_INVALID = "AP_REGISTRY_REVOCATION_INVALID"
    REVOCATION_STALE = "AP_REGISTRY_REVOCATION_STALE"
    REVOKED = "AP_REGISTRY_REVOKED"
    ROLLBACK = "AP_REGISTRY_ROLLBACK"
    RISK_TIER_CHANGED = "AP_REGISTRY_RISK_TIER_CHANGED"


class RegistryVerificationError(ValueError):
    """Stable verification failure that is safe to route to a deny decision."""

    def __init__(self, code: RegistryReasonCode, message: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {message}")


class RiskTier(StrEnum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"


class SignatureAlgorithm(StrEnum):
    ED25519 = "ed25519"
    ECDSA_P256_SHA256 = "ecdsa-p256-sha256"
    RSA_PSS_SHA256 = "rsa-pss-sha256"


def _validate_timestamp(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("registry timestamps must be UTC")
    if value.microsecond:
        raise ValueError("registry timestamps must use whole seconds")
    return value


def _validate_payload(value: JsonValue, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if not SAFE_PAYLOAD_KEY.fullmatch(key):
                raise ValueError(f"unsafe registry payload key: {path}.{key}")
            normalized = key.replace("-", "_")
            if normalized in RAW_SECRET_KEYS or normalized.endswith(RAW_SECRET_SUFFIXES):
                raise ValueError(f"raw secret/token field is forbidden: {path}.{key}")
            _validate_payload(nested, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_payload(nested, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in RAW_SECRET_VALUES):
            raise ValueError(f"raw secret/token value is forbidden: {path}")
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"non-finite registry payload number is forbidden: {path}")


class RegistryProvenance(RegistryModel):
    source_digest: str = Field(pattern=SHA256_PATTERN)
    publisher: str = Field(pattern=OWNER_PATTERN)
    reviewers: tuple[str, ...] = Field(min_length=1)
    release_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)

    @model_validator(mode="after")
    def validate_reviewers(self) -> RegistryProvenance:
        if len(set(self.reviewers)) != len(self.reviewers):
            raise ValueError("registry reviewers must be unique")
        if any(re.fullmatch(OWNER_PATTERN, reviewer) is None for reviewer in self.reviewers):
            raise ValueError("registry reviewers must be canonical owner references")
        return self


class RegistryRecord(RegistryModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentControlRegistryRecord"] = "AgentControlRegistryRecord"
    reference: str = Field(pattern=REFERENCE_PATTERN)
    release_epoch: int = Field(ge=0)
    version: str = Field(pattern=EXACT_VERSION_PATTERN)
    owner: str = Field(pattern=OWNER_PATTERN)
    schema_digest: str = Field(pattern=SHA256_PATTERN)
    risk_tier: RiskTier
    scopes: tuple[str, ...] = Field(min_length=1)
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    provenance: RegistryProvenance
    payload: dict[str, JsonValue] = Field(min_length=1)

    @field_validator("issued_at", "expires_at")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def validate_record(self) -> RegistryRecord:
        if self.expires_at <= self.issued_at:
            raise ValueError("registry record expiry must be after issue time")
        if len(set(self.scopes)) != len(self.scopes):
            raise ValueError("registry scopes must be unique")
        if any(re.fullmatch(SAFE_IDENTIFIER_PATTERN, scope) is None for scope in self.scopes):
            raise ValueError("registry scopes must be bounded symbolic identifiers")
        if self.risk_tier in {RiskTier.R2, RiskTier.R3} and (
            self.provenance.publisher in self.provenance.reviewers
        ):
            raise ValueError("R2/R3 registry records require maker-checker separation")
        _validate_payload(self.payload)
        return self


class DetachedSignature(RegistryModel):
    key_id: str = Field(pattern=r"^(?:key|kms|sigstore):[a-z][a-z0-9]*(?:[._/-][a-z0-9]+)*$")
    algorithm: SignatureAlgorithm
    value: str = Field(pattern=r"^[A-Za-z0-9_-]{16,4096}$")


class SignedRegistryRecord(RegistryModel):
    record: RegistryRecord
    digest: str = Field(pattern=SHA256_PATTERN)
    signature: DetachedSignature


class RevocationState(RegistryModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentControlRegistryRevocationState"] = "AgentControlRegistryRevocationState"
    risk_tier: RiskTier
    epoch: int = Field(ge=0)
    issued_at: AwareDatetime
    next_update: AwareDatetime
    revoked_record_digests: tuple[str, ...]

    @field_validator("issued_at", "next_update")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def validate_state(self) -> RevocationState:
        if self.next_update <= self.issued_at:
            raise ValueError("revocation next_update must be after issued_at")
        if len(set(self.revoked_record_digests)) != len(self.revoked_record_digests):
            raise ValueError("revocation digests must be unique")
        if any(
            re.fullmatch(SHA256_PATTERN, digest) is None for digest in self.revoked_record_digests
        ):
            raise ValueError("revocation entries must be SHA-256 digests")
        return self


class SignedRevocationState(RegistryModel):
    state: RevocationState
    digest: str = Field(pattern=SHA256_PATTERN)
    signature: DetachedSignature


class OnlineRevocationStatus(RegistryModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentControlRegistryOnlineRevocationStatus"] = (
        "AgentControlRegistryOnlineRevocationStatus"
    )
    risk_tier: RiskTier
    epoch: int = Field(ge=0)
    checked_at: AwareDatetime
    next_update: AwareDatetime
    revoked_record_digests: tuple[str, ...]

    @field_validator("checked_at", "next_update")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def validate_status(self) -> OnlineRevocationStatus:
        if self.next_update < self.checked_at:
            raise ValueError("online revocation next_update cannot precede checked_at")
        if len(set(self.revoked_record_digests)) != len(self.revoked_record_digests):
            raise ValueError("online revocation digests must be unique")
        if any(
            re.fullmatch(SHA256_PATTERN, digest) is None for digest in self.revoked_record_digests
        ):
            raise ValueError("online revocation entries must be SHA-256 digests")
        return self


class DetachedSignatureVerifier(Protocol):
    """External verifier port; implementations own key resolution and trust policy."""

    def __call__(self, content: bytes, signature: DetachedSignature, /) -> bool: ...


class OnlineRevocationChecker(Protocol):
    """External online-status port; implementations own transport and server authentication."""

    def __call__(
        self,
        *,
        reference: str,
        record_digest: str,
        checked_at: datetime,
    ) -> OnlineRevocationStatus: ...


class VerifiedRegistryReceipt(RegistryModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentControlRegistryVerificationReceipt"] = (
        "AgentControlRegistryVerificationReceipt"
    )
    status: Literal["verified"] = "verified"
    evidence_scope: Literal["registry-record-verification"] = "registry-record-verification"
    authority_granted: Literal[False] = False
    runtime_admission: Literal["not-evaluated"] = "not-evaluated"
    reference: str = Field(pattern=REFERENCE_PATTERN)
    risk_tier: RiskTier
    record_digest: str = Field(pattern=SHA256_PATTERN)
    record_epoch: int = Field(ge=0)
    record_version: str = Field(pattern=EXACT_VERSION_PATTERN)
    schema_digest: str = Field(pattern=SHA256_PATTERN)
    scopes: tuple[str, ...] = Field(min_length=1)
    record_expires_at: AwareDatetime
    signature_key_id: str
    signature_algorithm: SignatureAlgorithm
    revocation_source: Literal["signed-state", "online"]
    revocation_state_digest: str = Field(pattern=SHA256_PATTERN)
    revocation_epoch: int = Field(ge=0)
    checked_at: AwareDatetime
    next_update: AwareDatetime

    @field_validator("record_expires_at", "checked_at", "next_update")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _validate_timestamp(value)


class VerifiedRegistryResolution(RegistryModel):
    record: RegistryRecord
    receipt: VerifiedRegistryReceipt


_BOUNDARY_MODEL_TYPES: tuple[type[RegistryModel], ...] = (
    RegistryProvenance,
    RegistryRecord,
    DetachedSignature,
    SignedRegistryRecord,
    RevocationState,
    SignedRevocationState,
    OnlineRevocationStatus,
    VerifiedRegistryReceipt,
    VerifiedRegistryResolution,
)


def _copy_declared_value(value: object, *, seen: set[int]) -> object:
    if isinstance(value, RegistryModel):
        return _reconstruct_registry_model(value, seen=seen)
    if isinstance(value, dict):
        if type(value) is not dict:
            raise ValueError("registry boundary mappings must use the built-in dict type")
        identity = id(value)
        if identity in seen:
            raise ValueError("registry boundary values must not contain cycles")
        seen.add(identity)
        try:
            mapping = cast(dict[object, object], value)
            return {key: _copy_declared_value(nested, seen=seen) for key, nested in mapping.items()}
        finally:
            seen.remove(identity)
    if isinstance(value, list):
        if type(value) is not list:
            raise ValueError("registry boundary lists must use the built-in list type")
        identity = id(value)
        if identity in seen:
            raise ValueError("registry boundary values must not contain cycles")
        seen.add(identity)
        try:
            return [_copy_declared_value(nested, seen=seen) for nested in cast(list[object], value)]
        finally:
            seen.remove(identity)
    if isinstance(value, tuple):
        if type(value) is not tuple:
            raise ValueError("registry boundary tuples must use the built-in tuple type")
        identity = id(value)
        if identity in seen:
            raise ValueError("registry boundary values must not contain cycles")
        seen.add(identity)
        try:
            return tuple(
                _copy_declared_value(nested, seen=seen)
                for nested in cast(tuple[object, ...], value)
            )
        finally:
            seen.remove(identity)
    return value


def _reconstruct_registry_model(
    value: RegistryModel,
    *,
    seen: set[int],
) -> RegistryModel:
    model_type = type(value)
    if model_type not in _BOUNDARY_MODEL_TYPES:
        raise ValueError("registry boundary requires an exact supported model type")
    raw = cast(dict[str, object], object.__getattribute__(value, "__dict__"))
    declared_fields = set(model_type.model_fields)
    if type(raw) is not dict or set(raw) != declared_fields:
        raise ValueError("registry boundary contains missing or undeclared instance fields")
    identity = id(value)
    if identity in seen:
        raise ValueError("registry boundary values must not contain cycles")
    seen.add(identity)
    try:
        declared = {
            name: _copy_declared_value(raw[name], seen=seen) for name in model_type.model_fields
        }
    finally:
        seen.remove(identity)
    return model_type.model_validate(declared)


def _reconstruct_as[RegistryModelT: RegistryModel](
    value: object,
    expected_type: type[RegistryModelT],
) -> RegistryModelT:
    if type(value) is not expected_type:
        raise ValueError("registry boundary model type does not match the declared contract")
    reconstructed = _reconstruct_registry_model(cast(RegistryModel, value), seen=set())
    return cast(RegistryModelT, reconstructed)


def canonical_registry_bytes(value: RegistryModel) -> bytes:
    """Serialize a strict registry model with the repository's canonical JSON profile."""

    reconstructed = _reconstruct_registry_model(value, seen=set())
    serialized = BaseModel.model_dump(reconstructed, mode="json")
    return canonical_json(serialized).encode("utf-8")


def canonical_registry_sha256(value: RegistryModel) -> str:
    return hashlib.sha256(canonical_registry_bytes(value)).hexdigest()


def _fail(code: RegistryReasonCode, message: str) -> NoReturn:
    raise RegistryVerificationError(code, message)


def _verify_signature(
    value: RegistryModel,
    *,
    declared_digest: str,
    signature: DetachedSignature,
    verifier: DetachedSignatureVerifier,
    subject: str,
) -> str:
    content = canonical_registry_bytes(value)
    actual_digest = hashlib.sha256(content).hexdigest()
    if actual_digest != declared_digest:
        _fail(RegistryReasonCode.DIGEST_MISMATCH, f"{subject} digest does not match content")
    try:
        verified = verifier(content, signature)
    except Exception:
        _fail(RegistryReasonCode.SIGNATURE_INVALID, f"{subject} signature verifier failed")
    if verified is not True:
        _fail(RegistryReasonCode.SIGNATURE_INVALID, f"{subject} signature is not verified")
    return actual_digest


def _normalize_now(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        _fail(RegistryReasonCode.REVOCATION_INVALID, "verification time must be timezone-aware")
    normalized = now.astimezone(UTC)
    if normalized.microsecond:
        _fail(RegistryReasonCode.REVOCATION_INVALID, "verification time must use whole seconds")
    return normalized


def _validate_freshness(
    *,
    risk_tier: RiskTier,
    checked_at: datetime,
    issued_at: datetime,
    next_update: datetime,
) -> None:
    if issued_at > checked_at:
        _fail(RegistryReasonCode.REVOCATION_INVALID, "revocation evidence is not yet valid")
    if checked_at >= next_update:
        _fail(RegistryReasonCode.REVOCATION_STALE, "revocation evidence is stale")
    bound = REVOCATION_BOUNDS[risk_tier.value]
    if next_update - issued_at > bound:
        _fail(RegistryReasonCode.REVOCATION_STALE, "revocation freshness exceeds risk bound")


def _signed_revocation(
    envelope: SignedRevocationState,
    *,
    record: RegistryRecord,
    record_digest: str,
    checked_at: datetime,
    verifier: DetachedSignatureVerifier,
) -> tuple[str, int, datetime]:
    try:
        safe_envelope = _reconstruct_as(envelope, SignedRevocationState)
    except Exception:
        _fail(
            RegistryReasonCode.DIGEST_MISMATCH,
            "revocation state envelope is not an exact validated contract",
        )
    state = safe_envelope.state
    if state.risk_tier != record.risk_tier:
        _fail(RegistryReasonCode.REVOCATION_INVALID, "revocation risk tier does not match record")
    digest = _verify_signature(
        state,
        declared_digest=safe_envelope.digest,
        signature=safe_envelope.signature,
        verifier=verifier,
        subject="revocation state",
    )
    _validate_freshness(
        risk_tier=record.risk_tier,
        checked_at=checked_at,
        issued_at=state.issued_at,
        next_update=state.next_update,
    )
    if record_digest in state.revoked_record_digests:
        _fail(RegistryReasonCode.REVOKED, "registry record digest is revoked")
    return digest, state.epoch, state.next_update


def _online_revocation(
    checker: OnlineRevocationChecker,
    *,
    record: RegistryRecord,
    record_digest: str,
    checked_at: datetime,
) -> tuple[str, int, datetime]:
    try:
        status = checker(
            reference=record.reference,
            record_digest=record_digest,
            checked_at=checked_at,
        )
    except Exception:
        _fail(RegistryReasonCode.REVOCATION_REQUIRED, "online revocation check failed")
    try:
        safe_status = _reconstruct_as(status, OnlineRevocationStatus)
    except Exception:
        _fail(RegistryReasonCode.REVOCATION_INVALID, "online checker returned an invalid status")
    if safe_status.risk_tier != record.risk_tier:
        _fail(RegistryReasonCode.REVOCATION_INVALID, "online risk tier does not match record")
    if safe_status.checked_at != checked_at:
        _fail(RegistryReasonCode.REVOCATION_INVALID, "online check is not bound to this resolution")
    if record.risk_tier == RiskTier.R3:
        if safe_status.next_update != checked_at:
            _fail(RegistryReasonCode.REVOCATION_STALE, "R3 online status must not be reusable")
    else:
        _validate_freshness(
            risk_tier=record.risk_tier,
            checked_at=checked_at,
            issued_at=safe_status.checked_at,
            next_update=safe_status.next_update,
        )
    if record_digest in safe_status.revoked_record_digests:
        _fail(RegistryReasonCode.REVOKED, "registry record digest is revoked")
    return (
        canonical_registry_sha256(safe_status),
        safe_status.epoch,
        safe_status.next_update,
    )


def verify_registry_record(
    envelope: SignedRegistryRecord,
    *,
    expected_reference: str,
    expected_version: str,
    expected_schema_digest: str,
    requested_scopes: tuple[str, ...],
    effective_risk_tier: RiskTier,
    now: datetime,
    signature_verifier: DetachedSignatureVerifier,
    signed_revocation: SignedRevocationState | None = None,
    online_revocation_checker: OnlineRevocationChecker | None = None,
    previous_receipt: VerifiedRegistryReceipt | None = None,
) -> VerifiedRegistryResolution:
    """Verify one exact record without consulting workspace files or implicit fallback state."""

    try:
        safe_envelope = _reconstruct_as(envelope, SignedRegistryRecord)
    except Exception:
        _fail(
            RegistryReasonCode.DIGEST_MISMATCH,
            "registry record envelope is not an exact validated contract",
        )
    record = safe_envelope.record
    checked_at = _normalize_now(now)
    if not isinstance(expected_reference, str):
        _fail(RegistryReasonCode.REFERENCE_MISMATCH, "expected reference must be a string")
    if record.reference != expected_reference:
        _fail(
            RegistryReasonCode.REFERENCE_MISMATCH,
            "resolved reference is not the requested reference",
        )
    if (
        not isinstance(expected_version, str)
        or re.fullmatch(EXACT_VERSION_PATTERN, expected_version) is None
    ):
        _fail(RegistryReasonCode.PIN_MISMATCH, "expected version is not an exact version pin")
    if record.version != expected_version:
        _fail(RegistryReasonCode.PIN_MISMATCH, "registry record version does not match pin")
    if (
        not isinstance(expected_schema_digest, str)
        or re.fullmatch(SHA256_PATTERN, expected_schema_digest) is None
    ):
        _fail(RegistryReasonCode.PIN_MISMATCH, "expected schema digest is not a SHA-256 pin")
    if record.schema_digest != expected_schema_digest:
        _fail(RegistryReasonCode.PIN_MISMATCH, "registry schema digest does not match pin")
    if (
        not isinstance(requested_scopes, tuple)
        or not all(isinstance(scope, str) for scope in requested_scopes)
        or len(set(requested_scopes)) != len(requested_scopes)
        or any(re.fullmatch(SAFE_IDENTIFIER_PATTERN, scope) is None for scope in requested_scopes)
        or record.scopes != requested_scopes
    ):
        _fail(
            RegistryReasonCode.SCOPE_MISMATCH,
            "registry scopes must exactly match the bounded request",
        )
    if not isinstance(effective_risk_tier, RiskTier) or record.risk_tier != effective_risk_tier:
        _fail(
            RegistryReasonCode.RISK_TIER_MISMATCH,
            "registry risk tier does not match the externally evaluated tier",
        )
    if record.issued_at > checked_at:
        _fail(RegistryReasonCode.NOT_YET_VALID, "registry record is not yet valid")
    if checked_at >= record.expires_at:
        _fail(RegistryReasonCode.EXPIRED, "registry record has expired")
    record_digest = _verify_signature(
        record,
        declared_digest=safe_envelope.digest,
        signature=safe_envelope.signature,
        verifier=signature_verifier,
        subject="registry record",
    )

    if previous_receipt is not None:
        if previous_receipt.reference != record.reference:
            _fail(RegistryReasonCode.ROLLBACK, "previous receipt belongs to another reference")
        if previous_receipt.risk_tier != record.risk_tier:
            _fail(RegistryReasonCode.RISK_TIER_CHANGED, "risk-tier change requires revalidation")
        if record.release_epoch < previous_receipt.record_epoch or (
            record.release_epoch == previous_receipt.record_epoch
            and record_digest != previous_receipt.record_digest
        ):
            _fail(RegistryReasonCode.ROLLBACK, "registry record release rollback detected")

    if record.risk_tier == RiskTier.R3:
        if signed_revocation is not None or online_revocation_checker is None:
            _fail(RegistryReasonCode.REVOCATION_REQUIRED, "R3 requires a fresh online check")
        revocation_source: Literal["signed-state", "online"] = "online"
        revocation_digest, revocation_epoch, next_update = _online_revocation(
            online_revocation_checker,
            record=record,
            record_digest=record_digest,
            checked_at=checked_at,
        )
    else:
        if (signed_revocation is None) == (online_revocation_checker is None):
            _fail(
                RegistryReasonCode.REVOCATION_REQUIRED,
                "exactly one signed or online revocation source is required",
            )
        if signed_revocation is not None:
            revocation_source = "signed-state"
            revocation_digest, revocation_epoch, next_update = _signed_revocation(
                signed_revocation,
                record=record,
                record_digest=record_digest,
                checked_at=checked_at,
                verifier=signature_verifier,
            )
        else:
            if online_revocation_checker is None:
                _fail(RegistryReasonCode.REVOCATION_REQUIRED, "online revocation source is missing")
            revocation_source = "online"
            revocation_digest, revocation_epoch, next_update = _online_revocation(
                online_revocation_checker,
                record=record,
                record_digest=record_digest,
                checked_at=checked_at,
            )

    if previous_receipt is not None and revocation_epoch < previous_receipt.revocation_epoch:
        _fail(RegistryReasonCode.ROLLBACK, "revocation epoch rollback detected")
    if (
        previous_receipt is not None
        and revocation_source == "signed-state"
        and previous_receipt.revocation_source == "signed-state"
        and revocation_epoch == previous_receipt.revocation_epoch
        and revocation_digest != previous_receipt.revocation_state_digest
    ):
        _fail(RegistryReasonCode.ROLLBACK, "revocation state changed without an epoch advance")

    receipt = VerifiedRegistryReceipt(
        reference=record.reference,
        risk_tier=record.risk_tier,
        record_digest=record_digest,
        record_epoch=record.release_epoch,
        record_version=record.version,
        schema_digest=record.schema_digest,
        scopes=record.scopes,
        record_expires_at=record.expires_at,
        signature_key_id=safe_envelope.signature.key_id,
        signature_algorithm=safe_envelope.signature.algorithm,
        revocation_source=revocation_source,
        revocation_state_digest=revocation_digest,
        revocation_epoch=revocation_epoch,
        checked_at=checked_at,
        next_update=next_update,
    )
    return VerifiedRegistryResolution(record=record, receipt=receipt)


__all__ = [
    "DetachedSignature",
    "DetachedSignatureVerifier",
    "OnlineRevocationChecker",
    "OnlineRevocationStatus",
    "RegistryProvenance",
    "RegistryReasonCode",
    "RegistryRecord",
    "RegistryVerificationError",
    "RevocationState",
    "RiskTier",
    "SignatureAlgorithm",
    "SignedRegistryRecord",
    "SignedRevocationState",
    "VerifiedRegistryReceipt",
    "VerifiedRegistryResolution",
    "canonical_registry_bytes",
    "canonical_registry_sha256",
    "verify_registry_record",
]
