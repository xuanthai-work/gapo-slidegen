# Plan: Slide roles, layout budgets, and visual intent

## Goal
Improve generated slide quality by constraining the LLM's design space without changing the renderer or editor. We add semantic slide roles, per-layout content budgets, and richer visual-intent for asset planning.

## What we keep unchanged
- Frontend editor and canvas
- Canonical `SlideElement` output schema
- `PresentonTemplateAdapter` flatten mechanism
- One-click generation flow latency target (2-4 LLM calls)

## What we change
1. Add `SlideRole` to `StoryOutlineItem`.
2. Add `layout_id` + `content_budget` to `StoryOutlineItem` (and therefore to outline JSON).
3. Add a small mapping from `SlideRole` to candidate Presenton `layout_id`s.
4. Change `PresentonContentGenerator` to trust `item.layout_id` when present, otherwise fall back to current behavior.
5. Improve `build_story_prompt` to:
   - Ask the LLM to pick a `SlideRole` per slide.
   - Provide per-role block counts and per-slot character budgets.
   - Tell the LLM to write content that fits the layout budget (e.g. "title ≤ 55 chars, block body ≤ 85 chars").
6. Improve `StubAssetPlanner` into `VisualIntentAssetPlanner`:
   - Each `AssetRequest` carries a `visual_intent` object with `concept`, `mood`, `composition`, `avoid`.
   - The planner still decides which slots are image-capable based on the selected layout.
   - The generation prompt is derived from visual intent, not from raw slide text.

## Files changed
- `apps/api/app/generation/stages/models.py`
  - Add `SlideRole` Literal
  - Add `role: SlideRole | None` to `StoryOutlineItem`
  - Add `layout_id: str | None` and `content_budget: dict[str, int]` to `StoryOutlineItem`
  - Add `visual_intent: dict[str, object] | None` to `AssetRequest`
- `apps/api/app/generation/stages/content_generator.py`
  - Add `ROLE_LAYOUT_CANDIDATES`: `dict[SlideRole, tuple[str, ...]]` mapping semantic roles to Presenton layout ids.
- `apps/api/app/generation/stages/presenton_content_generator.py`
  - Use `item.layout_id` first, then `MODERN_STORY_LAYOUTS.get(item.layout or "")`, then rotate fallback.
- `apps/api/app/generation/stages/asset_planner.py`
  - Rename/extend planner to `VisualIntentAssetPlanner`
  - Map layout id → image slot names (expand beyond `split-image`)
  - Build visual intent from title + content + role
- `apps/api/app/generation/gemini_provider.py`
  - Update Pydantic schema: `GeneratedOutlineItem` gets `role`, `layout_id`, `content_budget`
  - Update `build_story_prompt` with role vocabulary and budget instructions
- `apps/api/app/generation/stages/protocols.py`
  - No breaking change if optional fields default to None
- Tests:
  - `apps/api/tests/test_asset_planning.py` — visual intent, multi-slot layouts
  - `apps/api/tests/test_presenton_role_layout.py` — role→layout mapping
  - Update `apps/api/tests/test_llm_pipeline.py` and `test_staged_pipeline.py` if they assert exact outline shape

## Out of scope
- New custom layouts (we only map roles to existing Presenton layouts)
- VLM visual critic
- Theme engine beyond existing `theme_id`
- Multi-agent / multi-model splitting

## Verification
- `npm run check` passes
- `apps/api` tests pass
- Manual: generate a deck and observe more varied layouts and shorter block text
