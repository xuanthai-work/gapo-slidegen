# UIUX Sub-project 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring gapo-slidegen's auth, dashboard, composer, theme picker, generation banner, and recent decks list to "intentional editorial product" quality using an editorial publication design language.

**Architecture:** Big-bang CSS/component refactor in `apps/web`. Replace raw token block in `styles.css` with editorial tokens; add Fraunces/Inter/JetBrains Mono fonts; introduce dark mode; extract reusable components (skeleton, empty-state, landing-hero, theme-preview, template-card); redesign auth page, dashboard composer, theme picker (template cards 2×2 with live preview), generation banner, decks list. Editor and API files explicitly untouched.

**Tech Stack:** Next.js 16.3.0 (App Router, React 19.2.8), TypeScript 7.0.2, vitest 4.1.10, Playwright (E2E). No new runtime dependencies — fonts loaded as woff2 from `/public/fonts/`.

## Global Constraints

These constraints apply to every task. Each task's requirements implicitly include this section.

- **Editor out of scope.** Do not modify `apps/web/src/app/editor/page.tsx`, `editor-spike.tsx`, `editor-canvas.tsx`, or any file under `apps/web/src/app/editor/`.
- **API/backend out of scope.** Do not modify any file under `apps/api/` or `apps/web/src/app/api/`.
- **No new i18n keys.** Use existing English/Vietnamese strings only; do not add new translation entries.
- **No theme list changes.** Keep all 4 themes: `modern-blue`, `editorial-cobalt`, `warm-studio`, `midnight-signal`. Only the picker UX changes.
- **Custom Next.js.** This project uses a non-canonical Next.js build. Before writing any code that touches Next.js APIs, read `node_modules/next/dist/docs/01-app/01-getting-started/` (resolved from repo root). Heed deprecation notices in those docs.
- **Tailwind is NOT installed.** All styling continues to live in `apps/web/src/app/styles.css`. Use plain CSS with custom properties.
- **Testing.** Component tests use vitest. E2E uses Playwright. Existing API tests are unchanged.
- **Commit messages.** Use Conventional Commits prefix (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`). Body lines ≤ 72 chars. End with `Co-Authored-By: Claude <noreply@anthropic.com>`.
- **Branch.** Stay on `main`. Each task ends with a commit.
- **Visual regression scope.** Desktop 1280px only. No mobile/tablet screenshots in this sub-project.

---

## File structure

**Modify (foundation first, then screens consume):**
- `apps/web/src/app/styles.css` — replace token block, add @font-face, dark mode selector, motion utilities
- `apps/web/src/app/layout.tsx` — font preconnect, theme init script, lang from locale

**Create (shared primitives, Task 2–4; consumed by later tasks):**
- `apps/web/src/app/components/skeleton.tsx`
- `apps/web/src/app/components/empty-state.tsx`
- `apps/web/src/app/components/landing-hero.tsx`
- `apps/web/src/app/components/theme-preview.tsx`
- `apps/web/src/app/components/template-card.tsx`

**Modify (screens consume primitives above):**
- `apps/web/src/app/login/auth-screen.tsx`
- `apps/web/src/app/dashboard.tsx`

**Tests (added alongside their components and at the end):**
- `apps/web/src/app/components/__tests__/skeleton.test.tsx`
- `apps/web/src/app/components/__tests__/empty-state.test.tsx`
- `apps/web/src/app/components/__tests__/template-card.test.tsx`
- `apps/web/tests/e2e/shell.spec.ts`

**New assets:**
- `apps/web/public/fonts/fraunces-var.woff2`
- `apps/web/public/fonts/inter-var.woff2`
- `apps/web/public/fonts/jetbrains-mono-var.woff2`

Font files are sourced from Google Fonts' CDN at build time (downloaded via curl in Task 1, NOT vendored from a third-party npm package to keep dependencies clean).

---

## Task 1: Foundation — design tokens, fonts, dark mode

**Files:**
- Modify: `apps/web/src/app/styles.css`
- Create: `apps/web/public/fonts/fraunces-var.woff2`
- Create: `apps/web/public/fonts/inter-var.woff2`
- Create: `apps/web/public/fonts/jetbrains-mono-var.woff2`

This task replaces the existing `:root` token block with the editorial token system defined in §2 of the spec, downloads the three variable fonts, and wires them via `@font-face` with `font-display: swap`. It also adds the dark mode `[data-theme="dark"]` block, motion utilities, and preserves the existing reduced-motion block at the bottom of the file.

- [ ] **Step 1: Download the three variable font files**

Run from the repo root:

```bash
mkdir -p apps/web/public/fonts
curl -L -o apps/web/public/fonts/fraunces-var.woff2 "https://fonts.gstatic.com/s/fraunces/v37/6NUh8FyLNQOQZAnv9bYEvDiIdE9Ea92uemAk.woff2"
curl -L -o apps/web/public/fonts/inter-var.woff2 "https://fonts.gstatic.com/s/inter/v20/UcCO3FwrK3iLTeHuS_nVMrMxCp50ojIw2boKoduKmMEVuLyfAZ9hjp2YUcQ.woff2"
curl -L -o apps/web/public/fonts/jetbrains-mono-var.woff2 "https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxTOlOV.woff2"
```

Verify each file is > 50KB:

```bash
ls -la apps/web/public/fonts/
```

Expected: three `.woff2` files, each ≥ 50 KB.

- [ ] **Step 2: Replace the token block in styles.css**

Open `apps/web/src/app/styles.css`. Replace the existing `@font-face` block (lines 1–15, the Montserrat declarations) AND the existing `:root` block (lines 17–31) with the editorial token system below. Keep everything from `* { box-sizing: border-box; }` (line 33) onward unchanged for now — later tasks will refactor component CSS.

Insert at the top of the file (replacing lines 1–31):

```css
@font-face {
  font-family: "Fraunces";
  src: url("/fonts/fraunces-var.woff2") format("woff2-variations"),
       url("/fonts/fraunces-var.woff2") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Inter";
  src: url("/fonts/inter-var.woff2") format("woff2-variations"),
       url("/fonts/inter-var.woff2") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "JetBrains Mono";
  src: url("/fonts/jetbrains-mono-var.woff2") format("woff2-variations"),
       url("/fonts/jetbrains-mono-var.woff2") format("woff2");
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}

:root {
  color-scheme: light;
  --ink: #161618;
  --ink-soft: #3C3A36;
  --paper: #FBF8F2;
  --paper-card: #FFFFFF;
  --paper-warm: #F4EFE6;
  --accent: #B8651E;
  --accent-hover: #9D5617;
  --accent-soft: #F7EBD9;
  --border: #E5DECF;
  --border-strong: #C9C0AA;
  --muted: #7A7264;
  --success: #3D7A4F;
  --danger: #B23A2A;
  --info: #3A6B8C;

  --type-display: clamp(48px, 6.5vw, 88px);
  --type-h1: clamp(36px, 4.5vw, 56px);
  --type-h2: clamp(26px, 3vw, 36px);
  --type-h3: 20px;
  --type-body: 15px;
  --type-small: 13px;
  --type-eyebrow: 11px;
  --type-mono: 13px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --space-16: 64px;
  --space-24: 96px;
  --space-32: 128px;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-pill: 999px;

  --shadow-sm: 0 1px 2px rgba(60, 40, 20, 0.06);
  --shadow-md: 0 8px 24px rgba(60, 40, 20, 0.08);
  --shadow-lg: 0 18px 50px rgba(60, 40, 20, 0.10);

  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
  --duration-fast: 150ms;
  --duration-base: 220ms;
  --duration-slow: 320ms;

  --font-serif: "Fraunces", Georgia, serif;
  --font-sans: "Inter", "Segoe UI", "Be Vietnam Pro", sans-serif;
  --font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;

  font-family: var(--font-sans);
}

[data-theme="dark"] {
  color-scheme: dark;
  --ink: #F4EFE6;
  --ink-soft: #D9D2C2;
  --paper: #1A1916;
  --paper-card: #252320;
  --paper-warm: #2E2A24;
  --accent: #D8843F;
  --accent-hover: #E89552;
  --accent-soft: #3A2D1E;
  --border: #36322B;
  --border-strong: #4A453A;
  --muted: #9A8F7C;
  --success: #6FAE82;
  --danger: #D87060;
  --info: #6FA1C7;

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.20);
  --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.30);
  --shadow-lg: 0 18px 50px rgba(0, 0, 0, 0.40);
}

* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); }
button, input, textarea { font: inherit; }
button { color: inherit; }
a { color: inherit; }
```

Keep everything from `/* editor-shell */` onward unchanged.

- [ ] **Step 3: Add motion utilities at the end (before reduced-motion block)**

Find the `@media (prefers-reduced-motion: reduce)` block at the very end of `styles.css` (line 289). Insert the following BEFORE that block:

```css
.u-shimmer {
  background: linear-gradient(90deg,
    var(--paper-warm) 0%,
    var(--paper-card) 50%,
    var(--paper-warm) 100%);
  background-size: 200% 100%;
  animation: shimmer 1200ms var(--ease-out) infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.u-lift {
  transition: transform var(--duration-base) var(--ease-out),
              box-shadow var(--duration-base) var(--ease-out);
}

.u-lift:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.u-focus-ring:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.u-skip-link {
  position: absolute;
  top: -40px;
  left: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--ink);
  color: var(--paper);
  border-radius: var(--radius-sm);
  font-size: var(--type-small);
  text-decoration: none;
  z-index: 1000;
  transition: top var(--duration-fast) var(--ease-out);
}

.u-skip-link:focus {
  top: var(--space-2);
}

```

The existing reduced-motion block already handles `animation: none` for `prefers-reduced-motion`, so the shimmer animation will be disabled automatically.

- [ ] **Step 4: Verify the dev server still starts**

Run:

```bash
npm run dev --workspace @gapo-slidegen/web
```

Open http://localhost:3000 in a browser. Expected: the page loads, fonts swap in (you'll see the default Next.js fallback briefly), and existing layout works (yes, editor canvas and dashboard still render with old colors — those tokens stay for now; later tasks refactor them).

- [ ] **Step 5: Commit**

```bash
git add apps/web/public/fonts apps/web/src/app/styles.css
git commit -m "feat(ui): add editorial design tokens and variable fonts

Replace :root token block with editorial system (Fraunces/Inter/JetBrains
Mono, paper/ink/ochre). Add dark mode via [data-theme=\"dark\"]. Add motion
utilities (shimmer, lift, focus ring, skip link). Editor CSS unchanged."
```

---

## Task 2: Theme init script and dark mode toggle

**Files:**
- Modify: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/components/theme-toggle.tsx`

The root layout needs a theme init script (per spec §6.3) to prevent FOUC. A small toggle component lets users switch themes from the dashboard topbar.

- [ ] **Step 1: Modify layout.tsx**

Open `apps/web/src/app/layout.tsx`. Replace its contents with:

```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./styles.css";

const themeInitScript = `
try {
  var stored = localStorage.getItem("theme");
  var prefers = window.matchMedia("(prefers-color-scheme: dark)").matches;
  if (stored === "dark" || (!stored && prefers)) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
} catch (e) {}
`;

export const metadata: Metadata = {
  title: "Gapo SlideGen",
  description: "Create and edit presentations with AI assistance.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const defaultLang =
    typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("vi")
      ? "vi"
      : "en";

  return (
    <html lang={defaultLang} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

Note: `suppressHydrationWarning` is needed because the script mutates `<html>` before React hydrates.

- [ ] **Step 2: Create the theme toggle component**

Create `apps/web/src/app/components/theme-toggle.tsx`:

```tsx
"use client";

import { Moon, Sun } from "@phosphor-icons/react";
import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function readTheme(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setTheme(readTheme());
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    if (next === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try {
      localStorage.setItem("theme", next);
    } catch {}
  }

  return (
    <button
      type="button"
      className="theme-toggle u-focus-ring"
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      aria-pressed={theme === "dark"}
      onClick={toggle}
    >
      {mounted ? (theme === "dark" ? <Sun size={17} /> : <Moon size={17} />) : <Moon size={17} />}
    </button>
  );
}
```

- [ ] **Step 3: Add toggle styles to styles.css**

Append the following to `apps/web/src/app/styles.css` (before the reduced-motion block):

```css
.theme-toggle {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--paper-card);
  color: var(--ink-soft);
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-out),
              border-color var(--duration-fast) var(--ease-out);
}

.theme-toggle:hover {
  color: var(--ink);
  border-color: var(--border-strong);
}
```

- [ ] **Step 4: Verify theme toggle works**

Run `npm run dev --workspace @gapo-slidegen/web` if not running. Open http://localhost:3000. Add `<ThemeToggle />` temporarily to `dashboard.tsx` inside the topbar `<div className="account-menu">` (you'll wire it properly in a later task — for now, just to verify). Click the toggle. Expected: page background switches between `#FBF8F2` (light) and `#1A1916` (dark). Refresh: theme persists.

Remove the temporary `<ThemeToggle />` from `dashboard.tsx` before committing.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/layout.tsx apps/web/src/app/components/theme-toggle.tsx apps/web/src/app/styles.css
git commit -m "feat(ui): add dark mode toggle and FOUC-free theme init

Inline theme-init script in <head> applies data-theme before paint.
Toggle component persists choice to localStorage. Includes toggle styles."
```

---

## Task 3: Skeleton component (with tests)

**Files:**
- Create: `apps/web/src/app/components/skeleton.tsx`
- Create: `apps/web/src/app/components/__tests__/skeleton.test.tsx`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/src/app/components/__tests__/setup.ts`

Vitest is not configured for `apps/web` yet. This task sets up vitest + React Testing Library and creates the first shared primitive.

- [ ] **Step 1: Install vitest dev dependencies for the web workspace**

Run:

```bash
npm install --workspace @gapo-slidegen/web --save-dev vitest@4.1.10 @testing-library/react@16 @testing-library/jest-dom@6 jsdom@26 @vitejs/plugin-react@5
```

- [ ] **Step 2: Create vitest config**

Create `apps/web/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/app/components/__tests__/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

- [ ] **Step 3: Create test setup file**

Create `apps/web/src/app/components/__tests__/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Add test script to web package.json**

Open `apps/web/package.json`. Add the following inside the `scripts` block (right after `"typecheck"`):

```json
"test": "vitest run"
```

- [ ] **Step 5: Write the failing test for Skeleton**

Create `apps/web/src/app/components/__tests__/skeleton.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Skeleton } from "../skeleton";

describe("Skeleton", () => {
  it("renders a div with shimmer utility class", () => {
    const { container } = render(<Skeleton width="200px" height="40px" />);
    const div = container.firstChild as HTMLElement;
    expect(div.tagName).toBe("DIV");
    expect(div.className).toContain("u-shimmer");
  });

  it("applies inline width and height as CSS variables", () => {
    const { container } = render(<Skeleton width="320px" height="16px" />);
    const div = container.firstChild as HTMLElement;
    expect(div.style.getPropertyValue("--skeleton-width")).toBe("320px");
    expect(div.style.getPropertyValue("--skeleton-height")).toBe("16px");
  });

  it("uses default radius token when no radius prop given", () => {
    const { container } = render(<Skeleton />);
    const div = container.firstChild as HTMLElement;
    expect(div.style.getPropertyValue("--skeleton-radius")).toBe("var(--radius-sm)");
  });
});
```

- [ ] **Step 6: Run the test to verify it fails**

```bash
npm test --workspace @gapo-slidegen/web
```

Expected: FAIL with "Cannot find module '../skeleton'" or similar module resolution error.

- [ ] **Step 7: Implement the Skeleton component**

Create `apps/web/src/app/components/skeleton.tsx`:

```tsx
import type { CSSProperties } from "react";

export interface SkeletonProps {
  width?: string;
  height?: string;
  radius?: string;
  className?: string;
}

export function Skeleton({
  width = "100%",
  height = "1em",
  radius = "var(--radius-sm)",
  className = "",
}: SkeletonProps) {
  const style: CSSProperties = {
    "--skeleton-width": width,
    "--skeleton-height": height,
    "--skeleton-radius": radius,
    width: "var(--skeleton-width)",
    height: "var(--skeleton-height)",
    borderRadius: "var(--skeleton-radius)",
    display: "block",
  };
  return <div className={`u-shimmer ${className}`.trim()} style={style} aria-hidden="true" />;
}
```

- [ ] **Step 8: Run the test to verify it passes**

```bash
npm test --workspace @gapo-slidegen/web
```

Expected: PASS (3 tests).

- [ ] **Step 9: Commit**

```bash
git add apps/web
git commit -m "feat(ui): add Skeleton component with vitest setup

First shared primitive. Sets up vitest + React Testing Library for
apps/web. Tests verify shimmer class, CSS-variable width/height, and
default radius token."
```

---

## Task 4: EmptyState component (with tests)

