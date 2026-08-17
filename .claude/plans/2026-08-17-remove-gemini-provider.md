# Plan: Disable Gemini provider as fallback, keep schemas/prompts shared

## Goal
Stop using `GoogleAIStudioProvider` as the active provider while keeping the file around as a disabled legacy fallback. Move shared outline schemas and prompt builder to a provider-agnostic module so `company_gateway_provider.py` no longer depends on Gemini.

## Approach
1. Create `apps/api/app/generation/outline_schema.py` containing:
   - `StoryLayout` Literal
   - `GeneratedSlideBlock`, `ContentBudget`, `GeneratedOutlineItem`, `GeneratedOutlineResponse`
   - `GeneratedRewriteResponse`, `GeneratedSlideRewriteResponse`
   - `build_story_prompt()`
2. Rewrite `apps/api/app/generation/gemini_provider.py`:
   - Keep a minimal module docstring noting it is a legacy fallback
   - Remove active `GoogleAIStudioProvider` class and imports
   - Optionally re-export shared classes from `outline_schema` for backward compatibility
   - Or keep a commented-out `GoogleAIStudioProvider` stub
3. Update `apps/api/app/generation/company_gateway_provider.py`:
   - Import shared schemas/prompt from `outline_schema` instead of `gemini_provider`
4. Update `apps/api/app/generation/factory.py`:
   - Remove active construction of `GoogleAIStudioProvider`
   - Route default story/rewrite providers to `CompanyGatewayProvider`
   - Keep Gemini construction code commented if needed
5. Update tests:
   - `apps/api/tests/test_gemini_provider.py` -> rename or mark as legacy/disabled
   - Update `test_llm_pipeline.py` to use `CompanyGatewayProvider` instead of Gemini
6. Run `npm run check`
