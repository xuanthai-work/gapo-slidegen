"""Store normalized source title and sections."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260814_0003"
down_revision: str | None = "20260814_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_records",
        sa.Column("title", sa.String(500), nullable=False, server_default="Untitled source"),
    )
    op.add_column(
        "source_records",
        sa.Column("sections", postgresql.JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("source_records", "sections")
    op.drop_column("source_records", "title")
