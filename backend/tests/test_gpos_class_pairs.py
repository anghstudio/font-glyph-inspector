import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

from app.main import _decode_gpos_subtable, inspect_opentype
from fontTools.fontBuilder import FontBuilder
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.ttGlyphPen import TTGlyphPen


def value(xp=0, yp=0, xa=0, ya=0):
    return NS(XPlacement=xp, YPlacement=yp, XAdvance=xa, YAdvance=ya)


class GposClassPairTests(unittest.TestCase):
    def test_pairpos_format2_expands_pairs_and_preserves_zero_and_negative_values(self):
        matrix = [
            NS(Class2Record=[NS(Value1=None, Value2=None), NS(Value1=None, Value2=None)]),
            NS(Class2Record=[
                NS(Value1=value(xa=-80), Value2=value(yp=0)),
                NS(Value1=value(xp=0, yp=-12, xa=0, ya=0), Value2=None),
            ]),
        ]
        subtable = NS(
            Format=2, Coverage=NS(glyphs=["L1"]),
            ClassDef1=NS(classDefs={"L1": 1}), ClassDef2=NS(classDefs={"R1": 1}),
            Class1Record=matrix,
        )
        result = _decode_gpos_subtable(subtable, 2, ["L1", "R0", "R1"])
        pairs = {(p["left"], p["right"]): p for p in result["kerningPairs"]}

        self.assertEqual(result["format"], 2)
        self.assertEqual(result["totalPairCount"], 3)
        self.assertEqual(pairs[("L1", "R0")]["value1"]["XAdvance"], -80)
        self.assertEqual(pairs[("L1", "R0")]["value2"]["YPlacement"], 0)
        self.assertEqual(pairs[("L1", "R1")]["value1"], {
            "XPlacement": 0, "YPlacement": -12, "XAdvance": 0, "YAdvance": 0
        })
        self.assertFalse(result["expansionTruncated"])

    def test_real_font_fixture_decodes_pairpos_format2(self):
        glyph_order = [".notdef", "L1", "R0", "R1"]
        builder = FontBuilder(1000, isTTF=True)
        builder.setupGlyphOrder(glyph_order)
        builder.setupCharacterMap({65: "L1", 66: "R0", 67: "R1"})
        builder.setupGlyf({name: TTGlyphPen(None).glyph() for name in glyph_order})
        builder.setupHorizontalMetrics({name: (500, 0) for name in glyph_order})
        builder.setupHorizontalHeader(ascent=800, descent=-200)
        builder.setupNameTable({
            "familyName": "GPOS Fixture", "styleName": "Regular",
            "uniqueFontIdentifier": "GPOS Fixture", "fullName": "GPOS Fixture Regular",
            "psName": "GPOSFixture-Regular",
        })
        builder.setupOS2(); builder.setupPost(); builder.setupMaxp()
        addOpenTypeFeaturesFromString(
            builder.font,
            "@LEFT = [L1]; @RIGHT = [R0 R1]; feature kern { pos @LEFT @RIGHT -80; } kern;",
        )
        with tempfile.TemporaryDirectory() as directory:
            fixture_path = Path(directory) / "gpos-class-pair-fixture.ttf"
            builder.save(fixture_path)
            decoded = inspect_opentype(fixture_path)["GPOS"]["lookups"][0]["subtables"][0]

        self.assertEqual(decoded["format"], 2)
        self.assertTrue(decoded["classPairMatrix"].startswith("Class-based pair positioning expanded"))
        pairs = {(pair["left"], pair["right"]): pair for pair in decoded["kerningPairs"]}
        self.assertEqual(pairs[("L1", "R0")]["value1"]["XAdvance"], -80)
        self.assertEqual(pairs[("L1", ".notdef")]["value1"]["XAdvance"], 0)
        self.assertEqual(decoded["totalPairCount"], 4)

    def test_pairpos_format2_applies_expansion_safety_limit(self):
        import app.main as main
        original_limit = main.MAX_CLASS_PAIR_EXPANSION
        main.MAX_CLASS_PAIR_EXPANSION = 1
        try:
            subtable = NS(
                Format=2, Coverage=NS(glyphs=["L1"]),
                ClassDef1=NS(classDefs={}), ClassDef2=NS(classDefs={}),
                Class1Record=[NS(Class2Record=[NS(Value1=value(xa=-1), Value2=None)])],
            )
            result = _decode_gpos_subtable(subtable, 2, ["R1", "R2", "R3"])
        finally:
            main.MAX_CLASS_PAIR_EXPANSION = original_limit

        self.assertEqual(len(result["kerningPairs"]), 1)
        self.assertEqual(result["totalPairCount"], 3)
        self.assertTrue(result["expansionTruncated"])
        self.assertEqual(result["expansionLimit"], 1)


if __name__ == "__main__":
    unittest.main()
