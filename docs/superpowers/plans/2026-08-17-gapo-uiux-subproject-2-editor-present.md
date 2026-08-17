# UIUX Sub-project 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Bring gapo-slidegen's slide editor shell, present mode, command palette, and toast notifications to "intentional editorial product" quality, continuing the design language from sub-project 1.

**Architecture:** Chrome-only refactor in `apps/web`. The Konva canvas (`editor-canvas.tsx` and `packages/slide-editor/src/canvas.tsx`) is explicitly untouched. New reusable components (`command-palette`, `toast-provider`, `toast-item`, `use-toast`) are added and consumed by `editor-spike.tsx`. All styling lives in `apps/web/src/app/styles.css`.

**Tech Stack:** Next.js 16.3.0 (App Router, React 19.2.8), TypeScript 7.0.2, vitest 4.1.10, Playwright. No new runtime dependencies.

---

## Global Constraints

- **Editor canvas out of scope.** Do not modify `apps/web/src/app/editor/page.tsx`, `apps/web/src/app/editor-canvas.tsx`, `apps/web/src/app/editor-spike.tsx` beyond wiring new components, or `packages/slide-editor/src/canvas.tsx`.
- **API/backend out of scope.** Do not modify any file under `apps/api/` or `apps/web/src/app/api/`.
- **No new i18n keys.** Use existing English/Vietnamese strings only.
- **No theme list changes.** Keep all 4 themes.
- **No new runtime dependencies.** Build palette and toasts in-house with React + CSS.
- **Tailwind is NOT installed.** All styling continues to live in `apps/web/src/app/styles.css`.
- **Testing.** Component tests use vitest. E2E uses Playwright.
- **Commit messages.** Use Conventional Commits prefix. Body lines ≤ 72 chars. End with `Co-Authored-By: Claude <noreply@anthropic.com>`.
- **Branch.** Stay on `main`. Each task ends with a commit.
- **Visual regression scope.** Desktop 1280px only.
- **No auto-commit after user manually pushes.** Wait for explicit user approval before `git commit`.

---

## File structure

**Modify:**
- `apps/web/src/app/styles.css` — editor shell, present mode, command palette, toast styles
- `apps/web/src/app/editor-spike.tsx` — wire palette/toast, update layout hooks

**Create (shared primitives):**
- `apps/web/src/app/components/command-palette.tsx`
- `apps/web/src/app/components/command-palette-trigger.tsx`
- `apps/web/src/app/components/toast-provider.tsx`
- `apps/web/src/app/components/toast-item.tsx`
- `apps/web/src/app/components/use-toast.ts`

**Tests:**
- `apps/web/src/app/components/__tests__/command-palette.test.tsx`
- `apps/web/src/app/components/__tests__/toast.test.tsx`
- `apps/web/tests/e2e/editor.spec.ts`

---

## Task 1: Toast system

**Files:**
- Create: `apps/web/src/app/components/use-toast.ts`
- Create: `apps/web/src/app/components/toast-provider.tsx`
- Create: `apps/web/src/app/components/toast-item.tsx`
- Modify: `apps/web/src/app/styles.css`

Build an in-house toast stack. No new dependencies.

- [x] **Step 1: Define toast types and state hook**

Create `use-toast.ts`:
- Types: `ToastType = "success" | "error" | "info"`.
- `Toast` shape: `{ id: string; type: ToastType; message: string; duration?: number }`.
- `ToastContext` with `{ toasts: Toast[]; toast: (type, message, duration?) => string; dismiss: (id) => void; }`.
- `useToast()` hook consumes context.
- `ToastProvider` stores state, auto-dismisses via `setTimeout`, pauses on hover.

- [x] **Step 2: Render toast item**

Create `toast-item.tsx`:
- Icon per type (`Check`, `XCircle`, `Info` from `@phosphor-icons/react`).
- Message text.
- Progress bar at bottom; width animates from 100% to 0% over `duration`.
- `aria-live="polite"` on container, `role="status"` on item.
- Dismiss button with `aria-label="Dismiss notification"`.

- [x] **Step 3: Toast provider layout**

Create `toast-provider.tsx`:
- Fixed position top-right desktop, full-width bottom on narrow viewports.
- `role="region" aria-label="Notifications"`.
- Render list of `ToastItem`.
- Use React portal into `document.body` (guard for SSR).

- [x] **Step 4: Add CSS**

Add to `styles.css`:
- `.toast-region`, `.toast-item`, `.toast-icon`, `.toast-message`, `.toast-progress`, `.toast-close`.
- Entry animation: translate + fade, 220ms ease-out.
- Exit animation: translate + fade out.
- Reduced motion: disable entry/exit/progress animations.