**Files:**
- Create: `apps/web/src/app/components/empty-state.tsx`
- Create: `apps/web/src/app/components/__tests__/empty-state.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/app/components/__tests__/empty-state.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "../empty-state";

describe("EmptyState", () => {
  it("renders eyebrow, heading, and body when provided", () => {
    render(
      <EmptyState
        eyebrow="Your decks"
        heading="No presentations yet"
        body="Generated presentations will appear here."
      />,
    );
    expect(screen.getByText("Your decks")).toBeInTheDocument();
    expect(screen.getByText("No presentations yet")).toBeInTheDocument();
    expect(screen.getByText("Generated presentations will appear here.")).toBeInTheDocument();
  });

  it("renders action label as a button when provided", () => {
    render(
      <EmptyState
        heading="Empty"
        actionLabel="Create your first deck"
        onAction={() => {}}
      />,
    );
    const button = screen.getByRole("button", { name: "Create your first deck" });
    expect(button).toBeInTheDocument();
  });

  it("does not render action button when no actionLabel", () => {
    render(<EmptyState heading="Empty" />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
npm test --workspace @gapo-slidegen/web
```

Expected: FAIL with module not found.

- [ ] **Step 3: Implement EmptyState**

Create `apps/web/src/app/components/empty-state.tsx`:

```tsx
"use client";

import type { ReactNode } from "react";

export interface EmptyStateProps {
  icon?: ReactNode;
  eyebrow?: string;
  heading: string;
  body?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon,
  eyebrow,
  heading,
  body,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon ? <div className="empty-state__icon">{icon}</div> : null}
      {eyebrow ? <p className="empty-state__eyebrow">{eyebrow}</p> : null}
      <h3 className="empty-state__heading">{heading}</h3>
      {body ? <p className="empty-state__body">{body}</p> : null}
      {actionLabel && onAction ? (
        <button type="button" className="empty-state__action u-focus-ring" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Add EmptyState styles to styles.css**

Append to `apps/web/src/app/styles.css` (before the reduced-motion block):

```css
.empty-state {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-12) var(--space-4);
  text-align: center;
}

.empty-state__icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-pill);
  color: var(--accent);
  background: var(--accent-soft);
  margin-bottom: var(--space-2);
}

