"""Create source records and DB-backed generation jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260814_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

job_type = postgresql.ENUM("ingest", "generate", "export", name="job_type", create_type=False)
job_status = postgresql.ENUM(
    "queued", "running", "succeeded", "failed", "canceled", name="job_status", create_type=False
)


def upgrade() -> None:
    job_type.create(op.get_bind(), checkfirst=True)
    job_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "source_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("filename", sa.String(500)),
        sa.Column("content_type", sa.String(255)),
        sa.Column("storage_key", sa.String(1_000), unique=True),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("requires_ocr", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("warnings", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("delete_after", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_source_records_owner_id", "source_records", ["owner_id"])
    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("source_records.id", ondelete="SET NULL")),
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_job_progress_range"),
    )
    op.create_index("ix_generation_jobs_owner_id", "generation_jobs", ["owner_id"])
    op.create_index("ix_generation_jobs_source_id", "generation_jobs", ["source_id"])
    op.create_index("ix_generation_jobs_claim", "generation_jobs", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("generation_jobs")
    op.drop_table("source_records")
    job_status.drop(op.get_bind(), checkfirst=True)
    job_type.drop(op.get_bind(), checkfirst=True)
