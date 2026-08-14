# Gapo SlideGen

Gapo SlideGen is a self-hosted internal web application for creating, editing,
presenting, and exporting AI-assisted presentations.

The repository is being rebuilt as a modular monorepo. The first implementation
milestone establishes a versioned slide contract and isolates the editor from
authentication, persistence, and AI providers.

## Current status

- Architecture, implementation plan, product specification, and initial design
  direction have been approved.
- The previous implementation is preserved in Git branch
  `archive/pre-rebuild-20260813`.
- The M0 editor boundary and schema-native PPTX export spikes have passed.
- PPTX export produces separately editable text, shapes, tables, charts, and
  uploaded images; a manual PowerPoint/LibreOffice fidelity pass remains.
- The FastAPI ingestion boundary handles prompt, manuscript, DOCX, PPTX, and
  text PDFs. PostgreSQL job models and the first Alembic migration are present.
- Internal email/password accounts use Argon2 and revocable opaque session
  cookies. Ingestion endpoints require authentication.
- Authenticated source endpoints persist normalized content and place uploaded
  files below owner-specific storage prefixes with compensating cleanup.
- The web shell includes login/register, an authenticated source dashboard, and
  the editor boundary at `/editor`.
- Generation requests run through PostgreSQL jobs and a separate provider
  worker. The current local stub validates the full flow without external data
  transfer; the gateway adapter is pending its API contract.

## Workspace

```text
apps/
  api/            FastAPI ingestion API and PostgreSQL job foundation
  web/            Next.js product shell and editor spike
packages/
  slide-schema/   Canonical presentation JSON and edit operations
  slide-editor/   Product-owned boundary around the ported editor subsystem
  pptx-exporter/  Canonical-schema to native OOXML adapter
docs/
  decisions/      Architecture and dependency decisions
  provenance/     Source, license, modification, and sync records
LICENSES/         Third-party license texts
```

## Commands

```bash
npm install
uv sync --project apps/api --python 3.12
npm run check
npm test
```

Run the local services independently:

```bash
npm run db:up
npm run db:migrate
npm run dev --workspace @gapo-slidegen/web
npm run api:dev
npm run worker:dev
```

The local PostgreSQL credentials in `compose.yaml` and `.env.example` are for
development only. Docker Desktop must be running before `npm run db:up`.

The application services and deployment configuration will be added through
vertical milestones after the M0 feasibility checks pass.
