"""Schema authority for resumable meeting uploads, analysis and speaker memory links."""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import VECTOR  # type: ignore[import-untyped]
from sqlalchemy import (
    BigInteger,
    Boolean,
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


class Meeting(AuditSoftDeleteMixin, Base):
    __tablename__ = "meeting"
    __table_args__ = (
        UniqueConstraint("tenant_id", "meeting_id", name="uq_meeting_tenant_identity"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_meeting_tenant_retry_key"),
        CheckConstraint(
            "size_bytes BETWEEN 1 AND 2147483648 AND uploaded_bytes BETWEEN 0 AND size_bytes",
            name="meeting_size",
        ),
        CheckConstraint("format IN ('WAV', 'FLAC')", name="meeting_format"),
        CheckConstraint(
            "status IN ('uploading', 'queued', 'running', 'finalizing', 'succeeded', 'failed', 'cancelled')",
            name="meeting_status",
        ),
        CheckConstraint("language IN ('tr', 'en', 'auto')", name="meeting_language"),
        CheckConstraint(
            "participant_count BETWEEN 1 AND 1000 AND expected_speakers BETWEEN 1 AND 1000 AND expected_speakers <= participant_count",
            name="meeting_counts",
        ),
        CheckConstraint(
            "duration_seconds > 0 AND duration_seconds <= 14400 AND sample_rate > 0 AND channels > 0",
            name="meeting_audio",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND claim_token >= 0 AND next_chunk_index BETWEEN 0 AND 240 AND processed_seconds >= 0 AND processed_seconds <= 14400",
            name="meeting_progress",
        ),
        Index(
            "ix_meeting_active_tenant",
            "tenant_id",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "ix_meeting_active_queue",
            "status",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
        {
            "comment": "Tenant-owned resumable uploaded meeting; fenced analysis preserves durable progress and retention."
        },
    )
    meeting_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Owning tenant; compound child references preserve isolation.",
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    format: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="Validated source container; WAV or FLAC only.",
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Expected complete source size reserved against the tenant storage budget.",
    )
    uploaded_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    source_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Complete source SHA-256 after acknowledged upload verification.",
    )
    storage_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="Opaque server-owned storage identity; never exposed as a filesystem path.",
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="uploading",
        comment="Upload, queue, fenced processing and terminal lifecycle; mirrored by the typed meeting response.",
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="auto")
    participant_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Optional participant upper bound; silent participants need not become acoustic clusters.",
    )
    expected_speakers: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Optional actually-speaking count expectation; never forces per-chunk merging.",
    )
    auto_enroll: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Tenant retry identity retained through terminal states until explicit expiry.",
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Canonical upload parameters fingerprint; changed settings cannot reuse a retry key.",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Attempts for the current bounded chunk; reset after its durable completion.",
    )
    claim_token: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Monotonic fencing generation across claims; stale workers cannot persist.",
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Count of durably completed analysis cores; context is not counted twice.",
    )
    processed_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Earliest retained source cleanup time; active analysis and durable sample references still protect data.",
    )
    upload_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Abandoned partial upload expiry; distinct from accepted source retention.",
    )
    source_removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class MeetingUploadPart(AuditSoftDeleteMixin, Base):
    __tablename__ = "meeting_upload_part"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "meeting_id", "index", name="uq_meeting_upload_part_position"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "meeting_id"],
            ["meeting.tenant_id", "meeting.meeting_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "index BETWEEN 0 AND 511 AND size_bytes BETWEEN 1 AND 4194304",
            name="meeting_upload_part_bounds",
        ),
        Index(
            "ix_meeting_upload_part_active_meeting",
            "tenant_id",
            "meeting_id",
            postgresql_where=text("is_deleted = false"),
        ),
        {
            "comment": "Acknowledged sequential source byte parts; immutable hash and position make retries safe."
        },
    )
    meeting_upload_part_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.tenant_id", ondelete="RESTRICT"), nullable=False
    )
    meeting_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Same-tenant parent meeting upload."
    )
    index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Zero-based part position; at most 512 parts of four MiB.",
    )
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="SHA-256 of this acknowledged byte range."
    )


class MeetingChunk(AuditSoftDeleteMixin, Base):
    __tablename__ = "meeting_chunk"
    __table_args__ = (
        UniqueConstraint("tenant_id", "meeting_id", "index", name="uq_meeting_chunk_position"),
        ForeignKeyConstraint(
            ["tenant_id", "meeting_id"],
            ["meeting.tenant_id", "meeting.meeting_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "index BETWEEN 0 AND 239 AND context_start >= 0 AND context_start <= core_start AND core_start < core_end AND core_end <= context_end AND context_end <= 14400 AND context_end - context_start <= 310",
            name="meeting_chunk_bounds",
        ),
        CheckConstraint("status = 'succeeded'", name="meeting_chunk_status"),
        CheckConstraint(
            "jsonb_typeof(result) = 'object' AND octet_length(result::text) <= 8388608",
            name="meeting_chunk_result",
        ),
        Index(
            "ix_meeting_chunk_active_meeting",
            "tenant_id",
            "meeting_id",
            postgresql_where=text("is_deleted = false"),
        ),
        {
            "comment": "Completed bounded provider result; core and context coordinates preserve progress without duplicate evidence."
        },
    )
    meeting_chunk_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.tenant_id", ondelete="RESTRICT"), nullable=False
    )
    meeting_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Same-tenant analysis source."
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    context_start: Mapped[float] = mapped_column(Float, nullable=False)
    core_start: Mapped[float] = mapped_column(Float, nullable=False)
    core_end: Mapped[float] = mapped_column(Float, nullable=False)
    context_end: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="succeeded")
    result: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Private bounded provider payload, including model identity; never returned by the public HTTP contract.",
    )


