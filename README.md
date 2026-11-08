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
- Review GSUB and GPOS feature tags and lookup counts, plus GDEF presence.
- View a live specimen using the uploaded font.
- Copy filtered characters and export a Unicode map as TSV.
- Review glyphs present in glyph order but absent from the best Unicode cmap.
- Select a mapped glyph to inspect its outline path, bounding box, advance width, side bearings, contour count, point count, and composite component count where supported.
- Inspect TrueType on-curve and off-curve points, decomposed component outlines, and recorded CFF/CFF2 outline points.
- Toggle point markers, control points, and metric guides in the glyph view.
- Review point indices, contour indices, and X/Y coordinates in the outline point table.
- Export an individual glyph outline as SVG.

### Project status

**Early development — v0.3.0.** This is an initial web migration. The original desktop tool contains deeper lookup decoding and Windows installed-font discovery that are not yet fully represented in this web version. Contributions and bug reports are welcome.

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
| `GET` | `/api/fonts/{id}/glyphs/{glyph_id}` | Inspect a glyph outline and horizontal/vertical metrics |

Uploads are limited to 30 MB and stored in the operating system's temporary directory. The initial version does not yet include user accounts, persistent storage, automatic cleanup, or production deployment hardening. Do not expose this development API publicly without adding appropriate rate limiting, upload lifecycle management, and operational security controls.

## Roadmap

### Phase 1 — Core Inspector (implemented)
- [x] Font upload, metadata, Unicode map, OpenType overview, table inventory, and specimen preview.
- [x] Search, Unicode block filtering, character copy, TSV export, and unmapped glyph list.

### Phase 2 — Glyph Engineering (v0.3.0)
- [x] Per-glyph outline path and bounding box inspection.
- [x] Advance width, left side bearing, units per em, and TrueType contour / point / component counts.
- [ ] Add point-level editing and visual on-curve / off-curve point labels.

### Phase 3 — OpenType Engineering
- [ ] Decode GSUB substitutions and GPOS positioning lookups into readable records.
- [ ] Inspect kerning pairs, mark attachment, ligatures, alternates, scripts, and language systems.

### Phase 4 — Variable Font Lab
- [ ] Inspect fvar axes, named instances, avar mappings, and variation metadata.
- [ ] Add interactive axis controls to the specimen preview.

### Phase 5 — Font Comparison
- [ ] Compare two fonts' glyph coverage, names, metrics, tables, and metadata.
- [ ] Highlight glyph and metric differences.

### Phase 6 — Validation & Export
- [ ] Add structural validation and actionable diagnostics.
- [ ] Export JSON / CSV data and printable inspection reports.

### Phase 7 — Workspace & Release
- [ ] Add batch inspection, recent sessions, and upload cleanup.
- [ ] Improve accessibility, automated tests, browser compatibility, and deployment hardening.

Editing and saving font binaries is a later, separately scoped capability. The initial roadmap focuses on trustworthy inspection before introducing write operations.

## Contributing

Issues and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

## License

Released under the [MIT License](LICENSE).

---

Made for type people. **Anghstudio**
