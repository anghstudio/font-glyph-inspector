# Font Glyph Inspector

## v0.8.1 — Variable Font Validation & Interpolation Analysis
The **VF Validation** tab checks axis ranges/defaults, named-instance coordinates, `avar` mappings, and `STAT` axis references. It uses FontTools `varLib.instancer` to generate real static instances at representative locations (default, axis endpoints, named instances, and selected multi-axis corners), then checks generated glyph/component references and horizontal metrics. This is structural and sampled validation—not proof of smooth visual interpolation or design intent.

## v0.8.0 — Variable Font Lab / Inspector
The **Variable** tab reads `fvar` axes and named instances, `avar` normalization maps, `STAT` design-axis metadata, and the presence of `gvar`, `CFF2`, `HVAR`, `VVAR`, `MVAR`, and `cvar`. Interactive sliders and named-instance presets drive a live browser specimen with CSS `font-variation-settings`. This is a read-only inspector: it does not edit or export modified font binaries. Static fonts are identified explicitly.

## v0.7.0 — Font Completeness & Quality Analyzer
The **Quality** tab evaluates Unicode character coverage across uppercase, lowercase, numerals, basic punctuation, common symbols, and extended Latin accents. It reports missing core characters as warnings, extended coverage gaps as informational findings, checks horizontal metric records, and exports a JSON report. Coverage is determined from Unicode `cmap` mappings; it does not verify whether a glyph drawing visually matches its character. The profile is a practical **MyFonts-inspired** Latin baseline, not an official MyFonts certification or exhaustive marketplace submission specification.

## v0.6.1 — Diagnostics coverage and format handling

- Detects glyphs extending beyond `hhea` ascender/descender for TrueType, CFF, and CFF2 outlines.
- Reports glyphs outside OS/2 Windows vertical metrics.
- Fixes warning/error summary counts.
- Handles WOFF2 checksum metadata without emitting false checksum-unavailable warnings.

<div align="center">
  <h1>Font Glyph Inspector</h1>
  <p><strong>A closer look at the structure behind every typeface.</strong></p>
  <p>Inspect glyphs, map Unicode coverage, and explore OpenType features in one workspace.</p>
  <p><code>Python</code> · <code>FastAPI</code> · <code>FontTools</code> · <code>React</code> · <code>Vite</code></p>
</div>

---

## Overview

Font Glyph Inspector is an open-source web application for type designers and font developers. It is based on Anghstudio's original Python/Tkinter Font Glyph Inspector and is being migrated to a browser-based interface with a Python font-analysis API.

### Current features

- Upload and inspect TTF, OTF, WOFF, and WOFF2 files (WOFF/WOFF2 support depends on the installed FontTools Brotli extras).
- Browse mapped Unicode characters with glyph names, codepoints, Unicode blocks, and glyph IDs.
- Search and filter the glyph map.
- Inspect font metadata, basic vertical metrics, glyph counts, and OpenType table inventory.
- Decode GSUB substitutions, ligature component sequences, GPOS single positioning and explicit pair-positioning kerning records.
- Inspect OpenType lookup types, flags, subtables, and feature-to-lookup relationships.
- View a live specimen using the uploaded font.
- Copy filtered characters and export a Unicode map as TSV.
- Review glyphs present in glyph order but absent from the best Unicode cmap.
- Inspect variable-font `fvar` axes, named instances, `avar` mappings, `STAT` axes, and variation-table inventory.
- Validate variable-font axis metadata and exercise representative locations by generating actual static instances with FontTools.
- Test axis values and named instances in a live browser specimen without changing the source font.
- Select a mapped glyph to inspect its outline path, bounding box, advance width, side bearings, contour count, point count, and composite component count where supported.
- Inspect TrueType on-curve and off-curve points, decomposed component outlines, and recorded CFF/CFF2 outline points.
- Toggle point markers, control points, and metric guides in the glyph view.
- Review point indices, contour indices, and X/Y coordinates in the outline point table.
- Export an individual glyph outline as SVG.
- Inspect normalized line, quadratic Bézier, and cubic Bézier segments with control points.
- Review contour start points, closed/open state, winding direction, and sampled signed area.
- Run conservative self-intersection and contour-boundary intersection diagnostics.

### Project status

**Early development — v0.8.1.** This is an evolving web-based font inspection workspace. The original desktop tool contains deeper lookup decoding and Windows installed-font discovery that are not yet fully represented in this web version. Contributions and bug reports are welcome.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer
- npm

## Run locally (Windows PowerShell)

Open two terminals from the repository root.

### 1. Start the API

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API health endpoint is available at <http://localhost:8000/api/health> and interactive API docs at <http://localhost:8000/docs>.

### 2. Start the web app

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

## Run locally (macOS / Linux)

### API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Web app

```bash
cd frontend
npm install
npm run dev
```

## Configuration

The frontend uses `http://localhost:8000` as its default API URL. To point it elsewhere, create `frontend/.env.local`:

```env
VITE_API_URL=http://localhost:8000
```

