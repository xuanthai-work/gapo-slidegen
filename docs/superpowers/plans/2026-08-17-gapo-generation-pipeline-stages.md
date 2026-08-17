# Generation pipeline stages implementation plan

**Goal:** Refactor the backend generation boundary into explicit pipeline stages
and add the missing **Asset planning** boundary so that AI-generated slides can
automatically receive images while keeping the default dashboard one-click flow
unchanged.

**Scope:** Backend only (`apps/api`). No dashboard or editor UI changes in this
slice; the advanced outline-review flow remains future work.

**Architecture:** Introduce a `GenerationPipeline` orchestrator composed of
small, swappable stage implementations. The worker calls the stages in order;
each stage has a deterministic output shape and is independently testable.

**Status target after this plan:** ADR `docs/decisions/m1-generation-pipeline-stages.md`
is fully reflected in code; automatic image assets are produced for generated
decks when an image provider is configured.

---

## Global constraints

- Keep the public `/v1/generations` and `/v1/outlines` contracts unchanged.
- Keep the dashboard one-click flow (source → generation job → editor) unchanged.
- Preserve all existing tests; update imports only when files move.
- No new runtime Python dependencies.
- Image-provider configuration remains optional; when disabled, generated decks
  keep placeholder shapes instead of images.
- A single failed asset generation must **not** fail the whole deck; it is
  logged and skipped gracefully.
- All asset IDs in final schema must be owner-scoped and validated before
  persistence, reusing the existing `collect_asset_ids()` check.

---

## File structure

**Create:**
- `apps/api/app/generation/stages/__init__.py`
- `apps/api/app/generation/stages/models.py` — shared stage data classes
- `apps/api/app/generation/stages/protocols.py` — stage protocols
- `apps/api/app/generation/stages/story_planner.py` — deterministic stub planner
- `apps/api/app/generation/stages/content_understanding.py` — optional/no-op stage
- `apps/api/app/generation/stages/layout_selector.py` — semantic → template layout mapping
- `apps/api/app/generation/stages/content_generator.py` — schema renderer with asset injection
- `apps/api/app/generation/stages/asset_planner.py` — decides which slides need assets
- `apps/api/app/generation/stages/asset_generator.py` — batched asset generation/storage
- `apps/api/app/generation/stages/orchestrator.py` — `GenerationPipeline`
- `apps/api/tests/test_staged_pipeline.py`
- `apps/api/tests/test_asset_planning.py`
- `apps/api/tests/test_asset_generation.py`
- `apps/api/tests/test_presenton_image_slots.py`

**Modify:**
- `apps/api/app/generation/provider.py` — re-export stage protocols; keep `PresentationProvider` facade
- `apps/api/app/generation/stub_provider.py` — extract native rendering into content generator; keep thin facade
- `apps/api/app/generation/gemini_provider.py` — reduce to story planner + rewrite provider
- `apps/api/app/generation/company_gateway_provider.py` — reduce to story planner + rewrite provider
- `apps/api/app/generation/factory.py` — compose stage implementations into pipeline
- `apps/api/app/generation/presenton_template.py` — support asset injection for image slots
- `apps/api/app/generation/worker.py` — call pipeline stages explicitly so asset generation can use the DB session
- `packages/slide-schema/src/schema.ts` — optional `cornerRadius` on `ImageElement` if template rounding is preserved

---

## Data model additions (`stages/models.py`)

- `ContentUnderstandingResult` — intent, audience, tone, key takeaways (nullable; stub returns `None`).
- `StoryOutlineItem` — typed version of the validated outline dict.
- `StoryOutline` — ordered list of items.
- `SlidePlan` — per-slide purpose and accepted slot kinds (image, chart, table).
- `AssetSlot` — `(slide_index, slot_name, slot_kind, position_hint)`.
- `AssetRequest` — `(slot, prompt_or_data, fallback_enabled)`.
- `AssetPlan` — list of requests plus `owner_id` and `language`.
- `GeneratedAsset` — `(slot, asset_id | None, warning)`.
- `SlideRenderContext` — carries outline, theme, language, and resolved asset map.

---

## Stage protocols (`stages/protocols.py`)

```python
class ContentUnderstanding(Protocol):
    name: str
    def understand(self, source: SourceDocument) -> ContentUnderstandingResult | None: ...

class StoryPlanner(Protocol):
    name: str
    def generate_outline(self, request: OutlineRequest) -> list[dict[str, object]]: ...

class LayoutSelector(Protocol):
    name: str
    def select(self, outline_item: StoryOutlineItem, theme_id: str) -> str: ...

class ContentGenerator(Protocol):
    name: str
    def render(self, request: GenerationRequest, outline: StoryOutline, assets: Mapping[tuple[int, str], str]) -> dict[str, object]: ...

class AssetPlanner(Protocol):
    name: str
    def plan(self, outline: StoryOutline, request: GenerationRequest) -> AssetPlan: ...

class AssetGenerator(Protocol):
    name: str
    def generate(self, plan: AssetPlan) -> list[GeneratedAsset]: ...
```

