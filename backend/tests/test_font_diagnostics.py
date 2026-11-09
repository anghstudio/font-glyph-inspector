import tempfile
import unittest
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from app.main import inspect_diagnostics


def build_fixture(path: Path) -> None:
    fb = FontBuilder(1000, isTTF=True)
    order = [".notdef", "space", "A"]
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({32: "space", 65: "A"})
    glyphs = {}
    for name in order:
        pen = TTGlyphPen(None)
        if name == "A":
            pen.moveTo((100, 0)); pen.lineTo((500, 700)); pen.lineTo((900, 0)); pen.closePath()
        glyphs[name] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({".notdef": (600, 0), "space": (300, 0), "A": (1000, 100)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Fixture", "styleName": "Regular", "uniqueFontIdentifier": "Fixture Regular", "fullName": "Fixture Regular", "psName": "Fixture-Regular"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.setupMaxp()
    fb.save(path)


def build_bounds_fixture(path: Path) -> None:
    fb = FontBuilder(1000, isTTF=True)
    order = [".notdef", "space", "D", "Q"]
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({68: "D", 81: "Q"})
    glyphs = {}
    for name in order:
        pen = TTGlyphPen(None)
        if name == "D":
            pen.moveTo((0, 285)); pen.lineTo((512, 285)); pen.lineTo((512, 975)); pen.lineTo((0, 975)); pen.closePath()
        elif name == "Q":
            pen.moveTo((0, -683)); pen.lineTo((576, -683)); pen.lineTo((576, 127)); pen.lineTo((0, 127)); pen.closePath()
        glyphs[name] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({".notdef": (600, 0), "space": (300, 0), "D": (600, 0), "Q": (600, 0)})
    fb.setupHorizontalHeader(ascent=690, descent=-168)
    fb.setupNameTable({"familyName": "Bounds Fixture", "styleName": "Regular", "uniqueFontIdentifier": "Bounds Fixture", "fullName": "Bounds Fixture", "psName": "Bounds-Fixture"})
    fb.setupOS2(sTypoAscender=690, sTypoDescender=-168, usWinAscent=690, usWinDescent=168)
    fb.setupPost()
    fb.setupMaxp()
    fb.save(path)


def build_cff2_bounds_fixture(path: Path) -> None:
    from fontTools.pens.t2CharStringPen import T2CharStringPen
    fb = FontBuilder(1000, isTTF=False)
    order = [".notdef", "D", "Q"]
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({68: "D", 81: "Q"})
    charstrings = {}
    for name in order:
        pen = T2CharStringPen(None, None, CFF2=True)
        if name == "D":
            pen.moveTo((0, 285)); pen.lineTo((512, 285)); pen.lineTo((512, 975)); pen.lineTo((0, 975)); pen.closePath()
        elif name == "Q":
            pen.moveTo((0, -683)); pen.lineTo((576, -683)); pen.lineTo((576, 127)); pen.lineTo((0, 127)); pen.closePath()
        charstrings[name] = pen.getCharString()
    fb.setupCFF2(charstrings)
    fb.setupHorizontalMetrics({".notdef": (600, 0), "D": (600, 0), "Q": (600, 0)})
    fb.setupHorizontalHeader(ascent=690, descent=-168)
    fb.setupNameTable({"familyName": "Bounds CFF2 Fixture", "styleName": "Regular", "uniqueFontIdentifier": "Bounds CFF2 Fixture", "fullName": "Bounds CFF2 Fixture", "psName": "Bounds-CFF2-Fixture"})
    fb.setupOS2(sTypoAscender=690, sTypoDescender=-168, usWinAscent=690, usWinDescent=168)
    fb.setupPost()
    fb.setupMaxp()
    fb.save(path)


class FontDiagnosticsTests(unittest.TestCase):
    def test_valid_fixture_reports_no_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.ttf"
            build_fixture(path)
            report = inspect_diagnostics(path)
            self.assertIn("summary", report)
            self.assertEqual(report["summary"]["errors"], 0)
            self.assertGreaterEqual(report["summary"]["passed"], 3)

    def test_report_has_structured_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.ttf"
            build_fixture(path)
            report = inspect_diagnostics(path)
            for finding in report["findings"]:
                self.assertIn(finding["severity"], {"error", "warning", "info"})
                self.assertTrue(finding["code"])
                self.assertTrue(finding["location"])
                self.assertTrue(finding["message"])

    def test_detects_vertical_bounds_in_truetype(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bounds.ttf"
            build_bounds_fixture(path)
            report = inspect_diagnostics(path)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("GLYPH_ABOVE_HHEA_ASCENDER", codes)
            self.assertIn("GLYPH_BELOW_HHEA_DESCENDER", codes)
            self.assertIn("GLYPH_OUTSIDE_WIN_METRICS", codes)
            self.assertGreater(report["summary"]["warnings"], 0)
            self.assertIn("D (975)", next(x["message"] for x in report["findings"] if x["code"] == "GLYPH_ABOVE_HHEA_ASCENDER"))

    def test_detects_vertical_bounds_in_cff2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bounds.otf"
            build_cff2_bounds_fixture(path)
            report = inspect_diagnostics(path)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("GLYPH_ABOVE_HHEA_ASCENDER", codes)
            self.assertIn("GLYPH_BELOW_HHEA_DESCENDER", codes)

    def test_woff2_does_not_report_unavailable_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bounds.woff2"
            build_bounds_fixture(path)
            from fontTools.ttLib import TTFont
            font = TTFont(str(path))
            font.flavor = "woff2"
            font.save(path)
            font.close()
            report = inspect_diagnostics(path)
            codes = {item["code"] for item in report["findings"]}
            self.assertNotIn("TABLE_CHECKSUM_UNAVAILABLE", codes)
            self.assertIn("GLYPH_ABOVE_HHEA_ASCENDER", codes)

    def test_detects_vertical_bounds_in_woff1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bounds.woff"
            build_bounds_fixture(path)
            from fontTools.ttLib import TTFont
            font = TTFont(str(path))
            font.flavor = "woff"
            font.save(path)
            font.close()
            report = inspect_diagnostics(path)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("GLYPH_ABOVE_HHEA_ASCENDER", codes)
            self.assertIn("GLYPH_BELOW_HHEA_DESCENDER", codes)



if __name__ == "__main__":
    unittest.main()

class FontQualityTests(unittest.TestCase):
    def test_reports_missing_core_characters_and_extended_coverage(self):
        from fontTools.ttLib import TTFont
        from app.main import analyze_font_quality
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage-fixture.ttf"
            build_fixture(path)
            font = TTFont(path)
            try:
                report = analyze_font_quality(font)
            finally:
                font.close()
        self.assertEqual(report["profile"], "MyFonts-inspired Latin production checklist")
        self.assertIn("F", report["groups"][0]["missingCharacters"])
        self.assertEqual(report["summary"]["requiredPresent"], 1)
        self.assertGreater(report["summary"]["requiredMissing"], 0)
        self.assertTrue(any(f["code"] == "MISSING_CORE_CHARACTERS" for f in report["findings"]))

    def test_reports_mapped_character_as_present(self):
        from fontTools.ttLib import TTFont
        from app.main import analyze_font_quality
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage-fixture.ttf"
            build_fixture(path)
            font = TTFont(path)
            try:
                report = analyze_font_quality(font)
            finally:
                font.close()
        uppercase = next(group for group in report["groups"] if group["name"] == "Uppercase")
        self.assertIn("A", uppercase["presentCharacters"])
        self.assertNotIn("A", uppercase["missingCharacters"])
