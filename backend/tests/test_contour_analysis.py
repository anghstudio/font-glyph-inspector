import unittest

from app.contour_analysis import analyze_glyph_contours


class PolygonGlyph:
    def draw(self, pen):
        pen.moveTo((0, 0))
        pen.lineTo((100, 0))
        pen.lineTo((100, 100))
        pen.lineTo((0, 100))
        pen.closePath()


class CurveGlyph:
    def draw(self, pen):
        pen.moveTo((0, 0))
        pen.qCurveTo((50, 100), (100, 0))
        pen.curveTo((125, -50), (175, -50), (200, 0))
        pen.endPath()


class EmptyGlyph:
    def draw(self, pen):
        return None


class ContourAnalysisTests(unittest.TestCase):
    def test_closed_polygon_direction_and_area(self):
        result = analyze_glyph_contours(PolygonGlyph(), {})
        contour = result["contours"][0]
        self.assertTrue(contour["closed"])
        self.assertEqual(contour["direction"], "counter-clockwise")
        self.assertAlmostEqual(contour["signedArea"], 10000, delta=1)
        self.assertEqual(result["segmentTypeTotals"]["line"], 4)
        self.assertEqual(result["diagnostics"], [])

    def test_quadratic_cubic_and_open_contour(self):
        result = analyze_glyph_contours(CurveGlyph(), {})
        self.assertEqual(result["segmentTypeTotals"]["quadratic"], 1)
        self.assertEqual(result["segmentTypeTotals"]["cubic"], 1)
        self.assertFalse(result["contours"][0]["closed"])
        self.assertIn("OPEN_CONTOUR", [item["code"] for item in result["diagnostics"]])

    def test_empty_glyph(self):
        result = analyze_glyph_contours(EmptyGlyph(), {})
        self.assertEqual(result["contourCount"], 0)
        self.assertEqual(result["segmentCount"], 0)


if __name__ == "__main__":
    unittest.main()
