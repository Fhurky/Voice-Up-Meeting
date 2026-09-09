"""Strict validation for the mandatory, fixed technology profile."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Eligibility(StrictProfileModel):
    all_of: tuple[
        Literal["user_interface_is_limited_to_prompt_chat_and_history"],
        Literal["no_general_purpose_business_ui"],
        Literal["no_separate_frontend_required"],
    ]


class SeparatedWeb(StrictProfileModel):
    frontend: Literal["react-spa"]
    backend: Literal["python-fastapi"]
    boundary: Literal["http-api"]


class ChatOnly(StrictProfileModel):
    framework: Literal["streamlit"]
    boundary: Literal["single-python-application"]
    eligibility: Eligibility
    approval: Literal["accepted-prd-must-declare-this-mode"]


class AllowedModes(StrictProfileModel):
    separated_web: SeparatedWeb = Field(alias="separated-web")
    chat_only_fullstack: ChatOnly = Field(alias="chat-only-fullstack")


class ApplicationModes(StrictProfileModel):
    default: Literal["separated-web"]
    allowed: AllowedModes


class Realtime(StrictProfileModel):
    server_sent_events: Literal["allowed"]
    web_socket: Literal["exception-only"]


class Architecture(StrictProfileModel):
    frontend_backend_separation: Literal["required-in-separated-web"]
    server_side_rendering: Literal["forbidden"]
    nextjs: Literal["forbidden"]
    realtime: Realtime


class Frontend(StrictProfileModel):
    runtime: Literal["nodejs-22"]
    language: Literal["typescript-strict"]
    type_checker: Literal["typescript-7-native"]
    framework: Literal["react-19"]
    build: Literal["vite-8"]
    routing: Literal["react-router-8"]
    rendering: Literal["client-side-spa"]
    api_contract: Literal["openapi-typescript-7"]
    api_contract_compiler_compatibility: Literal["typescript-5.9"]
    testing: Literal["vitest-4"]
    package_manager: Literal["npm-with-committed-lockfile"]


class Backend(StrictProfileModel):
    language: Literal["python-3.13"]
    minimum_language_version: Literal["3.13"]
    framework: Literal["fastapi"]
    validation: Literal["pydantic-2"]
    server: Literal["uvicorn"]
    concurrency: Literal["async"]
    testing: Literal["pytest"]
    alternatives: Literal["forbidden"]


class VectorPersistence(StrictProfileModel):
    status: Literal["allowed-with-accepted-prd"]
    database: Literal["same-postgresql-database"]
    extension: Literal["pgvector"]
    sql_extension_name: Literal["vector"]
    minimum_version: Literal["0.8.5"]
    python_binding: Literal["pgvector-python-sqlalchemy"]
    activation: Literal["reviewed-alembic-migration"]
    alternative_vector_database: Literal["forbidden"]
    data_type: Literal["vector-with-fixed-dimensions"]
    distance_metrics: list[Literal["cosine", "inner-product", "l2"]]
    search_modes: list[Literal["exact", "hnsw", "ivfflat"]]

    @model_validator(mode="after")
    def fixed_vector_options(self) -> VectorPersistence:
        if self.distance_metrics != ["cosine", "inner-product", "l2"]:
            raise ValueError("vector distance metrics must contain the fixed ordered set")
        if self.search_modes != ["exact", "hnsw", "ivfflat"]:
            raise ValueError("vector search modes must contain the fixed ordered set")
        return self


class Persistence(StrictProfileModel):
    engine: Literal["postgresql-17"]
    orm: Literal["sqlalchemy-2-async"]
    driver: Literal["asyncpg"]
    migrations: Literal["alembic"]
    schema_authority: Literal["app/backend/app/domain/models"]
    vector: VectorPersistence


class EmbeddingPrdContract(StrictProfileModel):
    required: list[
        Literal[
            "provider",
            "model-id",
            "model-version",
            "dimensions",
            "normalization",
            "distance-metric",
            "index-strategy",
            "quality-and-latency-thresholds",
        ]
    ]

    @model_validator(mode="after")
    def fixed_required_fields(self) -> EmbeddingPrdContract:
        expected = [
            "provider",
            "model-id",
            "model-version",
            "dimensions",
            "normalization",
            "distance-metric",
            "index-strategy",
            "quality-and-latency-thresholds",
        ]
        if self.required != expected:
            raise ValueError("embedding PRD fields must contain the fixed ordered set")
        return self


class EmbeddingStorage(StrictProfileModel):
    vector_store: Literal["persistence.pgvector"]
    model_identity: Literal["required-per-row"]
    source_identity: Literal["required-per-row"]
    content_hash: Literal["required-per-row"]
    tenant_scope: Literal["required-in-similarity-query"]
    sensitive_data: Literal["classification-minimization-and-retention-required"]


class EmbeddingLifecycle(StrictProfileModel):
    reembedding: Literal["versioned-backfill-validate-and-cutover"]
    mixed_model_search: Literal["forbidden"]
    destructive_rebuild: Literal["explicit-authorization-required"]


class Embeddings(StrictProfileModel):
    status: Literal["allowed-with-accepted-prd"]
    generation_boundary: Literal["application-port-with-infrastructure-adapter"]
    provider: Literal["approved-internal-or-on-premise"]
    runtime_egress: Literal["forbidden"]
    runtime_model_download: Literal["forbidden"]
    prd_contract: EmbeddingPrdContract
    storage: EmbeddingStorage
    lifecycle: EmbeddingLifecycle


class Security(StrictProfileModel):
    authentication: Literal["jwt-access-token"]
    authorization: Literal["rbac-with-application-super-admin"]
    tenant_isolation: Literal["required"]
    secrets: Literal["runtime-environment-or-precreated-kubernetes-secret"]


class Logging(StrictProfileModel):
    format: Literal["structured-json-to-stdout"]
    request_correlation: Literal["required"]
    sensitive_data: Literal["forbidden"]


class Monitoring(StrictProfileModel):
    collector: Literal["opentelemetry-collector"]
    metrics_store: Literal["prometheus"]
    trace_store: Literal["tempo"]
    log_store: Literal["loki"]
    dashboard: Literal["grafana"]


class ApplicationSignals(StrictProfileModel):
    baseline: Literal["health-readiness-and-structured-request-logs"]
    capability_specific_metrics_and_traces: Literal["accepted-prd-owned"]


class Observability(StrictProfileModel):
    enabled_by_default: Literal[True]
    logging: Logging
    monitoring: Monitoring
    application_signals: ApplicationSignals


class Delivery(StrictProfileModel):
    local: Literal["docker-compose"]
    cluster: Literal["kubernetes-with-helm"]
    runtime_egress: Literal["denied"]
    images: Literal["internal-registry-and-digest-pinned"]


class UpgradeTriggers(StrictProfileModel):
    security_scanner_finding: Literal["mandatory-upgrade-to-nearest-fixed-release"]
    upstream_security_advisory: Literal["mandatory-upgrade-to-nearest-fixed-release"]


class AdoptionWindow(StrictProfileModel):
    minimum_release_age_days: Literal[30]
    security_fix_exception: Literal["immediate-adoption-allowed"]
    downgrade_to_satisfy_window: Literal["forbidden"]


class Maintenance(StrictProfileModel):
    version_pins: Literal["governance-owned-floors"]
    upgrade_triggers: UpgradeTriggers
    adoption_window: AdoptionWindow
    evidence: list[
        Literal[
            "registry-release-date",
            "security-advisory-id",
            "dependency-admission-ledger",
            "compatibility-test-evidence",
        ]
    ]
    scanners: list[Literal["trivy", "semgrep", "dependabot", "osv"]]

    @model_validator(mode="after")
    def fixed_ordered_evidence(self) -> Maintenance:
        expected_evidence = [
            "registry-release-date",
            "security-advisory-id",
            "dependency-admission-ledger",
            "compatibility-test-evidence",
        ]
        if self.evidence != expected_evidence:
            raise ValueError("maintenance evidence must contain the fixed ordered set")
        if self.scanners != ["trivy", "semgrep", "dependabot", "osv"]:
            raise ValueError("maintenance scanners must contain the fixed ordered set")
        return self


class TechnologyProfile(StrictProfileModel):
    schema_version: Literal[2]
    profile_id: Literal["kt-vibecoding-python-web-v2"]
    authority: Literal["mandatory"]
    status: Literal["approved-baseline"]
    application_modes: ApplicationModes
    architecture: Architecture
    frontend: Frontend
    backend: Backend
    persistence: Persistence
    embeddings: Embeddings
    security: Security
    observability: Observability
    delivery: Delivery
    maintenance: Maintenance
    forbidden: list[
        Literal[
            "nextjs",
            "server-side-rendering",
            "nodejs-backend",
            "nestjs",
            "prisma",
            "mixed-python-and-node-backend",
            "agent-selected-backend-framework",
        ]
    ]

    @model_validator(mode="after")
    def fixed_forbidden_set(self) -> TechnologyProfile:
        expected = [
            "nextjs",
            "server-side-rendering",
            "nodejs-backend",
            "nestjs",
            "prisma",
            "mixed-python-and-node-backend",
            "agent-selected-backend-framework",
        ]
        if self.forbidden != expected:
            raise ValueError("forbidden technologies must contain the fixed ordered set")
        return self


def load_technology_profile(path: str | Path) -> TechnologyProfile:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return TechnologyProfile.model_validate(payload)
