import tempfile
import unittest
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from app.main import inspect_variable_font, validate_variable_font


def build_font(path: Path, variable: bool) -> None:
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
    fb.setupNameTable({"familyName": "Variable Fixture", "styleName": "Regular",
                       "uniqueFontIdentifier": "Variable Fixture", "fullName": "Variable Fixture Regular",
                       "psName": "VariableFixture-Regular"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost(); fb.setupMaxp()
    if variable:
        fb.setupFvar(
            axes=[("wght", 100, 400, 900, "Weight"), ("wdth", 75, 100, 125, "Width")],
            instances=[
                {"location": {"wght": 400, "wdth": 100}, "stylename": "Regular"},
                {"location": {"wght": 700, "wdth": 100}, "stylename": "Bold"},
            ],
        )
    fb.save(path)


class VariableFontInspectorTests(unittest.TestCase):
    def test_detects_static_font(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "static.ttf"
            build_font(path, variable=False)
            report = inspect_variable_font(path)
        self.assertFalse(report["isVariable"])
        self.assertEqual(report["axes"], [])
        self.assertIn("does not contain an fvar", report["message"])

    def test_reads_axes_and_named_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "variable.ttf"
            build_font(path, variable=True)
            report = inspect_variable_font(path)
        self.assertTrue(report["isVariable"])
        self.assertEqual(report["axisCount"], 2)
        weight = next(axis for axis in report["axes"] if axis["tag"] == "wght")
        self.assertEqual((weight["min"], weight["default"], weight["max"]), (100, 400, 900))
        self.assertEqual(report["instanceCount"], 2)
        bold = next(instance for instance in report["instances"] if instance["name"] == "Bold")
        self.assertEqual(bold["coordinates"]["wght"], 700)
        self.assertIn("fvar", report["tables"])

    def test_validation_exercises_representative_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "variable.ttf"
            build_font(path, variable=True)
            report = validate_variable_font(path)
        self.assertTrue(report["isVariable"])
        self.assertGreaterEqual(report["summary"]["locationsTested"], 3)
        self.assertEqual(report["summary"]["locationsFailed"], 0)
        self.assertTrue(any(test["name"] == "Default" for test in report["tests"]))

    def test_validation_marks_static_font_as_not_applicable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "static.ttf"
            build_font(path, variable=False)
            report = validate_variable_font(path)
        self.assertFalse(report["isVariable"])
        self.assertEqual(report["tests"], [])

    def test_report_contains_all_variation_table_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "variable.ttf"
            build_font(path, variable=True)
            report = inspect_variable_font(path)
        self.assertEqual(set(report["tables"]), {"fvar", "avar", "STAT", "gvar", "CFF2", "HVAR", "VVAR", "MVAR", "cvar"})


if __name__ == "__main__":
    unittest.main()
