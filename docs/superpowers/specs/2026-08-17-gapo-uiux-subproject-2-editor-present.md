# Gapo SlideGen — UIUX Sub-project 2: Editor + Present mode polish

**Status:** draft for approval 2026-08-17  
**Scope:** Slide editor shell, present mode, command palette, toast notifications  
**Out of scope:** Theme list changes, backend/API changes, new i18n keys, mobile editor, chart/math/mermaid blocks  
**Sub-project 3 (deferred):** Advanced canvas interactions, animation blocks, real-time collaboration hints

---

## 1. Goal

Bring the slide editor and present mode from "functional spike" to "intentional editorial product" by applying the same design language established in sub-project 1. Keep the existing feature surface and API contract intact; only the chrome, interactions, and feedback mechanisms are polished.

Success criteria:
- Editor shell (topbar, filmstrip, properties panel) uses the editorial token system cohesively.
- Present mode feels intentional: clear slide chrome, smooth keyboard navigation, visible progress.
- Command palette gives keyboard-first access to common editor actions.
- Toast notifications replace the fixed bottom-right error notice with non-blocking, accessible feedback.
- WCAG AA color contrast, full keyboard navigation, and reduced-motion support are maintained.

---

## 2. Scope

### 2.1 Editor shell polish

Apply the editorial design system to the editor surface without changing the canvas rendering logic.

- **Topbar**
  - Back button, brand wordmark (Fraunces), document title input, save state, undo/redo, Present, Export.
  - Height 52px → 60px to match dashboard topbar.
  - Sticky, `paper-card` background with subtle blur.
  - Use `--font-sans` for controls, `--font-serif` for wordmark.

- **Filmstrip**
  - Real mini-slide preview (reuse `theme-preview` pattern or CSS miniature) instead of text-only thumbnail.
  - Active slide: accent border + soft background.
  - Hover: lift + shadow.
  - Add slide button at bottom, disabled at max slides.

- **Workspace**
  - Insert bar: cleaner icon + label buttons, hover states.
  - Canvas frame: paper-card shadow, subtle workspace background (`paper-warm`).
  - Zoom/readout label in bottom-left.

- **Properties panel**
  - Tab switcher matches composer tabs (underline style).
  - Form inputs use the same 46px / 36px heights and focus rings as the dashboard.
  - AI panel: clearer hierarchy, accent icon, presets as subtle chips.
  - Empty state when no element selected uses `empty-state` primitive.
  - Delete action styled as a quiet danger button instead of hard-coded red.

### 2.2 Present mode polish

Replace the current bare overlay with an intentional presentation shell.

- Dark backdrop (`#080b12`) kept for contrast, but controls use the same editorial shapes.
- Slide stage centered, 16:9, with subtle shadow.
- Bottom control bar:
  - Previous / next buttons with clear disabled states.
  - Slide counter in `--font-mono`.
  - Exit button.
  - Auto-hide after 2s of mouse inactivity; reappear on mouse move or key press.
- Keyboard navigation preserved: `←` / `→` / `Space` / `Escape`.
- Click on left/right third of screen navigates slides (optional, guarded against text selection).

### 2.3 Command palette

A `Cmd/Ctrl + K` palette for editor actions. Built with React + CSS only (no new runtime dependencies).

- Trigger: global keyboard shortcut in editor route.
- Sections: Navigation (next/prev slide, go to slide), Edit (undo/redo, duplicate, delete), Insert (text, shape, image), Actions (present, export).
- Recent / frequent actions surfaced at top.
- Mouse and keyboard operable; `Escape` closes; `Enter` runs highlighted item; arrow keys move selection.
- No new i18n keys; labels reuse existing English strings only.

### 2.4 Toast notifications

Replace the fixed `editor-notice` element with a stack of non-blocking toasts.

- Built with React portal + CSS (no new runtime dependencies).
- Types: success (export done), error (save failed, export failed, AI error), info (save state changes optionally).
- Auto-dismiss after 5 seconds; progress bar indicates remaining time.
- Pause hover; reduced motion disables the progress bar animation.
- Position: top-right on desktop, bottom on very narrow viewports.

---

## 3. Out of scope

- Editor canvas rendering changes (`editor-canvas.tsx`, `packages/slide-editor/src/canvas.tsx`).
- Theme list changes; existing 4 themes remain.
- API/backend changes.
- New i18n keys.
- Chart, math, mermaid, or animation blocks.
- Mobile/tablet editor layout (existing breakpoint message preserved).

---

## 4. Global constraints

Same as sub-project 1 unless noted:

- **No new runtime dependencies.** Build command palette and toasts in-house with React + CSS.
- **No Tailwind.** All styling lives in `apps/web/src/app/styles.css`.
- **Editor canvas files explicitly untouched.** Only `editor-spike.tsx`, `styles.css`, and new component files are modified.
- **No new i18n keys.** Reuse existing English/Vietnamese strings where present.
- **Custom Next.js.** Read `node_modules/next/dist/docs/01-app/01-getting-started/` before touching Next.js APIs.
- **Testing.** Component tests with vitest; E2E with Playwright; desktop visual regression only.
- **Conventional Commits** with `Co-Authored-By: Claude <noreply@anthropic.com>`.
- **No auto-commit after user manually pushes.** Per recorded user instruction, assistant waits for explicit commit approval.

---

## 5. Design language continuation

Reuse the editorial token system from sub-project 1:

- Fonts: Fraunces (display/wordmark), Inter (UI/body), JetBrains Mono (numbers).
- Colors: `--ink`, `--paper`, `--paper-card`, `--paper-warm`, `--accent` `#B8651E`.
- Spacing/radius/shadow/motion tokens unchanged.
- Editor shell uses light mode by default; dark mode gets basic parity through existing `[data-theme="dark"]` tokens.
- Existing editor alias tokens (`--text`, `--surface`, etc.) are gradually replaced with direct token usage in this sub-project, but the aliases remain in `:root` for safety.

---

## 6. Component anatomy

### 6.1 Files to modify

| File | Change |
|---|---|
| `apps/web/src/app/styles.css` | Editor shell, present mode, command palette, toast styles |
| `apps/web/src/app/editor-spike.tsx` | Wire new components, remove inline notice, add palette + toast providers |

### 6.2 New files

| File | Purpose |
|---|---|
| `apps/web/src/app/components/command-palette.tsx` | `Cmd+K` palette UI and filtering |
| `apps/web/src/app/components/command-palette-trigger.tsx` | Global keyboard listener + mount point |
| `apps/web/src/app/components/toast-provider.tsx` | Toast container + state management |
| `apps/web/src/app/components/toast-item.tsx` | Single toast render + progress bar |
| `apps/web/src/app/components/use-toast.ts` | `toast()` imperative API hook |
| `apps/web/src/app/components/__tests__/command-palette.test.tsx` | Keyboard/mouse interaction tests |
| `apps/web/src/app/components/__tests__/toast.test.tsx` | Add/dismiss/pause tests |

### 6.3 Reused primitives

- `empty-state` for properties panel empty state.
- `skeleton` if editor loading state is added later.

---

## 7. Behavior & states

### 7.1 Editor loading

- Presentation load uses existing skeleton-like state text. Optionally wrap in a centered `empty-state` with a spinner icon, but keep changes minimal.

### 7.2 Save state

- Save state remains in topbar but uses a more subtle dot + label pattern:
  - Saved: muted check.
  - Unsaved changes: muted dot.
  - Saving: pulsing dot.
  - Save failed: danger dot + toast.

### 7.3 Present mode

- Enter via topbar "Present" or palette action.
- Exit via `Escape`, close button, or palette action.
- Slide transitions: 220ms cross-fade, disabled if reduced motion.

### 7.4 Command palette

- Open: `Cmd/Ctrl + K`.
- Close: `Escape`, click backdrop, or select an action.
- Filter by typing; empty state message if no match.
- Group actions by category.

### 7.5 Toasts

- API: `toast.success(message)`, `toast.error(message)`, `toast.info(message)`.
- Called from editor-spike where `setActionError` currently sets the fixed notice.
- Keep the existing error state if a toast is not appropriate for a persistent load error.

---

## 8. Accessibility

- Focus rings: 2px accent + 2px offset on all new controls.
- Command palette: `role="dialog"`, `aria-modal="true"`, live region for result count.
- Toast region: `role="region"` `aria-live="polite"` on the container.
- Present mode: `role="dialog"` `aria-modal="true"`, visible focus on controls.
- Keyboard shortcuts documented in palette and tooltips where feasible.

---

## 9. Testing strategy

- **Component tests:** command palette filtering/keyboard, toast add/dismiss/pause.
- **E2E smoke:** open editor → present mode → navigate slides → exit → command palette opens → run an action.
- **Visual regression:** editor shell, present mode, command palette, toast stack.
- **Reduced motion:** spot-check transitions disabled.

---

## 10. Rollout & risks

| Risk | Mitigation |
|---|---|
| Command palette conflicts with existing shortcuts | Only register on `/editor` route; Escape closes, does not trap. |
| Toast z-index conflicts with present mode | Toast container z-index below present mode (100) but above editor shell (20). |
| Real mini-slide preview too heavy | Use CSS-only miniature using theme tokens, same as `theme-preview`. |
| Regressions in canvas interactions | Canvas files untouched; only chrome changes. |

---

## 11. Open questions deferred to sub-project 3

- Animation and transition blocks between slides.
- Chart, math, mermaid blocks.
- Drag-and-drop layer panel reordering.
- Real-time collaboration cursors.
