# PptxGenJS provenance

## Dependency

- Project: PptxGenJS
- Repository: https://github.com/gitbrent/PptxGenJS
- Installed package: `pptxgenjs@4.0.1`
- Release date: 2025-06-26
- License: MIT
- Copyright: 2015-present Brent Ely
- npm integrity:
  `sha512-TeJISr8wouAuXw4C1F/mC33xbZs/FuEG6nH9FG1Zj+nuPcGMP5YRHl6X+j3HSUnS1f3at6k75ZZXPMZlA5Lj9A==`

The dependency is pinned in `package-lock.json`. Its license text is stored at
`LICENSES/PptxGenJS-MIT.txt`.

## Usage

`packages/pptx-exporter` calls the public PptxGenJS API to build OOXML objects
from the product-owned canonical slide schema. No PptxGenJS source file is
copied or modified.

## Verification

- Package manifest and type declarations report version 4.0.1 and MIT.
- `npm audit --json` reports zero known vulnerabilities after installation.
- The exporter golden test opens the generated archive and verifies native
  shape, table, chart, text, and image parts.
