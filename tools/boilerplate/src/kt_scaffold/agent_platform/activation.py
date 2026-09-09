"""Signed, short-lived authorization boundary for disposable conformance workspaces."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal, NoReturn

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from kt_scaffold.agent_platform.admission import (
    AdmissionAuthorityScope,
    AdmissionPinSet,
    AdmissionRevocationChecker,
    AdmissionVerificationError,
    CanonicalContractDigest,
    ClientId,
    ClientRuntimePin,
    ProjectionArtifactDigest,
    ProjectionPins,
    RevocationSource,
    RuntimeEvidencePins,
    SignedAdmissionRecord,
    VerifiedAdmissionReceipt,
    VerifiedAdmissionRecord,
    canonical_admission_sha256,
    verify_admission_record,
)
from kt_scaffold.agent_platform.manifest import canonical_json
from kt_scaffold.agent_platform.models import (
    CompilationResult,
    ProjectionArtifact,
    reconstruct_exact_model,
    revalidate_compilation_result,
)
from kt_scaffold.agent_platform.registry import (
    DetachedSignature,
    DetachedSignatureVerifier,
    RiskTier,
)
from kt_scaffold.fsops import apply_file_set
from kt_scaffold.models import Change
from kt_scaffold.safety import SafetyError, resolved_root, safe_join

SHA256_PATTERN = r"^[0-9a-f]{64}$"
CLIENT_ID_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
OWNER_PATTERN = r"^(?:team|person):[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
SAFE_ID_PATTERN = r"^[a-z][a-z0-9]*(?:[-.:/][a-z0-9]+)*$"
MAX_CONFORMANCE_GRANT_TTL = timedelta(minutes=15)
CANONICAL_AGENT_IDS = frozenset(
    {
        "application-security",
        "code-review",
        "requirements-scope",
        "test-automation",
    }
)
ACTIVATION_STATE_ROOT = ".kt-scaffold/agent-activation"
LIVE_DISCOVERY_ROOTS = {
    ClientId.CODEX: ".codex/agents",
    ClientId.CLAUDE_CODE: ".claude/agents",
    ClientId.GITHUB_COPILOT_VSCODE: ".github/agents",
    ClientId.CURSOR: ".cursor/agents",
}


class ActivationModel(BaseModel):
    """Strict immutable activation-boundary model."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EffectiveRuntimeSnapshot(ActivationModel):
    """Trusted live client and execution evidence observed at activation time."""

    client: ClientRuntimePin
    runtime_evidence: RuntimeEvidencePins


