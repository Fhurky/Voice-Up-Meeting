"""meeting_window_bounds

Revision ID: 755327e73d5c
Revises: 9cf5f2d22daf
Create Date: 2026-09-11 05:25:41.855082
"""

from collections.abc import Sequence

from alembic import op

revision: str = "755327e73d5c"
down_revision: str | None = "9cf5f2d22daf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The named-check autogenerator does not compare expression changes.
    # Preserve existing checkpoint rows and their historical index domain.
    op.drop_constraint(
        op.f("ck_meeting_chunk_meeting_chunk_bounds"), "meeting_chunk", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_meeting_chunk_meeting_chunk_bounds"),
        "meeting_chunk",
        "index BETWEEN 0 AND 239 AND context_start >= 0 AND context_start <= core_start "
        "AND core_start < core_end AND core_end <= context_end AND context_end <= 14400 "
        "AND context_end - context_start <= 310",
    )


def downgrade() -> None:
    raise RuntimeError(
        "Restoring the legacy window limit requires an explicit data review"
    )