.empty-state__eyebrow {
  margin: 0;
  color: var(--accent);
  font-size: var(--type-eyebrow);
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.empty-state__heading {
  margin: 0;
  font-family: var(--font-serif);
  font-size: var(--type-h3);
  font-weight: 600;
  color: var(--ink);
}

.empty-state__body {
  margin: 0;
  max-width: 420px;
  color: var(--ink-soft);
  font-size: var(--type-body);
  line-height: 1.55;
}

.empty-state__action {
  margin-top: var(--space-2);
  padding: 10px var(--space-4);
  border: 0;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: var(--paper);
  font-family: var(--font-sans);
  font-size: var(--type-small);
  font-weight: 650;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.empty-state__action:hover {
  background: var(--accent-hover);
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npm test --workspace @gapo-slidegen/web
```

Expected: PASS for all Skeleton + EmptyState tests (6 total).

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/components
git commit -m "feat(ui): add EmptyState component

Reusable empty state with icon + eyebrow + heading + body + CTA.
Styles use editorial tokens. Tests cover rendered props and action."
```

---

## Task 5: LandingHero component

**Files:**
- Create: `apps/web/src/app/components/landing-hero.tsx`

- [ ] **Step 1: Implement LandingHero**

Create `apps/web/src/app/components/landing-hero.tsx`:

```tsx
export interface LandingHeroProps {
  eyebrow?: string;
  heading: string;
  body?: string;
  align?: "left" | "center";
}

export function LandingHero({ eyebrow, heading, body, align = "left" }: LandingHeroProps) {
  return (
    <section className={`landing-hero landing-hero--${align}`}>
      {eyebrow ? <p className="landing-hero__eyebrow eyebrow">{eyebrow}</p> : null}
      <h1 className="landing-hero__heading">{heading}</h1>
      {body ? <p className="landing-hero__body">{body}</p> : null}
    </section>
  );
}
```

- [ ] **Step 2: Add LandingHero styles**

Append to `apps/web/src/app/styles.css`:

```css
.landing-hero {
  display: grid;
  gap: var(--space-3);
  max-width: 720px;
}

.landing-hero--center {
  justify-items: center;
  text-align: center;
}

.landing-hero__heading {
  margin: 0;
  font-family: var(--font-serif);
  font-size: var(--type-display);
  font-weight: 600;
  line-height: 0.96;
  letter-spacing: -0.04em;
  color: var(--ink);
}

.landing-hero__body {
  margin: 0;
  max-width: 560px;
  color: var(--ink-soft);
  font-size: var(--type-body);
  line-height: 1.55;
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/app/components/landing-hero.tsx apps/web/src/app/styles.css
git commit -m "feat(ui): add LandingHero component

Editorial hero block: eyebrow + display serif heading + sans body.
Reusable across auth intro and dashboard hero."
```

---

## Task 6: ThemePreview component

**Files:**
- Create: `apps/web/src/app/components/theme-preview.tsx`

This component renders a small slide thumbnail for the theme picker. It is a CSS-only miniature — it does NOT use the editor canvas (which loads with `ssr: false` per `editor-canvas.tsx`). It uses theme tokens + theme color overrides.

- [ ] **Step 1: Inspect existing theme definitions**

The dashboard already defines the theme palette as a TypeScript array (lines 26–31 of `dashboard.tsx`). Read it:

```bash
sed -n '24,32p' apps/web/src/app/dashboard.tsx
```

You should see 4 themes with id, name, colors (3-element tuple). Keep this structure; we'll reuse it in `TemplateCard`.

- [ ] **Step 2: Implement ThemePreview**

Create `apps/web/src/app/components/theme-preview.tsx`:

```tsx
export interface ThemePreviewColors {
  paper: string;
  ink: string;
  accent: string;
}

export interface ThemePreviewProps {
  colors: ThemePreviewColors;
  name: string;
}

export function ThemePreview({ colors, name }: ThemePreviewProps) {
  return (
    <div
      className="theme-preview"
      role="img"
      aria-label={`${name} theme preview`}
      style={{
        background: colors.paper,
        color: colors.ink,
      }}
    >
      <div className="theme-preview__band" style={{ background: colors.accent }} />
      <div className="theme-preview__heading" style={{ background: colors.ink, opacity: 0.85 }} />
      <div className="theme-preview__line theme-preview__line--long" style={{ background: colors.ink, opacity: 0.35 }} />
      <div className="theme-preview__line theme-preview__line--short" style={{ background: colors.ink, opacity: 0.35 }} />
      <div className="theme-preview__row">
        <span style={{ background: colors.accent, opacity: 0.6 }} />
        <span style={{ background: colors.ink, opacity: 0.20 }} />
        <span style={{ background: colors.ink, opacity: 0.20 }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add ThemePreview styles**

Append to `apps/web/src/app/styles.css`:

```css
.theme-preview {
  position: relative;
  aspect-ratio: 16 / 9;
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  overflow: hidden;
  font-family: var(--font-sans);
}

.theme-preview__band {
  position: absolute;
  top: 0;
  left: 0;
  height: 4px;
  width: 28%;
}

.theme-preview__heading {
  width: 65%;
  height: 14px;
  border-radius: 2px;
  margin-bottom: var(--space-2);
}

.theme-preview__line {
  height: 6px;
  border-radius: 2px;
  margin-bottom: var(--space-1);
}

.theme-preview__line--long { width: 85%; }
.theme-preview__line--short { width: 55%; margin-bottom: var(--space-2); }

.theme-preview__row {
  display: flex;
  gap: 6px;
  margin-top: var(--space-2);
}

.theme-preview__row span {
  flex: 1;
  height: 24px;
  border-radius: 3px;
}
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/app/components/theme-preview.tsx apps/web/src/app/styles.css
git commit -m "feat(ui): add ThemePreview miniature renderer

CSS-only 16:9 miniature showing theme colors as a slide mock. No
dependency on editor canvas; safe for SSR and theme picker."
```

---

## Task 7: TemplateCard component (with tests)

**Files:**
- Create: `apps/web/src/app/components/template-card.tsx`
- Create: `apps/web/src/app/components/__tests__/template-card.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/app/components/__tests__/template-card.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TemplateCard } from "../template-card";

const palette = {
  paper: "#FFFFFF",
  ink: "#161618",
  accent: "#B8651E",
};

describe("TemplateCard", () => {
  it("renders the theme name", () => {
    render(
      <TemplateCard
        id="modern-blue"
        name="Modern Blue"
        colors={palette}
        selected={false}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByText("Modern Blue")).toBeInTheDocument();
  });

  it("applies is-selected class when selected is true", () => {
    const { container } = render(
      <TemplateCard
        id="modern-blue"
        name="Modern Blue"
        colors={palette}
        selected={true}
        onSelect={() => {}}
      />,
    );
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("is-selected");
  });

  it("calls onSelect with the theme id when clicked", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <TemplateCard
        id="warm-studio"
        name="Warm Studio"
        colors={palette}
        selected={false}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(container.firstChild as HTMLElement);
    expect(onSelect).toHaveBeenCalledWith("warm-studio");
  });

  it("sets role=radio and aria-checked for radio-group semantics", () => {
    render(
      <TemplateCard
        id="modern-blue"
        name="Modern Blue"
        colors={palette}
        selected={true}
        onSelect={() => {}}
      />,
    );
    const card = screen.getByRole("radio", { name: /Modern Blue/i });
    expect(card.getAttribute("aria-checked")).toBe("true");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npm test --workspace @gapo-slidegen/web
```

Expected: FAIL with module not found.

- [ ] **Step 3: Implement TemplateCard**

Create `apps/web/src/app/components/template-card.tsx`:

```tsx
"use client";

import { Check } from "@phosphor-icons/react";
import type { KeyboardEvent } from "react";
import { ThemePreview, type ThemePreviewColors } from "./theme-preview";

export interface TemplateCardProps {
  id: string;
  name: string;
  colors: ThemePreviewColors;
  selected: boolean;
  onSelect: (id: string) => void;
}

export function TemplateCard({ id, name, colors, selected, onSelect }: TemplateCardProps) {
  function handleKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(id);
    }
  }

  return (
    <div
      className={`template-card u-lift u-focus-ring${selected ? " is-selected" : ""}`}
      role="radio"
      aria-checked={selected}
      tabIndex={0}
      onClick={() => onSelect(id)}
      onKeyDown={handleKey}
    >
      <ThemePreview colors={colors} name={name} />
      <div className="template-card__footer">
        <span className="template-card__name">{name}</span>
        {selected ? (
          <span className="template-card__check" aria-hidden="true">
            <Check size={14} weight="bold" />
          </span>
        ) : null}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Add TemplateCard styles**

Append to `apps/web/src/app/styles.css`:

```css
.template-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--paper-card);
  cursor: pointer;
}

.template-card.is-selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

.template-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-1);
}

.template-card__name {
  font-family: var(--font-sans);
  font-size: var(--type-small);
  font-weight: 650;
  color: var(--ink);
}

.template-card__check {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: var(--radius-pill);
  background: var(--accent);
  color: var(--paper);
}
```

- [ ] **Step 5: Run tests to verify pass**

```bash
npm test --workspace @gapo-slidegen/web
```

Expected: PASS (4 TemplateCard tests + 6 prior = 10 total).

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/components/template-card.tsx apps/web/src/app/components/__tests__/template-card.test.tsx apps/web/src/app/styles.css
git commit -m "feat(ui): add TemplateCard with live theme preview

Reusable theme picker card. Uses ThemePreview miniature. role=radio,
keyboard activatable, aria-checked wired. Hover lift + accent border
when selected."
```

---

## Task 8: Auth screen — split-panel editorial

**Files:**
- Modify: `apps/web/src/app/login/auth-screen.tsx`
- Modify: `apps/web/src/app/styles.css` (refactor `.auth-page` block)

The auth page already has the right structure (split-panel). This task refactors CSS to use editorial tokens and the new component patterns.

- [ ] **Step 1: Read current styles for `.auth-page`**

```bash
sed -n '151,180p' apps/web/src/app/styles.css
```

Note the existing selectors: `.auth-page`, `.auth-intro`, `.brand-mark`, `.auth-benefits`, `.auth-panel`, `.auth-card`, `.auth-form`, `.password-field`, `.auth-submit`, `.auth-switch`, `.form-error`.

- [ ] **Step 2: Refactor auth-screen.tsx**

Open `apps/web/src/app/login/auth-screen.tsx`. Replace the entire return JSX of the `AuthScreen` function with the following (keep all state and handlers above):

```tsx
  return (
    <main className="auth-page">
      <a className="u-skip-link" href="#auth-form">Skip to form</a>

      <section className="auth-intro" aria-label="Product introduction">
        <div className="brand-mark"><PresentationChart size={23} weight="fill" /></div>
        <p className="eyebrow">Gapo SlideGen</p>
        <h1 className="auth-intro__heading">Bring your knowledge to the world.</h1>
        <p className="auth-intro__copy">
          Start with a prompt, a finished manuscript, or an existing office document. Keep every
          slide editable through review and export.
        </p>
        <ul className="auth-benefits">
          <li><Check size={17} weight="bold" /> Native PowerPoint objects</li>
          <li><Check size={17} weight="bold" /> Private, account-owned sources</li>
          <li><Check size={17} weight="bold" /> English and Vietnamese content</li>
        </ul>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-card__icon"><Sparkle size={20} weight="fill" /></div>
          <p className="eyebrow">Internal workspace</p>
          <h2 className="auth-card__heading">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h2>
          <p className="auth-card__subtitle">
            {mode === "login"
              ? "Sign in with your work email to continue."
              : "Email verification is not required for this MVP."}
          </p>

          <form id="auth-form" className="auth-form" onSubmit={submit}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <label htmlFor="password">Password</label>
            <div className="password-field">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={mode === "register" ? 10 : 1}
                placeholder={mode === "register" ? "At least 10 characters" : "Your password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <button
                type="button"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? <EyeSlash size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {error ? <p className="form-error" role="alert">{error}</p> : null}
            <button className="auth-submit" type="submit" disabled={submitting}>
              {submitting ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
              {!submitting ? <ArrowRight size={17} weight="bold" /> : null}
            </button>
          </form>

          <button
            className="auth-switch"
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
          >
            {mode === "login" ? "Need an account? Create one" : "Already have an account? Sign in"}
          </button>
        </div>
      </section>
    </main>
  );
}
```

Note the changes:
- Added skip link `<a className="u-skip-link" href="#auth-form">`.
- Heading uses new class `auth-intro__heading` (serif).
- Card heading uses new class `auth-card__heading` (serif).
- Form has `id="auth-form"` for skip-link target.

- [ ] **Step 3: Refactor auth-page CSS block in styles.css**

Find the existing `.auth-page { ... }` block (around line 151). Replace the ENTIRE `.auth-page` and related auth selectors up to and including `.form-error, .dashboard-error { ... }` (line 180) with:

```css
.auth-page {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: minmax(420px, 1fr) minmax(540px, 1.1fr);
  background: var(--paper);
}

.auth-intro {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
  padding: clamp(48px, 7vw, 104px);
  color: var(--paper);
  background: var(--ink);
}

.auth-intro::before {
  content: "";
  position: absolute;
  width: 420px;
  height: 420px;
  right: -190px;
  top: -120px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  box-shadow: 0 0 0 70px rgba(255, 255, 255, 0.03),
              0 0 0 140px rgba(255, 255, 255, 0.02);
}

.auth-intro > * { position: relative; z-index: 1; }

.brand-mark {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin-bottom: var(--space-12);
  border-radius: var(--radius-md);
  color: var(--paper);
  background: var(--accent);
}

.auth-intro .eyebrow {
  color: var(--accent);
  font-size: var(--type-eyebrow);
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin: 0 0 var(--space-4);
}

.auth-intro__heading {
  max-width: 650px;
  margin: 0 0 var(--space-6);
  font-family: var(--font-serif);
  font-size: clamp(38px, 5vw, 68px);
  line-height: 0.98;
  letter-spacing: -0.045em;
  font-weight: 600;
  color: var(--paper);
}

.auth-intro__copy {
  max-width: 590px;
  margin: 0;
  color: rgba(244, 239, 230, 0.78);
  font-size: 17px;
  line-height: 1.65;
}

.auth-benefits {
  display: grid;
  gap: var(--space-3);
  margin: var(--space-12) 0 0;
  padding: 0;
  list-style: none;
  color: var(--paper);
  font-size: 14px;
}

.auth-benefits li {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.auth-benefits svg {
  color: var(--accent);
}

.auth-panel {
  display: grid;
  place-items: center;
  padding: var(--space-12) var(--space-8);
  background: var(--paper);
}

.auth-card {
  width: min(100%, 420px);
}

.auth-card__icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  margin-bottom: var(--space-8);
  border-radius: var(--radius-md);
  color: var(--accent);
  background: var(--accent-soft);
}

.auth-card .eyebrow {
  color: var(--accent);
  font-size: var(--type-eyebrow);
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin: 0 0 var(--space-2);
}

.auth-card__heading {
  margin: 0 0 var(--space-2);
  font-family: var(--font-serif);
  font-size: 34px;
  font-weight: 600;
  letter-spacing: -0.025em;
  color: var(--ink);
}

.auth-card__subtitle {
  margin: 0 0 var(--space-8);
  color: var(--ink-soft);
  line-height: 1.55;
}

.auth-form {
  display: grid;
  gap: var(--space-2);
}

.auth-form label {
  margin-top: var(--space-2);
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
}

.auth-form input {
  width: 100%;
  height: 46px;
  padding: 0 13px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  color: var(--ink);
  background: var(--paper-card);
}

.password-field {
  position: relative;
}

.password-field input {
  padding-right: 46px;
}

.password-field button {
  position: absolute;
  top: 50%;
  right: 6px;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--muted);
  background: transparent;
  cursor: pointer;
  transform: translateY(-50%);
}

.password-field button:hover {
  color: var(--ink);
  background: var(--paper-warm);
}

.auth-form input:focus {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-color: transparent;
}

.auth-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: 47px;
  margin-top: var(--space-4);
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--paper);
  background: var(--accent);
  font-weight: 650;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.auth-submit:hover { background: var(--accent-hover); }
.auth-submit:disabled { cursor: wait; opacity: 0.7; }

.auth-switch {
  width: 100%;
  margin-top: var(--space-4);
  border: 0;
  color: var(--accent);
  background: transparent;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}

.form-error,
.dashboard-error {
  margin: var(--space-2) 0 0;
  color: var(--danger);
  font-size: 13px;
  line-height: 1.45;
}
```

- [ ] **Step 4: Verify visual**

Run `npm run dev --workspace @gapo-slidegen/web`. Open http://localhost:3000/login. Expected: split-panel with dark editorial left (large Fraunces headline), warm paper right with serif form heading, accent ochre focus rings, skip link visible on focus.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/login/auth-screen.tsx apps/web/src/app/styles.css
git commit -m "feat(ui): redesign auth page with editorial split-panel

Left panel: dark ink background, Fraunces display heading, accent
benefits icons. Right panel: warm paper with serif form heading.
Skip-to-form link, focus rings, password reveal polished."
```

---

## Task 9: Dashboard — topbar, hero, theme picker, banner, decks list

**Files:**
- Modify: `apps/web/src/app/dashboard.tsx`
- Modify: `apps/web/src/app/styles.css`

This is the largest task. It rewires `dashboard.tsx` to use new components (LandingHero, ThemePreview, TemplateCard, EmptyState, Skeleton, ThemeToggle) and replaces the existing CSS classes with editorial token styles. Editor files are not touched.

- [ ] **Step 1: Update theme definitions in dashboard.tsx**

Open `apps/web/src/app/dashboard.tsx`. The `themes` array at lines 26–31 currently has 3-color tuples. Replace the tuple type with the editorial palette structure expected by `TemplateCard`:

Find:

```ts
const themes: Array<{ id: ThemeId; name: string; colors: [string, string, string] }> = [
  { id: "modern-blue", name: "Modern Blue", colors: ["#FFFFFF", "#1E4CD9", "#F5F8FE"] },
  { id: "editorial-cobalt", name: "Editorial", colors: ["#172033", "#285FC7", "#E3AA45"] },
  { id: "warm-studio", name: "Warm Studio", colors: ["#2E2925", "#C45132", "#D9A441"] },
  { id: "midnight-signal", name: "Midnight", colors: ["#09111F", "#4F86F7", "#F4B860"] },
];
```

Replace with:

```ts
type ThemePalette = { paper: string; ink: string; accent: string };

const themes: Array<{ id: ThemeId; name: string; colors: ThemePalette }> = [
  {
    id: "modern-blue",
    name: "Modern Blue",
    colors: { paper: "#FFFFFF", ink: "#1E4CD9", accent: "#F5F8FE" },
  },
  {
    id: "editorial-cobalt",
    name: "Editorial",
    colors: { paper: "#172033", ink: "#285FC7", accent: "#E3AA45" },
  },
  {
    id: "warm-studio",
    name: "Warm Studio",
    colors: { paper: "#2E2925", ink: "#C45132", accent: "#D9A441" },
  },
  {
    id: "midnight-signal",
    name: "Midnight",
    colors: { paper: "#09111F", ink: "#4F86F7", accent: "#F4B860" },
  },
];
```

- [ ] **Step 2: Add imports for new components**

Find the existing imports at the top of `dashboard.tsx` (lines 3–22). Add these imports at the end of the existing import block:

```ts
import { EmptyState } from "./components/empty-state";
import { LandingHero } from "./components/landing-hero";
import { Skeleton } from "./components/skeleton";
import { TemplateCard } from "./components/template-card";
import { ThemeToggle } from "./components/theme-toggle";
import { FilePpt } from "@phosphor-icons/react";
```

(FilePpt is already imported in the existing file; the additional import line is just to keep the new imports together. Verify it doesn't duplicate — if `FilePpt` is already imported from `@phosphor-icons/react`, remove that line.)

- [ ] **Step 3: Replace the loading state**

Find the existing loading branch:

```tsx
  if (loading) {
    return <main className="dashboard-loading">Loading your workspace…</main>;
  }
```

Replace with:

```tsx
  if (loading) {
    return (
      <main className="dashboard-shell">
        <header className="dashboard-topbar">
          <a className="dashboard-brand" href="/">
            <span className="dashboard-brand__mark"><MagicWand size={18} weight="fill" /></span>
            <span className="dashboard-brand__wordmark">Gapo SlideGen</span>
          </a>
        </header>
        <div className="dashboard-content">
          <div className="dashboard-hero">
            <Skeleton width="120px" height="11px" />
            <div style={{ height: "var(--space-3)" }} />
            <Skeleton width="60%" height="56px" />
            <div style={{ height: "var(--space-3)" }} />
            <Skeleton width="80%" height="16px" />
          </div>
          <Skeleton width="100%" height="320px" radius="var(--radius-lg)" />
        </div>
      </main>
    );
  }
```

- [ ] **Step 4: Replace the topbar + hero block**

Find the JSX starting at `<main className="dashboard-shell">` and ending at the closing `</section>` of `.dashboard-hero` (currently lines 276–295). Replace with:

```tsx
  return (
    <main className="dashboard-shell">
      <a className="u-skip-link" href="#dashboard-content">Skip to main content</a>

      <header className="dashboard-topbar">
        <a className="dashboard-brand" href="/">
          <span className="dashboard-brand__mark"><MagicWand size={18} weight="fill" /></span>
          <span className="dashboard-brand__wordmark">Gapo SlideGen</span>
        </a>
        <div className="account-menu">
          <span>{user?.email}</span>
          <ThemeToggle />
          <button className="icon-button" onClick={logout} aria-label="Sign out">
            <SignOut size={18} />
          </button>
        </div>
      </header>

      <div id="dashboard-content" className="dashboard-content">
        <LandingHero
          eyebrow="Presentation workspace"
          heading="What are we presenting?"
          body="Bring a rough idea or finished content. The source stays editable and owned by you."
        />
```

- [ ] **Step 5: Replace the composer card**

Find the existing `<section className="composer-card">` block (currently lines 297–382). Replace with:

```tsx
        <section className="composer-card">
          <div className="composer-tabs" role="tablist" aria-label="Source type">
            <button
              className={mode === "prompt" ? "is-active" : ""}
              role="tab"
              aria-selected={mode === "prompt"}
              onClick={() => setMode("prompt")}
            >
              Prompt
            </button>
            <button
              className={mode === "manuscript" ? "is-active" : ""}
              role="tab"
              aria-selected={mode === "manuscript"}
              onClick={() => setMode("manuscript")}
            >
              Full text
            </button>
            <button
              className={mode === "file" ? "is-active" : ""}
              role="tab"
              aria-selected={mode === "file"}
              onClick={() => setMode("file")}
            >
              Upload
            </button>
          </div>

          {mode === "file" ? (
            <div className="upload-panel">
              <div className="upload-panel__icon"><UploadSimple size={25} /></div>
              <h2>Upload an existing document</h2>
              <p>DOCX, PPTX, or text-based PDF · maximum 25 MB</p>
              <input
                ref={fileInput}
                className="visually-hidden"
                id="source-file"
                type="file"
                accept=".docx,.pptx,.pdf"
                disabled={submitting}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void uploadFile(file);
                }}
              />
              <label className="button button--primary" htmlFor="source-file">
                <UploadSimple size={17} /> {submitting ? "Working…" : "Choose file & generate"}
              </label>
              <fieldset className="template-picker" aria-label="Visual theme">
                <legend className="template-picker__legend">Visual theme</legend>
                <div className="template-picker__grid">
                  {themes.map((theme) => (
                    <TemplateCard
                      key={theme.id}
                      id={theme.id}
                      name={theme.name}
                      colors={theme.colors}
                      selected={themeId === theme.id}
                      onSelect={(id) => setThemeId(id as ThemeId)}
                    />
                  ))}
                </div>
              </fieldset>
            </div>
          ) : (
            <form className="composer-form" onSubmit={createTextSource}>
              <label htmlFor="composer-title" className="composer-form__label">
                Presentation title <span className="composer-form__hint">(optional)</span>
              </label>
              <input
                id="composer-title"
                placeholder="A concise, memorable title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={500}
              />
              <label htmlFor="composer-text" className="composer-form__label">
                {mode === "prompt" ? "Prompt" : "Source text"}
              </label>
              <textarea
                id="composer-text"
                placeholder={
                  mode === "prompt"
                    ? "Describe the audience, goal, and key message…"
                    : "Paste the complete content you want organized into slides…"
                }
                value={text}
                onChange={(event) => setText(event.target.value)}
                required
              />
              <fieldset className="template-picker" aria-label="Visual theme">
                <legend className="template-picker__legend">Visual theme</legend>
                <div className="template-picker__grid">
                  {themes.map((theme) => (
                    <TemplateCard
                      key={theme.id}
                      id={theme.id}
                      name={theme.name}
                      colors={theme.colors}
                      selected={themeId === theme.id}
                      onSelect={(id) => setThemeId(id as ThemeId)}
                    />
                  ))}
                </div>
              </fieldset>
              <div className="composer-actions">
                <span>You will go straight to the editable presentation.</span>
                <button
                  className="button button--primary"
                  type="submit"
                  disabled={submitting || !text.trim()}
                >
                  <MagicWand size={17} /> {submitting ? "Working…" : "Generate presentation"}
                </button>
              </div>
            </form>
          )}
          {error ? <p className="dashboard-error" role="alert">{error}</p> : null}
        </section>
```

- [ ] **Step 6: Replace the generation banner**

Find the existing `<section className={`generation-banner...`}>` block (around line 384–431). Replace with:

```tsx
        {activeGenerationSource ? (
          <section
            className={`generation-banner${
              activeGenerationJob?.status === "failed" ? " generation-banner--failed" : ""
            }${
              activeGenerationJob?.status === "canceled" ? " generation-banner--canceled" : ""
            }`}
            aria-live="polite"
          >
            <span className="generation-banner__icon">
              <MagicWand size={20} />
            </span>
            <div className="generation-banner__content">
              <p className="generation-banner__eyebrow">
                {activeGenerationJob?.status === "failed"
                  ? "Generation failed"
                  : activeGenerationJob?.status === "canceled"
                    ? "Generation canceled"
                    : "Building presentation"}
              </p>
              <strong className="generation-banner__heading">
                {activeGenerationJob?.status === "running" || activeGenerationJob?.status === "queued"
                  ? `“${activeGenerationSource.title}”`
                  : activeGenerationJob?.status === "failed" || activeGenerationJob?.status === "canceled"
                    ? activeGenerationSource.title
                    : `“${activeGenerationSource.title}”`}
              </strong>
              <p className="generation-banner__body">
                {startingSourceId === activeGenerationSource.id || activeGenerationJob?.status === "queued"
                  ? "Queued — preparing your source…"
                  : activeGenerationJob?.status === "running"
                    ? `Creating the story and editable slides… ${activeGenerationJob.progress}%`
                    : activeGenerationJob?.status === "failed"
                      ? activeGenerationJob.error_message || "The presentation could not be generated."
                      : activeGenerationJob?.status === "canceled"
                        ? "No presentation was saved from this job."
                        : "Starting generation…"}
              </p>
              {activeGenerationJob?.status === "queued" || activeGenerationJob?.status === "running" ? (
                <div
                  className="generation-progress"
                  role="progressbar"
                  aria-label="Presentation generation progress"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={activeGenerationJob.progress}
                >
                  <span style={{ width: `${activeGenerationJob.progress}%` }} />
                </div>
              ) : null}
            </div>
            {activeGenerationJob?.status === "failed" || activeGenerationJob?.status === "canceled" ? (
              <button className="button" onClick={() => void startGeneration(activeGenerationSource)}>
                Retry
              </button>
            ) : activeGenerationJob?.status === "queued" || activeGenerationJob?.status === "running" ? (
              <button
                className="button generation-cancel"
                disabled={cancelingJobId === activeGenerationJob.id}
                onClick={() =>
                  void cancelGeneration(activeGenerationSource.id, activeGenerationJob.id)
                }
              >
                {cancelingJobId === activeGenerationJob.id ? "Canceling…" : "Cancel"}
              </button>
            ) : (
              <span className="generation-pulse" aria-hidden="true" />
            )}
          </section>
        ) : null}
```

- [ ] **Step 7: Replace the recent decks list section**

Find the existing `<section className="presentation-section">` block. Replace with:

```tsx
        <section className="presentation-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Your decks</p>
              <h2 className="section-heading__title">Recent presentations</h2>
            </div>
            <span className="section-heading__count">
              {presentations.length} deck{presentations.length === 1 ? "" : "s"}
            </span>
          </div>
          {presentations.length === 0 ? (
            <EmptyState
              icon={<FilePpt size={22} weight="duotone" />}
              eyebrow="Your decks"
              heading="No presentations yet"
              body="Generated presentations will appear here so you can reopen and continue editing them."
            />
          ) : (
            <div className="presentation-strip">
              {presentations.map((presentation) => {
                const candidate = presentation.document as { slides?: unknown[] } | null;
                const count = Array.isArray(candidate?.slides) ? candidate.slides.length : 0;
                return (
                  <article className="presentation-item u-lift" key={presentation.id}>
                    {renamingPresentationId === presentation.id ? (
                      <form
                        className="presentation-rename"
                        onSubmit={(event) => void renamePresentation(event, presentation)}
                      >
                        <label htmlFor={`rename-${presentation.id}`}>Presentation name</label>
                        <input
                          id={`rename-${presentation.id}`}
                          value={renameDraft}
                          maxLength={500}
                          autoFocus
                          onChange={(event) => setRenameDraft(event.target.value)}
                        />
                        <div>
                          <button
                            className="button button--primary"
                            type="submit"
                            disabled={!renameDraft.trim() || presentationActionId === presentation.id}
                          >
                            {presentationActionId === presentation.id ? "Saving…" : "Save"}
                          </button>
                          <button
                            className="button"
                            type="button"
                            disabled={presentationActionId === presentation.id}
                            onClick={() => setRenamingPresentationId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <a
                          className="presentation-item__open"
                          href={`/editor?presentation=${presentation.id}`}
                        >
                          <span className="presentation-item__preview">
                            <FilePpt size={24} />
                          </span>
                          <span className="presentation-item__copy">
                            <strong>{presentation.title}</strong>
                            <small className="presentation-item__count">
                              <span className="presentation-item__count-number">{count}</span> slide{count === 1 ? "" : "s"}
                            </small>
                          </span>
                          <ArrowRight size={16} />
                        </a>
                        <div className="presentation-item__actions">
                          <button
                            type="button"
                            aria-label={`Rename ${presentation.title}`}
                            title="Rename"
                            disabled={presentationActionId === presentation.id}
                            onClick={() => {
                              setRenamingPresentationId(presentation.id);
                              setRenameDraft(presentation.title);
                            }}
                          >
                            <PencilSimple size={15} />
                          </button>
                          <button
                            type="button"
                            aria-label={`Delete ${presentation.title}`}
                            title="Delete"
                            disabled={presentationActionId === presentation.id}
                            onClick={() => void deletePresentation(presentation)}
                          >
                            <Trash size={15} />
                          </button>
                        </div>
                      </>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
```

- [ ] **Step 8: Refactor dashboard CSS in styles.css**

Find the existing `.dashboard-loading` through `.presentation-rename` CSS block (around lines 182–258). Replace the ENTIRE block with:

```css
.dashboard-loading {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  color: var(--muted);
}

.dashboard-shell {
  width: 100%;
  min-width: 0;
  min-height: 100dvh;
  overflow-x: clip;
  background: var(--paper);
}

.dashboard-topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  width: 100%;
  min-width: 0;
  height: 60px;
  padding: 0 clamp(18px, 4vw, 54px);
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
}

[data-theme="dark"] .dashboard-topbar {
  background: rgba(37, 35, 32, 0.94);
}

.dashboard-brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
  color: var(--ink);
}

.dashboard-brand__mark {
  display: grid;
  place-items: center;
  width: 31px;
  height: 31px;
  border-radius: var(--radius-sm);
  color: var(--paper);
  background: var(--accent);
}

.dashboard-brand__wordmark {
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.account-menu {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--ink-soft);
  font-size: 13px;
}

.dashboard-content {
  width: min(1080px, calc(100% - 36px));
  min-width: 0;
  margin: 0 auto;
  padding: var(--space-16) 0 var(--space-24);
  display: grid;
  gap: var(--space-12);
}

.composer-card {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--paper-card);
  box-shadow: var(--shadow-md);
}

.composer-tabs {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2);
  border-bottom: 1px solid var(--border);
  background: var(--paper-warm);
}

.composer-tabs button {
  min-width: 96px;
  padding: 8px 13px;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--ink-soft);
  background: transparent;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out),
              color var(--duration-fast) var(--ease-out);
}

.composer-tabs button:hover {
  color: var(--ink);
}

.composer-tabs button.is-active {
  color: var(--ink);
  background: var(--paper-card);
  box-shadow: var(--shadow-sm);
}

.composer-form {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-6);
}

.composer-form__label {
  font-size: 13px;
  font-weight: 650;
  color: var(--ink);
}

.composer-form__hint {
  color: var(--muted);
  font-weight: 450;
}

.composer-form input,
.composer-form textarea {
  width: 100%;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  color: var(--ink);
  background: var(--paper-card);
  font-family: var(--font-sans);
}

.composer-form input {
  height: 46px;
  padding: 0 13px;
}

.composer-form textarea {
  min-height: 160px;
  padding: 13px;
  resize: vertical;
  line-height: 1.55;
}

.composer-form input:focus,
.composer-form textarea:focus {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-color: transparent;
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-top: var(--space-2);
}

.composer-actions > span {
  color: var(--muted);
  font-size: var(--type-small);
}

.template-picker {
  width: 100%;
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.template-picker__legend {
  margin-bottom: var(--space-2);
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 650;
}

.template-picker__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.button {
  padding: 0 14px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid var(--border);
  background: var(--paper-card);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out),
              border-color var(--duration-fast) var(--ease-out);
}

.button--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--paper);
}

.button--primary:hover {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.button:disabled {
  cursor: wait;
  opacity: 0.62;
}

.icon-button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--paper-card);
  color: var(--ink-soft);
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-out);
}

.icon-button:hover {
  color: var(--ink);
}

.upload-panel {
  display: flex;
  min-height: 280px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  text-align: center;
  gap: var(--space-3);
}

.upload-panel__icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-pill);
  color: var(--accent);
  background: var(--accent-soft);
}

.upload-panel h2 {
  margin: var(--space-2) 0 0;
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 600;
  color: var(--ink);
}

.upload-panel p {
  margin: 0;
  color: var(--muted);
  font-size: var(--type-small);
}

.upload-panel label {
  cursor: pointer;
}

.dashboard-error {
  margin: 0 var(--space-6) var(--space-4);
  padding: 11px 13px;
  border-radius: var(--radius-sm);
  background: rgba(178, 58, 42, 0.08);
  color: var(--danger);
}

.generation-banner {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  border: 1px solid var(--accent);
  border-radius: var(--radius-md);
  background: var(--accent-soft);
}

.generation-banner--failed {
  border-color: var(--danger);
  background: rgba(178, 58, 42, 0.08);
}

.generation-banner--canceled {
  border-color: var(--border);
  background: var(--paper-warm);
}

.generation-banner__icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  color: var(--accent);
  background: var(--paper-card);
}

.generation-banner__content {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.generation-banner__eyebrow {
  margin: 0;
  color: var(--accent);
  font-size: var(--type-eyebrow);
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.generation-banner--failed .generation-banner__eyebrow { color: var(--danger); }
.generation-banner--canceled .generation-banner__eyebrow { color: var(--muted); }

.generation-banner__heading {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
}

.generation-banner__body {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--type-small);
  line-height: 1.45;
}

.generation-progress {
  overflow: hidden;
  width: min(420px, 100%);
  height: 4px;
  margin-top: var(--space-2);
  border-radius: var(--radius-pill);
  background: rgba(184, 101, 30, 0.15);
}

.generation-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--accent);
  transition: width var(--duration-base) var(--ease-out);
}

.generation-cancel { min-width: 84px; }

.generation-pulse {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-pill);
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(184, 101, 30, 0.45);
  animation: generation-pulse 1500ms var(--ease-out) infinite;
}

@keyframes generation-pulse {
  70% { box-shadow: 0 0 0 10px rgba(184, 101, 30, 0); }
  100% { box-shadow: 0 0 0 0 rgba(184, 101, 30, 0); }
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.section-heading__title {
  margin: var(--space-1) 0 0;
  font-family: var(--font-serif);
  font-size: var(--type-h2);
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.section-heading__count {
  color: var(--muted);
  font-size: var(--type-small);
}

.presentation-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--paper-card);
}

.presentation-item {
  display: flex;
  align-items: stretch;
  min-width: 0;
  padding: var(--space-2);
}

.presentation-item:nth-child(even) {
  border-left: 1px solid var(--border);
}

.presentation-item:nth-child(n + 3) {
  border-top: 1px solid var(--border);
}

.presentation-item__open {
  display: grid;
  grid-template-columns: 66px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  flex: 1;
  padding: var(--space-2);
  color: inherit;
  text-decoration: none;
  border-radius: var(--radius-sm);
}

.presentation-item__preview {
  display: grid;
  place-items: center;
  aspect-ratio: 16 / 9;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--accent);
  background: var(--accent-soft);
}

.presentation-item__copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.presentation-item__copy strong {
  overflow: hidden;
  font-family: var(--font-serif);
  font-size: 15px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink);
}

.presentation-item__count {
  color: var(--muted);
  font-size: var(--type-small);
}

.presentation-item__count-number {
  font-family: var(--font-mono);
  font-weight: 500;
}

.presentation-item__actions {
  display: flex;
  align-items: center;
  gap: 2px;
  padding-left: var(--space-2);
}

.presentation-item__actions button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--muted);
  background: transparent;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-out),
              background var(--duration-fast) var(--ease-out);
}

.presentation-item__actions button:hover:not(:disabled) {
  color: var(--ink);
  background: var(--paper-warm);
}

.presentation-item__actions button:last-child:hover:not(:disabled) {
  color: var(--danger);
  background: rgba(178, 58, 42, 0.08);
}

.presentation-item__actions button:disabled {
  opacity: 0.4;
  cursor: wait;
}

.presentation-rename {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px var(--space-3);
  width: 100%;
  padding: var(--space-2);
}

.presentation-rename label {
  grid-column: 1 / -1;
  color: var(--ink-soft);
  font-size: 11px;
  font-weight: 700;
}

.presentation-rename input {
  min-width: 0;
  height: 36px;
  padding: 0 9px;
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  color: var(--ink);
  background: var(--paper-card);
}

.presentation-rename input:focus {
  outline: 2px solid var(--accent-soft);
  outline-offset: 1px;
}

.presentation-rename > div {
  display: flex;
  gap: var(--space-1);
}

.presentation-rename .button {
  min-height: 36px;
  padding-inline: var(--space-3);
}
```

Keep the existing `.editor-shell` through `.present-mode` blocks unchanged, the `.eyebrow` and `.visually-hidden` utility classes unchanged, and the media queries at the bottom unchanged.

- [ ] **Step 9: Verify visually**

Run `npm run dev --workspace @gapo-slidegen/web`. Open http://localhost:3000/login → register → land on dashboard. Verify:

- Topbar: serif "Gapo SlideGen" wordmark, theme toggle, sign-out icon.
- Hero: large Fraunces headline "What are we presenting?", accent eyebrow.
- Composer: warm-paper tabs, form with serif labels, theme picker with 2×2 template cards each showing live mini slide preview.
- Generate: button works, banner appears with eyebrow + serif title + progress bar.
- Recent decks: 2-column grid, paper cards with serif titles, mono-formatted slide counts.

Take a screenshot at 1280px viewport for the visual baseline.

- [ ] **Step 10: Run all unit tests**

```bash
npm test --workspace @gapo-slidegen/web
```

Expected: PASS for all 10 component tests (Skeleton + EmptyState + TemplateCard).

- [ ] **Step 11: Commit**

```bash
git add apps/web/src/app/dashboard.tsx apps/web/src/app/styles.css
git commit -m "feat(ui): redesign dashboard with editorial tokens

Topbar serif wordmark + theme toggle. Hero via LandingHero. Composer
with serif labels and TemplateCard 2x2 theme picker (live preview).
Generation banner: eyebrow + serif title + body + progress. Decks list
polish: serif titles, mono slide counts, EmptyState when empty.

Editor CSS scoped and unchanged."
```

---

## Task 10: Smoke E2E test (Playwright)

**Files:**
- Create: `apps/web/playwright.config.ts`
- Create: `apps/web/tests/e2e/shell.spec.ts`
- Modify: `apps/web/package.json` (add e2e script + devDeps)

- [ ] **Step 1: Install Playwright**

```bash
npm install --workspace @gapo-slidegen/web --save-dev @playwright/test@1.50
npx playwright install chromium
```

- [ ] **Step 2: Create Playwright config**

Create `apps/web/playwright.config.ts`:

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    viewport: { width: 1280, height: 800 },
    trace: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
    },
  ],
});
```

- [ ] **Step 3: Create smoke test**

Create `apps/web/tests/e2e/shell.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test.describe("shell", () => {
  test("auth page renders editorial split-panel", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /bring your knowledge/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in|create account/i })).toBeVisible();
    await expect(page.locator(".u-skip-link")).toHaveCount(1);
  });

  test("theme toggle switches data-theme", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("html")).not.toHaveAttribute("data-theme", "dark");
    await page.getByRole("button", { name: /switch to dark theme/i }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("dashboard requires auth and redirects to login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("register, then dashboard composer is interactive", async ({ page }) => {
    const email = `e2e-${Date.now()}@example.com`;
    await page.goto("/login");
    await page.getByRole("button", { name: /need an account/i }).click();
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("verysecurepassword123");
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/$|\/dashboard/);

    await expect(page.getByRole("heading", { name: /what are we presenting/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /prompt/i })).toHaveAttribute("aria-selected", "true");

    // Theme picker has 4 cards
    const cards = page.getByRole("radio");
    await expect(cards).toHaveCount(4);

    // Select a non-default theme
    await page.getByRole("radio", { name: /warm studio/i }).click();
    await expect(page.getByRole("radio", { name: /warm studio/i })).toHaveAttribute("aria-checked", "true");
  });
});
```

- [ ] **Step 4: Add e2e script to package.json**

Open `apps/web/package.json`. Add to scripts:

```json
"e2e": "playwright test"
```

- [ ] **Step 5: Run dev server and E2E**

In one terminal:

```bash
npm run db:up
npm run db:migrate
npm run api:dev
npm run worker:dev
npm run dev --workspace @gapo-slidegen/web
```

Wait for the API to be ready. In another terminal:

```bash
npm run e2e --workspace @gapo-slidegen/web
```

Expected: 4 tests pass. If a test fails due to timing, increase `expect.timeout` in `playwright.config.ts` (max 10s).

- [ ] **Step 6: Commit**

```bash
git add apps/web/playwright.config.ts apps/web/tests apps/web/package.json
git commit -m "test(e2e): add Playwright smoke tests for shell

