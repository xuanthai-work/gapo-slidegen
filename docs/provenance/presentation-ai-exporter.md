# Presentation AI exporter provenance

## Source

- Project: Presentation AI by ALLWEONE
- Repository: https://github.com/allweonedev/presentation-ai
- License: MIT
- Candidate source:
  `src/components/presentation/export/domToPptxConverter.ts`

## Approved reuse level

Level 3: port selected conversion logic only after the export spike identifies
the exact functions required.

## Planned changes

- Read canonical slide JSON instead of browser DOM.
- Remove application, editor, and browser-state dependencies.
- Preserve native PowerPoint text, image, shape, table, and chart objects where
  possible.
- Use an explicit SVG or image fallback only for unsupported effects.

## Current port status

No Presentation AI source file has been copied yet. Exact upstream revision,
copied functions, dependencies, and tests will be recorded before the port.
