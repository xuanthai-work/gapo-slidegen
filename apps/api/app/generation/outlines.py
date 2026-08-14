from uuid import UUID, uuid4

from sqlalchemy import Select, Update, func, select, update
from sqlalchemy.orm import Session

from ..models import OutlineRecord, User
from ..sources.service import build_owned_source_query
from .provider import OutlineProvider, OutlineRequest


class OutlineNotFound(ValueError):
    pass


class OutlineConflict(ValueError):
    pass


class InvalidOutline(ValueError):
    pass


def validate_outline_items(items: object) -> list[dict[str, object]]:
    if not isinstance(items, list) or not 1 <= len(items) <= 30:
        raise InvalidOutline("An outline must contain between 1 and 30 slides.")
    ids: set[str] = set()
    validated: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict):
            raise InvalidOutline("Every outline item must be an object.")
        item_id = item.get("id")
        title = item.get("title")
        content = item.get("content", "")
        if not isinstance(item_id, str) or not item_id.strip() or len(item_id) > 160:
            raise InvalidOutline("Every outline item requires a stable id.")
        if item_id in ids:
            raise InvalidOutline("Outline item ids must be unique.")
        if not isinstance(title, str) or not title.strip() or len(title) > 500:
            raise InvalidOutline("Every outline item requires a valid title.")
        if not isinstance(content, str) or len(content) > 100_000:
            raise InvalidOutline("Outline item content is invalid.")
        ids.add(item_id)
        validated.append({"id": item_id, "title": title.strip(), "content": content.strip()})
    return validated


def build_owned_outline_query(outline_id: UUID, owner_id: UUID) -> Select[tuple[OutlineRecord]]:
    return select(OutlineRecord).where(
        OutlineRecord.id == outline_id,
        OutlineRecord.owner_id == owner_id,
    )


def build_source_outline_query(source_id: UUID, owner_id: UUID) -> Select[tuple[OutlineRecord]]:
    return (
        select(OutlineRecord)
        .where(
            OutlineRecord.source_id == source_id,
            OutlineRecord.owner_id == owner_id,
        )
        .order_by(OutlineRecord.updated_at.desc(), OutlineRecord.id.desc())
        .limit(1)
    )


def build_update_outline_statement(
    outline_id: UUID,
    owner_id: UUID,
    expected_revision: int,
    items: list[dict[str, object]],
) -> Update:
    return (
        update(OutlineRecord)
        .where(
            OutlineRecord.id == outline_id,
            OutlineRecord.owner_id == owner_id,
            OutlineRecord.revision == expected_revision,
        )
        .values(items=items, revision=expected_revision + 1, updated_at=func.now())
        .returning(OutlineRecord)
    )


class OutlineService:
    def __init__(self, session: Session, provider: OutlineProvider) -> None:
        self.session = session
        self.provider = provider

    def create(
        self,
        *,
        user: User,
        source_id: UUID,
        slide_count: int,
        language: str,
    ) -> OutlineRecord:
        source = self.session.scalar(build_owned_source_query(source_id, user.id))
        if source is None:
            raise OutlineNotFound("Source not found.")
        existing = self.session.scalar(build_source_outline_query(source_id, user.id))
        if existing is not None:
            return existing
        items = validate_outline_items(
            self.provider.generate_outline(
                OutlineRequest(
                    title=source.title,
                    text=source.extracted_text,
                    sections=source.sections,
                    language=language,
                    slide_count=slide_count,
                    source_kind=source.kind,
                )
            )
        )
        record = OutlineRecord(
            id=uuid4(),
            owner_id=user.id,
            source_id=source.id,
            title=source.title,
            language=language,
            items=items,
            revision=0,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_owned(self, outline_id: UUID, user: User) -> OutlineRecord | None:
        return self.session.scalar(build_owned_outline_query(outline_id, user.id))

    def update(
        self,
        *,
        outline_id: UUID,
        user: User,
        expected_revision: int,
        items: object,
    ) -> OutlineRecord:
        validated = validate_outline_items(items)
        record = self.session.scalar(
            build_update_outline_statement(
                outline_id,
                user.id,
                expected_revision,
                validated,
            )
        )
        if record is not None:
            return record
        if self.get_owned(outline_id, user) is None:
            raise OutlineNotFound("Outline not found.")
        raise OutlineConflict("Outline changed in another session. Reload before saving again.")
