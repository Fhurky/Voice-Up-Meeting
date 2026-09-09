"""Fail-closed verification of exact, time-bound Agent Platform admission records.

The verifier is intentionally a pure port. It owns no signing key, trust root, registry transport,
runtime activator, or execution engine. External callers inject signature and revocation decisions;
the returned receipt records admission scope but performs no activation or action.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal, NoReturn, Protocol

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from kt_scaffold.agent_platform.manifest import canonical_json
from kt_scaffold.agent_platform.models import reconstruct_exact_model
from kt_scaffold.agent_platform.registry import (
    DetachedSignature,
    DetachedSignatureVerifier,
    RiskTier,
)

SHA256_PATTERN = r"^[0-9a-f]{64}$"
OWNER_PATTERN = r"^(?:team|person):[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
SAFE_ID_PATTERN = r"^[a-z0-9][a-z0-9]*(?:[-._:/][a-z0-9]+)*$"
STABLE_VERSION_PATTERN = r"^[0-9]+\.[0-9]+\.[0-9]+$"
CANONICAL_AGENT_IDS = (
    "application-security",
    "code-review",
    "requirements-scope",
    "test-automation",
)
ADMISSION_TTL_BOUNDS = {
    RiskTier.R0: timedelta(days=90),
    RiskTier.R1: timedelta(days=30),
    RiskTier.R2: timedelta(days=14),
    RiskTier.R3: timedelta(days=7),
}
REVOCATION_FRESHNESS_BOUNDS = {
    RiskTier.R0: timedelta(hours=4),
    RiskTier.R1: timedelta(hours=4),
    RiskTier.R2: timedelta(minutes=15),
}
UNSTABLE_IDENTIFIERS = frozenset(
    {
        "alpha",
        "beta",
        "canary",
        "dev",
        "head",
        "latest",
        "main",
        "master",
        "nightly",
        "preview",
        "rc",
        "snapshot",
        "wildcard",
    }
)
RAW_SECRET_VALUE = re.compile(r"(?i)^(?:bearer\s+|sk[-_]|ghp[-_]|github_pat[-_]|xox[baprs][-_])")


class AdmissionModel(BaseModel):
    """Immutable strict model for admission input and evidence boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AdmissionReasonCode(StrEnum):
    DIGEST_MISMATCH = "AP_ADMISSION_DIGEST_MISMATCH"
    SIGNATURE_INVALID = "AP_ADMISSION_SIGNATURE_INVALID"
    ID_MISMATCH = "AP_ADMISSION_ID_MISMATCH"
    PIN_MISMATCH = "AP_ADMISSION_PIN_MISMATCH"
    RISK_TIER_MISMATCH = "AP_ADMISSION_RISK_TIER_MISMATCH"
    NOT_YET_VALID = "AP_ADMISSION_NOT_YET_VALID"
    EXPIRED = "AP_ADMISSION_EXPIRED"
    REVOCATION_REQUIRED = "AP_ADMISSION_REVOCATION_REQUIRED"
    REVOCATION_INVALID = "AP_ADMISSION_REVOCATION_INVALID"
    REVOCATION_STALE = "AP_ADMISSION_REVOCATION_STALE"
    REVOKED = "AP_ADMISSION_REVOKED"
    ROLLBACK = "AP_ADMISSION_ROLLBACK"


