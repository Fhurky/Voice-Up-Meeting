"""User-approved text versions; immutable acoustic source remains owned by meeting transcripts."""

from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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


class MeetingTranscriptRevision(AuditSoftDeleteMixin, Base):
    __tablename__ = "meeting_transcript_revision"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "meeting_id",
            "meeting_transcript_id",
            "revision",
            name="uq_transcript_revision_position",
        ),
        UniqueConstraint("preview_id", name="uq_transcript_revision_preview"),
        ForeignKeyConstraint(
            ["tenant_id", "meeting_id", "meeting_transcript_id"],
            [
                "meeting_transcript.tenant_id",
                "meeting_transcript.meeting_id",
                "meeting_transcript.meeting_transcript_id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint("revision BETWEEN 1 AND 2147483647", name="transcript_revision_number"),
        CheckConstraint(
            "is_deleted OR (length(corrected_text) BETWEEN 1 AND 1216 AND source_text_sha256 ~ '^[a-f0-9]{64}$' AND context_sha256 ~ '^[a-f0-9]{64}$')",
            name="transcript_revision_source",
        ),
        CheckConstraint(
            "jsonb_typeof(edits) = 'array' AND jsonb_array_length(edits) <= 3 AND octet_length(edits::text) <= 4096",
            name="transcript_revision_edits",
        ),
        CheckConstraint(
            "policy_version = 'tr-context-words-v2'", name="transcript_revision_policy"
        ),
        Index(
            "ix_transcript_revision_active_source",
            "tenant_id",
            "meeting_id",
            "meeting_transcript_id",
            "revision",
            postgresql_where=text("is_deleted = false"),
        ),
        {
            "comment": "Explicitly user-approved transcript versions; source text, speaker identity and audio coordinates remain unchanged."
        },
    )
    meeting_transcript_revision_id: Mapped[int] = mapped_column(
        BigInteger, Identity(), primary_key=True
    )
    public_id: Mapped[str] = mapped_column(Text, default=new_public_id, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Owning tenant; the compound source key prevents cross-tenant attachment.",
    )
    meeting_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Owning meeting through the compound transcript source reference.",
    )
    meeting_transcript_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Exact immutable source transcript in the same tenant and meeting.",
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Monotonically increasing user-approved version within one transcript; prior versions remain available to retention.",
    )
    preview_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        comment="Server-issued proposal identity; retries cannot append the same approval twice.",
    )
    source_text_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 of exact original UTF-8 transcript text; cleared with retained payloads.",
    )
    context_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Hash of source-bound context observed before the user approved this version.",
    )
    corrected_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="User-approved text projection; never overwrites source text and is scrubbed with its meeting.",
    )
    edits: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        comment="At most three exact original/replacement edits with Unicode code-point start_char/end_char offsets; scrubbed with the source.",
    )
    model_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Exact installed local model name that proposed this approved version.",
    )
    model_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Installed model digest verified before and after generation.",
    )
    policy_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Source projection policy; tr-context-words-v2 retains semantic review warnings for user approval.",
    )
