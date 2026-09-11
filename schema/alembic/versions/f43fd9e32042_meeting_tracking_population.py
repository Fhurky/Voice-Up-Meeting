"""meeting_tracking_population

Revision ID: f43fd9e32042
Revises: 7e86c6c45b2a
Create Date: 2026-09-10 21:53:01.488638
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR

revision: str = "f43fd9e32042"
down_revision: str | None = "7e86c6c45b2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Generated from the Accepted 002 Decision 12 authority and reviewed as additive.
    op.add_column(
        "meeting_speaker",
        sa.Column(
            "tracking_embedding",
            VECTOR(256),
            nullable=True,
            comment="Private Community embedding-component centroid for meeting-local tracking only; never enrollment evidence or an ECAPA vector.",
        ),
    )
    op.add_column(
        "meeting_speaker",
        sa.Column(
            "tracking_model_id",
            sa.String(length=120),
            nullable=True,
            comment="Owning diarization package of the private embedding component; incompatible populations never match.",
        ),
    )
    op.add_column(
        "meeting_speaker",
        sa.Column(
            "tracking_model_revision",
            sa.String(length=64),
            nullable=True,
            comment="Immutable package revision for the tracking component, independent from the ECAPA profile revision.",
        ),
    )
    op.create_check_constraint(
        op.f("ck_meeting_speaker_meeting_speaker_tracking_metadata"),
        "meeting_speaker",
        "(tracking_embedding IS NULL AND tracking_model_id IS NULL AND tracking_model_revision IS NULL) OR (tracking_embedding IS NOT NULL AND tracking_model_id IS NOT NULL AND tracking_model_revision IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_meeting_speaker_meeting_speaker_tracking_metadata"),
        "meeting_speaker",
        type_="check",
    )
    op.drop_column("meeting_speaker", "tracking_model_revision")
    op.drop_column("meeting_speaker", "tracking_model_id")
    op.drop_column("meeting_speaker", "tracking_embedding")
