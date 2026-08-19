from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class GenerationCheckpointStatus(StrEnum):
    PARTIAL = "partial"
    COMPLETED = "completed"


def _enum_values(enum: type[StrEnum]) -> list[str]:
    return [member.value for member in enum]


class GenerationCheckpoint(Base):
    __tablename__ = "generation_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "slide_id",
            name="uq_generation_checkpoints_job_slide",
        ),
        CheckConstraint(
            "attempt >= 1",
            name="ck_generation_checkpoints_attempt_positive",
        ),
        CheckConstraint(
            "sequence >= 1",
            name="ck_generation_checkpoints_sequence_positive",
        ),
        Index(
            "ix_generation_checkpoints_job_sequence",
            "job_id",
            "sequence",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    job_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_id: Mapped[str] = mapped_column(String(160), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_slots: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    canonical_slide: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    status: Mapped[GenerationCheckpointStatus] = mapped_column(
        Enum(
            GenerationCheckpointStatus,
            name="generation_checkpoint_status",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=GenerationCheckpointStatus.PARTIAL,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
