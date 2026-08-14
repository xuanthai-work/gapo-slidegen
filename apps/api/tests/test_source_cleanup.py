from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.models import SourceRecord
from app.sources.cleanup import build_expired_sources_query, delete_expired_sources
from app.storage import LocalObjectStorage


class FakeScalarResult:
    def __init__(self, records: list[SourceRecord]) -> None:
        self.records = records

    def __iter__(self):
        return iter(self.records)


class FakeSession:
    def __init__(self, records: list[SourceRecord]) -> None:
        self.records = records
        self.deleted: list[SourceRecord] = []
        self.flushed = False

    def scalars(self, _statement):
        return FakeScalarResult(self.records)

    def delete(self, record: SourceRecord) -> None:
        self.deleted.append(record)

    def flush(self) -> None:
        self.flushed = True


def _source(storage_key: str | None) -> SourceRecord:
    return SourceRecord(
        id=uuid4(),
        owner_id=uuid4(),
        kind="prompt",
        title="Expired source",
        storage_key=storage_key,
        extracted_text="No longer needed",
        sections=[],
        requires_ocr=False,
        warnings=[],
        delete_after=datetime.now(UTC) - timedelta(minutes=1),
    )


def test_expired_query_is_bounded_locked_and_skips_active_jobs() -> None:
    statement = build_expired_sources_query(now=datetime.now(UTC), limit=25)
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "source_records.delete_after" in sql
    assert "NOT (EXISTS" in sql
    assert "generation_jobs.status IN ('queued', 'running')" in sql
    assert "LIMIT 25" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql


def test_cleanup_deletes_object_before_database_record(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    file_record = _source("users/owner/sources/expired/source.docx")
    text_record = _source(None)
    storage.put(file_record.storage_key or "", b"expired")
    session = FakeSession([file_record, text_record])

    deleted = delete_expired_sources(
        session,  # type: ignore[arg-type]
        storage,
        now=datetime.now(UTC),
        limit=10,
    )

    assert deleted == 2
    assert session.deleted == [file_record, text_record]
    assert session.flushed
    assert not (tmp_path / (file_record.storage_key or "")).exists()
