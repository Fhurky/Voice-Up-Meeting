"""speaker_identity_pilot

Revision ID: 9486b1bc12a9
Revises: 202608060001
Create Date: 2026-09-08 21:09:08.321525
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "9486b1bc12a9"
down_revision: str | None = "202608060001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extension binary is supplied by the admitted, digest-pinned PostgreSQL image.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector VERSION '0.8.6'")
    op.create_table(
        "recording",
        sa.Column("recording_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            nullable=False,
            comment="Owning application tenant; all references are tenant-qualified.",
        ),
        sa.Column(
            "storage_key",
            sa.String(length=64),
            nullable=False,
            comment="Opaque server-generated filename beneath the configured owned audio root.",
        ),
        sa.Column(
            "sha256",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 of the original uploaded bytes, used for semantic idempotency.",
        ),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "format",
            sa.String(length=8),
            nullable=False,
            comment="Decoded audio container: WAV or FLAC; mirrored by RecordingResponse.",
        ),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=True,
            comment="Tenant-scoped upload retry key; cleared after its retention period.",
        ),
        sa.Column("idempotency_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Earliest cleanup time; active sample or job references always prevent cleanup.",
        ),
        sa.Column("file_removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "props",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("format IN ('WAV', 'FLAC')", name=op.f("ck_recording_recording_format")),
        sa.CheckConstraint(
            "size_bytes > 0 AND duration_seconds > 0",
            name=op.f("ck_recording_recording_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_recording_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("recording_id", name=op.f("pk_recording")),
        sa.UniqueConstraint("public_id", name=op.f("uq_recording_public_id")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_recording_storage_key")),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_recording_tenant_retry_key"),
        sa.UniqueConstraint("tenant_id", "recording_id", name="uq_recording_tenant_identity"),
        comment="Speaker identity source audio metadata; opaque owned files follow reference-aware retention.",
    )
    op.create_index(
        "ix_recording_active_tenant",
        "recording",
        ["tenant_id", "created_at"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_table(
        "speaker_profile",
        sa.Column(
            "speaker_profile_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            nullable=False,
            comment="Owning application tenant; identity matching never crosses this boundary.",
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(length=120), nullable=False),
        sa.Column(
            "model_revision",
            sa.String(length=64),
            nullable=False,
            comment="Immutable embedding population identifier; different versions are never scored together.",
        ),
        sa.Column(
            "embedding",
            VECTOR(dim=192),
            nullable=False,
            comment="L2-normalized 192-dimensional ECAPA centroid; exact cosine search only.",
        ),
        sa.Column(
            "source_sha256",
            sa.String(length=64),
            nullable=False,
            comment="Canonical hash of the sorted active sample source hashes composing this centroid.",
        ),
        sa.Column(
            "props",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "sample_count BETWEEN 1 AND 20",
            name=op.f("ck_speaker_profile_speaker_profile_sample_count"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_speaker_profile_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("speaker_profile_id", name=op.f("pk_speaker_profile")),
        sa.UniqueConstraint("public_id", name=op.f("uq_speaker_profile_public_id")),
        sa.UniqueConstraint(
            "tenant_id", "speaker_profile_id", name="uq_speaker_profile_tenant_identity"
        ),
        comment="Speaker identity profile with an equal-weight normalized mean of verified source samples.",
    )
    op.create_index(
        "ix_speaker_profile_active_tenant_model",
        "speaker_profile",
        ["tenant_id", "model_revision"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_table(
        "speaker_job",
        sa.Column("speaker_job_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            nullable=False,
            comment="Owning application tenant; compound foreign keys prevent cross-tenant sources and targets.",
        ),
        sa.Column(
            "recording_id",
            sa.BigInteger(),
            nullable=False,
            comment="Same-tenant source recording; active jobs prevent its cleanup.",
        ),
        sa.Column(
            "target_profile_id",
            sa.BigInteger(),
            nullable=True,
            comment="Same-tenant existing profile to append to; active status is rechecked at commit.",
        ),
        sa.Column("requested_name", sa.String(length=120), nullable=True),
        sa.Column(
            "purpose",
            sa.String(length=16),
            nullable=False,
            comment="enroll creates or extends a profile; identify is strictly read-only for profiles.",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            comment="queued, running, succeeded or failed; mirrored by SpeakerJobResponse.",
        ),
        sa.Column("model_id", sa.String(length=120), nullable=False),
        sa.Column("model_revision", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "fingerprint",
            sa.String(length=64),
            nullable=False,
            comment="Canonical source hash, purpose, model version and normalized target fingerprint.",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column(
            "claim_token",
            sa.Integer(),
            nullable=False,
            comment="Increases on every claim; stale workers cannot commit even if inference finishes later.",
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Public SpeakerResult contract only; no embedding, source audio or filesystem path.",
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "props",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "(purpose = 'identify' AND target_profile_id IS NULL AND requested_name IS NULL) OR (purpose = 'enroll' AND ((target_profile_id IS NULL) <> (requested_name IS NULL)))",
            name=op.f("ck_speaker_job_speaker_job_target"),
        ),
        sa.CheckConstraint(
            "purpose IN ('enroll', 'identify')",
            name=op.f("ck_speaker_job_speaker_job_purpose"),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name=op.f("ck_speaker_job_speaker_job_status"),
        ),
        sa.CheckConstraint(
            "attempt_count BETWEEN 0 AND 2",
            name=op.f("ck_speaker_job_speaker_job_attempt_count"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "recording_id"],
            ["recording.tenant_id", "recording.recording_id"],
            name=op.f("fk_speaker_job_tenant_id_recording"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "target_profile_id"],
            ["speaker_profile.tenant_id", "speaker_profile.speaker_profile_id"],
            name=op.f("fk_speaker_job_tenant_id_speaker_profile"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_speaker_job_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("speaker_job_id", name=op.f("pk_speaker_job")),
        sa.UniqueConstraint("public_id", name=op.f("uq_speaker_job_public_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "purpose",
            "idempotency_key",
            name="uq_speaker_job_tenant_retry_key",
        ),
        sa.UniqueConstraint("tenant_id", "speaker_job_id", name="uq_speaker_job_tenant_identity"),
        comment="Speaker identity durable work; expiring leases and monotonically increasing fencing tokens protect terminal writes.",
    )
    op.create_index(
        "ix_speaker_job_active_queue",
        "speaker_job",
        ["status", "created_at"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_speaker_job_tenant_recording",
        "speaker_job",
        ["tenant_id", "recording_id"],
        unique=False,
    )
    op.create_index(
        "ix_speaker_job_tenant_target",
        "speaker_job",
        ["tenant_id", "target_profile_id"],
        unique=False,
    )
    op.create_table(
        "speaker_sample",
        sa.Column(
            "speaker_sample_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            nullable=False,
            comment="Owning application tenant; compound references enforce source and target identity.",
        ),
        sa.Column(
            "speaker_profile_id",
            sa.BigInteger(),
            nullable=False,
            comment="Same-tenant profile whose active centroid includes this vector.",
        ),
        sa.Column(
            "recording_id",
            sa.BigInteger(),
            nullable=False,
            comment="Same-tenant immutable source recording retained while this sample is active.",
        ),
        sa.Column(
            "speaker_job_id",
            sa.BigInteger(),
            nullable=False,
            comment="Same-tenant enrollment job; uniqueness prevents duplicate enrollment after retries.",
        ),
        sa.Column("embedding", VECTOR(dim=192), nullable=False),
        sa.Column("model_id", sa.String(length=120), nullable=False),
        sa.Column("model_revision", sa.String(length=64), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("speech_seconds", sa.Float(), nullable=False),
        sa.Column("windows_count", sa.Integer(), nullable=False),
        sa.Column(
            "props",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id", "recording_id"],
            ["recording.tenant_id", "recording.recording_id"],
            name=op.f("fk_speaker_sample_tenant_id_recording"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "speaker_job_id"],
            ["speaker_job.tenant_id", "speaker_job.speaker_job_id"],
            name=op.f("fk_speaker_sample_tenant_id_speaker_job"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "speaker_profile_id"],
            ["speaker_profile.tenant_id", "speaker_profile.speaker_profile_id"],
            name=op.f("fk_speaker_sample_tenant_id_speaker_profile"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_speaker_sample_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("speaker_sample_id", name=op.f("pk_speaker_sample")),
        sa.UniqueConstraint("public_id", name=op.f("uq_speaker_sample_public_id")),
        sa.UniqueConstraint("tenant_id", "speaker_job_id", name="uq_speaker_sample_tenant_job"),
        comment="Speaker identity verified enrollment samples; one result per durable job prevents retry duplication.",
    )
    op.create_index(
        "ix_speaker_sample_active_profile",
        "speaker_sample",
        ["tenant_id", "speaker_profile_id"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_speaker_sample_tenant_recording",
        "speaker_sample",
        ["tenant_id", "recording_id"],
        unique=False,
    )
    permission_table = sa.table(
        "app_permission",
        sa.column("public_id", sa.Text()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
    )
    op.bulk_insert(
        permission_table,
        [
            {
                "public_id": "7fc2e51a-5b1b-4fa1-93c5-29576a7d6b11",
                "code": "speaker_profiles:read",
                "name": "Read speaker profiles",
            },
            {
                "public_id": "7fc2e51a-5b1b-4fa1-93c5-29576a7d6b12",
                "code": "speaker_profiles:write",
                "name": "Manage speaker profiles",
            },
            {
                "public_id": "7fc2e51a-5b1b-4fa1-93c5-29576a7d6b13",
                "code": "speaker_analysis:run",
                "name": "Run speaker analysis",
            },
            {
                "public_id": "7fc2e51a-5b1b-4fa1-93c5-29576a7d6b14",
                "code": "speaker_analysis:read",
                "name": "Read speaker analysis",
            },
        ],
    )


def downgrade() -> None:
    raise RuntimeError(
        "Speaker data removal requires an explicitly authorized destructive migration"
    )
