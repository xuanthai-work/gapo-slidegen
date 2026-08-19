# M1 generation pipeline boundary

Status: implemented. Company gateway is the live LLM adapter; Gemini is
disabled. Operational detail lives in `docs/generation-pipeline-architecture.md`.

## Flow

1. An authenticated user creates a generation request from an owned source.
2. FastAPI verifies source ownership and enqueues a PostgreSQL `generate` job.
3. A separate worker claims the job with `FOR UPDATE SKIP LOCKED`.
4. The configured presentation provider returns canonical slide JSON.
5. The worker stores the presentation under the same owner and completes the
   job with a presentation id.
6. The dashboard polls job status and opens the persisted document in the web
   editor when generation succeeds.
7. Editor changes are debounced and saved through an optimistic-revision PATCH.

The dashboard uses one-click generation from a new source and opens the editable
presentation when the background job completes. The worker runs staged
understanding, outline, deck/slide planning, layout selection, copy writing,
compile, and rule-based validate/repair. There is no user-facing outline review
in the default web flow. Existing outline records and endpoints remain for
database compatibility and are not called by the web product.

All job and presentation reads filter by the authenticated owner. The maximum
slide count remains 30 at both the API and canonical schema boundaries. New
generation flow always uses Auto: the AI chooses a narrative-appropriate count,
normally 5 to 15. The user can add or remove slides in the editor afterward.
The offline stub uses a bounded word-count heuristic for Auto mode.

Generation jobs also snapshot a validated theme id. Modern Blue is the default
and is compiled from the pinned Presenton Modern template artifact;
Editorial Cobalt, Warm Studio, and Midnight Signal use product-owned native
layouts. Chart and table layouts remain excluded from automatic selection.

## Provider boundary

`PresentationProvider` receives normalized source text, sections, language,
an optional requested slide count, title, and a preallocated presentation id.
The worker actually runs `GenerationPipeline` (`apps/api/app/generation/stages/`),
which composes story planning, layout selection, copy writing, and compile.
The same planner boundary exposes outline generation and scoped rewrite.

Configured providers:

- `stub` — deterministic offline placeholder. Safe default in `.env.example`.
- `company-gateway` — OpenAI-compatible chat completions. This is the live
  generation path. JSON stages paste schema into the prompt (no native
  `response_format`); copy stream uses a tagged grammar. Requests set
  `max_tokens` to 8192.

`google-ai-studio` is **not** constructed by `factory.py`. The Gemini module
remains in the tree as commented legacy. Re-enable only by changing the factory.

The same planner supports scoped text rewriting from the editor. A whole-slide
response must contain exactly the original block ids; geometry stays local.

Text-to-image generation is disabled at the API (`build_image_provider` raises)
and in the worker (`NullAssetPlanner` / `NullAssetGenerator`). Uploaded images
and non-image flows continue to work.

## Worker behavior

- Claim and provider execution are separated so the row lock is not held while
  waiting for model output.
- A deleted or wrong-owner source fails the claimed job.
- Provider failures produce a terminal failed job with a bounded error message.
- Successful output is stored in `presentations.document` as canonical JSON.
- A process crash recovery policy for stale running jobs remains future work.

## Save contract

Presentation updates require the current database revision. The update statement
filters by presentation id, owner id, and expected revision in one atomic query.
A stale editor receives HTTP 409 and stops autosaving until the user reloads,
instead of silently overwriting another tab.

Before persistence, the API checks document identity, schema version, title,
30-slide limit, stable slide/element ids, supported element types, finite
geometry, non-negative sizes, and nesting depth. The browser also validates a
loaded document with the canonical Zod schema.

The client queues only the newest pending document and serializes PATCH
requests. This prevents overlapping autosaves from creating false conflicts.

Image elements reference an immutable asset id instead of a filesystem path or
public URL. The API accepts PNG, JPEG, and WebP files up to 10 MB, validates
their magic bytes, and stores them below an owner-specific prefix. Asset reads
and deletes filter by the authenticated owner. Presentation saves recursively
verify every referenced asset id, preventing one user from attaching another
user's upload by editing canonical JSON directly.

Owned presentations are listed on the dashboard for reopening. Present mode
renders the canonical document read-only and supports keyboard navigation. The
Next.js Node route exports the current in-memory document through the existing
schema-native PPTX adapter after verifying the user's FastAPI session. It uses
that same session to resolve owned assets from FastAPI and embeds their bytes in
the PPTX; no AI or external service receives presentation content during
export.

Presentation rename and delete operations filter by both presentation id and
authenticated owner. Rename updates the database title and canonical
`document.title` together. Both operations require the expected revision;
stale dashboard/editor tabs receive HTTP 409 instead of overwriting or deleting
newer work. Editor title changes use the existing canonical operation and
autosave path, while dashboard rename uses a dedicated atomic endpoint.
Deleting a presentation does not eagerly delete assets because an immutable
asset id may still be referenced by another deck or edit history.

## Local run

After PostgreSQL is running and migrated, run the worker separately:

```bash
npm run worker:dev
```

`SLIDEGEN_GENERATION_PROVIDER=stub` is the safe local default until the company
gateway is configured. After changing provider settings, restart **both** the
API process and `npm run worker:dev`.
