"""Add durable semantic checkpoints for generation reconnects."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260819_0008"
down_revision: str | None = "20260818_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

checkpoint_status = postgresql.ENUM(
    "partial",
    "completed",
    name="generation_checkpoint_status",
    create_type=False,
)


def upgrade() -> None:
    checkpoint_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "generation_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slide_id", sa.String(160), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "completed_slots",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("canonical_slide", postgresql.JSONB()),
        sa.Column("status", checkpoint_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "job_id",
            "slide_id",
            name="uq_generation_checkpoints_job_slide",
        ),
        sa.CheckConstraint(
            "attempt >= 1",
            name="ck_generation_checkpoints_attempt_positive",
        ),
        sa.CheckConstraint(
            "sequence >= 1",
            name="ck_generation_checkpoints_sequence_positive",
        ),
    )
    op.create_index(
        "ix_generation_checkpoints_job_sequence",
        "generation_checkpoints",
        ["job_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_table("generation_checkpoints")
    checkpoint_status.drop(op.get_bind(), checkfirst=True)