- [x] **Step 5: Component tests**

Create `toast.test.tsx`:
- Render provider, call `toast.error("x")`, assert visible.
- Assert auto-dismiss after duration.
- Assert pause on hover extends visible time.
- Assert dismiss button removes toast.

- [x] **Step 6: Commit**

`feat(ui): add toast notification system`

---

## Task 2: Command palette

**Files:**
- Create: `apps/web/src/app/components/command-palette.tsx`
- Create: `apps/web/src/app/components/command-palette-trigger.tsx`
- Modify: `apps/web/src/app/styles.css`

Build a `Cmd/Ctrl + K` palette. No new dependencies.

- [x] **Step 1: Define command shape**

Create `command-palette.tsx` with exported types:
- `CommandAction = { id: string; label: string; shortcut?: string; section: string; icon?: ReactNode; action: () => void; }`.
- `CommandPaletteProps = { isOpen: boolean; onClose: () => void; commands: CommandAction[]; }`.

- [x] **Step 2: Implement UI**

- Backdrop click closes.
- Search input at top.
- Grouped list by section.
- Highlighted item navigable with arrow keys; Enter runs; Escape closes.
- Empty state when filter returns nothing.
- `role="dialog" aria-modal="true"`.

- [x] **Step 3: Keyboard trigger**

Create `command-palette-trigger.tsx`:
- Global `keydown` listener for `Cmd/Ctrl + K` and `Escape`.
- Renders `CommandPalette` with `isOpen` state.
- Accepts `commands` prop.
- Guards against inputs/contenteditable.

- [x] **Step 4: Add CSS**

Add to `styles.css`:
- `.command-palette-backdrop`, `.command-palette`, `.command-palette__input`, `.command-palette__group`, `.command-palette__item`, `.command-palette__empty`.
- Centered modal, max-width 560px, paper-card, shadow-lg.
- Highlighted item: accent-soft background.
- Focus ring on input and items.

- [x] **Step 5: Component tests**

Create `command-palette.test.tsx`:
- Open/close via props.
- Filter by typing.
- Arrow keys + Enter selects.
- Escape closes.
- Click outside closes.

- [x] **Step 6: Commit**

`feat(ui): add cmd+k command palette`

---

## Task 3: Editor shell editorial polish

**Files:**
- Modify: `apps/web/src/app/styles.css`
- Modify: `apps/web/src/app/editor-spike.tsx`

Redesign editor chrome to match sub-project 1 tokens and typography.

- [x] **Step 1: Topbar**

Update CSS and JSX:
- Height 60px.
- Brand wordmark in Fraunces.
- Document title input: same styling as dashboard inputs.
- Save state as subtle dot + label.
- Undo/redo icon buttons match dashboard icon-button style.
- Present / Export buttons use `.button` and `.button--primary`.

- [x] **Step 2: Filmstrip**

Update CSS:
- Thumbnail preview uses CSS miniature (title + body lines) using theme colors from `slide.theme` or `document.theme`.
- Active slide: accent border + `accent-soft` background.
- Hover: `u-lift` behavior.
- Number badge in `--font-mono`.
- Add slide button styled like dashboard secondary button.

JSX change: render mini preview markup instead of text-only preview. Keep it lightweight; do not import the Konva canvas.

- [x] **Step 3: Workspace**

Update CSS:
- Insert bar buttons use `.button--quiet` style (border, icon + label).
- Canvas frame uses `--shadow-lg` and `--paper-card` background.
- Zoom readout in bottom-left uses `--font-mono`.

- [x] **Step 4: Properties panel**

Update CSS:
- Tab switcher matches composer tabs (underline style).
- Form inputs match dashboard composer (border, focus ring).
- AI panel: accent icon container, serif heading, chip-style presets.
- Empty selection state uses `empty-state` primitive.
- Delete button styled as quiet danger (border + text color, no hard-coded red background).

- [x] **Step 5: Commit**

`feat(ui): redesign editor shell with editorial tokens`

---

## Task 4: Present mode polish

**Files:**
- Modify: `apps/web/src/app/styles.css`
- Modify: `apps/web/src/app/editor-spike.tsx`

Redesign the full-screen present overlay.

- [x] **Step 1: Visual shell**

Update CSS:
- Backdrop: dark `#080b12`.
- Stage: centered 16:9, paper-card shadow.
- Control bar: bottom center, floating pill shape with translucent dark background.
- Buttons: circular, 38px, hover background `rgba(255,255,255,0.12)`.
- Counter in `--font-mono`.

