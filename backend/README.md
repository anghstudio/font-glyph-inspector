# Backend

FastAPI + FontTools API for local font inspection.

## Run

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## v0.4 contour analysis

`GET /api/fonts/{font_id}/glyphs/{glyph_id}` preserves all v0.3 fields and adds `contourAnalysis`:

- Normalized line, quadratic, and cubic segments with start/control/end coordinates.
- Contour closed state and direction in font coordinates (Y-up).
- Signed area estimated from 12-step Bézier flattening.
- Conservative boundary-intersection diagnostics using flattened segments.

This is read-only analysis. Intersection diagnostics are not a filled-area overlap test, and the sampled area/intersection results are approximations. TrueType implied on-curve points and composite components are handled by FontTools' `BasePen` drawing pipeline.


### Font diagnostics (v0.6.1)
`GET /api/fonts/{font_id}/diagnostics` returns a read-only integrity report with summary counts and structured findings. Current checks cover SFNT table presence/ranges/checksums where stored by the format, core metrics, Unicode cmap consistency, TrueType composite references, `loca` offsets, and glyph vertical bounds against `hhea` and OS/2 metrics for TrueType, CFF, and CFF2 outlines. WOFF2 checksum fields that are not exposed by the format are skipped rather than reported as font defects.


### Font completeness and quality (v0.7.0)
`GET /api/fonts/{font_id}/quality` returns character coverage groups, missing Unicode characters, basic horizontal metric checks, and structured quality findings. The baseline covers Latin uppercase/lowercase, numerals, punctuation, common symbols, and Latin-1 accented letters. The profile is MyFonts-inspired and intentionally disclosed as a practical checklist rather than an official marketplace certification.
