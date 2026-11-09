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
from .contour_analysis import analyze_glyph_contours

APP_VERSION = "0.8.1"
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




def _value_record(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    fields = ("XPlacement", "YPlacement", "XAdvance", "YAdvance")
    return {key: getattr(value, key, 0) or 0 for key in fields}


def _coverage_names(coverage: Any) -> list[str]:
    return list(getattr(coverage, "glyphs", []) or getattr(coverage, "Glyphs", []) or []) if coverage else []


def _class_defs(class_def: Any) -> dict[str, int]:
    return dict(getattr(class_def, "classDefs", {}) or {}) if class_def else {}


def _decode_gsub_subtable(subtable: Any, lookup_type: int) -> dict[str, Any]:
    result: dict[str, Any] = {"type": lookup_type}
    if lookup_type == 7:  # ExtensionSubst
        actual = getattr(subtable, "ExtensionLookupType", 0)
        nested = getattr(subtable, "ExtSubTable", None)
        result["extensionLookupType"] = actual
        result["extension"] = _decode_gsub_subtable(nested, actual) if nested else {}
    elif lookup_type == 1:
        mapping = getattr(subtable, "mapping", None)
        if mapping is not None:
            result["substitutions"] = [{"from": a, "to": b} for a, b in mapping.items()]
        else:
            cov = _coverage_names(getattr(subtable, "Coverage", None))
            substitutes = list(getattr(subtable, "Substitute", []) or [])
            result["substitutions"] = [{"from": a, "to": b} for a, b in zip(cov, substitutes)]
    elif lookup_type in (2, 3):
        mapping = getattr(subtable, "mapping", None)
        if mapping is not None:
            result["substitutions"] = [{"from": key, "to": (list(value) if isinstance(value, (list, tuple)) else value)} for key, value in mapping.items()]
        else:
            cov = _coverage_names(getattr(subtable, "Coverage", None))
            sets = getattr(subtable, "Sequence" if lookup_type == 2 else "AlternateSet", []) or []
            field = "Variant"
            result["substitutions"] = [{"from": a, "to": list(getattr(st, field, []) or [])} for a, st in zip(cov, sets)]
    elif lookup_type == 4:
        ligatures = []
        mapping = getattr(subtable, "ligatures", None)
        if mapping is not None:
            for first, lig_list in mapping.items():
                for lig in lig_list:
                    components = [first, *(getattr(lig, "Component", []) or [])]
                    ligatures.append({"components": components, "input": " + ".join(components), "result": getattr(lig, "LigGlyph", "")})
        else:
            cov = _coverage_names(getattr(subtable, "Coverage", None))
            sets = getattr(subtable, "LigatureSet", []) or []
            for first, lig_set in zip(cov, sets):
                for lig in getattr(lig_set, "Ligature", []) or []:
                    components = [first, *(getattr(lig, "Component", []) or [])]
                    ligatures.append({"components": components, "input": " + ".join(components), "result": getattr(lig, "LigGlyph", "")})
        result["ligatures"] = ligatures
    else:
        result["coverage"] = _coverage_names(getattr(subtable, "Coverage", None))
        result["description"] = "Contextual or specialized substitution; raw structured data is summarized by coverage."
    return result


MAX_CLASS_PAIR_EXPANSION = 5000


def _decode_gpos_subtable(subtable: Any, lookup_type: int, glyph_order: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"type": lookup_type}
    if lookup_type == 9:
        actual = getattr(subtable, "ExtensionLookupType", 0)
        nested = getattr(subtable, "ExtSubTable", None)
        result["extensionLookupType"] = actual
        result["extension"] = _decode_gpos_subtable(nested, actual, glyph_order) if nested else {}
    elif lookup_type == 1:
        cov = _coverage_names(getattr(subtable, "Coverage", None))
        fmt = getattr(subtable, "Format", 1)
        if fmt == 1:
            value = _value_record(getattr(subtable, "Value", None))
            result["positioning"] = [{"glyph": g, "value": value} for g in cov]
        else:
            values = getattr(subtable, "Value", []) or []
            result["positioning"] = [{"glyph": g, "value": _value_record(v)} for g, v in zip(cov, values)]
    elif lookup_type == 2:
        cov = _coverage_names(getattr(subtable, "Coverage", None))
        pair_sets = getattr(subtable, "PairSet", []) or []
        pairs = []
        for first, pair_set in zip(cov, pair_sets):
            for record in getattr(pair_set, "PairValueRecord", []) or []:
                pairs.append({
                    "left": first, "right": getattr(record, "SecondGlyph", ""),
                    "value1": _value_record(getattr(record, "Value1", None)),
                    "value2": _value_record(getattr(record, "Value2", None)),
                })
        fmt = getattr(subtable, "Format", None)
        if fmt == 2:
            class_def1 = _class_defs(getattr(subtable, "ClassDef1", None))
            class_def2 = _class_defs(getattr(subtable, "ClassDef2", None))
            class1_records = getattr(subtable, "Class1Record", []) or []
            all_glyphs = list(glyph_order or [])
            left_glyphs = cov
            total = 0
            expanded = []
            truncated = False
            for left in left_glyphs:
                class1_index = class_def1.get(left, 0)
                if class1_index >= len(class1_records):
                    continue
                class2_records = getattr(class1_records[class1_index], "Class2Record", []) or []
                for right in all_glyphs:
                    class2_index = class_def2.get(right, 0)
                    if class2_index >= len(class2_records):
                        continue
                    matrix_record = class2_records[class2_index]
                    raw1 = getattr(matrix_record, "Value1", None)
                    raw2 = getattr(matrix_record, "Value2", None)
                    # None means no ValueRecord; a present all-zero record is meaningful and retained.
                    if raw1 is None and raw2 is None:
                        continue
                    total += 1
                    if len(expanded) < MAX_CLASS_PAIR_EXPANSION:
                        expanded.append({
                            "left": left, "right": right,
                            "value1": _value_record(raw1), "value2": _value_record(raw2),
                            "class1": class1_index, "class2": class2_index,
                        })
                    else:
                        truncated = True
            pairs = expanded
            result["class1GlyphCount"] = len({g for g in left_glyphs})
            result["class2GlyphCount"] = len(all_glyphs)
            result["class1Count"] = len(class1_records)
            result["class2Count"] = max((len(getattr(r, "Class2Record", []) or []) for r in class1_records), default=0)
            result["classPairMatrix"] = "Class-based pair positioning expanded from the OpenType class matrix."
            result["expandedPairCount"] = len(expanded)
            result["totalPairCount"] = total
            result["expansionTruncated"] = truncated
            result["expansionLimit"] = MAX_CLASS_PAIR_EXPANSION
        result["kerningPairs"] = pairs
        result["pairCount"] = len(pairs)
        result["format"] = fmt
    else:
        result["coverage"] = _coverage_names(getattr(subtable, "Coverage", None))
        result["description"] = "Specialized positioning lookup; coverage and lookup metadata are available."
    return result


def inspect_opentype(path: Path) -> dict[str, Any]:
    font = TTFont(str(path), lazy=False)
    try:
        output: dict[str, Any] = {}
        for tag in ("GSUB", "GPOS"):
            if tag not in font:
                output[tag] = {"present": False, "lookups": [], "features": []}
                continue
            table = font[tag].table
            lookup_list = getattr(table, "LookupList", None)
            lookup_objects = getattr(lookup_list, "Lookup", []) if lookup_list else []
            lookups = []
            for index, lookup in enumerate(lookup_objects):
                lookup_type = getattr(lookup, "LookupType", 0)
                subtables = []
                for sub_index, subtable in enumerate(getattr(lookup, "SubTable", []) or []):
                    try:
                        decoded = (_decode_gsub_subtable(subtable, lookup_type) if tag == "GSUB"
                                   else _decode_gpos_subtable(subtable, lookup_type, font.getGlyphOrder()))
                        decoded["subtableIndex"] = sub_index
                    except Exception as exc:
                        decoded = {"subtableIndex": sub_index, "warning": str(exc)}
                    subtables.append(decoded)
                lookups.append({
                    "index": index, "type": lookup_type,
                    "typeName": (GSUB_LOOKUP_NAMES if tag == "GSUB" else GPOS_LOOKUP_NAMES).get(lookup_type, "Unknown"),
                    "flag": getattr(lookup, "LookupFlag", 0),
                    "markFilteringSet": getattr(lookup, "MarkFilteringSet", None),
                    "subtableCount": len(subtables), "subtables": subtables,
                })
            feature_records = getattr(getattr(table, "FeatureList", None), "FeatureRecord", []) or []
            features = []
            for record in feature_records:
                feature = getattr(record, "Feature", None)
                features.append({
                    "tag": getattr(record, "FeatureTag", "????"),
                    "lookupIndices": list(getattr(feature, "LookupListIndex", []) or []),
                })
            output[tag] = {"present": True, "lookups": lookups, "features": features}
        return output
    finally:
        font.close()


GSUB_LOOKUP_NAMES = {
    1: "Single substitution", 2: "Multiple substitution", 3: "Alternate substitution",
    4: "Ligature substitution", 5: "Contextual substitution", 6: "Chaining contextual substitution",
    7: "Extension substitution", 8: "Reverse chaining single substitution",
}
GPOS_LOOKUP_NAMES = {
    1: "Single positioning", 2: "Pair adjustment", 3: "Cursive attachment",
    4: "Mark-to-base attachment", 5: "Mark-to-ligature attachment", 6: "Mark-to-mark attachment",
    7: "Contextual positioning", 8: "Chaining contextual positioning", 9: "Extension positioning",
}



# Structure and integrity diagnostics. Findings are evidence-based; optional tables are
# informational rather than errors because valid fonts may omit them.
def inspect_diagnostics(path: Path) -> dict[str, Any]:
    from fontTools.ttLib.sfnt import calcChecksum

    font = TTFont(str(path), lazy=False, recalcBBoxes=False, recalcTimestamp=False)
    findings: list[dict[str, Any]] = []
    checks = {"passed": 0, "warnings": 0, "errors": 0, "info": 0}

    def add(severity: str, code: str, location: str, message: str, recommendation: str = "") -> None:
        findings.append({"severity": severity, "code": code, "location": location,
                         "message": message, "recommendation": recommendation})
        counter_key = {"warning": "warnings", "error": "errors"}.get(severity, severity)
        if counter_key in checks:
            checks[counter_key] += 1

    try:
        tags = [tag for tag in font.keys() if tag != "GlyphOrder"]
        required = {"head", "maxp", "cmap", "name"}
        recommended = {"hhea", "hmtx", "OS/2", "post"}
        for tag in sorted(required - set(tags)):
            add("error", "MISSING_REQUIRED_TABLE", tag, f"Required table {tag} is missing.",
                "Verify the font export and regenerate the font.")
        for tag in sorted(recommended - set(tags)):
            add("warning", "MISSING_COMMON_TABLE", tag, f"Common table {tag} is absent.",
                "Confirm whether this table is required for the font's intended outline flavor and use.")

        reader = getattr(font, "reader", None)
        if reader is not None:
            seen_ranges: list[tuple[int, int, str]] = []
            for tag, entry in getattr(reader, "tables", {}).items():
                offset, length = int(entry.offset), int(entry.length)
                if offset < 0 or length < 0:
                    add("error", "INVALID_TABLE_RANGE", tag, "Table has a negative offset or length.")
                if length:
                    for old_start, old_end, old_tag in seen_ranges:
                        if max(offset, old_start) < min(offset + length, old_end):
                            add("warning", "OVERLAPPING_TABLE_DATA", tag,
                                f"Table data overlaps the byte range of {old_tag}.",
                                "Inspect the SFNT directory and confirm the file was generated correctly.")
                    seen_ranges.append((offset, offset + length, tag))
                expected_value = getattr(entry, "checkSum", None)
                if expected_value is None:
                    expected_value = getattr(entry, "origChecksum", None)
                if expected_value is None and getattr(font, "flavor", None) == "woff2":
                    # WOFF2's transformed directory entries do not expose the SFNT checkSum field.
                    # This is a format limitation, not a damaged-font warning.
                    continue
                try:
                    raw = font.getTableData(tag)
                    actual = calcChecksum(raw)
                    expected = int(expected_value)
                    # head.checkSumAdjustment is intentionally excluded from a head table checksum comparison.
                    if tag == "head" and len(raw) >= 12:
                        raw = raw[:8] + b"\0\0\0\0" + raw[12:]
                        actual = calcChecksum(raw)
                    if actual != expected:
                        add("warning", "TABLE_CHECKSUM_MISMATCH", tag,
                            f"Stored checksum 0x{expected:08X} differs from calculated 0x{actual:08X}.",
                            "Rebuild the font with a standards-compliant font compiler.")
                except Exception as exc:
                    add("warning", "TABLE_CHECKSUM_UNAVAILABLE", tag, f"Could not verify checksum: {exc}")

        glyph_order = font.getGlyphOrder()
        glyph_count = len(glyph_order)
        if "maxp" in font and int(font["maxp"].numGlyphs) != glyph_count:
            add("error", "GLYPH_COUNT_MISMATCH", "maxp.numGlyphs",
                f"maxp declares {font['maxp'].numGlyphs} glyphs but glyph order contains {glyph_count}.")
        else:
            checks["passed"] += 1

        if "head" in font:
            upm = int(font["head"].unitsPerEm)
            if not 16 <= upm <= 16384:
                add("error", "INVALID_UNITS_PER_EM", "head.unitsPerEm",
                    f"Units per em value {upm} is outside the OpenType range 16–16384.")
            else:
                checks["passed"] += 1
            bbox = (font["head"].xMin, font["head"].yMin, font["head"].xMax, font["head"].yMax)
            if bbox[0] > bbox[2] or bbox[1] > bbox[3]:
                add("error", "INVALID_FONT_BOUNDS", "head", f"Global bounding box is inverted: {bbox}.")

        if "hhea" in font and "hmtx" in font:
            metrics = getattr(font["hmtx"], "metrics", {})
            missing_metrics = [g for g in glyph_order if g not in metrics]
            if missing_metrics:
                add("error", "MISSING_HORIZONTAL_METRICS", "hmtx",
                    f"{len(missing_metrics)} glyph(s) have no horizontal metric record; examples: {', '.join(missing_metrics[:8])}.")
            else:
                checks["passed"] += 1
            declared = int(font["hhea"].numberOfHMetrics)
            if declared < 1 or declared > glyph_count:
                add("error", "INVALID_NUMBER_OF_HMETRICS", "hhea.numberOfHMetrics",
                    f"Declared {declared} long metrics for {glyph_count} glyphs.")

        if "cmap" in font:
            cmap_tables = [t for t in font["cmap"].tables if t.isUnicode()]
            best = font.getBestCmap() or {}
            if not cmap_tables:
                add("warning", "NO_UNICODE_CMAP", "cmap", "No Unicode cmap subtable was found.")
            else:
                checks["passed"] += 1
            invalid = [(cp, name) for cp, name in best.items() if cp < 0 or cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF or name not in glyph_order]
            if invalid:
                add("error", "INVALID_CMAP_MAPPING", "cmap",
                    f"{len(invalid)} mapping(s) use an invalid Unicode scalar or unknown glyph name.",
                    "Review cmap records and glyph order consistency.")
            # Duplicate codepoints across subtables are normal when platform/encoding records mirror one another.
            codepoints = [set(t.cmap) for t in cmap_tables]
            if len(codepoints) > 1 and any(a != b for a, b in zip(codepoints, codepoints[1:])):
                add("info", "CMAP_SUBTABLE_VARIATION", "cmap",
                    "Unicode cmap subtables expose different coverage; this can be intentional for format/platform compatibility.")

        # Check actual outline bounds through the public glyphSet API. This works for
        # TrueType glyf as well as CFF/CFF2 outlines and composite glyphs.
        if "hhea" in font:
            glyph_set = font.getGlyphSet()
            ascender = int(font["hhea"].ascent)
            descender = int(font["hhea"].descent)
            above: list[tuple[str, int]] = []
            below: list[tuple[str, int]] = []
            outside_win: list[str] = []
            os2 = font["OS/2"] if "OS/2" in font else None
            win_ascent = int(os2.usWinAscent) if os2 is not None else None
            win_descent = -int(os2.usWinDescent) if os2 is not None else None
            for glyph_name in glyph_order:
                try:
                    bounds_pen = BoundsPen(glyph_set)
                    glyph_set[glyph_name].draw(bounds_pen)
                    bounds = bounds_pen.bounds
                except Exception as exc:
                    add("warning", "GLYPH_BOUNDS_UNAVAILABLE", f"glyph.{glyph_name}",
                        f"Could not calculate outline bounds: {exc}")
                    continue
                if not bounds:
                    continue
                y_min, y_max = int(bounds[1]), int(bounds[3])
                if y_max > ascender:
                    above.append((glyph_name, y_max))
                if y_min < descender:
                    below.append((glyph_name, y_min))
                if win_ascent is not None and win_descent is not None and (y_max > win_ascent or y_min < win_descent):
                    outside_win.append(glyph_name)
            if above:
                examples = ", ".join(f"{name} ({value})" for name, value in above[:8])
                add("warning", "GLYPH_ABOVE_HHEA_ASCENDER", "hhea.ascent",
                    f"{len(above)} glyph(s) extend above hhea ascender {ascender}; examples: {examples}.",
                    "Review tall glyphs and line metrics; increase the ascender if the overshoot is intentional.")
            if below:
                examples = ", ".join(f"{name} ({value})" for name, value in below[:8])
                add("warning", "GLYPH_BELOW_HHEA_DESCENDER", "hhea.descent",
                    f"{len(below)} glyph(s) extend below hhea descender {descender}; examples: {examples}.",
                    "Review deep glyphs and line metrics; decrease the descender if the overshoot is intentional.")
            if outside_win:
                add("warning", "GLYPH_OUTSIDE_WIN_METRICS", "OS/2.usWinAscent/usWinDescent",
                    f"{len(outside_win)} glyph(s) extend outside Windows vertical metrics; examples: {', '.join(outside_win[:8])}.",
                    "Adjust usWinAscent/usWinDescent or review the glyph outlines.")

        if "glyf" in font:
            glyf = font["glyf"]
            known = set(glyph_order)
            empty = []
            for name in glyph_order:
                if name not in glyf:
                    continue
                glyph = glyf[name]
                if glyph.isComposite():
                    for component in glyph.components:
                        if component.glyphName not in known:
                            add("error", "MISSING_COMPOSITE_COMPONENT", f"glyf.{name}",
                                f"Composite glyph references missing component {component.glyphName}.")
                elif getattr(glyph, "numberOfContours", 0) == 0 and not getattr(glyph, "coordinates", []):
                    empty.append(name)
            if empty:
                add("info", "EMPTY_GLYPHS", "glyf",
                    f"{len(empty)} glyph(s) have empty outlines; examples: {', '.join(empty[:10])}. Empty space glyphs may be intentional.")
            if "loca" in font:
                offsets = list(getattr(font["loca"], "locations", []) or [])
                if len(offsets) != glyph_count + 1 or any(a > b for a, b in zip(offsets, offsets[1:])):
                    add("error", "INVALID_LOCA_OFFSETS", "loca", "loca offsets are not monotonic or do not match glyph count.")
                else:
                    checks["passed"] += 1

        if not findings:
            checks["passed"] += 1
            add("info", "NO_FINDINGS", "font", "No structural issues were detected by the current checks.")
        return {"version": APP_VERSION, "filename": path.name, "summary": checks,
                "findingCount": len(findings), "findings": findings,
                "scope": ["SFNT directory and table presence", "table checksums where stored by the format", "core metrics",
                          "Unicode cmap consistency", "vertical glyph bounds for TrueType/CFF/CFF2",
                          "TrueType composite references", "loca offsets"]}
    finally:
        font.close()



# Character-set quality profile. This is a practical MyFonts-inspired Latin
# production checklist, not a verbatim or officially endorsed MyFonts standard.
LATIN_UPPER = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
LATIN_LOWER = list("abcdefghijklmnopqrstuvwxyz")
LATIN_DIGITS = list("0123456789")
BASIC_PUNCTUATION = list(".,:;!?¡¿'\"“”‘’()[]{}-–—_…")
COMMON_SYMBOLS = list("@#&%*+=/\\€£¥¢$©®™°")
LATIN_ACCENTS = list("ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ")


def analyze_font_quality(font: TTFont) -> dict[str, Any]:
    """Analyze Unicode character coverage and basic horizontal metrics."""
    cmap = font.getBestCmap() or {}
    glyph_order = set(font.getGlyphOrder())
    valid_map = {cp: name for cp, name in cmap.items() if name in glyph_order}

    groups = [
        ("Uppercase", "required", LATIN_UPPER),
        ("Lowercase", "required", LATIN_LOWER),
        ("Numerals", "required", LATIN_DIGITS),
        ("Basic punctuation", "required", BASIC_PUNCTUATION),
        ("Common symbols", "recommended", COMMON_SYMBOLS),
        ("Latin accented", "recommended", LATIN_ACCENTS),
    ]
    results = []
    total_required = present_required = total_recommended = present_recommended = 0
    missing_required: list[str] = []
    missing_recommended: list[str] = []

    for label, priority, chars in groups:
        unique_chars = list(dict.fromkeys(chars))
        present = [ch for ch in unique_chars if ord(ch) in valid_map]
        missing = [ch for ch in unique_chars if ord(ch) not in valid_map]
        if priority == "required":
            total_required += len(unique_chars); present_required += len(present)
            missing_required.extend(missing)
        else:
            total_recommended += len(unique_chars); present_recommended += len(present)
            missing_recommended.extend(missing)
        results.append({
            "name": label, "priority": priority,
            "total": len(unique_chars), "present": len(present),
            "missingCount": len(missing),
            "coverage": round((len(present) / len(unique_chars)) * 100, 1) if unique_chars else 100,
            "presentCharacters": present,
            "missingCharacters": missing,
            "missingCodepoints": [f"U+{ord(ch):04X}" for ch in missing],
        })

    metrics = getattr(font.get("hmtx"), "metrics", {}) if "hmtx" in font else {}
    missing_metrics = [name for name in font.getGlyphOrder() if name not in metrics]
    zero_advance = []
    for name, metric in metrics.items():
        advance = int(metric[0])
        # Zero advance is often intentional for combining marks; report only as info.
        if advance == 0 and name not in {".notdef", "space", "nonmarkingreturn"}:
            zero_advance.append(name)

    findings = []
    if missing_required:
        findings.append({
            "severity": "warning", "code": "MISSING_CORE_CHARACTERS",
            "location": "Unicode cmap / Latin core",
            "message": f"{len(missing_required)} recommended core character(s) are missing: {' '.join(missing_required[:40])}{' …' if len(missing_required) > 40 else ''}.",
            "recommendation": "Add the missing Unicode characters if this typeface is intended for general Latin text use."
        })
    if missing_recommended:
        findings.append({
            "severity": "info", "code": "MISSING_EXTENDED_CHARACTERS",
            "location": "Unicode cmap / extended Latin",
            "message": f"{len(missing_recommended)} additional symbol or accented character(s) are not mapped: {' '.join(missing_recommended[:40])}{' …' if len(missing_recommended) > 40 else ''}.",
            "recommendation": "Consider adding these characters to improve language and typographic coverage."
        })
    if missing_metrics:
        findings.append({
            "severity": "error", "code": "MISSING_GLYPH_METRICS",
            "location": "hmtx",
            "message": f"{len(missing_metrics)} glyph(s) have no horizontal metric entry; examples: {', '.join(missing_metrics[:10])}.",
            "recommendation": "Provide a horizontal advance width and side-bearing record for every glyph."
        })
    if zero_advance:
        findings.append({
            "severity": "info", "code": "ZERO_ADVANCE_GLYPHS",
            "location": "hmtx",
            "message": f"{len(zero_advance)} glyph(s) have zero advance width; examples: {', '.join(zero_advance[:10])}. This can be intentional for combining marks.",
            "recommendation": "Review these metrics in context; zero advance is not automatically an error."
        })

    all_expected = total_required + total_recommended
    all_present = present_required + present_recommended
    return {
        "version": APP_VERSION,
        "profile": "MyFonts-inspired Latin production checklist",
        "profileNote": "A practical baseline for general-purpose Latin fonts, not an official MyFonts certification or exhaustive marketplace submission specification. Display, symbol, and non-Latin fonts may intentionally differ.",
        "summary": {
            "requiredTotal": total_required, "requiredPresent": present_required,
            "requiredMissing": len(missing_required),
            "recommendedTotal": total_recommended, "recommendedPresent": present_recommended,
            "recommendedMissing": len(missing_recommended),
            "overallCoverage": round((all_present / all_expected) * 100, 1) if all_expected else 100,
            "mappedUnicode": len(cmap), "totalGlyphs": len(font.getGlyphOrder()),
            "missingMetrics": len(missing_metrics), "zeroAdvanceGlyphs": len(zero_advance),
        },
        "groups": results,
        "findings": findings,
        "metrics": {"missingGlyphs": missing_metrics[:100], "zeroAdvanceGlyphs": zero_advance[:100]},
    }


def inspect_quality(path: Path) -> dict[str, Any]:
    font = TTFont(str(path), lazy=False)
    try:
        return analyze_font_quality(font)
    finally:
        font.close()


def inspect_variable_font(path: Path) -> dict[str, Any]:
    """Read variable-font axes, named instances, avar mappings and variation tables."""
    font = TTFont(str(path), lazy=False)
    try:
        if "fvar" not in font:
            return {"isVariable": False, "axes": [], "instances": [], "avar": {},
                    "tables": {tag: tag in font for tag in ("fvar", "avar", "STAT", "gvar", "CFF2", "HVAR", "VVAR", "MVAR", "cvar")},
                    "message": "This font does not contain an fvar table. It is not an OpenType variable font."}

        name_table = font["name"] if "name" in font else None
        def name_for(name_id: Any, fallback: str) -> str:
            if name_id is None or name_table is None:
                return fallback
            try:
                return name_table.getDebugName(int(name_id)) or fallback
            except Exception:
                return fallback

        fvar = font["fvar"]
        axes = []
        for axis in fvar.axes:
            tag = str(axis.axisTag)
            axes.append({"tag": tag, "name": name_for(getattr(axis, "axisNameID", None), tag),
                         "min": float(axis.minValue), "default": float(axis.defaultValue),
                         "max": float(axis.maxValue), "flags": int(getattr(axis, "flags", 0)),
                         "hidden": bool(int(getattr(axis, "flags", 0)) & 0x0001)})

        instances = []
        for index, instance in enumerate(fvar.instances):
            coords = {str(k): float(v) for k, v in (getattr(instance, "coordinates", {}) or {}).items()}
            ps_id = getattr(instance, "postscriptNameID", 0xFFFF)
            instances.append({"index": index,
                              "name": name_for(getattr(instance, "subfamilyNameID", None), f"Instance {index + 1}"),
                              "postScriptName": name_for(ps_id, "") if ps_id != 0xFFFF else "",
                              "coordinates": coords})

        avar = {}
        if "avar" in font:
            for tag, mapping in (getattr(font["avar"], "segments", {}) or {}).items():
                avar[str(tag)] = [{"from": float(src), "to": float(dst)} for src, dst in sorted(mapping.items())]

        stat_axes = []
        if "STAT" in font:
            stat = getattr(font["STAT"], "table", None)
            axis_records = getattr(getattr(stat, "DesignAxisRecord", None), "Axis", []) or []
            for axis in axis_records:
                stat_axes.append({"tag": str(getattr(axis, "AxisTag", "")),
                                  "name": name_for(getattr(axis, "AxisNameID", None), str(getattr(axis, "AxisTag", ""))),
                                  "ordering": int(getattr(axis, "AxisOrdering", 0))})

        variation_tables = {tag: tag in font for tag in ("fvar", "avar", "STAT", "gvar", "CFF2", "HVAR", "VVAR", "MVAR", "cvar")}
        return {"isVariable": True, "axes": axes, "instances": instances, "avar": avar,
                "statAxes": stat_axes, "tables": variation_tables,
                "axisCount": len(axes), "instanceCount": len(instances),
                "glyphVariationModel": "gvar" if "gvar" in font else ("CFF2" if "CFF2" in font else "not exposed"),
                "note": "Axis controls change the browser specimen using CSS font-variation-settings. They do not rewrite or export the font binary."}
    finally:
        font.close()



def validate_variable_font(path: Path) -> dict[str, Any]:
    """Validate variable-font metadata and exercise real instances at representative locations."""
    from itertools import product
    from fontTools.varLib.instancer import instantiateVariableFont

    font = TTFont(str(path), lazy=False)
    findings: list[dict[str, Any]] = []
    tests: list[dict[str, Any]] = []

    def add(severity: str, code: str, location: str, message: str, recommendation: str) -> None:
        findings.append({"severity": severity, "code": code, "location": location,
                         "message": message, "recommendation": recommendation})

    try:
        if "fvar" not in font:
            return {"isVariable": False, "summary": {"errors": 0, "warnings": 0, "info": 1, "locationsTested": 0},
                    "findings": [{"severity": "info", "code": "STATIC_FONT", "location": "fvar",
                                  "message": "This file has no fvar table, so variable interpolation cannot be tested.",
                                  "recommendation": "Upload an OpenType variable font containing fvar."}], "tests": [],
                    "scope": ["fvar metadata", "axis ranges", "named instances", "avar mappings", "real font instancing"]}

        axes = list(font["fvar"].axes)
        tags = [str(a.axisTag) for a in axes]
        if len(tags) != len(set(tags)):
            add("error", "DUPLICATE_AXIS_TAG", "fvar", "The fvar table contains duplicate axis tags.",
                "Each design axis must have a unique four-character tag.")
        axis_by_tag = {str(a.axisTag): a for a in axes}
        defaults = {str(a.axisTag): float(a.defaultValue) for a in axes}

        for axis in axes:
            tag = str(axis.axisTag)
            minimum, default, maximum = float(axis.minValue), float(axis.defaultValue), float(axis.maxValue)
            if not (minimum < maximum):
                add("error", "INVALID_AXIS_RANGE", f"fvar/{tag}",
                    f"Axis {tag} must have a minimum lower than its maximum (found {minimum}–{maximum}).",
                    "Correct the axis minValue and maxValue in the source font project.")
            if not minimum <= default <= maximum:
                add("error", "DEFAULT_OUT_OF_RANGE", f"fvar/{tag}",
                    f"Axis {tag} default {default} is outside its declared range {minimum}–{maximum}.",
                    "Move the default coordinate inside the axis range.")

        instances = list(font["fvar"].instances)
        for index, instance in enumerate(instances):
            coords = getattr(instance, "coordinates", {}) or {}
            for tag, axis in axis_by_tag.items():
                if tag not in coords:
                    add("warning", "INSTANCE_MISSING_COORDINATE", f"fvar/instance-{index + 1}/{tag}",
                        f"Named instance {index + 1} does not explicitly provide coordinate {tag}.",
                        "Check whether the instance coordinates are complete in the source font project.")
                    continue
                value = float(coords[tag])
                if not float(axis.minValue) <= value <= float(axis.maxValue):
                    add("error", "INSTANCE_OUT_OF_RANGE", f"fvar/instance-{index + 1}/{tag}",
                        f"Named instance {index + 1} sets {tag}={value}, outside {axis.minValue}–{axis.maxValue}.",
                        "Adjust the named instance coordinate to the declared axis range.")

        if "avar" in font:
            segments = getattr(font["avar"], "segments", {}) or {}
            for tag, mapping in segments.items():
                points = sorted((float(x), float(y)) for x, y in mapping.items())
                if points and (points[0][0] > -1 or points[-1][0] < 1):
                    add("warning", "AVAR_ENDPOINT_MISSING", f"avar/{tag}",
                        f"The avar mapping for {tag} does not explicitly span the full normalized -1 to +1 range.",
                        "Review the segment map endpoints and confirm that the mapping is intentional.")
                if any(points[i][1] > points[i + 1][1] for i in range(len(points) - 1)):
                    add("warning", "AVAR_NON_MONOTONIC", f"avar/{tag}",
                        f"The avar mapping for {tag} is non-monotonic.",
                        "Review the mapping; non-monotonic mappings may be intentional but can produce surprising axis behavior.")
                if tag not in axis_by_tag:
                    add("warning", "AVAR_UNKNOWN_AXIS", f"avar/{tag}",
                        f"The avar table references axis {tag}, which is not present in fvar.",
                        "Ensure avar axis tags correspond to fvar axes.")

        if "STAT" in font:
            stat = getattr(font["STAT"], "table", None)
            records = getattr(getattr(stat, "DesignAxisRecord", None), "Axis", []) or []
            for record in records:
                tag = str(getattr(record, "AxisTag", ""))
                if tag and tag not in axis_by_tag:
                    add("warning", "STAT_UNKNOWN_AXIS", f"STAT/{tag}",
                        f"STAT declares axis {tag}, but it is not present in fvar.",
                        "Review the STAT design axis records and keep them aligned with fvar.")

        # Test each axis endpoint independently, then all named instances and a bounded set
        # of combined corners. This exercises the actual fontTools instancer, not CSS preview.
        locations: list[tuple[str, dict[str, float]]] = [("Default", dict(defaults))]
        for tag, axis in axis_by_tag.items():
            for label, value in (("Min", float(axis.minValue)), ("Max", float(axis.maxValue))):
                loc = dict(defaults); loc[tag] = value
                locations.append((f"{tag} {label}", loc))
        for index, instance in enumerate(instances):
            coords = {tag: float(value) for tag, value in (getattr(instance, "coordinates", {}) or {}).items()}
            loc = dict(defaults); loc.update(coords)
            locations.append((f"Named instance {index + 1}", loc))

        if axes and len(axes) <= 5:
            # Full corners are useful for common 1–3 axis fonts; cap total test locations.
            corners = list(product(*[(float(a.minValue), float(a.maxValue)) for a in axes]))
            for corner_index, values in enumerate(corners[:32]):
                loc = dict(defaults); loc.update({str(a.axisTag): value for a, value in zip(axes, values)})
                locations.append((f"Axis corner {corner_index + 1}", loc))

        unique_locations: list[tuple[str, dict[str, float]]] = []
        seen = set()
        for label, loc in locations:
            key = tuple(sorted((k, round(v, 6)) for k, v in loc.items()))
            if key not in seen:
                seen.add(key); unique_locations.append((label, loc))
        unique_locations = unique_locations[:64]

        for label, location in unique_locations:
            test = {"name": label, "coordinates": location, "status": "passed", "glyphCount": 0, "message": "Instance generated successfully."}
            try:
                instance_font = instantiateVariableFont(font, location, inplace=False, optimize=True)
                try:
                    glyph_order = instance_font.getGlyphOrder()
                    test["glyphCount"] = len(glyph_order)
                    if "glyf" in instance_font:
                        for glyph_name in glyph_order:
                            glyph = instance_font["glyf"][glyph_name]
                            if glyph.isComposite():
                                for component in glyph.components:
                                    if getattr(component, "glyphName", None) not in glyph_order:
                                        raise ValueError(f"{glyph_name} references missing component {component.glyphName}")
                    if "hmtx" in instance_font:
                        missing_metrics = [g for g in glyph_order if g not in instance_font["hmtx"].metrics]
                        if missing_metrics:
                            raise ValueError(f"{len(missing_metrics)} glyph(s) have no horizontal metrics; e.g. {', '.join(missing_metrics[:5])}")
                    test["status"] = "passed"
                finally:
                    instance_font.close()
            except Exception as exc:
                test["status"] = "failed"
                test["message"] = str(exc)[:500]
                add("error", "INSTANCE_GENERATION_FAILED", label,
                    f"Could not generate a static instance at {location}: {str(exc)[:350]}",
                    "Inspect variation data (gvar/CFF2 and metric variation tables), axis coordinates, and glyph compatibility in the source font.")
            tests.append(test)

        if not any(f["severity"] == "error" for f in findings):
            add("info", "NO_STRUCTURAL_ERRORS_DETECTED", "variable-font",
                "No structural issue was detected by the implemented checks. This does not certify visual interpolation quality.",
                "Review the specimen at intermediate locations and inspect critical glyphs manually.")

        return {"isVariable": True,
                "summary": {"errors": sum(f["severity"] == "error" for f in findings),
                            "warnings": sum(f["severity"] == "warning" for f in findings),
                            "info": sum(f["severity"] == "info" for f in findings),
                            "locationsTested": len(tests), "locationsPassed": sum(t["status"] == "passed" for t in tests),
                            "locationsFailed": sum(t["status"] == "failed" for t in tests)},
                "findings": findings, "tests": tests,
                "scope": ["fvar axis ranges and defaults", "named instance coordinates", "avar mappings", "STAT axis references", "real static instancing at endpoints, named instances and selected axis corners", "glyph/component references and horizontal metrics in generated instances"],
                "limitations": ["Successful instancing does not prove that outlines interpolate smoothly or match the designer's intent.", "Visual anomalies such as kinks, weight inconsistency, or unexpected shape changes require specimen comparison and human review.", "Only a bounded set of representative locations is tested; the full continuous design space is not exhaustively sampled."]}
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
        contour_analysis = analyze_glyph_contours(glyph, glyph_set)
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
            "contourAnalysis": contour_analysis,
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


@app.get("/api/fonts/{font_id}/diagnostics")
def get_font_diagnostics(font_id: str) -> dict[str, Any]:
    return inspect_diagnostics(stored_font_path(font_id))


@app.get("/api/fonts/{font_id}/quality")
def get_font_quality(font_id: str) -> dict[str, Any]:
    return inspect_quality(stored_font_path(font_id))


@app.get("/api/fonts/{font_id}/opentype")
def get_opentype_details(font_id: str) -> dict[str, Any]:
    return inspect_opentype(stored_font_path(font_id))


@app.get("/api/fonts/{font_id}/variable")
def get_variable_font_details(font_id: str) -> dict[str, Any]:
    return inspect_variable_font(stored_font_path(font_id))


@app.get("/api/fonts/{font_id}/variable-validation")
def get_variable_font_validation(font_id: str) -> dict[str, Any]:
    return validate_variable_font(stored_font_path(font_id))
