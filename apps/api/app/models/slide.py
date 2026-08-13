import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Slide(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "slides"
    __table_args__ = (
        UniqueConstraint("presentation_id", "position", name="uq_slide_presentation_position"),
    )

    presentation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("presentations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    layout_key: Mapped[str] = mapped_column(String(60), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    speaker_notes: Mapped[str | None] = mapped_column(Text)

    presentation = relationship("Presentation", back_populates="slides")
