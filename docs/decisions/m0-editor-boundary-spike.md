# M0 editor boundary spike

Status: passed for the product boundary, partial for the full editor port

## What was proven

- Canonical presentation JSON validates at runtime and type-checks in both the
  editor package and Next.js application.
- JSON survives serialize and reload without data loss.
- Structured element updates are immutable, revisioned, and rejected when the
  target does not exist.
- A client-only Konva surface can render inside the Next.js product shell while
  remaining isolated from authentication, storage, routing, and providers.
- Text and shape elements can be selected, dragged, resized, and rotated.
- Property-panel text changes flow through the same validated operation
  boundary used by canvas changes.
- Next.js 16.3.0 builds the workspace packages with Turbopack.

## What this spike is not

The current canvas is a product-owned harness, not a replacement for the
approved Presenton Level 4 editor port. It intentionally implements only the
minimum interactions required to prove the boundary and dependency group.

## Remaining editor-port acceptance work

- Port Presenton rendering and editing modules named in the provenance record.
- Rich text through the pinned Tiptap 2.11.5 baseline, then evaluate Tiptap 3.
- Multi-selection, clipboard, grouping, layer controls, tables, charts, images,
  alignment guides, and full undo/redo.
- Add browser interaction tests and a save/reload golden fixture.

## Verification

- TypeScript typecheck: passed.
- Vitest: 3 files, 8 tests passed.
- Next.js production build: passed.
- Production HTTP smoke test: status 200 and expected product content present.