def effective_runtime_sha256(snapshot: EffectiveRuntimeSnapshot) -> str:
    snapshot = reconstruct_exact_model(
        snapshot,
        EffectiveRuntimeSnapshot,
        allowed_model_types=_ACTIVATION_INPUT_MODELS,
    )
    return hashlib.sha256(
        canonical_json(snapshot.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()


_ACTIVATION_INPUT_MODELS: frozenset[type[BaseModel]] = frozenset(
    {
        AdmissionAuthorityScope,
        AdmissionPinSet,
        CanonicalContractDigest,
        ClientRuntimePin,
        EffectiveRuntimeSnapshot,
        ProjectionArtifactDigest,
        ProjectionPins,
        RuntimeEvidencePins,
        VerifiedAdmissionReceipt,
    }
)


def _utc_seconds(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("conformance grant timestamps must be UTC")
    if value.microsecond:
        raise ValueError("conformance grant timestamps must use whole seconds")
    return value


class ProjectionDigest(ActivationModel):
    relative_path: str = Field(min_length=1, max_length=300)
    sha256: str = Field(pattern=SHA256_PATTERN)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        if (
            value.startswith(("/", "\\"))
            or "\\" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
        ):
            raise ValueError("projection digest path must be normalized and relative")
        return value


class ConformanceWorkspaceGrant(ActivationModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentConformanceWorkspaceGrant"] = "AgentConformanceWorkspaceGrant"
    grant_id: str = Field(pattern=SAFE_ID_PATTERN)
    nonce: str = Field(pattern=r"^[A-Za-z0-9_-]{16,128}$")
    client_id: str = Field(pattern=CLIENT_ID_PATTERN)
    risk_tier: Literal["R0", "R1"]
    purpose: Literal["real-client-conformance"] = "real-client-conformance"
    environment_id: str = Field(pattern=SAFE_ID_PATTERN)
    issuer: str = Field(pattern=OWNER_PATTERN)
    compiler_lock_sha256: str = Field(pattern=SHA256_PATTERN)
    projections: tuple[ProjectionDigest, ...] = Field(min_length=1, max_length=64)
    issued_at: AwareDatetime
    expires_at: AwareDatetime
    single_use: Literal[True] = True
    persistent_activation: Literal[False] = False
    runtime_admission: Literal[False] = False

    @field_validator("issued_at", "expires_at")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _utc_seconds(value)

    @model_validator(mode="after")
    def validate_window_and_inventory(self) -> ConformanceWorkspaceGrant:
        if self.expires_at <= self.issued_at:
            raise ValueError("conformance grant expiry must follow issue time")
        if self.expires_at - self.issued_at > MAX_CONFORMANCE_GRANT_TTL:
            raise ValueError("conformance grant exceeds the 15-minute maximum TTL")
        paths = [item.relative_path for item in self.projections]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ValueError("conformance grant projections must be unique and sorted")
        return self


class SignedConformanceWorkspaceGrant(ActivationModel):
    grant: ConformanceWorkspaceGrant
    digest: str = Field(pattern=SHA256_PATTERN)
    signature: DetachedSignature


class VerifiedConformanceWorkspaceGrant(ActivationModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["VerifiedAgentConformanceWorkspaceGrant"] = (
        "VerifiedAgentConformanceWorkspaceGrant"
    )
    status: Literal["verified"] = "verified"
    grant_id: str = Field(pattern=SAFE_ID_PATTERN)
    nonce: str = Field(pattern=r"^[A-Za-z0-9_-]{16,128}$")
    client_id: str = Field(pattern=CLIENT_ID_PATTERN)
    risk_tier: Literal["R0", "R1"]
    environment_id: str = Field(pattern=SAFE_ID_PATTERN)
    issuer: str = Field(pattern=OWNER_PATTERN)
    grant_digest: str = Field(pattern=SHA256_PATTERN)
    signature_key_id: str
    compiler_lock_sha256: str = Field(pattern=SHA256_PATTERN)
    projections: tuple[ProjectionDigest, ...] = Field(min_length=1, max_length=64)
    verified_at: AwareDatetime
    expires_at: AwareDatetime
    single_use: Literal[True] = True
    persistent_activation: Literal[False] = False
    runtime_admission: Literal[False] = False

    @field_validator("verified_at", "expires_at")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _utc_seconds(value)


_CONFORMANCE_BOUNDARY_MODELS: frozenset[type[BaseModel]] = frozenset(
    {
        ConformanceWorkspaceGrant,
        DetachedSignature,
        ProjectionDigest,
        SignedConformanceWorkspaceGrant,
    }
)


class ConformanceGrantReasonCode(StrEnum):
    DIGEST_MISMATCH = "AP_CONFORMANCE_GRANT_DIGEST_MISMATCH"
    SIGNATURE_INVALID = "AP_CONFORMANCE_GRANT_SIGNATURE_INVALID"
    EXPIRED = "AP_CONFORMANCE_GRANT_EXPIRED"
    NOT_YET_VALID = "AP_CONFORMANCE_GRANT_NOT_YET_VALID"
    BINDING_MISMATCH = "AP_CONFORMANCE_GRANT_BINDING_MISMATCH"


class ConformanceGrantVerificationError(ValueError):
    def __init__(self, code: ConformanceGrantReasonCode, detail: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {detail}")


def _fail(code: ConformanceGrantReasonCode, detail: str) -> NoReturn:
    raise ConformanceGrantVerificationError(code, detail)


def canonical_conformance_grant_bytes(grant: ConformanceWorkspaceGrant) -> bytes:
    rebuilt = reconstruct_exact_model(
        grant,
        ConformanceWorkspaceGrant,
        allowed_model_types=_CONFORMANCE_BOUNDARY_MODELS,
    )
    return canonical_json(rebuilt.model_dump(mode="json")).encode("utf-8")


def canonical_conformance_grant_sha256(grant: ConformanceWorkspaceGrant) -> str:
    return hashlib.sha256(canonical_conformance_grant_bytes(grant)).hexdigest()


def result_projection_digests(
    result: CompilationResult,
    client_id: str,
) -> tuple[ProjectionDigest, ...]:
    artifacts = tuple(item for item in result.artifacts if item.client_id == client_id)
    if not artifacts:
        _fail(
            ConformanceGrantReasonCode.BINDING_MISMATCH,
            f"compiled result has no projection for client {client_id}",
        )
    return tuple(
        ProjectionDigest(relative_path=item.relative_path, sha256=item.sha256)
        for item in sorted(artifacts, key=lambda value: value.relative_path)
    )


def verify_conformance_workspace_grant(
    envelope: SignedConformanceWorkspaceGrant,
    *,
    result: CompilationResult,
    client_id: str,
    environment_id: str,
    now: datetime,
    signature_verifier: DetachedSignatureVerifier,
) -> VerifiedConformanceWorkspaceGrant:
    """Verify an exact, signed, single-use grant without activating any path."""

    try:
        envelope = reconstruct_exact_model(
            envelope,
            SignedConformanceWorkspaceGrant,
            allowed_model_types=_CONFORMANCE_BOUNDARY_MODELS,
        )
    except (TypeError, ValueError):
        _fail(
            ConformanceGrantReasonCode.SIGNATURE_INVALID,
            "conformance materialization requires a canonical signed grant envelope",
        )
    if now.tzinfo is None or now.utcoffset() is None or now.microsecond:
        _fail(
            ConformanceGrantReasonCode.BINDING_MISMATCH,
            "verification time must be timezone-aware and use whole seconds",
        )
    checked_at = now.astimezone(UTC)
    grant = envelope.grant
    content = canonical_conformance_grant_bytes(grant)
    actual_digest = hashlib.sha256(content).hexdigest()
    if actual_digest != envelope.digest:
        _fail(ConformanceGrantReasonCode.DIGEST_MISMATCH, "grant digest does not match content")
    try:
        signature_valid = signature_verifier(content, envelope.signature)
    except Exception:
        _fail(ConformanceGrantReasonCode.SIGNATURE_INVALID, "grant signature verifier failed")
    if signature_valid is not True:
        _fail(ConformanceGrantReasonCode.SIGNATURE_INVALID, "grant signature is not verified")
    if grant.issued_at > checked_at:
        _fail(ConformanceGrantReasonCode.NOT_YET_VALID, "grant is not yet valid")
    if checked_at >= grant.expires_at:
        _fail(ConformanceGrantReasonCode.EXPIRED, "grant has expired")
    expected_projections = result_projection_digests(result, client_id)
    if (
        grant.client_id != client_id
        or grant.environment_id != environment_id
        or grant.compiler_lock_sha256 != result.lock_sha256
        or grant.projections != expected_projections
    ):
        _fail(
            ConformanceGrantReasonCode.BINDING_MISMATCH,
            "grant does not bind the exact client, environment, lock, and projections",
        )
    if re.fullmatch(SAFE_ID_PATTERN, environment_id) is None:
        _fail(ConformanceGrantReasonCode.BINDING_MISMATCH, "environment id is unsafe")
    return VerifiedConformanceWorkspaceGrant(
        grant_id=grant.grant_id,
        nonce=grant.nonce,
        client_id=grant.client_id,
        risk_tier=grant.risk_tier,
        environment_id=grant.environment_id,
        issuer=grant.issuer,
        grant_digest=actual_digest,
        signature_key_id=envelope.signature.key_id,
        compiler_lock_sha256=grant.compiler_lock_sha256,
        projections=grant.projections,
        verified_at=checked_at,
        expires_at=grant.expires_at,
    )


def assert_verified_grant_binding(
    authorization: VerifiedConformanceWorkspaceGrant,
    *,
    result: CompilationResult,
    client_id: str,
    environment_id: str,
    now: datetime,
) -> None:
    """Fail closed if a verified grant is replayed for another compilation or environment."""

    if now.tzinfo is None or now.utcoffset() is None or now.microsecond:
        _fail(
            ConformanceGrantReasonCode.BINDING_MISMATCH,
            "materialization time must be timezone-aware and use whole seconds",
        )
    checked_at = now.astimezone(UTC)
    expected = result_projection_digests(result, client_id)
    if (
        authorization.client_id != client_id
        or authorization.environment_id != environment_id
        or authorization.compiler_lock_sha256 != result.lock_sha256
        or authorization.projections != expected
    ):
        _fail(ConformanceGrantReasonCode.BINDING_MISMATCH, "verified grant binding changed")
    if checked_at < authorization.verified_at:
        _fail(ConformanceGrantReasonCode.NOT_YET_VALID, "verified grant predates verification")
    if checked_at >= authorization.expires_at:
        _fail(ConformanceGrantReasonCode.EXPIRED, "verified grant has expired")


def consume_verified_grant(
    authorization: VerifiedConformanceWorkspaceGrant,
    consumer: Callable[[str, str], bool],
) -> None:
    """Require an injected atomic one-time nonce consumer; no process-local fallback is used."""

    try:
        consumed = consumer(authorization.grant_id, authorization.nonce)
    except Exception:
        _fail(ConformanceGrantReasonCode.BINDING_MISMATCH, "grant consumer failed")
    if consumed is not True:
        _fail(ConformanceGrantReasonCode.BINDING_MISMATCH, "grant was already used or unavailable")


class ActivationReasonCode(StrEnum):
    AUTHORIZATION_INVALID = "AP_ACTIVATION_AUTHORIZATION_INVALID"
    STATE_INVALID = "AP_ACTIVATION_STATE_INVALID"
    OWNERSHIP_CONFLICT = "AP_ACTIVATION_OWNERSHIP_CONFLICT"


class AgentActivationError(ValueError):
    def __init__(self, code: ActivationReasonCode, detail: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {detail}")


def _activation_fail(code: ActivationReasonCode, detail: str) -> NoReturn:
    raise AgentActivationError(code, detail)


class ActivatedProjection(ActivationModel):
    agent_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    relative_path: str = Field(min_length=1, max_length=300)
    sha256: str = Field(pattern=SHA256_PATTERN)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        if (
            value.startswith(("/", "\\"))
            or "\\" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
        ):
            raise ValueError("activated projection path must be normalized and relative")
        return value


class AgentActivationLock(ActivationModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentProjectionActivationLock"] = "AgentProjectionActivationLock"
    activation_status: Literal["activated"] = "activated"
    admission_id: str
    admission_record_digest: str = Field(pattern=SHA256_PATTERN)
    admission_receipt_digest: str = Field(pattern=SHA256_PATTERN)
    admission_receipt: VerifiedAdmissionReceipt
    admission_epoch: int = Field(ge=0)
    risk_tier: RiskTier
    client_id: ClientId
    client_version: str
    runtime_artifact_digest: str = Field(pattern=SHA256_PATTERN)
    effective_runtime_sha256: str = Field(pattern=SHA256_PATTERN)
    compiler_lock_sha256: str = Field(pattern=SHA256_PATTERN)
    project_id: str = Field(pattern=SAFE_ID_PATTERN)
    environment_id: str = Field(pattern=SAFE_ID_PATTERN)
    environment_digest: str = Field(pattern=SHA256_PATTERN)
    activated_at: AwareDatetime
    admission_expires_at: AwareDatetime
    revocation_source: RevocationSource
    revocation_source_digest: str = Field(pattern=SHA256_PATTERN)
    revocation_epoch: int = Field(ge=0)
    revocation_next_update: AwareDatetime
    authority_intersection_required: Literal[True] = True
    artifacts: tuple[ActivatedProjection, ...] = Field(min_length=1, max_length=4)

    @field_validator("activated_at", "admission_expires_at", "revocation_next_update")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _utc_seconds(value)

    @model_validator(mode="after")
    def validate_inventory(self) -> AgentActivationLock:
        receipt = self.admission_receipt
        if (
            canonical_admission_sha256(receipt) != self.admission_receipt_digest
            or receipt.admission_id != self.admission_id
            or receipt.record_digest != self.admission_record_digest
            or receipt.record_epoch != self.admission_epoch
            or receipt.client_id != self.client_id
            or receipt.client_version != self.client_version
            or receipt.risk_tier != self.risk_tier
            or receipt.authority_scope.project_id != self.project_id
            or receipt.authority_scope.environment_id != self.environment_id
            or receipt.expires_at != self.admission_expires_at
            or receipt.revocation_source != self.revocation_source
            or receipt.revocation_source_digest != self.revocation_source_digest
            or receipt.revocation_epoch != self.revocation_epoch
            or receipt.next_update != self.revocation_next_update
        ):
            raise ValueError("activation state and admission receipt are inconsistent")
        identities = [(item.agent_id, item.relative_path) for item in self.artifacts]
        if identities != sorted(identities) or len(identities) != len(set(identities)):
            raise ValueError("activated projection inventory must be unique and sorted")
        if not {item.agent_id for item in self.artifacts} <= CANONICAL_AGENT_IDS:
            raise ValueError("activation state contains a non-canonical agent")
        expected_paths = {
            ClientId.CODEX: ".codex/agents/{agent}.toml",
            ClientId.CLAUDE_CODE: ".claude/agents/{agent}.md",
            ClientId.GITHUB_COPILOT_VSCODE: ".github/agents/{agent}.agent.md",
            ClientId.CURSOR: ".cursor/agents/{agent}.md",
        }
        template = expected_paths[self.client_id]
        if any(
            item.relative_path != template.format(agent=item.agent_id) for item in self.artifacts
        ):
            raise ValueError("activated projection path does not match the exact client schema")
        return self


def activation_state_path(client_id: ClientId | str) -> str:
    try:
        selected = client_id if isinstance(client_id, ClientId) else ClientId(client_id)
    except ValueError:
        _activation_fail(ActivationReasonCode.STATE_INVALID, f"unknown client id: {client_id}")
    return f"{ACTIVATION_STATE_ROOT}/{selected.value}.lock.json"


def canonical_activation_lock_bytes(state: AgentActivationLock) -> bytes:
    return canonical_json(state.model_dump(mode="json")).encode("utf-8")


def activation_lock_sha256(state: AgentActivationLock) -> str:
    return hashlib.sha256(canonical_activation_lock_bytes(state)).hexdigest()


def _checked_activation_time(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None or now.microsecond:
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "activation time must be timezone-aware and use whole seconds",
        )
    return now.astimezone(UTC)


def _load_activation_state(
    root: Path,
    client_id: ClientId,
) -> tuple[AgentActivationLock, bytes] | None:
    relative = activation_state_path(client_id)
    try:
        path = safe_join(root, relative)
    except SafetyError as exc:
        _activation_fail(ActivationReasonCode.STATE_INVALID, str(exc))
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        _activation_fail(ActivationReasonCode.STATE_INVALID, "activation state path is unsafe")
    content = path.read_bytes()
    try:
        state = AgentActivationLock.model_validate_json(content)
    except (UnicodeDecodeError, ValidationError) as exc:
        _activation_fail(ActivationReasonCode.STATE_INVALID, f"activation state is invalid: {exc}")
    if state.client_id != client_id or canonical_activation_lock_bytes(state) != content:
        _activation_fail(
            ActivationReasonCode.STATE_INVALID,
            "activation state is non-canonical or belongs to another client",
        )
    return state, content


def _admitted_artifacts(
    result: CompilationResult,
    authorization: VerifiedAdmissionRecord,
    *,
    project_id: str,
    environment_id: str,
    effective_runtime: EffectiveRuntimeSnapshot,
    now: datetime,
) -> tuple[ClientId, tuple[ProjectionArtifact, ...]]:
    checked_at = _checked_activation_time(now)
    record = authorization.record
    receipt = authorization.receipt
    pins = record.pins
    scope = pins.authority_scope
    if (
        receipt.record_digest != canonical_admission_sha256(record)
        or receipt.pinset_digest != canonical_admission_sha256(pins)
        or receipt.admission_id != record.admission_id
        or receipt.record_epoch != record.release_epoch
        or receipt.client_id != pins.client.client_id
        or receipt.client_version != pins.client.version
        or receipt.risk_tier != pins.risk_tier
        or receipt.owner != pins.owner
        or receipt.authority_scope != scope
    ):
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "verified admission record and receipt are internally inconsistent",
        )
    if pins.risk_tier.value == "R3":
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "persistent R3 activation is prohibited in this delivery",
        )
    if (
        checked_at < receipt.checked_at
        or checked_at < receipt.not_before
        or checked_at >= receipt.expires_at
        or checked_at >= receipt.next_update
    ):
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "admission validity or revocation freshness window is not current",
        )
    if (
        scope.project_id != project_id
        or scope.environment_id != environment_id
        or pins.client != effective_runtime.client
        or pins.runtime_evidence != effective_runtime.runtime_evidence
        or pins.projection.lock_digest != result.lock_sha256
    ):
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "admission does not bind the complete effective runtime tuple or compiler lock",
        )
    client_id = pins.client.client_id
    compiled = tuple(item for item in result.artifacts if item.client_id == client_id.value)
    compiled_by_agent = {item.agent_id: item for item in compiled}
    if len(compiled) != 4 or len(compiled_by_agent) != 4:
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "compiled result must contain the four exact admitted client projections",
        )
    observed_pins = tuple(
        ProjectionArtifactDigest(
            agent_id=agent_id,
            relative_path=compiled_by_agent[agent_id].relative_path,
            sha256=compiled_by_agent[agent_id].sha256,
        )
        for agent_id in sorted(compiled_by_agent)
    )
    if observed_pins != pins.projection.artifacts:
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "compiled projection paths or digests differ from the admission pin set",
        )
    if any(
        artifact.adapter_id != pins.runtime_evidence.adapter_id
        or artifact.adapter_version != pins.runtime_evidence.adapter_version
        for artifact in compiled
    ):
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "compiled adapter identity differs from the admission pin set",
        )
    selected = tuple(compiled_by_agent[agent_id] for agent_id in scope.agent_ids)
    return client_id, selected


def _activation_state(
    result: CompilationResult,
    authorization: VerifiedAdmissionRecord,
    artifacts: tuple[ProjectionArtifact, ...],
    *,
    project_id: str,
    environment_id: str,
    effective_runtime: EffectiveRuntimeSnapshot,
    now: datetime,
) -> AgentActivationLock:
    record = authorization.record
    receipt = authorization.receipt
    return AgentActivationLock(
        admission_id=record.admission_id,
        admission_record_digest=receipt.record_digest,
        admission_receipt_digest=canonical_admission_sha256(receipt),
        admission_receipt=receipt,
        admission_epoch=record.release_epoch,
        risk_tier=record.pins.risk_tier,
        client_id=record.pins.client.client_id,
        client_version=record.pins.client.version,
        runtime_artifact_digest=effective_runtime.client.runtime_artifact_digest,
        effective_runtime_sha256=effective_runtime_sha256(effective_runtime),
        compiler_lock_sha256=result.lock_sha256,
        project_id=project_id,
        environment_id=environment_id,
        environment_digest=effective_runtime.runtime_evidence.environment_digest,
        activated_at=_checked_activation_time(now),
        admission_expires_at=receipt.expires_at,
        revocation_source=receipt.revocation_source,
        revocation_source_digest=receipt.revocation_source_digest,
        revocation_epoch=receipt.revocation_epoch,
        revocation_next_update=receipt.next_update,
        artifacts=tuple(
            ActivatedProjection(
                agent_id=item.agent_id,
                relative_path=item.relative_path,
                sha256=item.sha256,
            )
            for item in sorted(artifacts, key=lambda value: (value.agent_id, value.relative_path))
        ),
    )


def activate_admitted_client(
    root: str | Path,
    result: CompilationResult,
    authorization: SignedAdmissionRecord,
    *,
    expected_admission_id: str,
    expected_pins: AdmissionPinSet,
    effective_risk_tier: RiskTier,
    signature_verifier: DetachedSignatureVerifier,
    revocation_checker: AdmissionRevocationChecker,
    effective_runtime: EffectiveRuntimeSnapshot,
    project_id: str,
    environment_id: str,
    now: datetime,
    previous_receipt: VerifiedAdmissionReceipt | None = None,
    previous_state_sha256: str | None = None,
    mode: str = "write",
    inject_failure_after: int | None = None,
) -> tuple[list[Change], list[dict[str, str]], AgentActivationLock]:
    """Reverify signed admission and activate only its exact live runtime tuple."""

    if mode not in {"write", "check"}:
        raise ValueError("mode must be write or check")
    try:
        result = revalidate_compilation_result(result)
    except (AttributeError, TypeError, ValueError) as exc:
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            f"compiled projection result failed boundary validation: {exc}",
        )
    try:
        project_root = resolved_root(root).resolve(strict=True)
    except (FileNotFoundError, SafetyError) as exc:
        _activation_fail(ActivationReasonCode.STATE_INVALID, f"activation root is invalid: {exc}")
    if not isinstance(authorization, SignedAdmissionRecord):
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "activation requires a signed admission envelope",
        )
    try:
        expected_pins = reconstruct_exact_model(
            expected_pins,
            AdmissionPinSet,
            allowed_model_types=_ACTIVATION_INPUT_MODELS,
        )
        effective_runtime = reconstruct_exact_model(
            effective_runtime,
            EffectiveRuntimeSnapshot,
            allowed_model_types=_ACTIVATION_INPUT_MODELS,
        )
        if previous_receipt is not None:
            previous_receipt = reconstruct_exact_model(
                previous_receipt,
                VerifiedAdmissionReceipt,
                allowed_model_types=_ACTIVATION_INPUT_MODELS,
            )
    except (TypeError, ValueError):
        _activation_fail(
            ActivationReasonCode.AUTHORIZATION_INVALID,
            "activation inputs failed exact boundary reconstruction",
        )
    current_state = _load_activation_state(project_root, expected_pins.client.client_id)
    if current_state is None:
        if previous_state_sha256 is not None:
            _activation_fail(
                ActivationReasonCode.STATE_INVALID,
                "an external previous-state digest was supplied but no state exists",
            )
    else:
        current_lock, current_content = current_state
        observed_state_sha256 = hashlib.sha256(current_content).hexdigest()
        if (
            previous_state_sha256 is None
            or re.fullmatch(SHA256_PATTERN, previous_state_sha256) is None
            or previous_state_sha256 != observed_state_sha256
        ):
            _activation_fail(
                ActivationReasonCode.STATE_INVALID,
                "existing activation state is not bound to the external previous-state digest",
            )
        if (
            previous_receipt is None
            or canonical_admission_sha256(previous_receipt) != current_lock.admission_receipt_digest
            or previous_receipt != current_lock.admission_receipt
        ):
            _activation_fail(
                ActivationReasonCode.AUTHORIZATION_INVALID,
                "existing activation state requires its exact previous admission receipt",
            )
    try:
        verified_authorization = verify_admission_record(
            authorization,
            expected_admission_id=expected_admission_id,
            expected_pins=expected_pins,
            effective_risk_tier=effective_risk_tier,
            now=now,
            signature_verifier=signature_verifier,
            revocation_checker=revocation_checker,
            previous_receipt=previous_receipt,
        )
    except AdmissionVerificationError as exc:
        _activation_fail(ActivationReasonCode.AUTHORIZATION_INVALID, str(exc))
    client_id, artifacts = _admitted_artifacts(
        result,
        verified_authorization,
        project_id=project_id,
        environment_id=environment_id,
        effective_runtime=effective_runtime,
        now=now,
    )
    state = _activation_state(
        result,
        verified_authorization,
        artifacts,
        project_id=project_id,
        environment_id=environment_id,
        effective_runtime=effective_runtime,
        now=now,
    )
    state_relative = activation_state_path(client_id)
    state_content = canonical_activation_lock_bytes(state)
    expected = {item.relative_path: item.content.encode("utf-8") for item in artifacts}
    expected[state_relative] = state_content
    if current_state is not None:
        current_lock = current_state[0]
        if state.admission_epoch < current_lock.admission_epoch or (
            state.admission_epoch == current_lock.admission_epoch
            and state.admission_record_digest != current_lock.admission_record_digest
        ):
            _activation_fail(
                ActivationReasonCode.AUTHORIZATION_INVALID,
                "activation admission release would roll back or rewrite an existing epoch",
            )
        if state.risk_tier != current_lock.risk_tier:
            _activation_fail(
                ActivationReasonCode.AUTHORIZATION_INVALID,
                "activation risk-tier transition requires a new trusted state boundary",
            )
        if state.revocation_epoch < current_lock.revocation_epoch:
            _activation_fail(
                ActivationReasonCode.AUTHORIZATION_INVALID,
                "activation revocation epoch would roll back",
            )
        if (
            state.revocation_epoch == current_lock.revocation_epoch
            and state.revocation_source == RevocationSource.SIGNED_STATE
            and current_lock.revocation_source == RevocationSource.SIGNED_STATE
            and state.revocation_source_digest != current_lock.revocation_source_digest
        ):
            _activation_fail(
                ActivationReasonCode.AUTHORIZATION_INVALID,
                "signed revocation state changed without an epoch advance",
            )
    old_artifacts = (
        {item.relative_path: item.sha256 for item in current_state[0].artifacts}
        if current_state
        else {}
    )
    changes: list[Change] = []
    drift: list[dict[str, str]] = []
    owned_updates: dict[str, str] = {}
    owned_deletes: dict[str, str] = {}
    conflicts: list[str] = []

    for relative, content in sorted(expected.items()):
        try:
            destination = safe_join(project_root, relative)
        except SafetyError as exc:
            _activation_fail(ActivationReasonCode.STATE_INVALID, str(exc))
        if not destination.exists():
            changes.append(Change(path=relative, action="create"))
            drift.append({"path": relative, "reason": "missing"})
            continue
        if destination.is_symlink() or not destination.is_file():
            conflicts.append(relative)
            continue
        current = destination.read_bytes()
        current_digest = hashlib.sha256(current).hexdigest()
        if relative == state_relative:
            if current_state is None:
                conflicts.append(relative)
                continue
            owned_updates[relative] = current_digest
        else:
            owned_digest = old_artifacts.get(relative)
            if owned_digest is None or current_digest != owned_digest:
                conflicts.append(relative)
                continue
            owned_updates[relative] = owned_digest
        if current == content:
            changes.append(Change(path=relative, action="skip"))
        else:
            changes.append(Change(path=relative, action="update"))
            drift.append({"path": relative, "reason": "content differs"})

    for relative, digest in sorted(old_artifacts.items()):
        if relative in expected:
            continue
        try:
            destination = safe_join(project_root, relative)
        except SafetyError as exc:
            _activation_fail(ActivationReasonCode.STATE_INVALID, str(exc))
        if not destination.exists():
            changes.append(Change(path=relative, action="skip"))
            continue
        if destination.is_symlink() or not destination.is_file():
            conflicts.append(relative)
            continue
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            conflicts.append(relative)
            continue
        owned_deletes[relative] = digest
        changes.append(Change(path=relative, action="delete"))
        drift.append({"path": relative, "reason": "stale activated projection"})

    if conflicts:
        _activation_fail(
            ActivationReasonCode.OWNERSHIP_CONFLICT,
            f"unowned, edited, or unsafe activation paths: {', '.join(sorted(conflicts))}",
        )
    if mode == "write" and drift:
        try:
            applied = apply_file_set(
                project_root,
                expected,
                owned_updates=owned_updates,
                owned_deletes=owned_deletes,
                inject_failure_after=inject_failure_after,
            )
        except (OSError, RuntimeError, SafetyError, ValueError) as exc:
            _activation_fail(ActivationReasonCode.OWNERSHIP_CONFLICT, str(exc))
        if any(item.action == "conflict" for item in applied):
            _activation_fail(
                ActivationReasonCode.OWNERSHIP_CONFLICT,
                "activation ownership changed during the transaction",
            )
        return applied, drift, state
    return sorted(changes, key=lambda item: item.path), drift, state


