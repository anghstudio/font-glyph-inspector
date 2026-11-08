from __future__ import annotations

import os
import re
import tempfile
import uuid
import unicodedata
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.recordingPen import RecordingPen, DecomposingRecordingPen

APP_VERSION = "0.3.0"
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
ALLOWED_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
UPLOAD_DIR = Path(tempfile.gettempdir()) / "anghstudio-font-glyph-inspector"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Font Glyph Inspector API",
    version=APP_VERSION,
    description="Inspect font glyphs, Unicode coverage, OpenType layout features, and font tables.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# A compact, intentionally readable block map. Unlisted codepoints are classified as Other.
UNICODE_BLOCKS = [
    (0x0000, 0x007F, "Basic Latin"), (0x0080, 0x00FF, "Latin-1 Supplement"),
    (0x0100, 0x017F, "Latin Extended-A"), (0x0180, 0x024F, "Latin Extended-B"),
    (0x0250, 0x02AF, "IPA Extensions"), (0x02B0, 0x02FF, "Spacing Modifier Letters"),
    (0x0300, 0x036F, "Combining Diacritical Marks"), (0x0370, 0x03FF, "Greek and Coptic"),
    (0x0400, 0x04FF, "Cyrillic"), (0x0500, 0x052F, "Cyrillic Supplement"),
    (0x0530, 0x058F, "Armenian"), (0x0590, 0x05FF, "Hebrew"),
    (0x0600, 0x06FF, "Arabic"), (0x0900, 0x097F, "Devanagari"),
    (0x2000, 0x206F, "General Punctuation"), (0x2070, 0x209F, "Superscripts and Subscripts"),
    (0x20A0, 0x20CF, "Currency Symbols"), (0x2100, 0x214F, "Letterlike Symbols"),
    (0x2190, 0x21FF, "Arrows"), (0x2200, 0x22FF, "Mathematical Operators"),
    (0x2300, 0x23FF, "Miscellaneous Technical"), (0x2500, 0x257F, "Box Drawing"),
    (0x2580, 0x259F, "Block Elements"), (0x25A0, 0x25FF, "Geometric Shapes"),
    (0x2600, 0x26FF, "Miscellaneous Symbols"), (0x2700, 0x27BF, "Dingbats"),
    (0x3040, 0x309F, "Hiragana"), (0x30A0, 0x30FF, "Katakana"),
    (0x4E00, 0x9FFF, "CJK Unified Ideographs"), (0xAC00, 0xD7AF, "Hangul Syllables"),
    (0x1F300, 0x1F5FF, "Miscellaneous Symbols and Pictographs"),
]


def unicode_block(codepoint: int) -> str:
    for start, end, name in UNICODE_BLOCKS:
        if start <= codepoint <= end:
            return name
    return "Other / Unclassified"


def name_records(font: TTFont) -> dict[str, str]:
    result: dict[str, str] = {}
    if "name" not in font:
        return result
    name_ids = {1: "family", 2: "subfamily", 4: "fullName", 6: "postScriptName", 16: "typographicFamily", 17: "typographicSubfamily"}
    for record in font["name"].names:
        key = name_ids.get(record.nameID)
        if key and key not in result:
            try:
                result[key] = record.toUnicode()
            except Exception:
                continue
    return result


def layout_summary(font: TTFont, tag: str) -> dict[str, Any]:
    if tag not in font:
        return {"present": False, "features": [], "lookupCount": 0}
    try:
        table = font[tag].table
        lookup_list = getattr(table, "LookupList", None)
        lookups = getattr(lookup_list, "Lookup", []) if lookup_list else []
        feature_list = getattr(table, "FeatureList", None)
        records = getattr(feature_list, "FeatureRecord", []) if feature_list else []
        features = []
        for record in records or []:
            feature = getattr(record, "Feature", None)
            features.append({
                "tag": getattr(record, "FeatureTag", "????"),
                "lookups": list(getattr(feature, "LookupListIndex", []) or []),
            })
        return {"present": True, "features": features, "lookupCount": len(lookups)}
    except Exception as exc:
        return {"present": True, "features": [], "lookupCount": 0, "warning": str(exc)}


