# Plan: Accurate slide thumbnail previews in editor

## Goal
Replace the editor's placeholder wireframe thumbnails with lightweight, accurate previews that render the actual slide content (text, shapes, images) using the same slide schema data as the main canvas.

## Why
The current `thumbnail__preview-*` spans only show a generic band + heading + lines, so every slide looks identical in the filmstrip. Real content previews help users scan, reorder, and orient themselves without opening each slide.

## Approach
Build a new `SlideThumbnail` component that projects slide elements onto a 16:9 HTML layer scaled to the thumbnail size. This is the lightest option: no new runtime dependency, no per-thumbnail Konva stage, and enough fidelity for the filmstrip.

## Files changed
- `apps/web/src/app/components/slide-thumbnail.tsx` (new)
  - Props: `{ slide: Slide; resolveAssetUrl?: (assetId: string) => string }`
  - Renders a `div` with `aspect-ratio: 16 / 9` and `position: relative`
  - Each child element is absolutely positioned using percentages derived from `EDITOR_STAGE_WIDTH / HEIGHT` (1280×720)
  - Supported element types:
    - `text` / `text-list`: render truncated text with inherited theme color
    - `shape` (rectangle, ellipse): render colored box / oval
    - `image`: render `<img>` if `resolveAssetUrl` is available and loads; otherwise a placeholder rect
    - `group`, `flex`, `grid`, `container`: flatten first-level children (best-effort, no deep layout)
    - `line`, `table`, `chart`, `svg`: skipped silently (do not break thumbnail)
  - Text is clamped to element bounds; font size scaled by the same ratio
- `apps/web/src/app/components/__tests__/slide-thumbnail.test.tsx` (new)
  - Tests render text, shape, image fallback, and skip unknown types
- `apps/web/src/app/editor-spike.tsx` (modified)
  - Import `SlideThumbnail`
  - Replace the placeholder spans inside `thumbnail__preview` with `<SlideThumbnail slide={item} resolveAssetUrl={resolveAssetUrl} />`
  - Keep the outer `thumbnail__preview` wrapper for aspect-ratio and background color
- `apps/web/src/app/styles.css` (modified)
  - Replace `.thumbnail__preview-*` placeholder styles with `.slide-thumbnail` styles
  - Keep `.thumbnail`, `.thumbnail-row`, `.thumbnail-actions`, `.thumbnail__number` unchanged
  - Ensure text inside thumbnail is not selectable and does not capture pointer events

## Out of scope
- Deep layout of flex/grid/container children (first-level flatten only)
- Rendering tables, charts, SVGs, arrows, and lines
- Full fidelity matching the Konva canvas (acceptable for a thumbnail)

## Verification
- `npm run check` passes
- New Vitest tests pass
- Manual visual check: filmstrip shows distinct content per slide for the canonical fixture and generated presentations