`provider.py` keeps `PresentationProvider` as a backward-compatible facade that
delegates to the pipeline and disables asset generation (NullAssetGenerator).

---

## Task 1: Extract stage skeleton

**Files:** create `stages/` package, `models.py`, `protocols.py`, `orchestrator.py`.

- [ ] **Step 1:** Create `stages/models.py` with frozen dataclasses and helper
      constructors from raw outline dicts.
- [ ] **Step 2:** Create `stages/protocols.py` with the six protocols above.
- [ ] **Step 3:** Create `stages/orchestrator.py` `GenerationPipeline` class.
      Methods:
      - `generate_outline(request) -> list[dict]` (delegates to story planner).
      - `plan_assets(request, outline) -> AssetPlan` (delegates to asset planner).
      - `render(request, outline, assets) -> dict` (delegates to content generator).
      - `generate(request) -> dict` convenience method that runs with
        `NullAssetGenerator` so existing provider tests keep working.
- [ ] **Step 4:** Add `apps/api/tests/test_staged_pipeline.py` proving that
      `GenerationPipeline` with all-null stages returns a valid canonical
      document for stub and modern themes.
- [ ] **Step 5:** Commit `refactor(api): introduce generation stage protocols and orchestrator`.

---

## Task 2: Refactor rendering into `ContentGenerator`

**Files:** `stages/content_generator.py`, `stubs/native_renderer.py`, modify
`stub_provider.py`, `presenton_template.py`.

- [ ] **Step 1:** Move native (compatibility theme) rendering functions from
      `stub_provider.py` into `stages/content_generator.py` as
      `NativeContentGenerator`.
- [ ] **Step 2:** Move Modern Blue `PresentonTemplateAdapter` rendering into
      `stages/content_generator.py` as `PresentonContentGenerator`.
- [ ] **Step 3:** Make `stub_provider.py` a thin facade that instantiates
      `GenerationPipeline(..., NullAssetGenerator)` and exposes the existing
      `generate()` and `generate_outline()` signatures.
- [ ] **Step 4:** Update `factory.py` so `build_provider()` returns a configured
      `GenerationPipeline` instead of a monolithic provider. Keep
      `StubPresentationProvider` callable for tests that directly import it.
- [ ] **Step 5:** Run `npm run api:test`; fix import/test regressions.
- [ ] **Step 6:** Commit `refactor(api): split presentation renderer into ContentGenerator stages`.

---

## Task 3: Reduce LLM providers to `StoryPlanner`

**Files:** `gemini_provider.py`, `company_gateway_provider.py`.

- [ ] **Step 1:** Remove `renderer = StubPresentationProvider()` from both
      classes; rename internal classes to `GoogleAIStudioStoryPlanner` and
      `CompanyGatewayStoryPlanner` while keeping public aliases for backward
      compatibility if needed.
- [ ] **Step 2:** Ensure both classes implement `StoryPlanner` and the existing
      rewrite provider protocol only.
- [ ] **Step 3:** Update `factory.py` wiring: the LLM class is used as the
      pipeline's `story_planner`; rendering and asset planning come from stub
      stages.
- [ ] **Step 4:** Update unit tests (`test_gemini_provider.py`,
      `test_company_gateway_provider.py`) to assert outline output only, not
      full documents.
- [ ] **Step 5:** Commit `refactor(api): isolate LLM providers as StoryPlanner`.

---

## Task 4: Add asset planning

**Files:** `stages/asset_planner.py`, `tests/test_asset_planning.py`.

- [ ] **Step 1:** Implement `StubAssetPlanner` that inspects each outline item's
      `layout`:
      - `split-image` → one `AssetRequest` for slot `main_visual_panel` with a
        prompt derived from slide title + content.
      - `profile-cards` / `alternating-cards` → optional card-image slots
        (prompt derived from card heading + body).
      - other layouts → no asset requests.
- [ ] **Step 2:** Add `AssetPlanningRequest` to `stages/models.py`.
- [ ] **Step 3:** Add tests covering:
      - `split-image` yields exactly one request.
      - `feature-list` yields zero requests.
      - prompts include slide title and are bounded.
- [ ] **Step 4:** Commit `feat(api): add deterministic AssetPlanner stage`.

---