Tests auth split-panel, theme toggle persistence, auth redirect,
and dashboard composer + theme picker interactions. Desktop 1280px
viewport only per spec scope."
```

---

## Task 11: Visual baseline + reduced-motion verification

**Files:**
- Modify: `apps/web/package.json` (add visual script)
- Create: `apps/web/tests/visual/capture.mjs`

- [ ] **Step 1: Add visual capture script**

Create `apps/web/tests/visual/capture.mjs`:

```js
import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const OUT = path.resolve("./tests/visual/baselines");
await mkdir(OUT, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const page = await context.newPage();

const targets = [
  { name: "01-auth-login.png", url: "/login", waitFor: "h1" },
  { name: "02-auth-register.png", url: "/login", waitFor: "button:has-text('Need an account?')", click: "button:has-text('Need an account?')" },
  { name: "03-dashboard-blank.png", url: "/", waitFor: "h1", requiresAuth: true },
  { name: "04-dashboard-template-picker.png", url: "/", waitFor: "[role=radio]", requiresAuth: true },
];

for (const target of targets) {
  console.log(`Capturing ${target.name}…`);
  await page.goto(`http://localhost:3000${target.url}`);
  if (target.click) {
    await page.click(target.click);
  }
  await page.waitForSelector(target.waitFor, { timeout: 10_000 });
  // Allow fonts to settle
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(OUT, target.name), fullPage: false });
  console.log(`  saved ${target.name}`);
}

