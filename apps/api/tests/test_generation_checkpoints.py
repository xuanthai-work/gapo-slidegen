from uuid import UUID, uuid4

from sqlalchemy.dialects import postgresql

from app.generation.checkpoints import GenerationCheckpointService
from app.generation.events import GenerationEvent, SLOT_SNAPSHOT
from app.generation.models import SlideContent
from app.generation.checkpoint_repository import (
    CheckpointUpsert,
    GenerationCheckpointRepository,
    build_checkpoint_upsert_statement,
    build_job_checkpoints_query,
)
from app.models import GenerationCheckpoint, GenerationCheckpointStatus


def _completed_event(*, attempt: int = 2, sequence: int = 8) -> GenerationEvent:
    return GenerationEvent(
        version=1,
        type="slide.completed",
        job_id=str(uuid4()),
        attempt=attempt,
        sequence=sequence,
        slide_id="slide-2",
        slot=None,
        data={
            "content": SlideContent(
                slide_id="slide-2",
                title="A title",
                layout_id="title-body",
                slots={"body": "A body", "items": [{"heading": "First"}]},
            )
        },
    )


def test_checkpoint_model_keys_each_job_slide_and_cascades_with_job() -> None:
    table = GenerationCheckpoint.__table__

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    job_fk = next(iter(table.c.job_id.foreign_keys))

    assert ("job_id", "slide_id") in unique_columns
    assert job_fk.target_fullname == "generation_jobs.id"
    assert job_fk.ondelete == "CASCADE"
    assert table.c.completed_slots.type.__class__.__name__ == "JSONB"
    assert table.c.canonical_slide.nullable is True


def test_checkpoint_upsert_only_replaces_newer_attempt_or_nonstale_sequence() -> None:
    values = CheckpointUpsert(
        job_id=uuid4(),
        slide_id="slide-1",
        attempt=3,
        sequence=7,
        completed_slots=[{"slot": "title", "value": "Replacement"}],
        canonical_slide=None,
        status=GenerationCheckpointStatus.COMPLETED,
    )

    sql = str(
        build_checkpoint_upsert_statement(values).compile(
            dialect=postgresql.dialect(),
        )
    )

    assert "ON CONFLICT (job_id, slide_id) DO UPDATE" in sql
    assert "generation_checkpoints.attempt < excluded.attempt" in sql
    assert "generation_checkpoints.attempt = excluded.attempt" in sql
    assert "generation_checkpoints.sequence <= excluded.sequence" in sql
    assert " OR " in sql
    assert "completed_slots = excluded.completed_slots" in sql


def test_job_checkpoint_query_is_ordered_by_completion_sequence() -> None:
    job_id = uuid4()

    sql = str(
        build_job_checkpoints_query(job_id).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "WHERE generation_checkpoints.job_id =" in sql
    assert "ORDER BY generation_checkpoints.sequence, generation_checkpoints.slide_id" in sql


def test_checkpoint_repository_reports_stale_attempt_when_upsert_returns_nothing() -> None:
    class FakeSession:
        def scalar(self, statement):
            return None

    repository = GenerationCheckpointRepository(FakeSession())  # type: ignore[arg-type]
    event = _completed_event()

    result = repository.upsert(
        CheckpointUpsert(
            job_id=UUID(event.job_id),
            slide_id=event.slide_id,
            attempt=event.attempt,
            sequence=event.sequence,
            completed_slots=[],
            canonical_slide=None,
            status=GenerationCheckpointStatus.COMPLETED,
        )
    )

    assert result is None


def test_checkpoint_service_persists_completed_content_in_slot_order() -> None:
    writes: list[CheckpointUpsert] = []

    class FakeRepository:
        def upsert(self, checkpoint: CheckpointUpsert) -> GenerationCheckpoint:
            writes.append(checkpoint)
            return GenerationCheckpoint()

    event = _completed_event()
    canonical_slide = {"id": "slide-2", "elements": []}

    result = GenerationCheckpointService(FakeRepository()).record_event(  # type: ignore[arg-type]
        event,
        validated_canonical_slide=canonical_slide,
    )

    assert result is not None
    assert writes[0].completed_slots == [
        {"slot": "title", "value": "A title"},
        {"slot": "body", "value": "A body"},
        {"slot": "items", "value": [{"heading": "First"}]},
    ]
    assert writes[0].canonical_slide == canonical_slide
    assert writes[0].status is GenerationCheckpointStatus.COMPLETED


def test_checkpoint_service_never_persists_snapshot_or_token_events() -> None:
    class FailingRepository:
        def upsert(self, checkpoint: CheckpointUpsert) -> GenerationCheckpoint:
            raise AssertionError("Transient events must not reach PostgreSQL")

    completed = _completed_event()
    service = GenerationCheckpointService(FailingRepository())  # type: ignore[arg-type]

    for event_type in (SLOT_SNAPSHOT, "slot.token"):
        event = GenerationEvent(
            version=completed.version,
            type=event_type,
            job_id=completed.job_id,
            attempt=completed.attempt,
            sequence=completed.sequence,
            slide_id=completed.slide_id,
            slot="body",
            data={"value": "transient"},
        )
        assert service.record_event(event) is None


def test_checkpoint_service_exposes_ordered_job_reconnect_state() -> None:
    job_id = uuid4()
    expected = [GenerationCheckpoint(slide_id="slide-1")]

    class FakeRepository:
        def list_for_job(self, requested_job_id: UUID) -> list[GenerationCheckpoint]:
            assert requested_job_id == job_id
            return expected

    service = GenerationCheckpointService(FakeRepository())  # type: ignore[arg-type]

    assert service.list_for_job(job_id) is expected
