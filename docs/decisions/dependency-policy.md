# Dependency policy

Status: accepted for M0

## Rule

New product-owned code starts on the latest stable dependency version that
passes compatibility and license checks. A ported subsystem starts from the
version group used by its pinned upstream commit, then upgrades one compatible
group at a time after its contract tests pass.

Lockfiles pin reproducible builds. Floating `latest` ranges are not used in
committed manifests.

## Editor compatibility group

Pinned Presenton source commit:
`523b9cb47889e1fc124bb0dab77015b344a46f76`

| Package | Presenton baseline | Stable checked 2026-08-13 | M0 decision |
| --- | ---: | ---: | --- |
| Next.js | 16.2.6 | 16.3.0 | Use stable for product shell after editor spike |
| React | 19.2.6 | 19.2.8 | Test editor on 19.2.8 |
| React DOM | 19.2.6 | 19.2.8 | Keep aligned with React |
| Konva | 10.3.0 | 10.3.0 | Use 10.3.0 |
| React Konva | 19.2.4 | 19.2.5 | Test 19.2.5 |
| Tiptap React | 2.11.5 | 3.30.1 | Start 2.11.5; upgrade only after rich-text tests pass |
| TypeScript | 5.x | 7.0.2 | Use 7.0.2 for product-owned packages; verify editor separately |
| Zod | 4.0.5 | 4.4.3 | Use 4.4.3 |

Tiptap is deliberately the exception because the stable release crosses a
major boundary and the Presenton editor uses its APIs extensively.

## Backend baseline

The first FastAPI ingestion/job slice uses Python 3.12 and exact direct
dependency pins. Versions and the audit date are recorded in
`m1-ingestion-and-jobs.md`; the uv lockfile pins the full transitive graph.
