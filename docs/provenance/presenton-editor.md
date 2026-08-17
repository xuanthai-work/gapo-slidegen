# Presenton editor provenance

## Source

- Project: Presenton
- Canonical repository: https://github.com/presenton/presenton
- Locally inspected checkout: `D:\work\Gapo\presenton`
- Pinned revision: `523b9cb47889e1fc124bb0dab77015b344a46f76`
- License: Apache License 2.0
- Upstream notice: `NOTICE` at the pinned revision

The local checkout has a non-canonical Git remote. Reuse is attributed to the
canonical `presenton/presenton` project and pinned by commit hash.

## Approved reuse level

Level 4: retain the slide editor subsystem near its upstream structure while
placing it behind a product-owned boundary.

## Approved source boundary

Primary upstream directory:

```text
servers/nextjs/components/slide-editor/
```

Supporting modules will only be added here after they are individually named,
license-checked, and shown to be necessary by the editor spike.

## Product boundary

The ported editor must not own or import:

- Authentication or user ownership
- Application routing
- Database persistence
- AI provider configuration
- Product navigation or branding
- Direct API URLs

It receives validated presentation data and emits typed edit operations or a
validated next document through callbacks.

## Intentional changes

- Add stable IDs to presentations, slides, and elements.
- Add explicit schema versions.
- Validate data at the boundary with `@gapo-slidegen/slide-schema`.
- Replace direct Redux persistence with callback-driven persistence.
- Replace upstream branding and product-level events.
- Keep canvas units at 1280 by 720.
- Add contract fixtures and save/reload tests.

## Upstream sync

The pinned commit is the only comparison baseline. Upstream changes are not
merged automatically. A sync requires a reviewed diff, provenance update,
dependency audit, and editor contract test run.

## Test obligations

- Load a canonical deck fixture.
- Select and edit text.
- Drag and resize elements.
- Copy, paste, group, ungroup, undo, and redo.
- Save and reload without data loss.
- Reject an invalid document at the product boundary.

## Current editor port status

No Presenton editor implementation files have been copied yet. The canonical
schema is a product-owned adaptation informed by the upstream data model. The
template adapter below is independent of a future editor subsystem port.

## Modern template vertical slice

The first template port adapts geometry, content roles, typography, and visual
tokens from these files at the pinned revision:

```text
templates/modern/template.json
templates/executive/static/Montserrat Regular.ttf
templates/executive/static/Montserrat Bold.ttf
servers/nextjs/app/(presentation-generator)/(dashboard)/theme/components/ThemePanel/constants.ts
```

The pinned `templates/modern/template.json` is vendored unchanged at
`apps/api/app/generation/templates/modern.json` (SHA-256
`2BF0E68287893B0314DA49A46C7237A6BA6D1B32F1EB0BE2A457DCDB52C0D323`).
`PresentonTemplateAdapter` reads that artifact at runtime and compiles its
nested component tree into the product-owned canonical schema.

Intentional changes:

- Flatten Presenton groups, containers, flex rows, and grids into individually
  editable canonical elements while retaining `componentId` and
  `componentSlot` provenance metadata.
- Map AI-authored story blocks directly into the named text slots. Sentence
  splitting remains only as backward compatibility for legacy unstructured
  outlines and the offline stub.
- Convert polygon vectors to their editable rectangular bounds because the MVP
  shape schema does not yet support arbitrary vector points.
- Replace image and icon slots with editable placeholders until generated or
  uploaded assets can be assigned to template slots.
- Keep chart and table layouts disabled in automatic selection until structured
  generation can supply truthful data for them.
- Keep all element identities, geometry, and text editable through the current
  editor and PPTX adapter.
- Serve Montserrat locally instead of loading the Google Fonts CSS URL at
  runtime.
- Name the adapted initial theme `modern-blue` to avoid using Presenton as
  product branding.

The adapter automatically cycles through six compatible Modern content layouts;
the imported artifact contains all ten upstream layouts. The Montserrat font
files are licensed under the SIL Open Font License 1.1.
The license text is stored at `LICENSES/Montserrat-OFL-1.1.txt`. The repeatable
import command is:

```powershell
.\scripts\import-presenton-modern-assets.ps1 -PresentonRoot D:\work\Gapo\presenton
```
