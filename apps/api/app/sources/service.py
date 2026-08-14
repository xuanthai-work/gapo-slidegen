import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from ..ingestion import SourceDocument, extract_document
from ..models import SourceRecord, User
from ..storage import ObjectStorage


def safe_filename(value: str) -> str:
    basename = Path(value.replace("\\", "/")).name
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("._")
    return (sanitized or "upload")[:180]


def build_owned_source_query(source_id: UUID, owner_id: UUID) -> Select[tuple[SourceRecord]]:
    return select(SourceRecord).where(
        SourceRecord.id == source_id,
        SourceRecord.owner_id == owner_id,
    )


def build_owned_sources_query(owner_id: UUID, limit: int = 50) -> Select[tuple[SourceRecord]]:
    return (
        select(SourceRecord)
        .where(SourceRecord.owner_id == owner_id)
        .order_by(SourceRecord.created_at.desc(), SourceRecord.id.desc())
        .limit(limit)
    )


class SourceService:
    def __init__(self, session: Session, storage: ObjectStorage, retention: timedelta) -> None:
        self.session = session
        self.storage = storage
        self.retention = retention

    def _record(
        self,
        *,
        user: User,
        document: SourceDocument,
        filename: str | None = None,
        content_type: str | None = None,
        storage_key: str | None = None,
    ) -> SourceRecord:
        record = SourceRecord(
            id=uuid4(),
            owner_id=user.id,
            kind=document.kind,
            title=document.title,
            filename=filename,
            content_type=content_type,
            storage_key=storage_key,
            extracted_text=document.text,
            sections=[section.model_dump() for section in document.sections],
            requires_ocr=document.requires_ocr,
            warnings=document.warnings,
            delete_after=datetime.now(UTC) + self.retention,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def create_text(self, user: User, document: SourceDocument) -> SourceRecord:
        return self._record(user=user, document=document)

    def create_file(
        self,
        user: User,
        *,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> SourceRecord:
        document = extract_document(filename, content_type, data)
        source_id = uuid4()
        clean_name = safe_filename(filename)
        key = f"users/{user.id}/sources/{source_id}/{clean_name}"
        self.storage.put(key, data)
        try:
            record = SourceRecord(
                id=source_id,
                owner_id=user.id,
                kind=document.kind,
                title=document.title,
                filename=clean_name,
                content_type=content_type,
                storage_key=key,
                extracted_text=document.text,
                sections=[section.model_dump() for section in document.sections],
                requires_ocr=document.requires_ocr,
                warnings=document.warnings,
                delete_after=datetime.now(UTC) + self.retention,
            )
            self.session.add(record)
            self.session.flush()
            return record
        except Exception:
            self.storage.delete(key)
            raise

    def get_owned(self, source_id: UUID, user: User) -> SourceRecord | None:
        return self.session.scalar(build_owned_source_query(source_id, user.id))

    def list_owned(self, user: User, limit: int = 50) -> list[SourceRecord]:
        return list(self.session.scalars(build_owned_sources_query(user.id, limit)))

    def delete_owned(self, source_id: UUID, user: User) -> bool:
        record = self.get_owned(source_id, user)
        if record is None:
            return False
        if record.storage_key:
            self.storage.delete(record.storage_key)
        self.session.delete(record)
        self.session.flush()
        return True
