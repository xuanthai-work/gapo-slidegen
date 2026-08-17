# Gapo SlideGen — UIUX Sub-project 1: Editorial publication shell

**Status:** design approved 2026-08-17
**Scope:** Auth, landing, dashboard/composer, theme picker, generation progress, recent decks list
**Out of scope:** Slide editor, present mode, theme list changes, backend/API changes, new i18n keys
**Sub-project 2 (deferred):** Slide editor + present mode polish — separate spec after this ships

---

## 1. Goal

Bring gapo-slidegen's marketing/auth and dashboard/composer surfaces from "functional skeleton" to "intentional product" by adopting an editorial publication design language. Match Presenton's polish level on the entry-point surfaces while preserving the current feature surface and API contract.

Success criteria:
- Cohesive editorial design system across auth, landing, dashboard, composer, generation progress, and recent decks list
- Polished states (loading, empty, error) — no raw spinners or empty boxes
- WCAG AA color contrast, full keyboard navigation, clear focus rings
- Restrained motion (180–320ms) with reduced-motion respected
- Light mode primary; dark mode has basic parity

---

## 2. Design language

**Aesthetic:** Editorial publication. Serif display + clean sans body. Warm paper + ink + 1 accent. Confident micro-copy with personality.

### 2.1 Typography

| Role | Family | Notes |
|---|---|---|
| Display, h1, h2, brand wordmark | **Fraunces** (variable serif) | Optical sizing, SOFT axis |
| Body, labels, buttons, controls | **Inter** (variable sans) | Default UI sans |
| Numeric (tabular) | **JetBrains Mono** | Slide counts, progress %, file sizes |

Existing Montserrat is kept for the editor canvas only (it is wired to the Presenton Modern template).

### 2.2 Type scale (CSS custom properties)

- `--type-display` — `clamp(48px, 6.5vw, 88px)` / 0.96 line-height / Fraunces 600 / -0.04em
- `--type-h1` — `clamp(36px, 4.5vw, 56px)` / 1.04 / Fraunces 600 / -0.03em
- `--type-h2` — `clamp(26px, 3vw, 36px)` / 1.1 / Fraunces 600 / -0.02em
- `--type-h3` — `20px` / 1.3 / Inter 650 / -0.01em
- `--type-body` — `15px` / 1.55 / Inter 450
- `--type-small` — `13px` / 1.5 / Inter 450
- `--type-eyebrow` — `11px` / 1 / Inter 700 / 0.12em / uppercase
- `--type-mono` — `13px` / 1.4 / JetBrains Mono 500 / tabular

### 2.3 Color tokens (light primary)

- `--ink` — `#161618` (warm near-black)
- `--ink-soft` — `#3C3A36`
- `--paper` — `#FBF8F2` (warm cream — page background)
- `--paper-card` — `#FFFFFF`
- `--paper-warm` — `#F4EFE6`
- `--accent` — `#B8651E` (editorial ochre)
- `--accent-hover` — `#9D5617`
- `--accent-soft` — `#F7EBD9`
- `--border` — `#E5DECF`
- `--border-strong` — `#C9C0AA`
- `--muted` — `#7A7264`
- `--success` — `#3D7A4F`
- `--danger` — `#B23A2A`
- `--info` — `#3A6B8C`

### 2.4 Dark mode (basic parity)

- Background → `#1A1916`
- Surface → `#252320`
- Ink → `#F4EFE6`
- Accent → `#D8843F` (lighter for contrast)
- Border → `#36322B`

Other tokens map 1:1 from light; no per-theme dark palette in this sub-project.

### 2.5 Spacing, radius, shadow

- Spacing scale: 4px base — `4, 8, 12, 16, 24, 32, 48, 64, 96, 128`
- Radius: `6px` (controls), `10px` (cards), `16px` (large cards), `999px` (pills)
- Shadows (warm-tinted): `--shadow-sm`, `--shadow-md`, `--shadow-lg`

### 2.6 Motion

- `--ease-out` — `cubic-bezier(0.22, 1, 0.36, 1)`
- `--duration-fast` — 150ms
- `--duration-base` — 220ms
- `--duration-slow` — 320ms
- Reduced-motion: all transitions → 0ms, no pulse animations

---

## 3. Layout patterns

### 3.1 Auth page (`/login`)

Split-panel: `minmax(420px, 1fr) minmax(540px, 1.1fr)`.