## Task 5: Add batched asset generation

**Files:** `stages/asset_generator.py`, modify `worker.py`,
`tests/test_asset_generation.py`.

- [ ] **Step 1:** Implement `NullAssetGenerator` returning an empty asset map.
- [ ] **Step 2:** Implement `ImageAssetGenerator` initialized with:
      - `session_factory`
      - `storage: ObjectStorage`
      - `image_provider: ImageGenerationProvider | None`
      - `concurrency: int` (default 2)
- [ ] **Step 3:** `ImageAssetGenerator.generate(plan: AssetPlan)`:
      - Skip if no image provider or no requests.
      - For each request, call `provider.generate_image(...)` inside a thread-pool
        with bounded concurrency.
      - Validate bytes via `detect_image_type()` (reuse `assets.py`).
      - Store asset via `store_asset()` (reuse `assets.py` helper; may need to
        move it to a shared location to avoid circular imports).
      - Return list of `GeneratedAsset`; on failure return `asset_id=None` and a
        warning message.
- [ ] **Step 4:** Update `worker.py` `process_once`:
      - Build `GenerationPipeline` from `build_provider()`.
      - Call `pipeline.generate_outline(request)` (or use `claimed.outline`).
      - Call `pipeline.plan_assets(request, outline)`.
      - If requests exist, open a DB session and call
        `ImageAssetGenerator(...).generate(plan)` with the owner id.
      - Call `pipeline.render(request, outline, asset_map)`.
      - Persist the presentation as today.
      - Update job progress at each stage (20/40/60/80/100).
- [ ] **Step 5:** Add tests using a fake image provider and in-memory storage;
      verify assets are stored and referenced in the final document.
- [ ] **Step 6:** Commit `feat(api): generate and store image assets during deck creation`.

---

## Task 6: Inject assets into Presenton layouts

**Files:** `stages/content_generator.py`, `presenton_template.py`,
`tests/test_presenton_image_slots.py`.

- [ ] **Step 1:** Extend `PresentonTemplateAdapter.compile_slide(..., assets:
      Mapping[str, str] | None = None)` where key is slot name and value is
      asset id.
- [ ] **Step 2:** When flattening an `element_type == "image"`, if the element
      has a `name` matching an asset slot and an asset id is provided, emit a
      canonical `type: "image"` element with:
      - `assetId`, `position`, `size`, `fit` (from template or default `cover`).
      - `focusX`, `focusY` normalized from template `focus_x/focus_y`.
      - `alt` derived from slot purpose.
      - Optional `cornerRadius` preserved if schema is extended.
- [ ] **Step 3:** If no asset is provided, keep the existing placeholder shape.
- [ ] **Step 4:** Add tests for:
      - adapter emits `type: image` when asset map has the slot.
      - adapter emits `type: shape` placeholder when asset map is empty.
      - generated image element validates against `slideElementSchema`.
- [ ] **Step 5:** If template border radius is meaningful, add optional
      `cornerRadius` to `ImageElement` in `packages/slide-schema/src/schema.ts`
      and update `pptx-exporter` to apply rounded masks or ignore it with a
      warning. Otherwise document that border radius is dropped for images.
- [ ] **Step 6:** Commit `feat(api): convert Presenton image slots into canonical image elements`.

---

## Task 7: Integration & regression

- [ ] **Step 1:** Run full backend test suite: `npm run api:test`.
- [ ] **Step 2:** Run type checks: `npm run check`.
- [ ] **Step 3:** Run a manual end-to-end generation with `stub` provider and
      verify produced schema still has only text/shape elements.
- [ ] **Step 4:** Configure image provider and run one generation with a
      `split-image` layout; verify final document contains a real `image` element
      and the asset is owner-scoped in `.data/storage`.
- [ ] **Step 5:** Commit `test(api): add generation pipeline stage integration coverage`.

---

## Task 8: Update decision records

- [ ] **Step 1:** Update `docs/decisions/m1-generation-pipeline-stages.md`
      status to "implemented" and add a "Current code locations" section pointing
      to `apps/api/app/generation/stages/`.
- [ ] **Step 2:** Add a short note in README under "AI-Powered Generation" about
      automatic image placement when an image provider is configured.
- [ ] **Step 3:** Commit `docs: update pipeline stages ADR and README`.

---

## Rollback / safety

- Each task is independently committable and reviewable.
- If asset generation proves unreliable, `ImageAssetGenerator` can be replaced
  with `NullAssetGenerator` in `factory.py` without touching the rest of the
  pipeline.
- The old monolithic `StubPresentationProvider` facade stays in place until all
  tests and worker code are migrated, so no task leaves the repo in a broken
  state.