def deactivate_client(
    root: str | Path,
    client_id: ClientId | str,
    *,
    expected_state_sha256: str,
    mode: str = "write",
    inject_failure_after: int | None = None,
) -> tuple[list[Change], list[dict[str, str]]]:
    """Delete only unchanged activation-lock-owned files; no admission is needed for recovery."""

    if mode not in {"write", "check"}:
        raise ValueError("mode must be write or check")
    try:
        selected = client_id if isinstance(client_id, ClientId) else ClientId(client_id)
        project_root = resolved_root(root).resolve(strict=True)
    except (ValueError, FileNotFoundError, SafetyError) as exc:
        _activation_fail(
            ActivationReasonCode.STATE_INVALID,
            f"deactivation input is invalid: {exc}",
        )
    loaded = _load_activation_state(project_root, selected)
    if loaded is None:
        return [], []
    state, state_content = loaded
    observed_state_sha256 = hashlib.sha256(state_content).hexdigest()
    if (
        re.fullmatch(SHA256_PATTERN, expected_state_sha256) is None
        or expected_state_sha256 != observed_state_sha256
    ):
        _activation_fail(
            ActivationReasonCode.STATE_INVALID,
            "activation state is not bound to the external expected-state digest",
        )
    state_relative = activation_state_path(selected)
    owned_deletes = {item.relative_path: item.sha256 for item in state.artifacts}
    owned_deletes[state_relative] = hashlib.sha256(state_content).hexdigest()
    changes: list[Change] = []
    drift: list[dict[str, str]] = []
    conflicts: list[str] = []
    for relative, digest in sorted(owned_deletes.items()):
        try:
            destination = safe_join(project_root, relative)
        except SafetyError as exc:
            _activation_fail(ActivationReasonCode.STATE_INVALID, str(exc))
        if not destination.exists():
            changes.append(Change(path=relative, action="skip"))
            continue
        if destination.is_symlink() or not destination.is_file():
            conflicts.append(relative)
            continue
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            conflicts.append(relative)
            continue
        changes.append(Change(path=relative, action="delete"))
        drift.append({"path": relative, "reason": "activated projection owned by lock"})
    if conflicts:
        _activation_fail(
            ActivationReasonCode.OWNERSHIP_CONFLICT,
            f"edited or unsafe activated paths: {', '.join(sorted(conflicts))}",
        )
    if mode == "write" and drift:
        try:
            applied = apply_file_set(
                project_root,
                {},
                owned_deletes=owned_deletes,
                inject_failure_after=inject_failure_after,
            )
        except (OSError, RuntimeError, SafetyError, ValueError) as exc:
            _activation_fail(ActivationReasonCode.OWNERSHIP_CONFLICT, str(exc))
        if any(item.action == "conflict" for item in applied):
            _activation_fail(
                ActivationReasonCode.OWNERSHIP_CONFLICT,
                "deactivation ownership changed during the transaction",
            )
        return applied, drift
    return changes, drift


__all__ = [
    "ACTIVATION_STATE_ROOT",
    "LIVE_DISCOVERY_ROOTS",
    "MAX_CONFORMANCE_GRANT_TTL",
    "ActivatedProjection",
    "ActivationReasonCode",
    "AgentActivationError",
    "AgentActivationLock",
    "ConformanceGrantReasonCode",
    "ConformanceGrantVerificationError",
    "ConformanceWorkspaceGrant",
    "EffectiveRuntimeSnapshot",
    "ProjectionDigest",
    "SignedConformanceWorkspaceGrant",
    "VerifiedConformanceWorkspaceGrant",
    "assert_verified_grant_binding",
    "activate_admitted_client",
    "activation_lock_sha256",
    "activation_state_path",
    "canonical_conformance_grant_bytes",
    "canonical_conformance_grant_sha256",
    "consume_verified_grant",
    "deactivate_client",
    "effective_runtime_sha256",
    "result_projection_digests",
    "verify_conformance_workspace_grant",
]