Left panel:
- Brand mark (small) + eyebrow + display serif headline ("Bring your knowledge to the world.")
- Sans subtitle paragraph
- Benefits list with check icons (Inter 650 + accent check color)
- Background: `--ink` (#161618) — sharp contrast với right panel

Right panel:
- Background `--paper`
- Form card centered with serif h2 ("Welcome back" / "Create your account"), subtitle, stacked fields, primary submit button (accent ochre)
- Password reveal toggle polished

### 3.2 Dashboard topbar

- Sticky, paper-card background với subtle blur
- Brand wordmark in Fraunces (left)
- Account menu: email + sign-out icon (right)
- Height 60px, padding `0 clamp(18px, 4vw, 54px)`

### 3.3 Dashboard hero

- Eyebrow uppercase (`PRESENTATION WORKSPACE`)
- Display serif headline: "What are we presenting?"
- Sans subtitle paragraph
- Max-width 720px

### 3.4 Composer card

- Paper-card với `--shadow-md`, radius 16px
- Mode tabs: underline-style (editorial) thay vì filled pills
- Three modes: `Prompt` / `Full text` / `Upload`
- Form inputs: 46px height, padding tuned, focus rings accent ochre
- Theme picker redesigned: **template cards 2×2 grid** với live mini-slide preview
- Submit button: accent ochre, Fraunces 600 cho label

### 3.5 Theme picker (template cards)

- Grid 2 columns desktop, 1 column < 768px
- Each card: 16:9 aspect ratio preview (real mini slide render, not just colors) + theme name + selected border (accent ochre)
- Hover: lift (`translateY(-2px)`) + shadow-md
- Selected: 2px accent border + small check icon
- Mini slide renderer: reuse canvas component pattern; if too heavy, fallback to swatch + name with thumbnail-style frame
- Maintain 4 themes (no list changes): Modern Blue, Editorial Cobalt, Warm Studio, Midnight Signal

### 3.6 Generation progress banner

- Inline banner under composer card
- Editorial treatment: eyebrow + heading + body + progress dots
- States: queued → running → done / failed / canceled
- Progress bar: 4px tall, accent ochre fill, `--paper-warm` track
- Failed/canceled state: red/warm muted background with retry CTA

### 3.7 Recent decks list

- Keep 2-column grid
- Card polish: paper-card, lift on hover, accent ochre preview icon background
- Editorial type hierarchy: title in Inter 650, slide count in `--type-mono`
- Rename/delete actions: icon buttons, hover reveals color

---

## 4. Component anatomy

### 4.1 Files to modify

| File | Change |
|---|---|
| `apps/web/src/app/styles.css` | Replace `:root` token block; add Fraunces/Inter/JetBrains Mono @font-face; add dark mode `[data-theme="dark"]` block; spacing/radius/shadow/motion utilities; keep reduced-motion block |
| `apps/web/src/app/layout.tsx` | Add font preconnect + display swap; inject theme init script (avoid FOUC); set default lang from user locale |
| `apps/web/src/app/login/auth-screen.tsx` | Layout, typography, micro-copy polish (per §3.1) |
| `apps/web/src/app/dashboard.tsx` | Topbar, hero, composer card, theme picker (template cards), generation banner, decks list (per §3.2–3.7) |

### 4.2 Files NOT modified in this sub-project

- `apps/web/src/app/editor/page.tsx`
- `apps/web/src/app/editor-spike.tsx`
- `apps/web/src/app/editor-canvas.tsx`
- `apps/web/src/app/api/export/route.ts`
- Any `apps/api/**` file

### 4.3 New files

| File | Purpose |
|---|---|
| `apps/web/src/app/components/landing-hero.tsx` | Extracted hero block (for reuse if landing splits later) |
| `apps/web/src/app/components/template-card.tsx` | Theme picker template card with preview |
| `apps/web/src/app/components/theme-preview.tsx` | Mini slide renderer for theme preview |
| `apps/web/src/app/components/empty-state.tsx` | Reusable empty state: icon + eyebrow + heading + body + CTA |
| `apps/web/src/app/components/skeleton.tsx` | Reusable skeleton with warm shimmer |

### 4.4 Reuse note

Mini slide preview renderer must NOT depend on the editor canvas (which loads with `dynamic({ ssr: false })`). Investigate `packages/slide-editor` for a headless preview component; if none exists, fallback to a CSS-only miniature that uses theme tokens.

---

## 5. Behavior & states

### 5.1 Loading

- Dashboard boot: skeleton (paper-card placeholders) với warm shimmer (1200ms cycle, reduced-motion off → static)
- Auth check: existing `dashboard-loading` text → replace với skeleton cho topbar + hero + composer
- Generation submit: button label transitions to "Working…" with subtle inline progress

### 5.2 Empty

- Recent decks empty: empty-state component với icon (file-ppt outline), eyebrow `YOUR DECKS`, heading `No presentations yet`, body, CTA `Create your first deck`
- Theme picker empty: not applicable (always 4 themes)

### 5.3 Error

- Form errors: existing `dashboard-error` block giữ, polish với warm-red background + icon
- API errors: surface với structured empty/error component where applicable
- Generation failed: banner switches to error state with retry button

### 5.4 Generation progress states

- **Queued**: pulse dot + "Queued — preparing your source…"
- **Running**: progress bar fills + "Creating the story and editable slides… {N}%"
- **Succeeded**: redirect to `/editor?presentation=…` (existing)
- **Failed**: red-tinted banner + retry
- **Canceled**: muted banner + retry

### 5.5 Theme picker interactions

- Hover: lift + shadow-md (220ms ease-out)
- Selected: 2px accent border + check icon
- Keyboard: arrow keys move selection within grid; Enter confirms (single click already works)
- Focus ring: 2px accent with 2px offset

### 5.6 Reduced motion

- All transitions → 0ms
- Pulse animations → none
- Skeleton shimmer → static block

---

## 6. Theming

### 6.1 Light mode (primary)

Tokens per §2.3. Default theme on first visit.

### 6.2 Dark mode (basic parity)

Tokens per §2.4. Toggle in topbar account menu (small icon). Persisted in `localStorage["theme"]`.

### 6.3 Theme init (avoid FOUC)

Inline script in `<head>` (before paint):

```js
try {
  const stored = localStorage.getItem("theme");
  if (stored === "dark" || (!stored && matchMedia("(prefers-color-scheme: dark)").matches)) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
} catch {}
```

---

## 7. Accessibility

- WCAG AA color contrast on text (verify accent ochre on paper ≥ 4.5:1 for body, ≥ 3:1 for large)
- Full keyboard navigation: tab order, focus rings (2px accent + 2px offset), skip-to-content link on auth/dashboard
- ARIA: icon buttons có `aria-label`, tabs có `role="tablist"` + `aria-selected`, progress bar có `role="progressbar"` + `aria-valuenow`
- Reduced-motion media query respected
- Form labels: explicit `<label htmlFor>`, not placeholder-only
- Error messages: `role="alert"`

---

## 8. Testing strategy

- **Visual regression** — screenshots at desktop (1280px) only for auth, dashboard, composer, generation banner states (queued/running/failed), theme picker
- **Smoke E2E (Playwright)** — auth login → dashboard renders → composer submit → theme picker select → generation banner appears → recent decks list
- **Component tests** — new shared primitives (`empty-state`, `template-card`, `skeleton`, `theme-preview`)
- **Existing API tests** — unchanged
- **No mobile/tablet screenshots in this sub-project** (out of scope; existing media queries handle smaller viewports)

---

## 9. Rollout & risks

### 9.1 Strategy

Big-bang: single PR per sub-project. Smaller change sets would create inconsistent intermediate states ("half-editorial, half-old").

### 9.2 Risks

| Risk | Mitigation |
|---|---|
| Font loading FOUC | Theme init script runs before paint; font-display: swap |
| Regression in editor visual (canvas uses Montserrat) | Editor files explicitly out of scope; existing CSS variables scoped to `.editor-*` selectors kept |
| Mini preview too heavy | Fallback to CSS-only miniature using theme tokens |
| Reduced-motion not respected | Single `@media (prefers-reduced-motion)` block at end of styles.css; all new transitions reference motion tokens |
| Dark mode parity gaps | Document as "basic parity" not "full polish"; defer dark polish to sub-project 3+ |
| Type system drift across future PRs | Token naming convention (`--type-*`, `--paper-*`, `--ink-*`) documented in this spec |

### 9.3 Validation

Before merge: smoke E2E green; visual screenshots match design tokens; reduced-motion verified; keyboard nav spot-checked.

---

## 10. Sub-project 2 outcomes (completed)

The following items were deferred from sub-project 1 and completed in sub-project 2:

- ✅ Present mode polish
- ✅ Command palette (`cmdk`-style, scoped to the editor route)
- ✅ Confetti / sonner-style toasts in editor

## 11. Open questions deferred to sub-project 3

- Editor canvas polish (Konva-style, layer panel, drag-and-drop improvements)
- Chart/math/mermaid blocks (Presenton has; out of scope here)
- Animation and transition blocks between slides
- Real-time collaboration cursors

---

## 12. Decisions log

| Decision | Choice |
|---|---|
| Aesthetic | Editorial publication shell |
| Heading font | Fraunces (variable serif) |
| Body font | Inter (variable sans) |
| Numeric font | JetBrains Mono (tabular) |
| Accent color | Editorial ochre `#B8651E` |
| Theme picker | Template cards 2×2 with live preview |
| Dark mode | Basic parity only |
| Animation budget | Restrained, 180–320ms, reduced-motion respected |
| A11y bar | WCAG AA + keyboard + focus rings |
| Test scope | Desktop visual regression only |
| Rollout | Big-bang single PR |
| Out of scope | Editor, present mode, theme list, API, new i18n |