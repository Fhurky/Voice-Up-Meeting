"""Validated inputs and stable result envelopes shared by CLI and MCP."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kt_scaffold import __version__

SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
ENV_PREFIX_RE = re.compile(r"^[A-Z][A-Z0-9_]*_$")
HEADER_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

BackendProfile = Literal["python-fastapi"]
PersistenceProfile = Literal["sqlalchemy-alembic"]
AgentClientId = Literal[
    "claude-code",
    "codex",
    "cursor",
    "github-copilot-vscode",
]
DEFAULT_AGENT_CLIENTS: tuple[AgentClientId, ...] = (
    "claude-code",
    "codex",
    "cursor",
    "github-copilot-vscode",
)
ArtifactAuthority = Literal["mandatory", "recommended", "project-owned"]
ArtifactKind = Literal["rule", "skill", "guidance"]
RuleScope = Literal[
    "governance", "process", "backend", "frontend", "schema", "deployment", "quality"
]
ScaffoldEntryKind = Literal["file", "directory"]


class Answers(BaseModel):
    """The complete, non-secret answer object persisted in a scaffold."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_intent: str = Field(min_length=10, max_length=4000)
    primary_domain: str
    product_name: str = Field(default="Vibe Coding Boilerplate", min_length=1, max_length=120)
    product_slug: str = "app"
    backend_profile: BackendProfile = "python-fastapi"
    persistence_profile: PersistenceProfile = "sqlalchemy-alembic"
    env_prefix: str | None = None
    api_prefix: str | None = None
    tenant_header: str = "x-tenant-id"
    locales: list[str] = Field(default_factory=lambda: ["en", "tr"], min_length=1)
    observability: bool = True
    agent_clients: list[AgentClientId] = Field(
        default_factory=lambda: list(DEFAULT_AGENT_CLIENTS), min_length=1, max_length=4
    )
    generator_version: str = __version__
    recommendation_rationale: str | None = None

    @field_validator("primary_domain", "product_slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not SLUG_RE.fullmatch(value):
            raise ValueError("must be a lowercase hyphenated slug")
        return value

    @field_validator("tenant_header")
    @classmethod
    def validate_header(cls, value: str) -> str:
        if not HEADER_RE.fullmatch(value):
            raise ValueError("must be a lowercase HTTP header name")
        return value

    @field_validator("locales")
    @classmethod
    def validate_locales(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for locale in values:
            locale = locale.lower()
            if not re.fullmatch(r"[a-z]{2}(?:-[a-z]{2})?", locale):
                raise ValueError(f"unsupported locale shape: {locale}")
            if locale not in normalized:
                normalized.append(locale)
        return normalized

    @field_validator("agent_clients")
    @classmethod
    def validate_agent_clients(cls, values: list[AgentClientId]) -> list[AgentClientId]:
        if len(values) != len(set(values)):
            raise ValueError("agent_clients must not contain duplicates")
        return sorted(values)

    @field_validator("generator_version")
    @classmethod
    def validate_generator_version(cls, value: str) -> str:
        # Persisted answers may have been produced by an older installed release.  Accept a
        # conservative SemVer shape here so update can load and advance those projects; init and
        # update still own the value and enforce the currently installed release at their command
        # boundaries.
        if not re.fullmatch(
            r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
            r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
            r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
            value,
        ):
            raise ValueError("generator_version must be a valid semantic version")
        return value

    @model_validator(mode="after")
    def resolve_profile_defaults(self) -> Answers:
        if self.env_prefix is None:
            self.env_prefix = self.product_slug.replace("-", "_").upper() + "_"
        if not ENV_PREFIX_RE.fullmatch(self.env_prefix):
            raise ValueError("env_prefix must be uppercase alphanumeric and end with underscore")
        if self.api_prefix is None:
            self.api_prefix = f"/api/{self.product_slug}/v1"
        if not re.fullmatch(
            r"/[a-z0-9][a-z0-9_-]*(?:/[a-z0-9][a-z0-9_-]*)*",
            self.api_prefix,
        ):
            raise ValueError(
                "api_prefix must be an absolute lowercase URL path without parent segments"
            )
        if self.recommendation_rationale is None:
            self.recommendation_rationale = (
                "The fixed Python profile uses FastAPI, SQLAlchemy and Alembic; backend technology "
                "is not selected by the developer or coding agent."
            )
        return self

    @property
    def target_package(self) -> str:
        return self.product_slug.replace("-", "_")


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    action: Literal["create", "update", "delete", "skip", "conflict"]
    diff_preview: str | None = None


class ToolResult(BaseModel):
    """Stable envelope returned byte-for-byte by every transport."""

    model_config = ConfigDict(extra="allow")

    ok: bool
    changes: list[Change] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class GovernanceArtifactRef(BaseModel):
    """Small, content-addressed governance inventory entry; never workspace content."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(pattern=r"^[a-z]+:[a-z0-9][a-z0-9-]*$")
    kind: ArtifactKind
    authority: ArtifactAuthority
    version: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProjectMetadata(BaseModel):
    """Bounded metadata exchanged with the governance MCP knowledge plane."""

    model_config = ConfigDict(extra="forbid")

    format: Literal[1] = 1
    blueprint_id: Literal["kt-vibecoding"] = "kt-vibecoding"
    blueprint_version: str
    project_intent: str = Field(min_length=10, max_length=4000)
    primary_domain: str = Field(pattern=SLUG_RE.pattern)
    backend_profile: BackendProfile
    persistence_profile: PersistenceProfile
    locales: list[str] = Field(min_length=1, max_length=20)
    governance_version: str
    governance_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifacts: list[GovernanceArtifactRef] = Field(max_length=512)

    @model_validator(mode="after")
    def unique_artifact_ids(self) -> ProjectMetadata:
        artifact_ids = [item.artifact_id for item in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("project metadata contains duplicate artifact ids")
        return self


class ScaffoldEntry(BaseModel):
    """One canonical entry in a deterministic scaffold bundle."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=240)
    kind: ScaffoldEntryKind
    mode: Literal["0644", "0755"]
    bytes: int = Field(ge=0, le=2 * 1024 * 1024)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_kind_fields(self) -> ScaffoldEntry:
        path = Path(self.path)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("scaffold entry path must be a safe relative POSIX path")
        if path.as_posix() != self.path or "\\" in self.path:
            raise ValueError("scaffold entry path must use normalized POSIX separators")
        if self.kind == "directory" and (self.bytes != 0 or self.sha256 is not None):
            raise ValueError("directory entries cannot carry bytes or sha256")
        if self.kind == "file" and self.sha256 is None:
            raise ValueError("file entries require sha256")
        return self


class ScaffoldArchive(BaseModel):
    """Digest-bound opaque payload metadata."""

    model_config = ConfigDict(extra="forbid")

    media_type: Literal["application/vnd.kt-scaffold.project+tar.gzip"] = (
        "application/vnd.kt-scaffold.project+tar.gzip"
    )
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=1, le=8 * 1024 * 1024)


class ScaffoldPatchSet(BaseModel):
    """Create-only manifest kept outside the archive for audit and preflight."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["create"] = "create"
    entry_count: int = Field(ge=1, le=2048)
    file_count: int = Field(ge=1, le=2048)
    uncompressed_bytes: int = Field(ge=1, le=16 * 1024 * 1024)
    entries: list[ScaffoldEntry] = Field(min_length=1, max_length=2048)

    @model_validator(mode="after")
    def validate_counts(self) -> ScaffoldPatchSet:
        if self.entry_count != len(self.entries):
            raise ValueError("entry_count does not match entries")
        files = [entry for entry in self.entries if entry.kind == "file"]
        if self.file_count != len(files):
            raise ValueError("file_count does not match file entries")
        if self.uncompressed_bytes != sum(entry.bytes for entry in files):
            raise ValueError("uncompressed_bytes does not match file entries")
        paths = [entry.path for entry in self.entries]
        if len(paths) != len(set(paths)):
            raise ValueError("scaffold patch set contains duplicate paths")
        return self


class ScaffoldBundleDescriptor(BaseModel):
    """Complete deterministic scaffold contract used by controlled offline import."""

    model_config = ConfigDict(extra="forbid")

    format: Literal[1] = 1
    bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_version: str
    answers_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tree_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    archive: ScaffoldArchive
    patch_set: ScaffoldPatchSet
    project_manifest: ProjectMetadata


class ScaffoldApplicationReceipt(BaseModel):
    """Local digest evidence emitted after transactional materialization."""

    model_config = ConfigDict(extra="forbid")

    format: Literal[1] = 1
    provenance: Literal["local-applicator-observed"] = "local-applicator-observed"
    bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_tree_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_tree_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["created", "unchanged"]
    file_count: int = Field(ge=1, le=2048)


class LocalMcpCreationReceipt(BaseModel):
    """Observed evidence from the installed local MCP creation boundary."""

    model_config = ConfigDict(extra="forbid")

    format: Literal[1] = 1
    provenance: Literal["local-mcp-observed"] = "local-mcp-observed"
    generator_version: str
    status: Literal["created", "unchanged"]
    expected_tree_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_tree_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_count: int = Field(ge=1, le=2048)
    entry_count: int = Field(ge=1, le=2048)


class GovernanceUpdateItem(BaseModel):
    """One intent-level alignment request, not a remote filesystem mutation."""

    model_config = ConfigDict(extra="forbid")

    artifact: GovernanceArtifactRef
    action: Literal["add", "align", "review", "preserve", "deprecate"]
    intent: str
    required_behaviors: list[str] = Field(default_factory=list)
    local_instruction: str


class GovernanceUpdateProposal(BaseModel):
    """Versioned proposal negotiated and applied by the local agent."""

    model_config = ConfigDict(extra="forbid")

    format: Literal[1] = 1
    proposal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    blueprint_id: Literal["kt-vibecoding"] = "kt-vibecoding"
    from_governance_version: str
    to_governance_version: str
    target_governance_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    items: list[GovernanceUpdateItem]
    unchanged: int = Field(ge=0)

    @model_validator(mode="after")
    def unique_item_ids(self) -> GovernanceUpdateProposal:
        artifact_ids = [item.artifact.artifact_id for item in self.items]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("governance proposal contains duplicate artifact ids")
        return self


class ReconciliationDecision(BaseModel):
    """Auditable local-agent disposition for one proposed governance change."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(pattern=r"^[a-z]+:[a-z0-9][a-z0-9-]*$")
    decision: Literal["accepted", "adapted", "deferred", "rejected"]
    rationale: str = Field(min_length=3, max_length=2000)
    preserved_behaviors: list[str] = Field(default_factory=list)


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[0-9]{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=8, max_length=120)
    scope: RuleScope
    authority: ArtifactAuthority = "recommended"
    priority: int = Field(ge=0, le=999)
    trigger: Literal["always", "path-match", "on-demand"]
    applies_to: list[str] = Field(default_factory=list)
    gate: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_./* -]+$")
    body: str
    source: Path

    @model_validator(mode="after")
    def path_trigger_has_globs(self) -> Rule:
        if self.title != self.title.strip() or "\n" in self.title:
            raise ValueError("rule title must be a trimmed single line")
        if len(self.applies_to) != len(set(self.applies_to)):
            raise ValueError(f"rule {self.id} contains duplicate applies_to globs")
        for glob in self.applies_to:
            if not glob or glob.startswith("/") or any(part == ".." for part in Path(glob).parts):
                raise ValueError(f"rule {self.id} contains an unsafe applies_to glob")
        if self.trigger == "path-match" and not self.applies_to:
            raise ValueError(f"path-scoped rule {self.id} requires applies_to")
        if self.trigger == "always" and self.applies_to:
            raise ValueError(f"non-path rule {self.id} cannot declare applies_to")
        return self