The backend accepts browser origins from `CORS_ORIGINS` (comma-separated). See `.env.example`.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/fonts` | Upload and inspect a font (`multipart/form-data`, field `file`) |
| `GET` | `/api/fonts/{id}/file` | Serve the uploaded font for live specimen preview |
| `GET` | `/api/fonts/{id}/glyphs/{glyph_id}` | Inspect a glyph outline, metrics, points, Bézier segments, and contour diagnostics |
| `GET` | `/api/fonts/{id}/variable` | Inspect variable-font axes, instances, and variation metadata |
| `GET` | `/api/fonts/{id}/variable-validation` | Validate variable-font metadata and generate representative static instances |

Uploads are limited to 30 MB and stored in the operating system's temporary directory. The initial version does not yet include user accounts, persistent storage, automatic cleanup, or production deployment hardening. Do not expose this development API publicly without adding appropriate rate limiting, upload lifecycle management, and operational security controls.

## Roadmap

### Phase 1 — Core Inspector (implemented)
- [x] Font upload, metadata, Unicode map, OpenType overview, table inventory, and specimen preview.
- [x] Search, Unicode block filtering, character copy, TSV export, and unmapped glyph list.

### Phase 2 — Glyph Engineering (v0.3.0)
- [x] Per-glyph outline path and bounding box inspection.
- [x] Advance width, left side bearing, units per em, and TrueType contour / point / component counts.
- [x] Add visual on-curve / off-curve point overlays and point table.


### Phase 2.1 — Bézier & Contour Lab (v0.4.0)
- [x] Normalize line, quadratic, and cubic outline segments.
- [x] Visualize Bézier segments and control polygons.
- [x] Inspect contour starts, open/closed state, direction, and sampled signed area.
- [x] Add conservative boundary intersection diagnostics.
- [ ] Add robust filled-area overlap detection and deeper curve intersection solving.

### Phase 3 — OpenType Engineering (v0.5.0)
- [x] Decode common GSUB single, multiple, alternate, and ligature substitutions.
- [x] Decode GPOS single positioning and explicit pair-adjustment records.
- [x] Inspect lookup types, flags, subtables, and feature-to-lookup mappings.
- [ ] Expand class-based kerning matrices and decode contextual, mark-attachment, script, and language-system structures.

### Phase 4 — Variable Font Lab & Validation (v0.8.1)
- [x] Inspect fvar axes, named instances, avar mappings, STAT axes, and variation-table inventory.
- [x] Add interactive axis controls and named-instance presets to the specimen preview.
- [x] Identify static fonts and explain why axis controls are unavailable.
- [ ] Add deeper STAT AxisValue format decoding and broader variable-font interpolation sampling.
- [x] Validate axis ranges, named instances, avar mappings, and STAT axis references.
- [x] Generate representative static instances and inspect structural consistency.
- [ ] Add side-by-side visual comparison of selected interpolation locations.

### Phase 5 — Font Comparison
- [ ] Compare two fonts' glyph coverage, names, metrics, tables, and metadata.
- [ ] Highlight glyph and metric differences.

### Phase 6 — Validation & Export
- [x] Add structural validation and actionable diagnostics.
- [ ] Export JSON / CSV data and printable inspection reports.

### Phase 7 — Workspace & Release
- [ ] Add batch inspection, recent sessions, and upload cleanup.
- [ ] Improve accessibility, automated tests, browser compatibility, and deployment hardening.

Contour signed area and boundary intersections currently use sampled approximations; boundary intersections do not prove filled-area overlap. Editing and saving font binaries is a later, separately scoped capability. The initial roadmap focuses on trustworthy inspection before introducing write operations.

## Contributing

Issues and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

## License

Released under the [MIT License](LICENSE).

---

Made for type people. **Anghstudio**


## OpenType GPOS class-based pair positioning (v0.5.1)

GPOS PairPos Format 2 class matrices are expanded into glyph-pair records for inspection. Both Value 1 and Value 2 expose X/Y Placement and X/Y Advance. Explicit zero values and negative adjustments are retained. The backend caps each class-based subtable at 5,000 expanded pairs; the interface paginates displayed records in groups of 100. When the cap is reached, the interface reports that the expansion is partial.


## v0.6.1 — Diagnostics coverage and format handling
The Diagnostics tab performs read-only checks for required/common tables, SFNT table ranges and checksums where stored by the file format, core metrics, Unicode cmap mappings, TrueType composite component references, and `loca` offsets. It also checks actual glyph outline bounds against `hhea` ascender/descender and OS/2 Windows vertical metrics across TrueType, CFF, and CFF2 outlines. Findings are classified as Error, Warning, or Info and include their location and recommended follow-up. WOFF2 directories do not expose the same per-table checksum field as ordinary SFNT directories, so unavailable WOFF2 checksums are not reported as font defects. A clean report means no issue was detected by the implemented checks; it is not a claim of complete OpenType specification conformance.


## v0.8.1 — Variable Font Validation & Interpolation Analysis
The **VF Validation** tab checks axis ranges/defaults, named-instance coordinates, `avar` mappings, and `STAT` axis references. It uses FontTools `varLib.instancer` to generate real static instances at representative locations (default, axis endpoints, named instances, and selected multi-axis corners), then checks generated glyph/component references and horizontal metrics. This is structural and sampled validation—not proof of smooth visual interpolation or design intent.

## v0.8.0 — Variable Font Lab / Inspector
The **Variable** tab reads `fvar` axes and named instances, `avar` normalization maps, `STAT` design-axis metadata, and the presence of `gvar`, `CFF2`, `HVAR`, `VVAR`, `MVAR`, and `cvar`. Interactive sliders and named-instance presets drive a live browser specimen with CSS `font-variation-settings`. This is a read-only inspector: it does not edit or export modified font binaries. Static fonts are identified explicitly.

## v0.7.0 — Font Completeness & Quality Analyzer
The new **Quality** tab evaluates a practical Latin production checklist: uppercase, lowercase, numerals, basic punctuation, common symbols, and extended Latin accents. It reports missing core characters as warnings, missing extended characters as informational findings, checks horizontal metric records, and exports a JSON report. Coverage is determined from Unicode `cmap` mappings; it does not verify whether a glyph drawing visually matches its character. The checklist is MyFonts-inspired, not an official MyFonts certification or a complete marketplace submission specification.
