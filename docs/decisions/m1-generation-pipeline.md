# M1 generation pipeline boundary

Status: local end-to-end foundation implemented; gateway adapter pending

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
presentation when the background job completes. The provider creates a bounded
internal story plan, but there is no user-facing outline review step. Existing
outline records and endpoints remain temporarily for database compatibility and
are not called by the web product.

All job and presentation reads filter by the authenticated owner. The maximum
slide count remains 30 at both the API and canonical schema boundaries.

Generation jobs also snapshot a validated theme id. Modern Blue is the default
and is compiled from the pinned Presenton Modern template artifact;
Editorial Cobalt, Warm Studio, and Midnight Signal remain compatibility
fallbacks for existing decks.
Modern Blue cycles through six upstream content layouts compatible with the
current text-only story plan. Its nested Presenton component tree is flattened
to editable canonical text and shape objects while retaining component/slot
metadata. Chart and table layouts remain excluded from automatic selection
until the story plan provides structured data. The three compatibility themes
continue to use their six product-owned native layout archetypes.

## Provider boundary

`PresentationProvider` receives normalized source text, sections, language,
slide count, title, and a preallocated presentation id. It returns canonical
presentation JSON and has no dependency on FastAPI, PostgreSQL, or the editor.
The same provider boundary exposes outline generation; the local stub keeps
both phases deterministic and offline until the gateway contract is available.

The default provider is `stub`. It deterministically creates native text and
shape elements and sends no data outside the machine. It exists to test the
queue, persistence, polling, and editor-loading path; it is not presented as AI
generation quality.

`google-ai-studio` is an optional temporary external provider. It uses Google's
official Gen AI SDK and a Pydantic response schema to create exactly the
requested number of outline items. The key and model id are backend-only
environment settings. Source text is bounded before transmission, and uploaded
assets are not included. Internal plan-to-slide rendering remains local and
deterministic, so the editable document never depends on model-generated
geometry. Provider errors are bounded and the configured key is redacted.

The same provider boundary supports scoped text rewriting. An authenticated
editor request sends either the selected text or all text blocks on the current
slide, plus the user instruction and language, to the backend provider. A
whole-slide response must contain exactly the original block ids; the client
keeps geometry and styles local and applies the rewrite as one canonical
`replace-slide` operation, preserving one-step undo/redo and autosave behavior.
The provider never receives the full presentation document for this operation.

Image generation uses a separate `ImageGenerationProvider` and model setting.
An authenticated request contains only a bounded prompt and aspect ratio. The
adapter returns bytes to the API, which independently validates size and image
magic bytes before persisting an owner-scoped asset. The editor can insert the
asset or replace a selected image through a normal canonical operation, so
autosave and undo/redo remain intact and the provider never receives slide
content, geometry, or existing assets. The default image provider is disabled;
uploaded images and all non-image-generation flows continue to work offline.

The company gateway adapter will be implemented after its request format,
structured-output behavior, model list, authentication method, and error
contract are known. A second provider can implement the same protocol later.

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

`SLIDEGEN_GENERATION_PROVIDER=stub` is the safe local default until the gateway
adapter is configured.
