Phosphor local icon pack
========================

This directory stores locally curated SVG icons for slide generation when image
generation is disabled.

Source archive
--------------
- Imported from `D:/work/Gapo/phosphor-icons.zip`
- Curated subset extracted into `phosphor/SVGs/regular/`
- License file copied to `phosphor/LICENSE`

Why local icons
---------------
- deterministic output (no network dependency)
- no runtime image generation cost
- easy semantic mapping from slide role/topic -> icon

Manifest
--------
- `phosphor/manifest.json` maps semantic keys to SVG filenames.
- Keep this map stable for reproducible generation output.

Selection policy
----------------
- Use SVG only (crisp scaling in editor/export).
- Prefer neutral, presentation-safe concepts:
  workflow, data, analytics, team, security, launch, quality, platform.
