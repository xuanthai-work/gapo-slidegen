"""Create initial users and presentation tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

presentation_status = sa.Enum(
    "draft",
    "outlining",
    "generating",
    "ready",
    "failed",
    name="presentation_status",
)
generation_job_status = sa.Enum(
    "queued",
    "running",
    "completed",
    "failed",
    name="generation_job_status",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "presentations",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=12), nullable=False),
        sa.Column("slide_count", sa.Integer(), nullable=False),
        sa.Column("status", presentation_status, nullable=False),
        sa.Column("theme_key", sa.String(length=60), nullable=False),
        sa.Column("outline", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_presentations_owner_id"),
        "presentations",
        ["owner_id"],
        unique=False,
    )

    op.create_table(
        "generation_jobs",
        sa.Column("presentation_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("status", generation_job_status, nullable=False),
        sa.Column("current_step", sa.String(length=120), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generation_jobs_owner_id"),
        "generation_jobs",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generation_jobs_presentation_id"),
        "generation_jobs",
        ["presentation_id"],
        unique=False,
    )

    op.create_table(
        "slides",
        sa.Column("presentation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("layout_key", sa.String(length=60), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("speaker_notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "presentation_id",
            "position",
            name="uq_slide_presentation_position",
        ),
    )
    op.create_index(
        op.f("ix_slides_presentation_id"),
        "slides",
        ["presentation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_slides_presentation_id"), table_name="slides")
    op.drop_table("slides")
    op.drop_index(
        op.f("ix_generation_jobs_presentation_id"),
        table_name="generation_jobs",
    )
    op.drop_index(op.f("ix_generation_jobs_owner_id"), table_name="generation_jobs")
    op.drop_table("generation_jobs")
    op.drop_index(op.f("ix_presentations_owner_id"), table_name="presentations")
    op.drop_table("presentations")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    generation_job_status.drop(op.get_bind(), checkfirst=True)
    presentation_status.drop(op.get_bind(), checkfirst=True)