def inspect_font(path: Path, font_id: str, original_name: str) -> dict[str, Any]:
    try:
        font = TTFont(str(path), lazy=False)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse this font: {exc}") from exc

    try:
        cmap = font.getBestCmap() or {}
        glyph_order = font.getGlyphOrder()
        glyph_ids = {name: index for index, name in enumerate(glyph_order)}
        mapped_names = set(cmap.values())
        glyphs = []
        for cp, glyph_name in sorted(cmap.items()):
            char = chr(cp)
            glyphs.append({
                "codepoint": cp,
                "unicode": f"U+{cp:04X}",
                "character": char,
                "glyphName": glyph_name,
                "unicodeName": unicodedata.name(char, "<unnamed>"),
                "block": unicode_block(cp),
                "category": unicodedata.category(char),
                "glyphId": glyph_ids.get(glyph_name),
            })

        metrics = {}
        if "head" in font:
            head = font["head"]
            metrics.update({"unitsPerEm": head.unitsPerEm, "fontRevision": head.fontRevision})
        if "hhea" in font:
            hhea = font["hhea"]
            metrics.update({"ascender": hhea.ascent, "descender": hhea.descent, "lineGap": hhea.lineGap})
        if "maxp" in font:
            metrics["numGlyphs"] = font["maxp"].numGlyphs

        tables = [{"tag": tag, "length": len(font.getTableData(tag))} for tag in sorted(font.keys()) if tag != "GlyphOrder"]
        return {
            "id": font_id,
            "filename": original_name,
            "metadata": name_records(font),
            "metrics": metrics,
            "statistics": {
                "mappedUnicode": len(glyphs),
                "totalGlyphs": len(glyph_order),
                "unmappedGlyphs": sum(1 for name in glyph_order if name not in mapped_names),
                "tableCount": len(tables),
            },
            "glyphs": glyphs,
            "unmappedGlyphs": [name for name in glyph_order if name not in mapped_names],
            "tables": tables,
            "opentype": {"GSUB": layout_summary(font, "GSUB"), "GPOS": layout_summary(font, "GPOS"), "GDEF": {"present": "GDEF" in font}},
        }
    finally:
        font.close()



