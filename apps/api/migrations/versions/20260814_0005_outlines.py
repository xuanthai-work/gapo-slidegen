"""Add editable, owned presentation outlines."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260814_0005"
down_revision: str | None = "20260814_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outlines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_records.id", ondelete="SET NULL"),
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_outlines_owner_id", "outlines", ["owner_id"])
    op.create_index("ix_outlines_source_id", "outlines", ["source_id"])
    op.add_column("presentations", sa.Column("outline_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "fk_presentations_outline_id",
        "presentations",
        "outlines",
        ["outline_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_presentations_outline_id", "presentations", ["outline_id"])


def downgrade() -> None:
    op.drop_index("ix_presentations_outline_id", table_name="presentations")
    op.drop_constraint("fk_presentations_outline_id", "presentations", type_="foreignkey")
    op.drop_column("presentations", "outline_id")
    op.drop_table("outlines")
