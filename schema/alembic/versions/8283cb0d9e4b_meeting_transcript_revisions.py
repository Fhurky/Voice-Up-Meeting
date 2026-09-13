"""meeting_transcript_revisions

Revision ID: 8283cb0d9e4b
Revises: 755327e73d5c
Create Date: 2026-09-13 17:48:54.636419
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8283cb0d9e4b"
down_revision: str | None = "755327e73d5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The existing source must expose its compound key before the new child FK is created.
    op.create_unique_constraint(
        "uq_meeting_transcript_tenant_identity",
        "meeting_transcript",
        ["tenant_id", "meeting_id", "meeting_transcript_id"],
    )
    op.create_table(
        "meeting_transcript_revision",
        sa.Column(
            "meeting_transcript_revision_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            nullable=False,
            comment="Owning tenant; the compound source key prevents cross-tenant attachment.",
        ),
        sa.Column(
            "meeting_id",
            sa.BigInteger(),
            nullable=False,
            comment="Owning meeting through the compound transcript source reference.",
        ),
        sa.Column(
            "meeting_transcript_id",
            sa.BigInteger(),
            nullable=False,
            comment="Exact immutable source transcript in the same tenant and meeting.",
        ),
        sa.Column(
            "revision",
            sa.Integer(),
            nullable=False,
            comment="Monotonically increasing user-approved version within one transcript; prior versions remain available to retention.",
        ),
        sa.Column(
            "preview_id",
            sa.String(length=36),
            nullable=False,
            comment="Server-issued proposal identity; retries cannot append the same approval twice.",
        ),
        sa.Column(
            "source_text_sha256",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 of exact original UTF-8 transcript text; cleared with retained payloads.",
        ),
        sa.Column(
            "context_sha256",
            sa.String(length=64),
            nullable=False,
            comment="Hash of source-bound context observed before the user approved this version.",
        ),
        sa.Column(
            "corrected_text",
            sa.Text(),
            nullable=False,
            comment="User-approved text projection; never overwrites source text and is scrubbed with its meeting.",
        ),
        sa.Column(
            "edits",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="At most three exact original/replacement edits with Unicode code-point start_char/end_char offsets; scrubbed with the source.",
        ),
        sa.Column(
            "model_name",
            sa.String(length=200),
            nullable=False,
            comment="Exact installed local model name that proposed this approved version.",
        ),
        sa.Column(
            "model_digest",
            sa.String(length=64),
            nullable=False,
            comment="Installed model digest verified before and after generation.",
        ),
        sa.Column(
            "policy_version",
            sa.String(length=32),
            nullable=False,
            comment="Source projection policy; tr-context-words-v2 retains semantic review warnings for user approval.",
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
            "is_deleted OR (length(corrected_text) BETWEEN 1 AND 1216 AND source_text_sha256 ~ '^[a-f0-9]{64}$' AND context_sha256 ~ '^[a-f0-9]{64}$')",
            name=op.f("ck_meeting_transcript_revision_transcript_revision_source"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(edits) = 'array' AND jsonb_array_length(edits) <= 3 AND octet_length(edits::text) <= 4096",
            name=op.f("ck_meeting_transcript_revision_transcript_revision_edits"),
        ),
        sa.CheckConstraint(
            "policy_version = 'tr-context-words-v2'",
            name=op.f("ck_meeting_transcript_revision_transcript_revision_policy"),
        ),
        sa.CheckConstraint(
            "revision BETWEEN 1 AND 2147483647",
            name=op.f("ck_meeting_transcript_revision_transcript_revision_number"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "meeting_id", "meeting_transcript_id"],
            [
                "meeting_transcript.tenant_id",
                "meeting_transcript.meeting_id",
                "meeting_transcript.meeting_transcript_id",
            ],
            name=op.f("fk_meeting_transcript_revision_tenant_id_meeting_transcript"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.tenant_id"],
            name=op.f("fk_meeting_transcript_revision_tenant_id_tenant"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "meeting_transcript_revision_id", name=op.f("pk_meeting_transcript_revision")
        ),
        sa.UniqueConstraint("preview_id", name="uq_transcript_revision_preview"),
        sa.UniqueConstraint("public_id", name=op.f("uq_meeting_transcript_revision_public_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "meeting_id",
            "meeting_transcript_id",
            "revision",
            name="uq_transcript_revision_position",
        ),
        comment="Explicitly user-approved transcript versions; source text, speaker identity and audio coordinates remain unchanged.",
    )
    op.create_index(
        "ix_transcript_revision_active_source",
        "meeting_transcript_revision",
        ["tenant_id", "meeting_id", "meeting_transcript_id", "revision"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    raise RuntimeError("Removing user-approved transcript revisions requires an explicit data review")
