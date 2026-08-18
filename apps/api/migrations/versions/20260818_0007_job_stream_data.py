"""Add stream_data to generation_jobs for real-time slide streaming."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260818_0007"
down_revision: str | None = "20260814_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column("stream_data", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "stream_data")