await browser.close();
console.log("Visual baselines captured.");
```

- [ ] **Step 2: Add visual script to package.json**

Add to `apps/web/package.json` scripts:

```json
"visual:capture": "node tests/visual/capture.mjs"
```

- [ ] **Step 3: Run visual capture (requires running app)**

With API + worker + web dev server still running:

```bash
npm run visual:capture --workspace @gapo-slidegen/web
```

Expected: 4 PNGs written to `apps/web/tests/visual/baselines/`. Verify each file is > 30KB (genuine screenshot, not blank).

- [ ] **Step 4: Verify reduced-motion**

Open Chrome devtools → Rendering → "Emulate CSS media feature prefers-reduced-motion: reduce". Reload dashboard. Expected: no pulse animation on generation banner placeholder; no shimmer on skeletons; hover transitions still visible but instant.

Take a screenshot for the record:

```bash
node -e "
const { chromium } = require('@playwright/test');
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    reducedMotion: 'reduce',
  });
  const page = await context.newPage();
  await page.goto('http://localhost:3000/');
  await page.waitForSelector('h1');
  await page.waitForTimeout(500);
  await page.screenshot({ path: './tests/visual/baselines/05-dashboard-reduced-motion.png' });
  await browser.close();
  console.log('Reduced-motion baseline captured.');
})();
"
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/tests/visual apps/web/package.json
git commit -m "test(visual): add desktop visual baseline capture

