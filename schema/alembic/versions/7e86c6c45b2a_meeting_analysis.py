"""meeting_analysis

Revision ID: 7e86c6c45b2a
Revises: 9486b1bc12a9
Create Date: 2026-09-10 20:19:19.707601
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "7e86c6c45b2a"
down_revision: str | None = "9486b1bc12a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Generated from the Accepted 002 schema authority, then reviewed for additive deployment.
    op.create_table(
        "meeting",
        sa.Column(
            "meeting_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            nullable=False,
            comment="Owning tenant; compound child references preserve isolation.",
        ),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column(
            "format",
            sa.String(length=8),
            nullable=False,
            comment="Validated source container; WAV or FLAC only.",
        ),
        sa.Column(
            "size_bytes",
            sa.BigInteger(),
            nullable=False,
            comment="Expected complete source size reserved against the tenant storage budget.",
        ),
        sa.Column("uploaded_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "source_sha256",
            sa.String(length=64),
            nullable=True,
            comment="Complete source SHA-256 after acknowledged upload verification.",
        ),
        sa.Column(
            "storage_key",
            sa.String(length=64),
            nullable=False,
            comment="Opaque server-owned storage identity; never exposed as a filesystem path.",
        ),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column("channels", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            comment="Upload, queue, fenced processing and terminal lifecycle; mirrored by the typed meeting response.",
        ),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column(
            "participant_count",
            sa.Integer(),
            nullable=True,
            comment="Optional participant upper bound; silent participants need not become acoustic clusters.",
        ),
        sa.Column(
            "expected_speakers",
            sa.Integer(),
            nullable=True,
            comment="Optional actually-speaking count expectation; never forces per-chunk merging.",
        ),
        sa.Column("auto_enroll", sa.Boolean(), nullable=False),
        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=True,
            comment="Tenant retry identity retained through terminal states until explicit expiry.",
        ),
        sa.Column(
            "fingerprint",
            sa.String(length=64),
            nullable=False,
            comment="Canonical upload parameters fingerprint; changed settings cannot reuse a retry key.",
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            comment="Attempts for the current bounded chunk; reset after its durable completion.",
        ),
        sa.Column(
            "claim_token",
            sa.Integer(),
            nullable=False,
            comment="Monotonic fencing generation across claims; stale workers cannot persist.",
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "next_chunk_index",
            sa.Integer(),
            nullable=False,
            comment="Count of durably completed analysis cores; context is not counted twice.",
        ),
        sa.Column("processed_seconds", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "source_expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Earliest retained source cleanup time; active analysis and durable sample references still protect data.",
        ),
        sa.Column(
            "upload_expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Abandoned partial upload expiry; distinct from accepted source retention.",
        ),
        sa.Column("source_removed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "format IN ('WAV', 'FLAC')", name=op.f("ck_meeting_meeting_format")
        ),
        sa.CheckConstraint(
            "language IN ('tr', 'en', 'auto')", name=op.f("ck_meeting_meeting_language")
        ),
        sa.CheckConstraint(
            "status IN ('uploading', 'queued', 'running', 'finalizing', 'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_meeting_meeting_status"),
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND claim_token >= 0 AND next_chunk_index BETWEEN 0 AND 240 AND processed_seconds >= 0 AND processed_seconds <= 14400",
            name=op.f("ck_meeting_meeting_progress"),
        ),
        sa.CheckConstraint(
            "duration_seconds > 0 AND duration_seconds <= 14400 AND sample_rate > 0 AND channels > 0",
            name=op.f("ck_meeting_meeting_audio"),
        ),
        sa.CheckConstraint(
            "participant_count BETWEEN 1 AND 1000 AND expected_speakers BETWEEN 1 AND 1000 AND expected_speakers <= participant_count",
            name=op.f("ck_meeting_meeting_counts"),
        ),
        sa.CheckConstraint(
            "size_bytes BETWEEN 1 AND 2147483648 AND uploaded_bytes BETWEEN 0 AND size_bytes",
            name=op.f("ck_meeting_meeting_size"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_meeting_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("meeting_id", name=op.f("pk_meeting")),
        sa.UniqueConstraint("public_id", name=op.f("uq_meeting_public_id")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_meeting_storage_key")),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_meeting_tenant_retry_key"
        ),
        sa.UniqueConstraint(
            "tenant_id", "meeting_id", name="uq_meeting_tenant_identity"
        ),
        comment="Tenant-owned resumable uploaded meeting; fenced analysis preserves durable progress and retention.",
    )
    op.create_index(
        "ix_meeting_active_queue",
        "meeting",
        ["status", "created_at"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_meeting_active_tenant",
        "meeting",
        ["tenant_id", "created_at"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_table(
        "meeting_chunk",
        sa.Column(
            "meeting_chunk_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "meeting_id",
            sa.BigInteger(),
            nullable=False,
            comment="Same-tenant analysis source.",
        ),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("context_start", sa.Float(), nullable=False),
        sa.Column("core_start", sa.Float(), nullable=False),
        sa.Column("core_end", sa.Float(), nullable=False),
        sa.Column("context_end", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Private bounded provider payload, including model identity; never returned by the public HTTP contract.",
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
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "jsonb_typeof(result) = 'object' AND octet_length(result::text) <= 8388608",
            name=op.f("ck_meeting_chunk_meeting_chunk_result"),
        ),
        sa.CheckConstraint(
            "status = 'succeeded'", name=op.f("ck_meeting_chunk_meeting_chunk_status")
        ),
        sa.CheckConstraint(
            "index BETWEEN 0 AND 239 AND context_start >= 0 AND context_start <= core_start AND core_start < core_end AND core_end <= context_end AND context_end <= 14400 AND context_end - context_start <= 70",
            name=op.f("ck_meeting_chunk_meeting_chunk_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "meeting_id"],
            ["meeting.tenant_id", "meeting.meeting_id"],
            name=op.f("fk_meeting_chunk_tenant_id_meeting"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_meeting_chunk_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("meeting_chunk_id", name=op.f("pk_meeting_chunk")),
        sa.UniqueConstraint("public_id", name=op.f("uq_meeting_chunk_public_id")),
        sa.UniqueConstraint(
            "tenant_id", "meeting_id", "index", name="uq_meeting_chunk_position"
        ),
        comment="Completed bounded provider result; core and context coordinates preserve progress without duplicate evidence.",
    )
    op.create_index(
        "ix_meeting_chunk_active_meeting",
        "meeting_chunk",
        ["tenant_id", "meeting_id"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_table(
        "meeting_upload_part",
        sa.Column(
            "meeting_upload_part_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "meeting_id",
            sa.BigInteger(),
            nullable=False,
            comment="Same-tenant parent meeting upload.",
        ),
        sa.Column(
            "index",
            sa.Integer(),
            nullable=False,
            comment="Zero-based part position; at most 512 parts of four MiB.",
        ),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "sha256",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 of this acknowledged byte range.",
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
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "index BETWEEN 0 AND 511 AND size_bytes BETWEEN 1 AND 4194304",
            name=op.f("ck_meeting_upload_part_meeting_upload_part_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "meeting_id"],
            ["meeting.tenant_id", "meeting.meeting_id"],
            name=op.f("fk_meeting_upload_part_tenant_id_meeting"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_meeting_upload_part_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "meeting_upload_part_id", name=op.f("pk_meeting_upload_part")
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_meeting_upload_part_public_id")),
        sa.UniqueConstraint(
            "tenant_id", "meeting_id", "index", name="uq_meeting_upload_part_position"
        ),
        comment="Acknowledged sequential source byte parts; immutable hash and position make retries safe.",
    )
    op.create_index(
        "ix_meeting_upload_part_active_meeting",
        "meeting_upload_part",
        ["tenant_id", "meeting_id"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_table(
        "meeting_speaker",
        sa.Column(
            "meeting_speaker_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "meeting_id",
            sa.BigInteger(),
            nullable=False,
            comment="Same-tenant meeting acoustic cluster scope.",
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "display_name",
            sa.String(length=120),
            nullable=True,
            comment="Manual meeting-local label; naming alone never supplies biometric evidence.",
        ),
        sa.Column(
            "profile_id",
            sa.BigInteger(),
            nullable=True,
            comment="Optional same-tenant persistent profile selected only by recognition or enrollment gates.",
        ),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column(
            "speech_seconds",
            sa.Float(),
            nullable=False,
            comment="Unique clean nonoverlapping source speech accumulated for this cluster; duration alone never authorizes enrollment.",
        ),
        sa.Column(
            "embedding",
            VECTOR(dim=192),
            nullable=True,
            comment="Private normalized ECAPA centroid; never expose through public DTOs.",
        ),
        sa.Column("model_id", sa.String(length=120), nullable=True),
        sa.Column(
            "model_revision",
            sa.String(length=64),
            nullable=True,
            comment="Immutable embedding population identity; incompatible versions are never matched.",
        ),
        sa.Column(
            "source_sha256",
            sa.String(length=64),
            nullable=True,
            comment="Canonical contributing source evidence hash for this centroid.",
        ),
        sa.Column(
            "clean_ranges",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Half-open original-source sample intervals; deduplicate context and retries before accumulating duration.",
        ),
        sa.Column(
            "enrollment_job_id",
            sa.BigInteger(),
            nullable=True,
            comment="Same-tenant durable enrollment job linking the existing profile sample lifecycle.",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            comment="Optimistic local naming version; persistent profile edits also check its own updated_at.",
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
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "decision IN ('profile_pending', 'recognized', 'enrolled', 'ambiguous')",
            name=op.f("ck_meeting_speaker_meeting_speaker_decision"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(clean_ranges) = 'array'",
            name=op.f("ck_meeting_speaker_meeting_speaker_clean_ranges"),
        ),
        sa.CheckConstraint(
            "embedding IS NULL OR (model_id IS NOT NULL AND model_revision IS NOT NULL AND source_sha256 IS NOT NULL)",
            name=op.f("ck_meeting_speaker_meeting_speaker_embedding_metadata"),
        ),
        sa.CheckConstraint(
            "ordinal >= 0 AND version >= 1 AND speech_seconds >= 0 AND speech_seconds <= 14400",
            name=op.f("ck_meeting_speaker_meeting_speaker_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enrollment_job_id"],
            ["speaker_job.tenant_id", "speaker_job.speaker_job_id"],
            name=op.f("fk_meeting_speaker_tenant_id_speaker_job"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "meeting_id"],
            ["meeting.tenant_id", "meeting.meeting_id"],
            name=op.f("fk_meeting_speaker_tenant_id_meeting"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "profile_id"],
            ["speaker_profile.tenant_id", "speaker_profile.speaker_profile_id"],
            name=op.f("fk_meeting_speaker_tenant_id_speaker_profile"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_meeting_speaker_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("meeting_speaker_id", name=op.f("pk_meeting_speaker")),
        sa.UniqueConstraint("public_id", name=op.f("uq_meeting_speaker_public_id")),
        sa.UniqueConstraint(
            "tenant_id", "enrollment_job_id", name="uq_meeting_speaker_enrollment_job"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "meeting_id",
            "meeting_speaker_id",
            name="uq_meeting_speaker_tenant_identity",
        ),
        sa.UniqueConstraint(
            "tenant_id", "meeting_id", "ordinal", name="uq_meeting_speaker_ordinal"
        ),
        comment="Meeting-local acoustic identity with optional persistent profile; clean unique speech and versioned names preserve safe memory.",
    )
    op.create_index(
        "ix_meeting_speaker_active_meeting",
        "meeting_speaker",
        ["tenant_id", "meeting_id"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_meeting_speaker_tenant_profile",
        "meeting_speaker",
        ["tenant_id", "profile_id"],
        unique=False,
    )
    op.create_table(
        "meeting_transcript",
        sa.Column(
            "meeting_transcript_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "meeting_id",
            sa.BigInteger(),
            nullable=False,
            comment="Same-tenant transcript source meeting.",
        ),
        sa.Column(
            "meeting_speaker_id",
            sa.BigInteger(),
            nullable=True,
            comment="Optional speaker from exactly this tenant and meeting; uncertainty does not remove text.",
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("start", sa.Float(), nullable=False),
        sa.Column("end", sa.Float(), nullable=False),
        sa.Column(
            "text",
            sa.Text(),
            nullable=False,
            comment="Private user transcript text; excluded from metrics and logs.",
        ),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("overlap", sa.Boolean(), nullable=False),
        sa.Column("uncertain", sa.Boolean(), nullable=False),
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
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            'ordinal >= 0 AND start >= 0 AND start < "end" AND "end" <= 14400',
            name=op.f("ck_meeting_transcript_meeting_transcript_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "meeting_id", "meeting_speaker_id"],
            [
                "meeting_speaker.tenant_id",
                "meeting_speaker.meeting_id",
                "meeting_speaker.meeting_speaker_id",
            ],
            name=op.f("fk_meeting_transcript_tenant_id_meeting_speaker"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "meeting_id"],
            ["meeting.tenant_id", "meeting.meeting_id"],
            name=op.f("fk_meeting_transcript_tenant_id_meeting"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_meeting_transcript_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "meeting_transcript_id", name=op.f("pk_meeting_transcript")
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_meeting_transcript_public_id")),
        sa.UniqueConstraint(
            "tenant_id", "meeting_id", "ordinal", name="uq_meeting_transcript_ordinal"
        ),
        comment="Paged source-timestamped words or transcript segments; uncertain and overlapping attribution remain explicit.",
    )
    op.create_index(
        "ix_meeting_transcript_active_meeting",
        "meeting_transcript",
        ["tenant_id", "meeting_id"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_meeting_transcript_tenant_speaker",
        "meeting_transcript",
        ["tenant_id", "meeting_id", "meeting_speaker_id"],
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
                "public_id": "ce265442-0d2c-4bae-894b-978f63f00821",
                "code": "meeting_analysis:read",
                "name": "Read meeting analysis",
            },
            {
                "public_id": "ce265442-0d2c-4bae-894b-978f63f00822",
                "code": "meeting_analysis:run",
                "name": "Run meeting analysis",
            },
        ],
    )
    # Carry forward only active equivalent analysis grants; naming still requires profile write.
    op.execute(sa.text("""
        INSERT INTO app_role_permission (role_id, permission_id)
        SELECT old_grant.role_id, new_permission.permission_id
        FROM app_role_permission AS old_grant
        JOIN app_role AS role ON role.role_id = old_grant.role_id
        JOIN app_permission AS old_permission ON old_permission.permission_id = old_grant.permission_id
        JOIN app_permission AS new_permission
          ON new_permission.code = replace(old_permission.code, 'speaker_analysis:', 'meeting_analysis:')
        WHERE old_permission.code IN ('speaker_analysis:read', 'speaker_analysis:run')
          AND old_grant.is_deleted = false AND old_permission.is_deleted = false
          AND role.is_deleted = false
        ON CONFLICT (role_id, permission_id) DO NOTHING
    """))


def downgrade() -> None:
    raise RuntimeError(
        "Meeting data removal requires an explicitly authorized destructive migration"
    )
