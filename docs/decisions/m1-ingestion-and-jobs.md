# M1 document ingestion and DB-backed jobs

Status: ingestion and source persistence implemented; cleanup worker pending

## Implemented boundary

The FastAPI application accepts either prompt/manuscript JSON or DOCX, PPTX,
and text-based PDF uploads. Every input is converted to one `SourceDocument`
contract with ordered sections, combined text, warnings, and a `requires_ocr`
flag.

Image-only PDFs are detected but not OCR'd. This keeps the agreed MVP boundary
explicit and prevents document data from being sent to an undeclared external
service.

Uploaded binary storage is represented by an `ObjectStorage` protocol. The
local adapter writes atomically below a configured root and rejects absolute or
traversing keys. A future S3, MinIO, or other cloud adapter can implement the
same protocol without changing ingestion logic.

## Job queue decision

Generation jobs use PostgreSQL as the source of truth. Workers claim one queued
row with `SELECT ... FOR UPDATE SKIP LOCKED`, then commit an explicit state
transition. This supports multiple worker processes without two workers
claiming the same job.

Allowed transitions are:

- `queued -> running | canceled`
- `running -> succeeded | failed | canceled`
- terminal states cannot transition again

The current concurrency target is two generation jobs. Redis is intentionally
not required at this scale. It can later be added for ephemeral signals or a
higher-throughput broker while PostgreSQL remains authoritative.

## Data lifecycle

`source_records` includes `storage_key` and `delete_after`. This supports the
approved automatic-deletion requirement. Authentication now establishes
ownership. Raw uploads are written under an owner-specific prefix, and a failed
database flush removes the just-written file to avoid an orphan. The default
retention period is 24 hours and is configurable. The scheduled cleanup worker
remains to be wired.

The authenticated dashboard can create prompt/manuscript sources, upload
supported documents, and list the latest 50 sources for the current owner. API
responses intentionally omit storage keys and owner ids.

## Dependency baseline checked 2026-08-14

- Python 3.12
- FastAPI 0.139.2
- Uvicorn 0.51.0
- SQLAlchemy 2.0.51
- Psycopg 3.3.4
- Alembic 1.18.5
- Pydantic Settings 2.14.2
- pypdf 6.13.3
- python-docx 1.2.0
- python-pptx 1.0.2
- python-multipart 0.0.32
- pytest 9.1.1 and HTTPX2 2.9.0 for tests

Exact direct and transitive versions are recorded in `apps/api/uv.lock`.

## Verification

- The ingestion, API, storage, ownership, job-query, and state-transition test
  suite passes.
- The initial Alembic migration compiles to PostgreSQL SQL offline.
- The claim query test verifies `FOR UPDATE SKIP LOCKED` under the PostgreSQL
  dialect.

## Next integration

Add the scheduled retention cleanup worker and the real gateway provider
adapter. Then add a PostgreSQL container integration test for migration
upgrade/downgrade and concurrent claims.
