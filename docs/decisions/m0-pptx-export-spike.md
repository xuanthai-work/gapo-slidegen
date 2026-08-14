# M0 schema-native PPTX export spike

Status: passed with a manual-open follow-up

## Decision

Use a product-owned canonical-schema adapter over PptxGenJS 4.0.1. Keep this
adapter independent from the browser editor and place it behind the future Node
export worker boundary.

The exporter creates native PowerPoint objects for text, text lists, shapes,
lines, tables, charts, and uploaded images. SVG is embedded as an image.
Container backgrounds remain native shapes. Group, flex, and grid parents are
flattened into individually editable child objects and emit structured
warnings. Missing assets are omitted with a warning instead of silently
rasterizing or inventing content.

No Presentation AI source was required for this spike. Its approved Level 3
port remains available if later fidelity tests identify conversion behavior
worth reusing.

## Coordinate contract

- Canonical editor stage: 1280 x 720 pixels.
- PPTX layout: 13.333333 x 7.5 inches.
- Conversion: 96 pixels per inch and 0.75 points per pixel.
- Maximum slide count continues to be enforced by the canonical schema.

## Automated evidence

The golden fixture contains text, shapes, a table, a chart, and an uploaded
image. Its test generates a real `.pptx`, opens its ZIP archive, and asserts:

- the slide XML contains text and separate PowerPoint shape/table nodes;
- the slide relationship targets a native chart part;
- the chart XML contains the source series;
- the archive contains a separate media asset;
- an unresolved asset creates an explicit warning.

The generated local artifact is
`.data/export-spike/native-elements-golden.pptx` and is intentionally ignored by
Git.

## Remaining acceptance check

This machine does not currently have LibreOffice available, so automated
render/open validation was not run. Before declaring production-grade export,
open the golden file in the target Microsoft PowerPoint version (and ideally
LibreOffice Impress), edit each object, save, reopen, and compare layout. Add
rendered-slide regression tests once an office renderer is present in the
Linux container image.
