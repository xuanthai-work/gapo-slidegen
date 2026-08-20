# M1 generation pipeline stages

Status: accepted and implemented. See `docs/generation-pipeline-architecture.md`
for the running worker path (call counts, copy policy, layout inventory).

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

Output shape: `ContentUnderstandingResult` (`intent`, `audience`, `tone`,
`key_takeaways`). Live path: `CompanyGatewayContentUnderstanding`. Stub returns
`None` and the outline still runs.

### 4. Story / Outline

Produce a structured story plan: ordered slides, each with a slide-level title,
a takeaway/content summary, an optional semantic layout id, and optional story
blocks (heading/body/label/value). This is the primary user-reviewable
checkpoint; the backend persists it as an `OutlineRecord` with optimistic
revision control.

Current output shape: list of outline items validated by
`validate_outline_items()` (`apps/api/app/generation/outlines.py`).

### 5. Slide planning

Map each outline item to a concrete slide purpose and communication structure
(density, item count, visual priority). Coordinates are still not assigned here.

Current implementation: `ProviderSlidePlanner` wrapping `plan_slide`, with
`OutlineSlidePlanner` as fallback.

### 6. Layout selection

Choose the final layout implementation for each slide purpose. The selected
Presenton template supplies layout ids; the color scheme is applied after
compile.

Current implementation: `ThemeDispatchLayoutSelector`, which always loads the
Presenton pack named in `theme_id` (`template:scheme`). Native selectors remain
only so older stored decks can still open.

### 7. Content generation

Fill the selected layout with finished text and shape elements according to the
outline copy. The result is still semantic: text runs, lists, and placeholder
shapes with logical positions, not final pixel coordinates.

Current implementation: `PresentonContentGenerator` for every new job.
`NativeContentGenerator` remains for previously stored native decks.

### 8. Asset planning

Decide which slides need generated or imported assets (images, charts, tables,
SVG diagrams) and produce an asset request list per slide. This stage must run
after layout selection so it knows which slots can accept assets.

Current implementation: `NullAssetPlanner` in
`apps/api/app/generation/stages/orchestrator.py`. Image slots stay empty.
`VisualIntentAssetPlanner` / `StubAssetPlanner` remain in the tree but are not
wired by `factory.py`.

### 9. Asset generation (optional, batched)

Execute the asset request list. Image generation uses
`ImageGenerationProvider`; chart/table/SVG generation may use local renderers.
Each produced asset is stored as an immutable, owner-scoped `AssetRecord` and
referenced by `assetId`.

Current implementation: `NullAssetGenerator` in the worker factory.
`ImageAssetGenerator` exists but is unused. Text-to-image HTTP routes return
disabled.

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
| User Prompt / Document | `apps/web/src/app/dashboard.tsx` | Generate opens template then color HUD. |
| Document normalization | `apps/api/app/ingestion.py` + `extract_document()` | Returns `SourceDocument`. |
| Content understanding | `apps/api/app/generation/stages/content_understanding.py` | One LLM call when the planner has `_chat`. |
| Story / Outline | `CompanyGatewayProvider.generate_outline` + `outline_schema.py` | Persisted outline records exist; web does not review them. |
| Deck planning | `ProviderDeckPlanner` / `plan_deck` | Narrative arc + per-slide role/goal. |
| Slide planning | `ProviderSlidePlanner` / `plan_slide` | One LLM call per slide: density, structure, archetype. |
| Layout selection | `ThemeDispatchLayoutSelector` | Presenton pack from `theme_id`. No LLM. |
| Content writing | `ProviderContentWriter` or `stream_deck_content` | One batch JSON call or one tagged stream. Slot names only; not layout ids. |
| Content generation | `ThemeDispatchContentGenerator` | Always Presenton compile + `apply_color_scheme`. |
| Asset planning | `NullAssetPlanner` | No-op. |
| Asset generation | `NullAssetGenerator` | No-op. |
| Validate / repair | `RuleBasedSlideValidator` + `DeterministicSlideRepairer` | Bounds, overlap, min font — not visual quality. |
| Slide schema | `packages/slide-schema` + `GenerationPipeline.render()` | Canonical JSON. |
| Renderer / Export | web canvas, present mode, `packages/pptx-exporter` | Read-only rendering. |

## Consequences

- Each stage has one responsibility, so providers and tests can swap a stage
  without rewriting the worker.
- The outline record can still become a user-facing checkpoint later; the
  default web flow skips that review.
- Asset planning/generation exist as code but are unwired (`Null*` in factory).
  Re-enabling images is a product choice, not an unfinished checklist item.

## Open questions

These are not a committed roadmap. Current progress is not necessarily the
right long-term direction.

- Eight Presenton packs × five schemes is the live inventory. Native layouts
  remain only for older stored decks. Visual mess is more often slot mapping or
  recolor contrast than a missing LLM stage.
- Deck/slide plan already carries `density` and `preferred_archetype`; each pack
  still has a modest set of auto-selectable layouts.
- Asset planning/generation code exists but is unwired.
- Rule-based validation does not score visual quality. A visual readability
  gate (screenshot + OCR, default off; not an aesthetic VLM) is specified in
  `docs/superpowers/specs/2026-08-20-visual-readability-gate-design.md`.
- An optional dashboard outline-review flow remains unbuilt.