Captures auth, register, dashboard, template picker, and reduced-motion
state at 1280px viewport. Scripts added for npm run visual:capture."
```

---

## Task 12: Final cleanup + PR

**Files:**
- Modify: `apps/web/src/app/styles.css` (remove now-unused old CSS if any remains)

- [ ] **Step 1: Lint and typecheck**

```bash
npm run check:node
```

Expected: typecheck passes. If vitest reports old imports failing, fix them.

- [ ] **Step 2: Remove the unused old `.auth-form input, .composer-form input, .composer-form textarea { ... }` block**

After Task 8 and Task 9 refactored the auth-page and dashboard CSS, the original `input { ... }` line in styles.css (around line 169 in the original file) is now redundant. Verify it's gone (Task 8 already replaced the auth CSS block; Task 9 replaced the dashboard CSS block). If anything remains, remove.

- [ ] **Step 3: Verify editor still works**

```bash
npm run dev --workspace @gapo-slidegen/web
```

Login, generate a stub presentation, open the editor. Confirm:
- Editor canvas uses Montserrat (NOT Fraunces) — unchanged.
- All editor buttons (insert text/shape/image, undo/redo, present) work.
- Properties panel + AI panel render with old styles (intentionally untouched).

- [ ] **Step 4: Run full test suite**

```bash
npm test --workspace @gapo-slidegen/web
npm run e2e --workspace @gapo-slidegen/web
```

Expected: all pass.

- [ ] **Step 5: Update README with new screenshots**

If desired, replace any dashboard screenshots in README.md (currently doesn't have screenshots — skip if absent).

- [ ] **Step 6: Commit any final cleanup**

```bash
git add -A
git diff --cached --quiet || git commit -m "chore(ui): remove redundant CSS after redesign"
```

- [ ] **Step 7: Push branch and open PR**

```bash
git push origin main
gh pr create --title "feat(ui): editorial publication shell (sub-project 1)" --body "..."
```

PR body should reference the spec at `docs/superpowers/specs/2026-08-17-gapo-uiux-subproject-1-shell-design.md` and list:
- New shared primitives (Skeleton, EmptyState, LandingHero, ThemePreview, TemplateCard, ThemeToggle)
- Refactored auth page (split-panel editorial)
- Refactored dashboard (topbar serif wordmark + theme toggle, LandingHero, TemplateCard 2x2 picker, editorial generation banner, EmptyState for empty decks)
- Dark mode (basic parity)
- Variable fonts (Fraunces / Inter / JetBrains Mono)
- Vitest + Playwright setup
- Editor explicitly untouched (sub-project 2 will cover)