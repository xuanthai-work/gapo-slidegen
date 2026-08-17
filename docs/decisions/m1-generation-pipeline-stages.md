# M1 generation pipeline stages

Status: accepted and implemented

## Context

The current M1 generation pipeline already separates source ingestion from
presentation rendering, but several conceptual phases are folded inside the
provider's `generate()` call. The web product uses a one-click flow that hides
the outline step, while the backend keeps outline records and endpoints mostly
for compatibility. As the product moves toward richer AI assistance — automatic
images, charts, tables, and possibly user-reviewable story plans — we need a
shared vocabulary for the pipeline stages so that each stage has a single
responsibility, a testable boundary, and an explicit output shape.

This decision refines `m1-generation-pipeline.md` by decomposing the provider
side into discrete stages without changing the public API or the default
dashboard behavior.

## Decision

A generation job is produced by the following stages, in order:

```text
User Prompt / Document
        ↓
Document normalization
        ↓
Content understanding
        ↓
Story / Outline
        ↓
Slide planning
        ↓
Layout selection
        ↓
Content generation
        ↓
Asset planning
        ↓
Asset generation  (optional, batched)
        ↓
Slide schema
        ↓
Renderer / Export
```

### 1. User Prompt / Document

Raw input from the authenticated user: a prompt, a manuscript, or an uploaded
DOCX/PPTX/text-PDF file. Captured by the web dashboard and delivered to
`/v1/sources/text` or `/v1/sources/files`.

### 2. Document normalization

Extract a clean, bounded text representation plus structural sections. This
stage is deterministic, runs inside the FastAPI process, and never calls an
external model.

Current output shape: `SourceDocument` (title, kind, text, sections).

### 3. Content understanding

Build a lightweight semantic summary of the normalized source: intent,
audience, key takeaways, tone, and any explicit constraints. This stage may be
implemented by a small LLM call or by deterministic heuristics; it is an
internal preparation step for outline generation.

Output shape (future): `ContentUnderstanding` carrying metadata only — no
finished copy.

### 4. Story / Outline

Produce a structured story plan: ordered slides, each with a slide-level title,
a takeaway/content summary, an optional semantic layout id, and optional story
blocks (heading/body/label/value). This is the primary user-reviewable
checkpoint; the backend persists it as an `OutlineRecord` with optimistic
revision control.

Current output shape: list of outline items validated by
`validate_outline_items()` (`apps/api/app/generation/outlines.py`).

### 5. Slide planning

Map each outline item to a concrete slide purpose and decide what kinds of
elements it will carry (title, body, list, metrics, image, chart, table). This is
a local decision layer; it does not yet assign coordinates.

### 6. Layout selection

Choose the final layout implementation for each slide purpose. For Modern Blue
this maps to `PresentonTemplateAdapter` layout ids; for compatibility themes it
maps to product-owned native archetypes.

Current mapping: `STORY_LAYOUT_IDS` → template ids
(`apps/api/app/generation/presenton_template.py`).

### 7. Content generation

Fill the selected layout with finished text and shape elements according to the
outline copy. The result is still semantic: text runs, lists, and placeholder
shapes with logical positions, not final pixel coordinates.

Current implementation: `PresentonContentGenerator` and `NativeContentGenerator`
in `apps/api/app/generation/stages/content_generator.py`.

### 8. Asset planning

Decide which slides need generated or imported assets (images, charts, tables,
SVG diagrams) and produce an asset request list per slide. This stage must run
after layout selection so it knows which slots can accept assets.

Current implementation: `StubAssetPlanner` in
`apps/api/app/generation/stages/asset_planner.py`. It currently assigns a hero
image to `split-image` slides only.

### 9. Asset generation (optional, batched)

Execute the asset request list. Image generation uses
`ImageGenerationProvider`; chart/table/SVG generation may use local renderers.
Each produced asset is stored as an immutable, owner-scoped `AssetRecord` and
referenced by `assetId`.

Current implementation: `ImageAssetGenerator` in
`apps/api/app/generation/stages/asset_generator.py`; executed by the worker
when an image provider is configured. Failures are logged per asset and do not
fail the whole deck.

### 10. Slide schema

Assemble the final canonical presentation JSON: absolute geometry, stable ids,
theme, and element tree. Must conform to `packages/slide-schema` and pass
`validate_presentation_document()`.

Current implementation: `GenerationPipeline.render()` delegates to the active
`ContentGenerator` (`apps/api/app/generation/stages/content_generator.py`).

### 11. Renderer / Export

Render the canonical document for display, present mode, or native PPTX export.
The renderer is read-only and does not mutate canonical geometry.

Current implementations: web editor canvas, present mode, and
`packages/pptx-exporter`.

## Mapping to current code

| Stage | Current location | Notes |
|---|---|---|
| User Prompt / Document | `apps/web/src/app/dashboard.tsx` | One-click flow today. |
| Document normalization | `apps/api/app/ingestion.py` + `extract_document()` | Returns `SourceDocument`. |
| Content understanding | Implicit inside `generate_outline()` prompts | Not a separate struct yet. |
| Story / Outline | `apps/api/app/generation/outlines.py` + `/v1/outlines` endpoints | Persisted but not exposed in product flow. |
| Slide planning | Implicit in outline item fields | Could be extracted. |
| Layout selection | `STORY_LAYOUT_IDS` → template ids | `apps/api/app/generation/presenton_template.py` |
| Content generation | `apps/api/app/generation/stages/content_generator.py` | `PresentonContentGenerator` and `NativeContentGenerator`. |
| Asset planning | `apps/api/app/generation/stages/asset_planner.py` | `StubAssetPlanner`; currently only `split-image` slides. |
| Asset generation | `apps/api/app/generation/stages/asset_generator.py` | `ImageAssetGenerator` with bounded thread-pool concurrency. |
| Slide schema | `packages/slide-schema/src/schema.ts` + `GenerationPipeline.render()` | Zod-validated canonical JSON assembled by ContentGenerator. |
| Renderer / Export | `packages/pptx-exporter/src/index.ts` + web canvas | Read-only rendering. |

## Consequences

- Each stage gains one clear responsibility, making it easier to swap providers,
  add tests, or retry a single stage.
- The outline record becomes a real checkpoint rather than a compatibility
  holdover.
- Asset planning is explicitly recognized as a missing boundary; it should be
  added before enabling automatic images, charts, or tables in generated decks.
- The default web flow can still skip user-facing outline review; the dashboard
  calls `/v1/generations` with `source_id` and lets the worker run all stages.
- A future "advanced" flow can stop at `Story / Outline` for user review, then
  continue from `/v1/generations` with `outline_id`.

## Future work

1. Define `ContentUnderstanding` as an explicit internal data structure and
   optional provider call.
2. Extend `StubAssetPlanner` to assign images/charts/tables to additional layouts
   (profile cards, alternating cards, highlight metrics, etc.).
3. Add chart/table/SVG asset generation alongside image generation.
4. Extend `STORY_LAYOUT_IDS` and the template adapter to accept chart and table
   data payloads.
5. Add an optional advanced flow in the dashboard that exposes the outline
   review step.