class MeetingSpeaker(AuditSoftDeleteMixin, Base):
    __tablename__ = "meeting_speaker"
    __table_args__ = (
        UniqueConstraint("tenant_id", "meeting_id", "ordinal", name="uq_meeting_speaker_ordinal"),
        UniqueConstraint(
            "tenant_id",
            "meeting_id",
            "meeting_speaker_id",
            name="uq_meeting_speaker_tenant_identity",
        ),
        UniqueConstraint(
            "tenant_id", "enrollment_job_id", name="uq_meeting_speaker_enrollment_job"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "meeting_id"],
            ["meeting.tenant_id", "meeting.meeting_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "profile_id"],
            ["speaker_profile.tenant_id", "speaker_profile.speaker_profile_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "enrollment_job_id"],
            ["speaker_job.tenant_id", "speaker_job.speaker_job_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "ordinal >= 0 AND version >= 1 AND speech_seconds >= 0 AND speech_seconds <= 14400",
            name="meeting_speaker_bounds",
        ),
        CheckConstraint(
            "decision IN ('profile_pending', 'recognized', 'enrolled', 'ambiguous')",
            name="meeting_speaker_decision",
        ),
        CheckConstraint(
            "embedding IS NULL OR (model_id IS NOT NULL AND model_revision IS NOT NULL AND source_sha256 IS NOT NULL)",
            name="meeting_speaker_embedding_metadata",
        ),
        CheckConstraint(
            "(tracking_embedding IS NULL AND tracking_model_id IS NULL AND tracking_model_revision IS NULL) OR (tracking_embedding IS NOT NULL AND tracking_model_id IS NOT NULL AND tracking_model_revision IS NOT NULL)",
            name="meeting_speaker_tracking_metadata",
        ),
        CheckConstraint(
            "jsonb_typeof(clean_ranges) = 'array'", name="meeting_speaker_clean_ranges"
        ),
        Index(
            "ix_meeting_speaker_active_meeting",
            "tenant_id",
            "meeting_id",
            postgresql_where=text("is_deleted = false"),
        ),
        Index("ix_meeting_speaker_tenant_profile", "tenant_id", "profile_id"),
        {
            "comment": "Meeting-local acoustic identity with optional persistent profile; clean unique speech and versioned names preserve safe memory."
        },
    )
    meeting_speaker_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.tenant_id", ondelete="RESTRICT"), nullable=False
    )
    meeting_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Same-tenant meeting acoustic cluster scope.",
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    display_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        comment="Manual meeting-local label; naming alone never supplies biometric evidence.",
    )
    profile_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Optional same-tenant persistent profile selected only by recognition or enrollment gates.",
    )
    decision: Mapped[str] = mapped_column(String(24), nullable=False, default="profile_pending")
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    speech_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
        comment="Unique clean nonoverlapping source speech accumulated for this cluster; duration alone never authorizes enrollment.",
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(192),
        nullable=True,
        comment="Private normalized ECAPA centroid; never expose through public DTOs.",
    )
    tracking_embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(256),
        nullable=True,
        comment="Private Community embedding-component centroid for meeting-local tracking only; never enrollment evidence or an ECAPA vector.",
    )
    tracking_model_id: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        comment="Owning diarization package of the private embedding component; incompatible populations never match.",
    )
    tracking_model_revision: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Immutable package revision for the tracking component, independent from the ECAPA profile revision.",
    )
    model_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_revision: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Immutable embedding population identity; incompatible versions are never matched.",
    )
    source_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Canonical contributing source evidence hash for this centroid.",
    )
    clean_ranges: Mapped[list[list[int]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="Half-open original-source sample intervals; deduplicate context and retries before accumulating duration.",
    )
    enrollment_job_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Same-tenant durable enrollment job linking the existing profile sample lifecycle.",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Optimistic local naming version; persistent profile edits also check its own updated_at.",
    )


class MeetingTranscript(AuditSoftDeleteMixin, Base):
    __tablename__ = "meeting_transcript"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "meeting_id", "ordinal", name="uq_meeting_transcript_ordinal"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "meeting_id"],
            ["meeting.tenant_id", "meeting.meeting_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "meeting_id", "meeting_speaker_id"],
            [
                "meeting_speaker.tenant_id",
                "meeting_speaker.meeting_id",
                "meeting_speaker.meeting_speaker_id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            'ordinal >= 0 AND start >= 0 AND start < "end" AND "end" <= 14400',
            name="meeting_transcript_bounds",
        ),
        Index(
            "ix_meeting_transcript_active_meeting",
            "tenant_id",
            "meeting_id",
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "ix_meeting_transcript_tenant_speaker",
            "tenant_id",
            "meeting_id",
            "meeting_speaker_id",
        ),
        {
            "comment": "Paged source-timestamped words or transcript segments; uncertain and overlapping attribution remain explicit."
        },
    )
    meeting_transcript_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.tenant_id", ondelete="RESTRICT"), nullable=False
    )
    meeting_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Same-tenant transcript source meeting."
    )
    meeting_speaker_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Optional speaker from exactly this tenant and meeting; uncertainty does not remove text.",
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    start: Mapped[float] = mapped_column(Float, nullable=False)
    end: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Private user transcript text; excluded from metrics and logs.",
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="tr")
    overlap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uncertain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
