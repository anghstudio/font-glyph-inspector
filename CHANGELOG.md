# Changelog

## 0.3.0 — Advanced Glyph Inspector
- Added outline point extraction for TrueType simple glyphs, including on-curve and off-curve classification.
- Added decomposed component point inspection for composite TrueType glyphs.
- Added recorded outline point support for CFF/CFF2 glyphs.
- Added interactive point/control-point and metrics-guide overlays.
- Added a coordinate table for glyph outline points.
- Added individual glyph SVG export.

# Changelog

## 0.2.0 — Glyph Engineering foundation

- Added a per-glyph inspection API endpoint.
- Added glyph outline path and bounding-box extraction through FontTools pens.
- Added advance width, left side bearing, units per em, and optional vertical metrics.
- Added TrueType contour, point, and composite-component counts where available.
- Expanded the glyph detail panel while preserving the existing editorial interface.
- Updated the project roadmap and API documentation.

## 0.1.0 — Initial web migration

- Added FastAPI font upload and inspection API.
- Added React/Vite responsive interface.
- Added glyph map, Unicode search/filter, specimen preview, metadata/statistics, OpenType feature overview, table inventory, unmapped glyph list, and TSV export.
- Added MIT license and contribution documentation.
