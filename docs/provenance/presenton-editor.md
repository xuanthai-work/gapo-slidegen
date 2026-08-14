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

## Current port status

No Presenton editor implementation files have been copied yet. The canonical
schema is a product-owned adaptation informed by the upstream data model.
