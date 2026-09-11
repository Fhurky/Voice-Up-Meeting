"""Schema authority for tenant-owned recordings, profiles, samples and durable jobs."""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import VECTOR  # type: ignore[import-untyped]
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.domain.models.mixins import AuditSoftDeleteMixin, new_public_id


class Recording(AuditSoftDeleteMixin, Base):
    __tablename__ = "recording"
    __table_args__ = (
        UniqueConstraint("tenant_id", "recording_id", name="uq_recording_tenant_identity"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_recording_tenant_retry_key"),
        CheckConstraint("size_bytes > 0 AND duration_seconds > 0", name="recording_positive"),
        CheckConstraint("format IN ('WAV', 'FLAC')", name="recording_format"),
        Index(
            "ix_recording_active_tenant",
            "tenant_id",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
        {
            "comment": "Speaker identity source audio metadata; opaque owned files follow reference-aware retention."
        },
    )
    recording_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Owning application tenant; all references are tenant-qualified.",
    )
    storage_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="Opaque server-generated filename beneath the configured owned audio root.",
    )
    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 of the original uploaded bytes, used for semantic idempotency.",
    )
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    format: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="Decoded audio container: WAV or FLAC; mirrored by RecordingResponse.",
    )
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Tenant-scoped upload retry key; cleared after its retention period.",
    )
    idempotency_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Earliest cleanup time; active sample or job references always prevent cleanup.",
    )
    file_removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SpeakerProfile(AuditSoftDeleteMixin, Base):
    __tablename__ = "speaker_profile"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "speaker_profile_id", name="uq_speaker_profile_tenant_identity"
        ),
        CheckConstraint("sample_count BETWEEN 1 AND 20", name="speaker_profile_sample_count"),
        ForeignKeyConstraint(
            ["tenant_id", "meeting_recording_id"],
            ["recording.tenant_id", "recording.recording_id"],
            ondelete="RESTRICT",
            name="fk_speaker_profile_meeting_recording",
        ),
        CheckConstraint(
            "(meeting_embedding IS NULL AND meeting_model_id IS NULL AND "
            "meeting_model_revision IS NULL AND meeting_preprocessing_version IS NULL AND "
            "meeting_source_sha256 IS NULL AND meeting_recording_id IS NULL) OR "
            "(meeting_embedding IS NOT NULL AND meeting_model_id IS NOT NULL AND "
            "meeting_model_revision IS NOT NULL AND meeting_preprocessing_version IS NOT NULL AND "
            "meeting_source_sha256 IS NOT NULL AND meeting_recording_id IS NOT NULL)",
            name="speaker_profile_meeting_population",
        ),
        Index(
            "ix_speaker_profile_active_tenant_model",
            "tenant_id",
            "model_revision",
            postgresql_where=text("is_deleted = false"),
        ),
        {
            "comment": "Speaker identity profile with an equal-weight normalized mean of verified source samples."
        },
    )
    speaker_profile_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Owning application tenant; identity matching never crosses this boundary.",
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    model_revision: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Immutable embedding population identifier; different versions are never scored together.",
    )
    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(192),
        nullable=False,
        comment="L2-normalized 192-dimensional ECAPA centroid; exact cosine search only.",
    )
    source_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Canonical hash of the sorted active sample source hashes composing this centroid.",
    )
    meeting_embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(256),
        nullable=True,
        comment="Separate normalized Community embedding component for verified meeting memory; never scored with ECAPA.",
    )
    meeting_model_id: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        comment="Immutable package identity of the optional meeting embedding component.",
    )
    meeting_model_revision: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Immutable revision of the separate 256-dimensional meeting population.",
    )
    meeting_preprocessing_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Versioned meeting quality and final retained-audio preprocessing lineage.",
    )
    meeting_source_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 of the exact retained PCM WAV used for the meeting memory vectors.",
    )
    meeting_recording_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Same-tenant retained source recording for this optional immutable meeting template.",
    )


class SpeakerJob(AuditSoftDeleteMixin, Base):
    __tablename__ = "speaker_job"
    __table_args__ = (
        UniqueConstraint("tenant_id", "speaker_job_id", name="uq_speaker_job_tenant_identity"),
        UniqueConstraint(
            "tenant_id",
            "purpose",
            "idempotency_key",
            name="uq_speaker_job_tenant_retry_key",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "recording_id"],
            ["recording.tenant_id", "recording.recording_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "target_profile_id"],
            ["speaker_profile.tenant_id", "speaker_profile.speaker_profile_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("purpose IN ('enroll', 'identify')", name="speaker_job_purpose"),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="speaker_job_status",
        ),
        CheckConstraint("attempt_count BETWEEN 0 AND 2", name="speaker_job_attempt_count"),
        CheckConstraint(
            "(purpose = 'identify' AND target_profile_id IS NULL AND requested_name IS NULL) OR (purpose = 'enroll' AND ((target_profile_id IS NULL) <> (requested_name IS NULL)))",
            name="speaker_job_target",
        ),
        Index(
            "ix_speaker_job_active_queue",
            "status",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
        Index("ix_speaker_job_tenant_recording", "tenant_id", "recording_id"),
        Index("ix_speaker_job_tenant_target", "tenant_id", "target_profile_id"),
        {
            "comment": "Speaker identity durable work; expiring leases and monotonically increasing fencing tokens protect terminal writes."
        },
    )
    speaker_job_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Owning application tenant; compound foreign keys prevent cross-tenant sources and targets.",
    )
    recording_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Same-tenant source recording; active jobs prevent its cleanup.",
    )
    target_profile_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Same-tenant existing profile to append to; active status is rechecked at commit.",
    )
    requested_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    purpose: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="enroll creates or extends a profile; identify is strictly read-only for profiles.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="queued",
        comment="queued, running, succeeded or failed; mirrored by SpeakerJobResponse.",
    )
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Canonical source hash, purpose, model version and normalized target fingerprint.",
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claim_token: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Increases on every claim; stale workers cannot commit even if inference finishes later.",
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Public SpeakerResult contract only; no embedding, source audio or filesystem path.",
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SpeakerSample(AuditSoftDeleteMixin, Base):
    __tablename__ = "speaker_sample"
    __table_args__ = (
        UniqueConstraint("tenant_id", "speaker_job_id", name="uq_speaker_sample_tenant_job"),
        ForeignKeyConstraint(
            ["tenant_id", "speaker_profile_id"],
            ["speaker_profile.tenant_id", "speaker_profile.speaker_profile_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "recording_id"],
            ["recording.tenant_id", "recording.recording_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "speaker_job_id"],
            ["speaker_job.tenant_id", "speaker_job.speaker_job_id"],
            ondelete="RESTRICT",
        ),
        Index(
            "ix_speaker_sample_active_profile",
            "tenant_id",
            "speaker_profile_id",
            postgresql_where=text("is_deleted = false"),
        ),
        Index("ix_speaker_sample_tenant_recording", "tenant_id", "recording_id"),
        {
            "comment": "Speaker identity verified enrollment samples; one result per durable job prevents retry duplication."
        },
    )
    speaker_sample_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Owning application tenant; compound references enforce source and target identity.",
    )
    speaker_profile_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Same-tenant profile whose active centroid includes this vector.",
    )
    recording_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Same-tenant immutable source recording retained while this sample is active.",
    )
    speaker_job_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Same-tenant enrollment job; uniqueness prevents duplicate enrollment after retries.",
    )
    embedding: Mapped[list[float]] = mapped_column(VECTOR(192), nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    speech_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    windows_count: Mapped[int] = mapped_column(Integer, nullable=False)