def stored_font_path(font_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", font_id):
        raise HTTPException(status_code=404, detail="Font upload not found. Upload it again.")
    matches = list(UPLOAD_DIR.glob(f"{font_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Font upload not found. Upload it again.")
    return matches[0]


def inspect_glyph(path: Path, glyph_id: int) -> dict[str, Any]:
    try:
        font = TTFont(str(path), lazy=False)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse this font: {exc}") from exc
    try:
        order = font.getGlyphOrder()
        if glyph_id < 0 or glyph_id >= len(order):
            raise HTTPException(status_code=404, detail="Glyph ID is outside this font's glyph order.")
        glyph_name = order[glyph_id]
        glyph_set = font.getGlyphSet()
        glyph = glyph_set[glyph_name]
        bounds_pen = BoundsPen(glyph_set)
        glyph.draw(bounds_pen)
        path_pen = SVGPathPen(glyph_set)
        glyph.draw(path_pen)
        bounds = bounds_pen.bounds
        bbox = None
        if bounds:
            x_min, y_min, x_max, y_max = bounds
            bbox = {"xMin": x_min, "yMin": y_min, "xMax": x_max, "yMax": y_max,
                    "width": x_max - x_min, "height": y_max - y_min}

        advance_width = lsb = None
        if "hmtx" in font and glyph_name in font["hmtx"].metrics:
            advance_width, lsb = font["hmtx"].metrics[glyph_name]
        advance_height = tsb = None
        if "vmtx" in font and glyph_name in font["vmtx"].metrics:
            advance_height, tsb = font["vmtx"].metrics[glyph_name]

        contour_count = point_count = component_count = None
        outline_points: list[dict[str, Any]] = []
        contour_ends: list[int] = []
        point_source = "recorded-outline"
        if "glyf" in font and glyph_name in font["glyf"]:
            glyf = font["glyf"][glyph_name]
            if glyf.isComposite():
                component_count = len(glyf.components)
                # Decompose components so designers can inspect the actual assembled outline.
                recorder = DecomposingRecordingPen(glyph_set)
                glyph.draw(recorder)
                contour_index = 0
                point_index = 0
                for operation, args in recorder.value:
                    if operation == "moveTo":
                        x, y = args[0]
                        outline_points.append({"index": point_index, "contour": contour_index, "x": x, "y": y, "kind": "on-curve"})
                        point_index += 1
                    elif operation == "lineTo":
                        for x, y in args:
                            outline_points.append({"index": point_index, "contour": contour_index, "x": x, "y": y, "kind": "on-curve"}); point_index += 1
                    elif operation == "curveTo":
                        for i, (x, y) in enumerate(args):
                            kind = "on-curve" if i == len(args)-1 else "control"
                            outline_points.append({"index": point_index, "contour": contour_index, "x": x, "y": y, "kind": kind}); point_index += 1
                    elif operation == "qCurveTo":
                        pts = [pt for pt in args if isinstance(pt, tuple) and len(pt) == 2]
                        for i, (x, y) in enumerate(pts):
                            kind = "on-curve" if i == len(pts)-1 else "control"
                            outline_points.append({"index": point_index, "contour": contour_index, "x": x, "y": y, "kind": kind}); point_index += 1
                    if operation in {"closePath", "endPath"}:
                        contour_ends.append(point_index - 1); contour_index += 1
                contour_count = contour_index
                point_count = len(outline_points)
                point_source = "decomposed-components"
            else:
                component_count = 0
                coords = getattr(glyf, "coordinates", []) or []
                flags = getattr(glyf, "flags", []) or []
                ends = list(getattr(glyf, "endPtsOfContours", []) or [])
                contour_count = max(0, getattr(glyf, "numberOfContours", 0))
                point_count = len(coords)
                contour_index = 0
                end_set = set(ends)
                for index, (x, y) in enumerate(coords):
                    outline_points.append({"index": index, "contour": contour_index, "x": int(x), "y": int(y), "kind": "on-curve" if index < len(flags) and (flags[index] & 1) else "control"})
                    if index in end_set:
                        contour_ends.append(index); contour_index += 1
                point_source = "glyf-table"
        else:
            recorder = RecordingPen()
            glyph.draw(recorder)
            contour_index = 0
            point_index = 0
            for operation, args in recorder.value:
                pts = [pt for pt in args if isinstance(pt, tuple) and len(pt) == 2]
                if operation == "moveTo":
                    pts = pts[:1]
                for i, (x, y) in enumerate(pts):
                    kind = "control" if operation in {"curveTo", "qCurveTo"} and i < len(pts)-1 else "on-curve"
                    outline_points.append({"index": point_index, "contour": contour_index, "x": float(x), "y": float(y), "kind": kind}); point_index += 1
                if operation in {"closePath", "endPath"}:
                    contour_ends.append(point_index - 1); contour_index += 1
            contour_count = contour_index
            point_count = len(outline_points)

        units_per_em = font["head"].unitsPerEm if "head" in font else None
        return {
            "glyphId": glyph_id, "glyphName": glyph_name, "unitsPerEm": units_per_em,
            "advanceWidth": advance_width, "leftSideBearing": lsb,
            "advanceHeight": advance_height, "topSideBearing": tsb,
            "bounds": bbox, "contourCount": contour_count,
            "pointCount": point_count, "componentCount": component_count,
            "outlinePath": path_pen.getCommands(),
            "outlineAvailable": bool(path_pen.getCommands()),
            "outlinePoints": outline_points,
            "contourEnds": contour_ends,
            "pointSource": point_source,
        }
    finally:
        font.close()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "name": "Font Glyph Inspector API", "version": APP_VERSION}


@app.post("/api/fonts")
async def upload_font(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = Path((file.filename or "font").replace("\\", "/")).name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Supported formats: TTF, OTF, WOFF, WOFF2.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum upload size is 30 MB.")

    font_id = uuid.uuid4().hex
    stored_path = UPLOAD_DIR / f"{font_id}{suffix}"
    stored_path.write_bytes(content)
    try:
        return inspect_font(stored_path, font_id, filename)
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise


@app.get("/api/fonts/{font_id}/file")
def get_font_file(font_id: str):
    path = stored_font_path(font_id)
    media = {".ttf": "font/ttf", ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2"}.get(path.suffix, "application/octet-stream")
    return FileResponse(path, media_type=media, filename=path.name)


@app.get("/api/fonts/{font_id}/glyphs/{glyph_id}")
def get_glyph_details(font_id: str, glyph_id: int) -> dict[str, Any]:
    if glyph_id < 0:
        raise HTTPException(status_code=404, detail="Glyph ID must be zero or greater.")
    return inspect_glyph(stored_font_path(font_id), glyph_id)
