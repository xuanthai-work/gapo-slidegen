import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PresentationStatus(StrEnum):
    DRAFT = "draft"
    OUTLINING = "outlining"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class Presentation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "presentations"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(12), default="vi", nullable=False)
    slide_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PresentationStatus] = mapped_column(
        Enum(
            PresentationStatus,
            name="presentation_status",
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        default=PresentationStatus.DRAFT,
        nullable=False,
    )
    theme_key: Mapped[str] = mapped_column(String(60), default="gapo-light", nullable=False)
    outline: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    owner = relationship("User", back_populates="presentations")
    slides = relationship(
        "Slide",
        back_populates="presentation",
        cascade="all, delete-orphan",
        order_by="Slide.position",
    )
    jobs = relationship(
        "GenerationJob", back_populates="presentation", cascade="all, delete-orphan"
    )