- [x] **Step 2: Auto-hide controls**

In `editor-spike.tsx`:
- Track `controlsVisible` state.
- Show on mouse move / key down; hide after 2s inactivity via `setTimeout`.
- Keep controls visible if hovering the bar.
- Reduced motion: skip fade transitions.

- [x] **Step 3: Slide transition**

In `editor-spike.tsx`:
- Wrap `SlideCanvas` in a container with cross-fade key.
- Use CSS opacity transition 220ms when `activeSlideIndex` changes.
- Reduced motion: no transition.

- [x] **Step 4: Click navigation**

Add click handlers on stage left/right thirds for previous/next.
- Guard against clicks on controls and text edits.
- `cursor: w-resize` / `e-resize` on hover edges (optional visual hint via invisible overlay).

- [x] **Step 5: Commit**

`feat(ui): redesign present mode with auto-hide controls`

---

## Task 5: Wire toast and palette into editor

**Files:**
- Modify: `apps/web/src/app/editor-spike.tsx`
- Modify: `apps/web/src/app/styles.css` (minor cleanup if needed)

- [x] **Step 1: Wrap editor with providers**

In `editor-spike.tsx`:
- Add `<ToastProvider>` and `<CommandPaletteTrigger>` around the existing JSX.
- Build `commands` array from existing actions: add slide, insert text/shape, present, export, undo/redo, duplicate, delete.
- Use `useToast()` to replace `setActionError` fixed notice.

- [x] **Step 2: Error handling**

- Replace `actionError ? <p className="editor-notice" ...>` with `toast.error(message)` calls.
- Keep `loadError` as a full-screen error (still appropriate for load failures).
- Optional: toast info on export success.

- [x] **Step 3: Add palette trigger hint**

Add a subtle keyboard hint in the topbar or bottom of the properties panel: "Cmd/Ctrl + K".

- [x] **Step 4: Commit**

`feat(ui): integrate toast and command palette into editor`

---

## Task 6: Editor E2E smoke tests

**Files:**
- Create: `apps/web/tests/e2e/editor.spec.ts`

- [x] **Step 1: Navigation and render**

- Register/login via API helper (reuse pattern from `shell.spec.ts` if possible).
- Create a presentation via API or dashboard composer.
- Navigate to `/editor?presentation={id}`.
- Assert topbar, filmstrip, workspace, properties panel visible.

- [x] **Step 2: Present mode**

- Click Present.
- Assert present mode visible, slide counter shows "1 / N".
- Press ArrowRight, assert counter changes.
- Press Escape, assert present mode closed.

- [x] **Step 3: Command palette**

- Press `Control+k` (or `Meta+k` depending on env).
- Assert palette input visible.
- Type "present", press Enter, assert present mode opens.

- [x] **Step 4: Toast**

- Trigger an action that produces an error (e.g., offline export if feasible) or success toast.
- Assert toast region contains message.

- [x] **Step 5: Commit**

`test(e2e): add editor present-mode and palette smoke tests`

---

## Task 7: Visual regression baselines

**Files:**
- Modify: `apps/web/tests/visual/capture.mjs`
- Create: baseline PNGs under `apps/web/tests/visual/baselines/`

- [x] **Step 1: Add capture targets**

In `capture.mjs`, add routes/paths:
- `/editor?presentation=...` with a stub-generated presentation (use a fixture or create via API).
- Present mode open.
- Command palette open.
- Toast visible (mock via query param or localStorage if needed; otherwise capture after triggering a toast).

- [x] **Step 2: Capture baselines**

Run `npm run visual:capture` to produce baseline PNGs.

- [x] **Step 3: Commit**

`test(visual): add editor and present-mode baselines`

---

## Task 8: Final verification and whole-branch review

- [x] **Step 1: Run all checks**

```bash
npm run check:node
npm run e2e
npm run visual:capture
```

- [x] **Step 2: Review for regressions**

- Ensure no changes to canvas files.
- Ensure no new i18n keys.
- Ensure no new runtime dependencies.
- Spot-check dark mode tokens in editor shell.

- [x] **Step 3: Fix any defects**

Apply fixes as separate commits.

- [x] **Step 4: Final commit if needed**

`chore(ui): final polish for editor sub-project`

**Note:** Per user instruction, do not auto-commit. Wait for explicit user approval before running `git commit`.

---

## Validation checklist

- [x] `npm run check:node` passes.
- [x] Playwright E2E for editor passes.
- [x] Visual baselines captured.
- [x] Reduced-motion transitions disabled.
- [x] Keyboard navigation in palette and present mode works.
- [x] No auto-commit after user push (wait for explicit approval).
