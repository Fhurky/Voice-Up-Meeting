"""Strict, serializable models for canonical agent projection compilation."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


class StrictModel(BaseModel):
    """Immutable model that rejects fields the compiler does not understand."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def reconstruct_exact_model[ModelT: BaseModel](
    value: object,
    expected_type: type[ModelT],
    *,
    allowed_model_types: frozenset[type[BaseModel]],
) -> ModelT:
    """Rebuild strict models from declared fields without invoking instance methods."""

    if type(value) is not expected_type or expected_type not in allowed_model_types:
        raise ValueError(f"boundary requires exact {expected_type.__name__} type")

    def declared_value(item: object) -> object:
        if isinstance(item, BaseModel):
            model_type = type(item)
            if model_type not in allowed_model_types:
                raise ValueError(f"unexpected nested model type: {model_type.__name__}")
            state = object.__getattribute__(item, "__dict__")
            declared_fields = model_type.model_fields
            if set(state) != set(declared_fields):
                raise ValueError(f"{model_type.__name__} contains unexpected runtime fields")
            return {name: declared_value(state[name]) for name in declared_fields}
        if isinstance(item, tuple):
            return tuple(declared_value(member) for member in item)
        if isinstance(item, list):
            return [declared_value(member) for member in item]
        if isinstance(item, dict):
            return {key: declared_value(member) for key, member in item.items()}
        return item

    return expected_type.model_validate(declared_value(value), strict=True)


class ReasonCode(StrEnum):
    ASSET_INVALID = "AP_ASSET_INVALID"
    DOCUMENT_INVALID = "AP_DOCUMENT_INVALID"
    SCHEMA_INVALID = "AP_SCHEMA_INVALID"
    SCHEMA_VALIDATION_FAILED = "AP_SCHEMA_VALIDATION_FAILED"
    SEMANTIC_VALIDATION_FAILED = "AP_SEMANTIC_VALIDATION_FAILED"
    MATRIX_INVALID = "AP_MATRIX_INVALID"
    REQUIRED_CAPABILITY_UNMAPPED = "AP_REQUIRED_CAPABILITY_UNMAPPED"
    FORBIDDEN_CAPABILITY = "AP_FORBIDDEN_CAPABILITY"
    MATERIAL_SEMANTIC_LOSS = "AP_MATERIAL_SEMANTIC_LOSS"
    ADAPTER_NOT_FOUND = "AP_ADAPTER_NOT_FOUND"
    OUTPUT_PATH_INVALID = "AP_OUTPUT_PATH_INVALID"
    OUTPUT_VALIDATION_FAILED = "AP_OUTPUT_VALIDATION_FAILED"
    DUPLICATE_OUTPUT = "AP_DUPLICATE_OUTPUT"


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    DEGRADED = "degraded"
    UNMAPPED = "unmapped"
    FORBIDDEN = "forbidden"


class ProjectionKind(StrEnum):
    NATIVE = "native"
    COMPATIBLE = "compatible"
    TRANSFORMED = "transformed"
    NONE = "none"


class Maturity(StrEnum):
    GA = "ga"
    PREVIEW = "preview"
    BETA = "beta"
    EXPERIMENTAL = "experimental"
    UNSPECIFIED = "unspecified"


class Lifecycle(StrEnum):
    CURRENT = "current"
    LEGACY = "legacy"
    DEPRECATED = "deprecated"


class AdapterStrategy(StrEnum):
    EMIT = "emit"
    IMPORT_WRAPPER = "import-wrapper"
    TRANSLATE = "translate"
    OMIT = "omit"


class Lossiness(StrEnum):
    NONE = "none"
    BOUNDED = "bounded"
    MATERIAL = "material"


