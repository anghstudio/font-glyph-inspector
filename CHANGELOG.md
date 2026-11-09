# Changelog

## 0.8.1 — Variable Font Validation & Interpolation Analysis
- Added structural validation for fvar axis ranges, default coordinates, unique tags, named-instance coordinates, avar mappings, and STAT axis references.
- Added real static-instance generation through FontTools varLib instancer at default, per-axis endpoints, named instances, and a bounded set of multi-axis corners.
- Added generated-instance checks for glyph count, TrueType composite references, and horizontal metrics.
- Added a dedicated VF Validation tab with severity-coded findings, per-location pass/fail results, test scope, and explicit limitations.
- Added an API endpoint at `/api/fonts/{id}/variable-validation`.
- Added automated tests for representative instance generation and static-font handling.
- Clarifies that structural instancing success does not certify smooth visual interpolation or design intent.

## 0.8.0 — Variable Font Lab / Inspector
- Added a variable-font inspection endpoint for fvar axis definitions and named instances.
- Added avar normalized-coordinate segment mappings and STAT design-axis metadata.
- Added variation-table inventory for fvar, avar, STAT, gvar, CFF2, HVAR, VVAR, MVAR, and cvar.
- Added interactive axis sliders, default reset, and named-instance presets for the live specimen.
- Added explicit static-font detection and read-only scope disclosure.
- Updated frontend and API versions to 0.8.0.

## 0.7.0 — Font Completeness & Quality Analyzer
- Added a dedicated Quality tab with a practical MyFonts-inspired Latin coverage profile.
- Checks uppercase, lowercase, numerals, basic punctuation, common symbols, and extended Latin characters through the best Unicode cmap.
- Reports required-profile gaps as warnings and extended coverage gaps as informational findings.
- Added horizontal metric completeness checks and informational zero-advance reporting.
- Added JSON quality report export.
- Clarifies that Unicode mapping checks do not assess visual glyph correctness and that the profile is not an official marketplace certification.

- Fixed warning/error summary counters.
- Added vertical outline-bound checks for TrueType, CFF, and CFF2 glyph sets.
- Avoided false WOFF2 checksum-unavailable warnings where the directory does not expose SFNT checksums.
- Expanded diagnostics scope reporting.