class AdmissionVerificationError(ValueError):
    """Stable denial result for an invalid or unverifiable admission record."""

    def __init__(self, code: AdmissionReasonCode, message: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {message}")


class ClientId(StrEnum):
    CODEX = "codex"
    CLAUDE_CODE = "claude-code"
    GITHUB_COPILOT_VSCODE = "github-copilot-vscode"
    CURSOR = "cursor"


class AdmissionAction(StrEnum):
    READ = "read"
    SEARCH = "search"
    ANALYZE = "analyze"
    REVIEW = "review"
    REPORT = "report"
    ISOLATED_TEST_EXECUTION = "isolated-test-execution"
    WORKSPACE_WRITE = "workspace-write"
    EXTERNAL_SIDE_EFFECT = "external-side-effect"


class ExecutionMode(StrEnum):
    ADVISORY = "advisory"
    DIRECT = "direct"


class RevocationSource(StrEnum):
    SIGNED_STATE = "signed-state"
    ONLINE = "online"


READ_ONLY_ACTIONS = frozenset(
    {
        AdmissionAction.READ,
        AdmissionAction.SEARCH,
        AdmissionAction.ANALYZE,
        AdmissionAction.REVIEW,
        AdmissionAction.REPORT,
    }
)


def _validate_timestamp(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("admission timestamps must be UTC")
    if value.microsecond:
        raise ValueError("admission timestamps must use whole seconds")
    return value


def _reject_unstable_or_secret(value: str, label: str) -> None:
    if any(marker in value for marker in ("*", "^", "~", ">", "<")):
        raise ValueError(f"{label} must not contain wildcard or range syntax")
    segments = set(re.split(r"[-._:/]+", value.casefold()))
    if segments & UNSTABLE_IDENTIFIERS:
        raise ValueError(f"{label} must be exact, stable, and non-prerelease")
    if RAW_SECRET_VALUE.search(value):
        raise ValueError(f"{label} must not contain a raw secret or token")


def _validate_agent_digest_set(
    values: tuple[CanonicalContractDigest, ...] | tuple[ProjectionArtifactDigest, ...],
    label: str,
) -> None:
    ids = tuple(item.agent_id for item in values)
    if ids != CANONICAL_AGENT_IDS:
        raise ValueError(f"{label} must contain the four canonical agents in stable order")


class CanonicalContractDigest(AdmissionModel):
    agent_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    sha256: str = Field(pattern=SHA256_PATTERN)


class ClientRuntimePin(AdmissionModel):
    client_id: ClientId
    version: str = Field(pattern=STABLE_VERSION_PATTERN)
    build_id: str = Field(pattern=SAFE_ID_PATTERN)
    runtime_artifact_digest: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_stable_identity(self) -> ClientRuntimePin:
        _reject_unstable_or_secret(self.build_id, "client build id")
        return self


class ProjectionArtifactDigest(AdmissionModel):
    agent_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    relative_path: str = Field(min_length=1)
    sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_path(self) -> ProjectionArtifactDigest:
        path = PurePosixPath(self.relative_path)
        if (
            path.is_absolute()
            or path.as_posix() != self.relative_path
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in self.relative_path
        ):
            raise ValueError("projection artifact path must be a normalized relative POSIX path")
        return self


class ProjectionPins(AdmissionModel):
    lock_digest: str = Field(pattern=SHA256_PATTERN)
    artifacts: tuple[ProjectionArtifactDigest, ...] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_artifacts(self) -> ProjectionPins:
        _validate_agent_digest_set(self.artifacts, "projection artifacts")
        if len({artifact.relative_path for artifact in self.artifacts}) != len(self.artifacts):
            raise ValueError("projection artifact paths must be unique")
        return self


class RuntimeEvidencePins(AdmissionModel):
    adapter_id: str = Field(pattern=SAFE_ID_PATTERN)
    adapter_version: str = Field(pattern=STABLE_VERSION_PATTERN)
    adapter_digest: str = Field(pattern=SHA256_PATTERN)
    resolved_model_id: str = Field(pattern=SAFE_ID_PATTERN)
    model_revision: str = Field(pattern=SAFE_ID_PATTERN)
    model_digest: str = Field(pattern=SHA256_PATTERN)
    tool_registry_digest: str = Field(pattern=SHA256_PATTERN)
    mcp_registry_digest: str = Field(pattern=SHA256_PATTERN)
    policy_digest: str = Field(pattern=SHA256_PATTERN)
    approval_policy_digest: str = Field(pattern=SHA256_PATTERN)
    identity_scope_digest: str = Field(pattern=SHA256_PATTERN)
    environment_digest: str = Field(pattern=SHA256_PATTERN)
    dataset_digest: str = Field(pattern=SHA256_PATTERN)
    conformance_evidence_digest: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_exact_runtime(self) -> RuntimeEvidencePins:
        for label, value in (
            ("adapter id", self.adapter_id),
            ("model id", self.resolved_model_id),
            ("model revision", self.model_revision),
        ):
            _reject_unstable_or_secret(value, label)
        return self


class AdmissionAuthorityScope(AdmissionModel):
    project_id: str = Field(pattern=SAFE_ID_PATTERN)
    environment_id: str = Field(pattern=SAFE_ID_PATTERN)
    agent_ids: tuple[str, ...] = Field(min_length=1, max_length=4)
    actions: tuple[AdmissionAction, ...] = Field(min_length=1)
    resources: tuple[str, ...] = Field(min_length=1)
    execution_mode: ExecutionMode

    @model_validator(mode="after")
    def validate_scope(self) -> AdmissionAuthorityScope:
        if tuple(sorted(self.agent_ids)) != self.agent_ids:
            raise ValueError("admitted agent ids must use stable sorted order")
        if not set(self.agent_ids) <= set(CANONICAL_AGENT_IDS):
            raise ValueError("admission scope contains an unknown agent")
        if len(set(self.agent_ids)) != len(self.agent_ids):
            raise ValueError("admitted agent ids must be unique")
        if len(set(self.actions)) != len(self.actions):
            raise ValueError("admitted actions must be unique")
        if len(set(self.resources)) != len(self.resources):
            raise ValueError("admitted resources must be unique")
        for resource in self.resources:
            if re.fullmatch(SAFE_ID_PATTERN, resource) is None:
                raise ValueError("admitted resources must be bounded symbolic identifiers")
            _reject_unstable_or_secret(resource, "admitted resource")
        return self


class AdmissionPinSet(AdmissionModel):
    client: ClientRuntimePin
    canonical_contracts: tuple[CanonicalContractDigest, ...] = Field(min_length=4, max_length=4)
    projection: ProjectionPins
    runtime_evidence: RuntimeEvidencePins
    risk_tier: RiskTier
    owner: str = Field(pattern=OWNER_PATTERN)
    authority_scope: AdmissionAuthorityScope

    @model_validator(mode="after")
    def validate_pins(self) -> AdmissionPinSet:
        _validate_agent_digest_set(self.canonical_contracts, "canonical contract digests")
        expected_paths = {
            ClientId.CODEX: ".codex/agents/{agent}.toml",
            ClientId.CLAUDE_CODE: ".claude/agents/{agent}.md",
            ClientId.GITHUB_COPILOT_VSCODE: ".github/agents/{agent}.agent.md",
            ClientId.CURSOR: ".cursor/agents/{agent}.md",
        }
        template = expected_paths[self.client.client_id]
        for artifact in self.projection.artifacts:
            if artifact.relative_path != template.format(agent=artifact.agent_id):
                raise ValueError("projection path does not match the exact admitted client")

        actions = set(self.authority_scope.actions)
        if self.risk_tier == RiskTier.R0 and not actions <= READ_ONLY_ACTIONS:
            raise ValueError("R0 admission is restricted to read-only actions")
        if self.risk_tier == RiskTier.R1 and AdmissionAction.EXTERNAL_SIDE_EFFECT in actions:
            raise ValueError("R1 admission cannot authorize external side effects")
        if self.risk_tier == RiskTier.R3 and (
            self.authority_scope.execution_mode != ExecutionMode.ADVISORY
            or not actions <= READ_ONLY_ACTIONS
        ):
            raise ValueError("R3 direct execution is prohibited in this delivery")
        return self


class AdmissionRecord(AdmissionModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentRuntimeAdmissionRecord"] = "AgentRuntimeAdmissionRecord"
    admission_id: str = Field(pattern=SAFE_ID_PATTERN)
    release_epoch: int = Field(ge=0)
    decision: Literal["admitted"] = "admitted"
    pins: AdmissionPinSet
    reviewers: tuple[str, ...] = Field(min_length=1)
    issued_at: AwareDatetime
    not_before: AwareDatetime
    expires_at: AwareDatetime

    @field_validator("issued_at", "not_before", "expires_at")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def validate_record(self) -> AdmissionRecord:
        _reject_unstable_or_secret(self.admission_id, "admission id")
        if self.issued_at > self.not_before or self.not_before >= self.expires_at:
            raise ValueError("admission time order must be issued <= not_before < expires")
        if self.expires_at - self.not_before > ADMISSION_TTL_BOUNDS[self.pins.risk_tier]:
            raise ValueError("admission expiry exceeds the risk-tier TTL")
        if len(set(self.reviewers)) != len(self.reviewers):
            raise ValueError("admission reviewers must be unique")
        if any(re.fullmatch(OWNER_PATTERN, reviewer) is None for reviewer in self.reviewers):
            raise ValueError("admission reviewers must be canonical owner ids")
        if self.pins.owner in self.reviewers:
            raise ValueError("admission owner and required reviewers must be separated")
        minimum_reviewers = 2 if self.pins.risk_tier in {RiskTier.R2, RiskTier.R3} else 1
        if len(self.reviewers) < minimum_reviewers:
            raise ValueError("risk tier requires additional independent reviewers")
        return self


class SignedAdmissionRecord(AdmissionModel):
    record: AdmissionRecord
    digest: str = Field(pattern=SHA256_PATTERN)
    signature: DetachedSignature


class AdmissionRevocationStatus(AdmissionModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentAdmissionRevocationStatus"] = "AgentAdmissionRevocationStatus"
    source: RevocationSource
    source_digest: str = Field(pattern=SHA256_PATTERN)
    risk_tier: RiskTier
    epoch: int = Field(ge=0)
    checked_at: AwareDatetime
    next_update: AwareDatetime
    revoked_admission_digests: tuple[str, ...]

    @field_validator("checked_at", "next_update")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def validate_status(self) -> AdmissionRevocationStatus:
        if self.next_update < self.checked_at:
            raise ValueError("revocation next_update cannot precede checked_at")
        if len(set(self.revoked_admission_digests)) != len(self.revoked_admission_digests):
            raise ValueError("revoked admission digests must be unique")
        if any(
            re.fullmatch(SHA256_PATTERN, digest) is None
            for digest in self.revoked_admission_digests
        ):
            raise ValueError("revoked admission entries must be SHA-256 digests")
        return self


class AdmissionRevocationChecker(Protocol):
    """External status port; callers own signature/transport/trust-root verification."""

    def __call__(
        self,
        *,
        admission_id: str,
        admission_digest: str,
        checked_at: datetime,
    ) -> AdmissionRevocationStatus: ...


class VerifiedAdmissionReceipt(AdmissionModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentRuntimeAdmissionVerificationReceipt"] = (
        "AgentRuntimeAdmissionVerificationReceipt"
    )
    verification_scope: Literal["admission-record-validity"] = "admission-record-validity"
    admission_decision: Literal["admitted"] = "admitted"
    runtime_authority_effect: Literal["requires-external-policy-intersection"] = (
        "requires-external-policy-intersection"
    )
    activation_performed: Literal[False] = False
    execution_performed: Literal[False] = False
    admission_id: str
    record_digest: str = Field(pattern=SHA256_PATTERN)
    record_epoch: int = Field(ge=0)
    pinset_digest: str = Field(pattern=SHA256_PATTERN)
    client_id: ClientId
    client_version: str = Field(pattern=STABLE_VERSION_PATTERN)
    risk_tier: RiskTier
    owner: str = Field(pattern=OWNER_PATTERN)
    authority_scope: AdmissionAuthorityScope
    issued_at: AwareDatetime
    not_before: AwareDatetime
    expires_at: AwareDatetime
    signature_key_id: str
    signature_algorithm: str
    revocation_source: RevocationSource
    revocation_status_digest: str = Field(pattern=SHA256_PATTERN)
    revocation_source_digest: str = Field(pattern=SHA256_PATTERN)
    revocation_epoch: int = Field(ge=0)
    checked_at: AwareDatetime
    next_update: AwareDatetime

    @field_validator("issued_at", "not_before", "expires_at", "checked_at", "next_update")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _validate_timestamp(value)


class VerifiedAdmissionRecord(AdmissionModel):
    record: AdmissionRecord
    receipt: VerifiedAdmissionReceipt


_ADMISSION_BOUNDARY_MODELS: frozenset[type[BaseModel]] = frozenset(
    {
        AdmissionAuthorityScope,
        AdmissionPinSet,
        AdmissionRecord,
        AdmissionRevocationStatus,
        CanonicalContractDigest,
        ClientRuntimePin,
        DetachedSignature,
        ProjectionArtifactDigest,
        ProjectionPins,
        RuntimeEvidencePins,
        SignedAdmissionRecord,
        VerifiedAdmissionReceipt,
        VerifiedAdmissionRecord,
    }
)


def canonical_admission_bytes(value: AdmissionModel) -> bytes:
    value_type = type(value)
    if value_type not in _ADMISSION_BOUNDARY_MODELS:
        raise ValueError("unsupported admission model type")
    rebuilt = reconstruct_exact_model(
        value,
        value_type,
        allowed_model_types=_ADMISSION_BOUNDARY_MODELS,
    )
    return canonical_json(rebuilt.model_dump(mode="json")).encode("utf-8")


def canonical_admission_sha256(value: AdmissionModel) -> str:
    return hashlib.sha256(canonical_admission_bytes(value)).hexdigest()


def _fail(code: AdmissionReasonCode, message: str) -> NoReturn:
    raise AdmissionVerificationError(code, message)


def _normalize_now(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        _fail(AdmissionReasonCode.REVOCATION_INVALID, "verification time must be timezone-aware")
    normalized = now.astimezone(UTC)
    if normalized.microsecond:
        _fail(AdmissionReasonCode.REVOCATION_INVALID, "verification time must use whole seconds")
    return normalized


def _verify_signature(envelope: SignedAdmissionRecord, verifier: DetachedSignatureVerifier) -> str:
    content = canonical_admission_bytes(envelope.record)
    digest = hashlib.sha256(content).hexdigest()
    if digest != envelope.digest:
        _fail(AdmissionReasonCode.DIGEST_MISMATCH, "admission digest does not match content")
    try:
        verified = verifier(content, envelope.signature)
    except Exception:
        _fail(AdmissionReasonCode.SIGNATURE_INVALID, "admission signature verifier failed")
    if verified is not True:
        _fail(AdmissionReasonCode.SIGNATURE_INVALID, "admission signature is not verified")
    return digest


def _check_revocation(
    checker: AdmissionRevocationChecker,
    *,
    record: AdmissionRecord,
    record_digest: str,
    checked_at: datetime,
) -> AdmissionRevocationStatus:
    try:
        status = checker(
            admission_id=record.admission_id,
            admission_digest=record_digest,
            checked_at=checked_at,
        )
    except ValidationError:
        _fail(AdmissionReasonCode.REVOCATION_INVALID, "revocation port returned invalid status")
    except Exception:
        _fail(AdmissionReasonCode.REVOCATION_REQUIRED, "admission revocation check failed")
    if not isinstance(status, AdmissionRevocationStatus):
        _fail(AdmissionReasonCode.REVOCATION_INVALID, "revocation port returned invalid status")
    try:
        status = reconstruct_exact_model(
            status,
            AdmissionRevocationStatus,
            allowed_model_types=_ADMISSION_BOUNDARY_MODELS,
        )
    except (TypeError, ValueError):
        _fail(AdmissionReasonCode.REVOCATION_INVALID, "revocation port returned invalid status")
    if status.risk_tier != record.pins.risk_tier:
        _fail(AdmissionReasonCode.REVOCATION_INVALID, "revocation risk tier does not match")
    if status.checked_at != checked_at:
        _fail(
            AdmissionReasonCode.REVOCATION_INVALID,
            "revocation status is not bound to this check",
        )
    if record.pins.risk_tier == RiskTier.R3:
        if status.source != RevocationSource.ONLINE or status.next_update != checked_at:
            _fail(AdmissionReasonCode.REVOCATION_STALE, "R3 requires a non-reusable online status")
    else:
        if checked_at >= status.next_update:
            _fail(AdmissionReasonCode.REVOCATION_STALE, "admission revocation status is stale")
        bound = REVOCATION_FRESHNESS_BOUNDS[record.pins.risk_tier]
        if status.next_update - status.checked_at > bound:
            _fail(AdmissionReasonCode.REVOCATION_STALE, "revocation freshness exceeds risk bound")
    if record_digest in status.revoked_admission_digests:
        _fail(AdmissionReasonCode.REVOKED, "admission record digest is revoked")
    return status


def verify_admission_record(
    envelope: SignedAdmissionRecord,
    *,
    expected_admission_id: str,
    expected_pins: AdmissionPinSet,
    effective_risk_tier: RiskTier,
    now: datetime,
    signature_verifier: DetachedSignatureVerifier,
    revocation_checker: AdmissionRevocationChecker,
    previous_receipt: VerifiedAdmissionReceipt | None = None,
) -> VerifiedAdmissionRecord:
    """Verify admission evidence and expose its scope without activating or executing it."""

    try:
        envelope = reconstruct_exact_model(
            envelope,
            SignedAdmissionRecord,
            allowed_model_types=_ADMISSION_BOUNDARY_MODELS,
        )
    except (TypeError, ValueError):
        _fail(AdmissionReasonCode.SIGNATURE_INVALID, "admission envelope is not canonical")
    try:
        expected_pins = reconstruct_exact_model(
            expected_pins,
            AdmissionPinSet,
            allowed_model_types=_ADMISSION_BOUNDARY_MODELS,
        )
    except (TypeError, ValueError):
        _fail(AdmissionReasonCode.PIN_MISMATCH, "expected admission pins are invalid")
    if previous_receipt is not None:
        try:
            previous_receipt = reconstruct_exact_model(
                previous_receipt,
                VerifiedAdmissionReceipt,
                allowed_model_types=_ADMISSION_BOUNDARY_MODELS,
            )
        except (TypeError, ValueError):
            _fail(AdmissionReasonCode.ROLLBACK, "previous admission receipt is invalid")
    checked_at = _normalize_now(now)
    record = envelope.record
    if record.admission_id != expected_admission_id:
        _fail(AdmissionReasonCode.ID_MISMATCH, "admission id does not match expected id")
    if record.pins != expected_pins:
        _fail(AdmissionReasonCode.PIN_MISMATCH, "admission tuple does not match exact pins")
    if not isinstance(effective_risk_tier, RiskTier) or (
        record.pins.risk_tier != effective_risk_tier
    ):
        _fail(
            AdmissionReasonCode.RISK_TIER_MISMATCH,
            "admission risk tier does not match externally evaluated tier",
        )
    if checked_at < record.not_before:
        _fail(AdmissionReasonCode.NOT_YET_VALID, "admission record is not yet valid")
    if checked_at >= record.expires_at:
        _fail(AdmissionReasonCode.EXPIRED, "admission record has expired")
    record_digest = _verify_signature(envelope, signature_verifier)

    if previous_receipt is not None:
        if previous_receipt.admission_id != record.admission_id:
            _fail(AdmissionReasonCode.ROLLBACK, "previous receipt belongs to another admission")
        if previous_receipt.risk_tier != record.pins.risk_tier:
            _fail(AdmissionReasonCode.RISK_TIER_MISMATCH, "risk-tier change requires revalidation")
        if record.release_epoch < previous_receipt.record_epoch or (
            record.release_epoch == previous_receipt.record_epoch
            and record_digest != previous_receipt.record_digest
        ):
            _fail(AdmissionReasonCode.ROLLBACK, "admission release rollback detected")

    status = _check_revocation(
        revocation_checker,
        record=record,
        record_digest=record_digest,
        checked_at=checked_at,
    )
    if previous_receipt is not None and status.epoch < previous_receipt.revocation_epoch:
        _fail(AdmissionReasonCode.ROLLBACK, "admission revocation epoch rollback detected")
    if (
        previous_receipt is not None
        and status.source == RevocationSource.SIGNED_STATE
        and previous_receipt.revocation_source == RevocationSource.SIGNED_STATE
        and status.epoch == previous_receipt.revocation_epoch
        and status.source_digest != previous_receipt.revocation_source_digest
    ):
        _fail(AdmissionReasonCode.ROLLBACK, "revocation state changed without epoch advance")

    receipt = VerifiedAdmissionReceipt(
        admission_id=record.admission_id,
        record_digest=record_digest,
        record_epoch=record.release_epoch,
        pinset_digest=canonical_admission_sha256(record.pins),
        client_id=record.pins.client.client_id,
        client_version=record.pins.client.version,
        risk_tier=record.pins.risk_tier,
        owner=record.pins.owner,
        authority_scope=record.pins.authority_scope,
        issued_at=record.issued_at,
        not_before=record.not_before,
        expires_at=record.expires_at,
        signature_key_id=envelope.signature.key_id,
        signature_algorithm=envelope.signature.algorithm.value,
        revocation_source=status.source,
        revocation_status_digest=canonical_admission_sha256(status),
        revocation_source_digest=status.source_digest,
        revocation_epoch=status.epoch,
        checked_at=checked_at,
        next_update=status.next_update,
    )
    return VerifiedAdmissionRecord(record=record, receipt=receipt)


__all__ = [
    "AdmissionAction",
    "AdmissionAuthorityScope",
    "AdmissionPinSet",
    "AdmissionReasonCode",
    "AdmissionRecord",
    "AdmissionRevocationChecker",
    "AdmissionRevocationStatus",
    "AdmissionVerificationError",
    "CanonicalContractDigest",
    "ClientId",
    "ClientRuntimePin",
    "ExecutionMode",
    "ProjectionArtifactDigest",
    "ProjectionPins",
    "RevocationSource",
    "RuntimeEvidencePins",
    "SignedAdmissionRecord",
    "VerifiedAdmissionReceipt",
    "VerifiedAdmissionRecord",
    "canonical_admission_bytes",
    "canonical_admission_sha256",
    "verify_admission_record",
]