class ConformanceStatus(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"


class AdmissionState(StrEnum):
    RESEARCH = "research"
    CANDIDATE = "candidate"
    ADMITTED = "admitted"
    DENIED = "denied"


class GenerationStatus(StrEnum):
    NOT_IMPLEMENTED = "not_implemented"
    CANDIDATE = "candidate"
    IMPLEMENTED = "implemented"


class DiscoveryBinding(StrictModel):
    scope: str = Field(min_length=1)
    location: str = Field(min_length=1)


class CapabilityMapping(StrictModel):
    capability: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    applies_to_surfaces: tuple[str, ...] = Field(min_length=1)
    status: SupportStatus
    projection: ProjectionKind
    maturity: Maturity
    lifecycle: Lifecycle
    volatile: StrictBool
    adapter_strategy: AdapterStrategy
    format: str = Field(min_length=1)
    lossiness: Lossiness
    discovery: tuple[DiscoveryBinding, ...]
    limitations: tuple[str, ...]
    source_ids: tuple[str, ...] = Field(min_length=1)
    conformance_status: ConformanceStatus

    @model_validator(mode="after")
    def validate_loss_claim(self) -> CapabilityMapping:
        if self.status == SupportStatus.SUPPORTED and self.lossiness != Lossiness.NONE:
            raise ValueError("supported mappings must declare lossiness=none")
        if self.status == SupportStatus.DEGRADED and (
            self.lossiness == Lossiness.NONE or not self.limitations
        ):
            raise ValueError("degraded mappings require non-zero loss and limitations")
        if self.status in {SupportStatus.UNMAPPED, SupportStatus.FORBIDDEN} and (
            self.projection != ProjectionKind.NONE or self.adapter_strategy != AdapterStrategy.OMIT
        ):
            raise ValueError("unmapped and forbidden mappings must use projection=none and omit")
        return self


class MatrixAdapter(StrictModel):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    generation_status: GenerationStatus
    client_version_range: str = Field(min_length=1)
    candidate_inventory_ref: str = Field(pattern=r"^client:[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class MatrixAdmission(StrictModel):
    state: AdmissionState
    reason: str = Field(min_length=1)


class MatrixConformance(StrictModel):
    status: ConformanceStatus
    runtime_version: str | None
    model_profile_digest: str | None
    projection_digest: str | None
    test_run_id: str | None


class MatrixClient(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    vendor: str = Field(min_length=1)
    product: str = Field(min_length=1)
    surfaces: tuple[str, ...] = Field(min_length=1)
    adapter: MatrixAdapter
    admission: MatrixAdmission
    conformance: MatrixConformance
    mappings: tuple[CapabilityMapping, ...] = Field(min_length=1)


class MatrixCapability(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    required: StrictBool
    intent: str = Field(min_length=1)


class MatrixSource(StrictModel):
    url: str = Field(pattern=r"^https://")
    retrieved_at: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class MatrixContract(StrictModel):
    schema_version: Literal["1.0"]
    schema_path: Literal["agent-platform/agent-contract.schema.json"]


class MatrixSemantics(StrictModel):
    supported: str
    degraded: str
    unmapped: str
    forbidden: str


class MatrixPolicy(StrictModel):
    mapping_claim_only: StrictBool
    support_values: tuple[SupportStatus, ...]
    projection_values: tuple[ProjectionKind, ...]
    maturity_values: tuple[Maturity, ...]
    lifecycle_values: tuple[Lifecycle, ...]
    adapter_strategy_values: tuple[AdapterStrategy, ...]
    lossiness_values: tuple[Lossiness, ...]
    conformance_values: tuple[ConformanceStatus, ...]
    admission_values: tuple[AdmissionState, ...]
    generation_values: tuple[GenerationStatus, ...]
    semantics: MatrixSemantics
    external_controls: tuple[str, ...] = Field(min_length=1)
    admission_rule: str = Field(min_length=1)
    requirement_semantics: str = Field(min_length=1)
    maturity_rule: str = Field(min_length=1)
    lifecycle_rule: str = Field(min_length=1)
    state_boundary: str = Field(min_length=1)
    manifest_capability_bindings: dict[str, str]


class RuntimeCandidateInventoryRef(StrictModel):
    schema_path: Literal["agent-platform/runtime-candidate.schema.json"]
    data_path: str = Field(pattern=r"^agent-platform/conformance/candidates/[a-z0-9.-]+\.yml$")
    claim_boundary: str = Field(min_length=1)


class ClientCapabilityMatrix(StrictModel):
    schema_version: Literal["1.0"]
    kind: Literal["ClientCapabilityMatrix"]
    as_of: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    status: Literal["research"]
    contract: MatrixContract
    runtime_candidate_inventory: RuntimeCandidateInventoryRef
    policy: MatrixPolicy
    capabilities: tuple[MatrixCapability, ...] = Field(min_length=1)
    sources: dict[str, MatrixSource]
    clients: tuple[MatrixClient, ...] = Field(min_length=1)


class ContentReference(StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DocumentationSource(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    url: str = Field(pattern=r"^https://")
    retrieved_at: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class CanonicalAgentPackage(StrictModel):
    agent_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    contract: dict[str, Any]
    policy: dict[str, Any]
    instructions: str = Field(min_length=1)
    inputs: tuple[ContentReference, ...] = Field(min_length=3, max_length=3)

    @property
    def description(self) -> str:
        return str(self.contract["metadata"]["description"])

    @property
    def max_duration_seconds(self) -> int:
        return int(self.contract["runtime"]["budgets"]["max_duration_seconds"])


class CanonicalPlatform(StrictModel):
    agents: tuple[CanonicalAgentPackage, ...] = Field(min_length=1)
    capability_matrix: ClientCapabilityMatrix
    platform_inputs: tuple[ContentReference, ...] = Field(min_length=4)


class MappedField(StrictModel):
    canonical: str = Field(min_length=1)
    projected_to: tuple[str, ...] = Field(min_length=1)


class SemanticLoss(StrictModel):
    code: str = Field(pattern=r"^AP_LOSS_[A-Z0-9_]+$")
    canonical: str = Field(min_length=1)
    lossiness: Literal["bounded"] = "bounded"
    disposition: Literal["omitted", "instruction-only", "inherited", "external-control"]
    statement: str = Field(min_length=1)


class ExternalControl(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    statement: str = Field(min_length=1)


class RenderedProjection(StrictModel):
    content: str = Field(min_length=1)
    mapped_fields: tuple[MappedField, ...] = Field(min_length=1)
    semantic_losses: tuple[SemanticLoss, ...] = Field(min_length=1)
    external_controls: tuple[ExternalControl, ...] = Field(min_length=1)
    validations: tuple[str, ...] = Field(min_length=1)


class ProjectionArtifact(StrictModel):
    client_id: str
    agent_id: str
    relative_path: str
    media_type: Literal["text/markdown", "application/toml"]
    adapter_id: str
    adapter_version: str
    client_version_range: str
    generation_status: Literal["implemented"]
    candidate_inventory_ref: str
    runtime_admission: Literal["research"]
    runtime_conformance: Literal["not_run"]
    canonical_schema_version: Literal["1.0"]
    canonical_contract_version: str
    documentation_sources: tuple[DocumentationSource, ...] = Field(min_length=1)
    omitted_optional_capabilities: tuple[str, ...]
    content: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inputs: tuple[ContentReference, ...]
    mapped_fields: tuple[MappedField, ...]
    semantic_losses: tuple[SemanticLoss, ...]
    external_controls: tuple[ExternalControl, ...]
    validations: tuple[str, ...]

    @model_validator(mode="after")
    def validate_content_and_path(self) -> ProjectionArtifact:
        path = PurePosixPath(self.relative_path)
        if (
            path.is_absolute()
            or path.as_posix() != self.relative_path
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in self.relative_path
        ):
            raise ValueError("projection path must be a normalized relative POSIX path")
        actual = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if actual != self.sha256:
            raise ValueError("projection content digest does not match content")
        if not self.content.endswith("\n") or "\r" in self.content:
            raise ValueError("projection content must use LF and end with one newline")
        return self


class ManifestArtifact(StrictModel):
    client_id: str
    agent_id: str
    relative_path: str
    media_type: str
    adapter_id: str
    adapter_version: str
    client_version_range: str
    generation_status: Literal["implemented"]
    candidate_inventory_ref: str
    runtime_admission: Literal["research"]
    runtime_conformance: Literal["not_run"]
    canonical_schema_version: Literal["1.0"]
    canonical_contract_version: str
    documentation_sources: tuple[DocumentationSource, ...] = Field(min_length=1)
    omitted_optional_capabilities: tuple[str, ...]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inputs: tuple[ContentReference, ...]
    mapped_fields: tuple[MappedField, ...]
    semantic_losses: tuple[SemanticLoss, ...]
    external_controls: tuple[ExternalControl, ...]
    validations: tuple[str, ...]


class ProjectionManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["AgentProjectionLock"] = "AgentProjectionLock"
    compiler_id: Literal["kt-scaffold-agent-projection"] = "kt-scaffold-agent-projection"
    compiler_version: str
    generation_status: Literal["generated"] = "generated"
    activation_status: Literal["not_activated"] = "not_activated"
    runtime_admission: Literal["research"] = "research"
    runtime_conformance: Literal["not_run"] = "not_run"
    inputs: tuple[ContentReference, ...] = Field(min_length=1)
    artifacts: tuple[ManifestArtifact, ...] = Field(min_length=1)


_PROJECTION_COMPONENT_MODELS: frozenset[type[BaseModel]] = frozenset(
    {
        ContentReference,
        DocumentationSource,
        ExternalControl,
        ManifestArtifact,
        MappedField,
        ProjectionArtifact,
        ProjectionManifest,
        SemanticLoss,
    }
)


class CompilationResult(StrictModel):
    artifacts: tuple[ProjectionArtifact, ...]
    manifest: ProjectionManifest
    lock_path: Literal["PROJECTIONS.lock.json"] = "PROJECTIONS.lock.json"
    lock_content: str
    lock_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_compilation_coherence(self) -> CompilationResult:
        try:
            artifacts = tuple(
                reconstruct_exact_model(
                    item,
                    ProjectionArtifact,
                    allowed_model_types=_PROJECTION_COMPONENT_MODELS,
                )
                for item in self.artifacts
            )
            manifest = reconstruct_exact_model(
                self.manifest,
                ProjectionManifest,
                allowed_model_types=_PROJECTION_COMPONENT_MODELS,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("compiled projection models failed exact reconstruction") from exc
        if hashlib.sha256(self.lock_content.encode("utf-8")).hexdigest() != self.lock_sha256:
            raise ValueError("projection lock digest does not match lock content")
        try:
            locked_manifest = ProjectionManifest.model_validate_json(self.lock_content)
        except ValueError as exc:
            raise ValueError("projection lock content is not a valid manifest") from exc
        canonical_lock = (
            json.dumps(
                locked_manifest.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        if self.lock_content != canonical_lock:
            raise ValueError("projection lock content is not canonical JSON")
        if locked_manifest != manifest:
            raise ValueError("projection lock content does not match the result manifest")

        artifact_paths = tuple(item.relative_path for item in artifacts)
        artifact_identities = tuple((item.client_id, item.agent_id) for item in artifacts)
        if len(artifact_paths) != len(set(artifact_paths)):
            raise ValueError("compiled projection paths must be unique")
        if len(artifact_identities) != len(set(artifact_identities)):
            raise ValueError("compiled client and agent identities must be unique")
        expected_manifest_artifacts = tuple(
            ManifestArtifact.model_validate(item.model_dump(exclude={"content"}))
            for item in sorted(artifacts, key=lambda value: value.relative_path)
        )
        if manifest.artifacts != expected_manifest_artifacts:
            raise ValueError("projection manifest artifact inventory does not match artifacts")

        manifest_input_paths = tuple(item.path for item in manifest.inputs)
        if manifest_input_paths != tuple(sorted(manifest_input_paths)) or len(
            manifest_input_paths
        ) != len(set(manifest_input_paths)):
            raise ValueError("projection manifest inputs must be unique and sorted")
        manifest_inputs = {item.path: item for item in manifest.inputs}
        for artifact in artifacts:
            artifact_input_paths = tuple(item.path for item in artifact.inputs)
            if artifact_input_paths != tuple(sorted(artifact_input_paths)) or len(
                artifact_input_paths
            ) != len(set(artifact_input_paths)):
                raise ValueError("projection artifact inputs must be unique and sorted")
            if any(manifest_inputs.get(item.path) != item for item in artifact.inputs):
                raise ValueError("projection manifest inputs do not bind every artifact input")
        return self

    def files(self) -> dict[str, bytes]:
        """Return inert bytes keyed by intended path; this method never writes them."""

        validated = revalidate_compilation_result(self)
        files = {item.relative_path: item.content.encode("utf-8") for item in validated.artifacts}
        files[validated.lock_path] = validated.lock_content.encode("utf-8")
        return files


_COMPILATION_RESULT_MODELS: frozenset[type[BaseModel]] = frozenset(
    {*_PROJECTION_COMPONENT_MODELS, CompilationResult}
)


def revalidate_compilation_result(value: object) -> CompilationResult:
    """Rebuild a result at a privileged boundary so model_copy cannot bypass validators."""

    return reconstruct_exact_model(
        value,
        CompilationResult,
        allowed_model_types=_COMPILATION_RESULT_MODELS,
    )


class AggregationReasonCode(StrEnum):
    MISSING_WORKER = "AGG_MISSING_WORKER"
    DUPLICATE_WORKER = "AGG_DUPLICATE_WORKER"
    INVALID_SCHEMA = "AGG_INVALID_SCHEMA"
    RAW_SOURCE_REJECTED = "AGG_RAW_SOURCE_REJECTED"
    INTEGRITY_FAILURE = "AGG_INTEGRITY_FAILURE"
    REQUEST_DIGEST_MISMATCH = "AGG_REQUEST_DIGEST_MISMATCH"
    TIMEOUT = "AGG_TIMEOUT"
    LOW_CONFIDENCE = "AGG_LOW_CONFIDENCE"
    PROHIBITED_AGENT = "AGG_PROHIBITED_AGENT"
    UNEXPECTED_WORKER = "AGG_UNEXPECTED_WORKER"
    UNKNOWN_POLICY_VERSION = "AGG_UNKNOWN_POLICY_VERSION"
    SCORE_PASS = "AGG_THRESHOLD_PASS"  # noqa: S105 - decision code, not a credential
    THRESHOLD_WARNING = "AGG_THRESHOLD_WARNING"
    THRESHOLD_FAIL = "AGG_THRESHOLD_FAIL"


class EvidenceReference(StrictModel):
    artifact_id: str = Field(pattern=r"^evidence:[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$", max_length=160)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorkerFinding(StrictModel):
    finding_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$", max_length=120)
    risk_score_basis_points: StrictInt = Field(ge=0, le=10_000)
    confidence_basis_points: StrictInt = Field(ge=0, le=10_000)
    evidence: tuple[EvidenceReference, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def unique_evidence(self) -> WorkerFinding:
        identities = [(item.artifact_id, item.sha256) for item in self.evidence]
        if len(identities) != len(set(identities)):
            raise ValueError("finding evidence references must be unique")
        return self


class WorkerFindingReportPayload(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["FindingReport"] = "FindingReport"
    output_contract: Literal["schema:finding-report"] = "schema:finding-report"
    worker: str = Field(pattern=r"^agent:[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["completed", "timeout"]
    findings: tuple[WorkerFinding, ...] = Field(max_length=128)

    @model_validator(mode="after")
    def validate_findings(self) -> WorkerFindingReportPayload:
        finding_ids = [item.finding_id for item in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("finding ids must be unique within a worker report")
        if self.status == "timeout" and self.findings:
            raise ValueError("timed-out worker reports cannot contain findings")
        return self


class WorkerFindingReport(WorkerFindingReportPayload):
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorkerWeight(StrictModel):
    worker: str = Field(pattern=r"^agent:[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    weight_micros: StrictInt = Field(gt=0, le=10_000_000)


class AggregationThresholds(StrictModel):
    fail_score_basis_points: StrictInt = Field(ge=0, le=10_000)
    warning_score_basis_points: StrictInt = Field(ge=0, le=10_000)
    confidence_floor_basis_points: StrictInt = Field(ge=0, le=10_000)
    compliance_baseline_basis_points: Literal[10_000] = 10_000

    @model_validator(mode="after")
    def ordered_thresholds(self) -> AggregationThresholds:
        if self.fail_score_basis_points <= self.warning_score_basis_points:
            raise ValueError("fail threshold must be greater than warning threshold")
        return self


class GovernedReviewConfiguration(StrictModel):
    aggregator_version: Literal["1.0.0"] = "1.0.0"
    scoring_algorithm: Literal["max-worker-risk-weighted-mean-v1"] = (
        "max-worker-risk-weighted-mean-v1"
    )
    orchestration_ref: Literal["orchestration:governed-review"] = "orchestration:governed-review"
    orchestration_version: str
    orchestration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_ref: Literal["policy:governed-review-aggregation"] = "policy:governed-review-aggregation"
    policy_version: str
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    required_workers: tuple[str, ...] = Field(min_length=4, max_length=4)
    prohibited_workers: tuple[str, ...] = Field(min_length=1)
    weights: tuple[WorkerWeight, ...] = Field(min_length=4, max_length=4)
    thresholds: AggregationThresholds
    raw_source_visible_to_aggregator: Literal[False] = False
    verify_result_integrity: Literal[True] = True
    thresholds_calibrated: Literal[False] = False
    runtime_admission: Literal[False] = False
    production_decision: Literal[False] = False


class WorkerAggregationTrace(StrictModel):
    worker: str = Field(pattern=r"^agent:[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    state: Literal[
        "valid",
        "missing",
        "duplicate",
        "invalid",
        "tampered",
        "request-mismatch",
        "timeout",
        "low-confidence",
        "prohibited",
        "unexpected",
    ]
    claimed_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    observed_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finding_count: StrictInt | None = Field(default=None, ge=0, le=128)
    risk_score_basis_points: StrictInt | None = Field(default=None, ge=0, le=10_000)
    weight_micros: StrictInt | None = Field(default=None, gt=0, le=10_000_000)


class GovernedReviewDecision(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    kind: Literal["GovernedReviewDecision"] = "GovernedReviewDecision"
    decision: Literal["PASS", "WARNING", "FAIL", "MANUAL_REVIEW"]
    reason_codes: tuple[AggregationReasonCode, ...] = Field(min_length=1)
    aggregator_version: Literal["1.0.0"] = "1.0.0"
    scoring_algorithm: Literal["max-worker-risk-weighted-mean-v1"] = (
        "max-worker-risk-weighted-mean-v1"
    )
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    orchestration_ref: Literal["orchestration:governed-review"]
    orchestration_version: str
    orchestration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_ref: Literal["policy:governed-review-aggregation"]
    policy_version: str
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    worker_traces: tuple[WorkerAggregationTrace, ...]
    risk_score_basis_points: StrictInt | None = Field(default=None, ge=0, le=10_000)
    compliance_score_basis_points: StrictInt | None = Field(default=None, ge=0, le=10_000)
    thresholds_calibrated: Literal[False] = False
    runtime_admission: Literal[False] = False
    production_decision: Literal[False] = False
