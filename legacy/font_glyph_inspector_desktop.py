"""
Font Glyph Inspector
Offline Windows desktop utility for type designers.

Requires:
    py -m pip install fonttools

Run:
    py font_glyph_inspector.py
"""

import os
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import winreg
from collections import defaultdict

from fontTools.ttLib import TTFont


APP_TITLE = "Font Glyph Inspector"
BG = "#f4f4f4"


def installed_fonts():
    result = defaultdict(set)
    locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"),
    ]
    fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

    for hive, keypath in locations:
        try:
            with winreg.OpenKey(hive, keypath) as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        display, value, _ = winreg.EnumValue(key, i)
                    except OSError:
                        continue
                    if not isinstance(value, str):
                        continue
                    p = Path(value)
                    if not p.is_absolute():
                        p = fonts_dir / p
                    if p.exists():
                        family = display.split("(")[0].strip()
                        result[family].add(str(p))
        except OSError:
            pass

    return {k: sorted(v) for k, v in result.items()}


def preferred_font(paths):
    for token in ("regular", "book", "roman", "normal", "medium"):
        for p in paths:
            if token in Path(p).stem.lower():
                return p
    return paths[0] if paths else None


def unicode_block(cp):
    blocks = [
        (0x0000, 0x007F, "Basic Latin"),
        (0x0080, 0x00FF, "Latin-1 Supplement"),
        (0x0100, 0x017F, "Latin Extended-A"),
        (0x0180, 0x024F, "Latin Extended-B"),
        (0x0250, 0x02AF, "IPA Extensions"),
        (0x02B0, 0x02FF, "Spacing Modifier Letters"),
        (0x0300, 0x036F, "Combining Diacritical Marks"),
        (0x0370, 0x03FF, "Greek and Coptic"),
        (0x0400, 0x04FF, "Cyrillic"),
        (0x0500, 0x052F, "Cyrillic Supplement"),
        (0x0530, 0x058F, "Armenian"),
        (0x0590, 0x05FF, "Hebrew"),
        (0x0600, 0x06FF, "Arabic"),
        (0x0900, 0x097F, "Devanagari"),
        (0x3040, 0x309F, "Hiragana"),
        (0x30A0, 0x30FF, "Katakana"),
        (0x4E00, 0x9FFF, "CJK Unified Ideographs"),
        (0xAC00, 0xD7AF, "Hangul Syllables"),
        (0x2000, 0x206F, "General Punctuation"),
        (0x2070, 0x209F, "Superscripts and Subscripts"),
        (0x20A0, 0x20CF, "Currency Symbols"),
        (0x2100, 0x214F, "Letterlike Symbols"),
        (0x2190, 0x21FF, "Arrows"),
        (0x2200, 0x22FF, "Mathematical Operators"),
        (0x2300, 0x23FF, "Miscellaneous Technical"),
        (0x2500, 0x257F, "Box Drawing"),
        (0x2580, 0x259F, "Block Elements"),
        (0x25A0, 0x25FF, "Geometric Shapes"),
        (0x2600, 0x26FF, "Miscellaneous Symbols"),
        (0x2700, 0x27BF, "Dingbats"),
        (0x1F300, 0x1F5FF, "Miscellaneous Symbols and Pictographs"),
    ]
    for lo, hi, name in blocks:
        if lo <= cp <= hi:
            return name
    return "Other / Unclassified"


def load_font(path):
    font = TTFont(path, lazy=False)
    cmap = {}
    for table in font["cmap"].tables:
        if table.isUnicode():
            for cp, name in table.cmap.items():
                cmap.setdefault(cp, name)

    glyph_order = font.getGlyphOrder()
    glyph_set = set(glyph_order)
    mapped_names = set(cmap.values())

    entries = []
    for cp, name in sorted(cmap.items()):
        try:
            char = chr(cp)
        except ValueError:
            continue
        entries.append({
            "cp": cp,
            "char": char,
            "name": name,
            "block": unicode_block(cp),
            "category": __import__("unicodedata").category(char),
        })

    unmapped = [g for g in glyph_order if g not in mapped_names]

    tables = sorted(font.keys())
    return font, entries, unmapped, tables


class Inspector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1450x900")
        self.minsize(1050, 700)

        self.fonts = installed_fonts()
        self.entries = []
        self.unmapped = []
        self.tables = []
        self.font = None
        self.font_path = None
        self.selected_glyph = None
        self.selected_cps = set()
        self.glyph_items = []
        self.layout_features = {"GSUB": [], "GPOS": []}
        self.layout_detail = {}

        self.size = tk.IntVar(value=42)
        self.columns = tk.IntVar(value=10)
        self.spacing = tk.IntVar(value=1)
        self.view = tk.StringVar(value="Glyph Map")
        self.query = tk.StringVar()
        self.block = tk.StringVar(value="All Blocks")
        self.show_code = tk.BooleanVar(value=True)
        self.show_name = tk.BooleanVar(value=True)

        self.build()
        self.bind("<Control-Shift-C>", lambda e: self.copy_all())
        self.bind("<Control-C>", lambda e: self.copy_selected_items())
        self.populate_fonts()

    def build(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Font").pack(side="left")
        self.font_box = ttk.Combobox(top, state="readonly", width=34)
        self.font_box.pack(side="left", padx=7)
        self.font_box.bind("<<ComboboxSelected>>", lambda e: self.open_font())

        ttk.Button(top, text="Load", command=self.open_font).pack(side="left")

        ttk.Label(top, text="View").pack(side="left", padx=(22, 5))
        view_box = ttk.Combobox(
            top, textvariable=self.view, state="readonly",
            values=["Glyph Map", "Paragraph", "One per line"],
            width=15
        )
        view_box.pack(side="left")
        view_box.bind("<<ComboboxSelected>>", lambda e: self.render())

        ttk.Label(top, text="Size").pack(side="left", padx=(18, 4))
        ttk.Spinbox(top, from_=12, to=120, textvariable=self.size,
                    width=5, command=self.render).pack(side="left")

        ttk.Label(top, text="Columns").pack(side="left", padx=(12, 4))
        ttk.Spinbox(top, from_=4, to=24, textvariable=self.columns,
                    width=5, command=self.render).pack(side="left")

        ttk.Label(top, text="Cell Gap").pack(side="left", padx=(12, 4))
        ttk.Spinbox(top, from_=0, to=10, textvariable=self.spacing,
                    width=5, command=self.render).pack(side="left")

        ttk.Button(top, text="OpenType Inspector", command=self.show_opentype).pack(side="right", padx=(6, 0))
        ttk.Button(top, text="Copy Characters", command=self.copy_characters_menu).pack(side="right")
        ttk.Button(top, text="Copy Selected", command=self.copy_selected_items).pack(side="right", padx=(0, 6))

        filters = ttk.Frame(self, padding=(10, 0, 10, 8))
        filters.pack(fill="x")

        ttk.Label(filters, text="Search").pack(side="left")
        search = ttk.Entry(filters, textvariable=self.query, width=28)
        search.pack(side="left", padx=7)
        search.bind("<KeyRelease>", lambda e: self.render())

        ttk.Label(filters, text="Unicode Block").pack(side="left", padx=(18, 5))
        self.block_box = ttk.Combobox(
            filters, textvariable=self.block, state="readonly", width=28
        )
        self.block_box.pack(side="left")
        self.block_box.bind("<<ComboboxSelected>>", lambda e: self.render())

        ttk.Checkbutton(filters, text="Unicode", variable=self.show_code,
                        command=self.render).pack(side="left", padx=15)
        ttk.Checkbutton(filters, text="Glyph name", variable=self.show_name,
                        command=self.render).pack(side="left")

        ttk.Button(filters, text="Export", command=self.export_menu).pack(side="right")

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=4)
        main.add(right, weight=1)

        self.canvas = tk.Canvas(left, background="white", highlightthickness=0)
        self.scroll_y = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        self.scroll_y.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.render())
        self.canvas.bind("<Button-1>", self.canvas_click)
        self.canvas.bind("<MouseWheel>", self.mousewheel)

        self.info = tk.Text(right, width=35, wrap="word", padx=12, pady=12,
                             font=("Segoe UI", 9))
        self.info.pack(fill="both", expand=True)
        self.info.configure(state="disabled")

        self.status = ttk.Label(self, text="Ready", padding=(10, 4))
        self.status.pack(fill="x")

    def populate_fonts(self):
        names = sorted(self.fonts, key=str.casefold)
        self.font_box["values"] = names
        if names:
            self.font_box.current(0)
            self.open_font()

    def open_font(self):
        family = self.font_box.get()
        path = preferred_font(self.fonts.get(family, []))
        if not path:
            return

        try:
            self.font, self.entries, self.unmapped, self.tables = load_font(path)
        except Exception as e:
            messagebox.showerror("Font error", str(e))
            return

        self.font_path = path
        self.selected_cps.clear()
        self.selected_glyph = None
        blocks = sorted({x["block"] for x in self.entries})
        self.block_box["values"] = ["All Blocks"] + blocks
        self.block.set("All Blocks")
        self.render()
        self.update_info()

    def read_layout_features(self):
        """Read the complete GSUB/GPOS feature tree from fontTools."""
        self.layout_features={"GSUB":[],"GPOS":[]}
        self.layout_detail={}
        self.layout_lookup_info={}

        for tag in ("GSUB","GPOS"):
            if tag not in self.font:
                continue
            try:
                ot=self.font[tag].table
                fl=getattr(ot,"FeatureList",None)
                records=getattr(fl,"FeatureRecord",None) if fl else []
                for rec in records or []:
                    ftag=getattr(rec,"FeatureTag",None)
                    feat=getattr(rec,"Feature",None)
                    if not ftag or feat is None:
                        continue
                    indices=list(getattr(feat,"LookupListIndex",None) or [])
                    if ftag not in self.layout_features[tag]:
                        self.layout_features[tag].append(ftag)
                    self.layout_detail[(tag,ftag)]={"lookups":indices}

                    for idx in indices:
                        try:
                            lookup=ot.LookupList.Lookup[idx]
                            self.layout_lookup_info[(tag,idx)]={
                                "type":getattr(lookup,"LookupType","?"),
                                "flag":getattr(lookup,"LookupFlag",0),
                                "subtables":len(getattr(lookup,"SubTable",None) or [])
                            }
                        except Exception:
                            pass
                self.layout_features[tag]=sorted(set(self.layout_features[tag]))
            except Exception:
                pass

    def _glyph_label(self, gid, glyph_order):
        try:
            return glyph_order[gid]
        except Exception:
            return f"gid:{gid}"

    def _coverage_glyphs(self, coverage, glyph_order):
        if coverage is None:
            return []
        try:
            return [self._glyph_label(gid, glyph_order) for gid in coverage.glyphs]
        except Exception:
            return []

    def _decode_gsub_lookup(self, lookup, glyph_order):
        rows = []
        ltype = getattr(lookup, "LookupType", None)
        for sub in getattr(lookup, "SubTable", []) or []:
            # GSUB 1: single substitution
            if ltype == 1:
                cov = self._coverage_glyphs(getattr(sub, "Coverage", None), glyph_order)
                if hasattr(sub, "DeltaGlyphID"):
                    for src in cov:
                        try:
                            gid = glyph_order.index(src)
                            dst = self._glyph_label(gid + sub.DeltaGlyphID, glyph_order)
                        except Exception:
                            dst = "?"
                        rows.append(f"{src}  →  {dst}")
                elif hasattr(sub, "Substitute"):
                    for src, dst in zip(cov, sub.Substitute):
                        rows.append(f"{src}  →  {dst}")
            # GSUB 2: multiple substitution
            elif ltype == 2:
                cov = self._coverage_glyphs(getattr(sub, "Coverage", None), glyph_order)
                for src, seq in zip(cov, getattr(sub, "Sequence", []) or []):
                    dsts=[self._glyph_label(x, glyph_order) for x in getattr(seq, "Substitute", [])]
                    rows.append(f"{src}  →  {' '.join(dsts)}")
            # GSUB 3: alternate substitution
            elif ltype == 3:
                cov = self._coverage_glyphs(getattr(sub, "Coverage", None), glyph_order)
                for src, alt in zip(cov, getattr(sub, "AlternateSet", []) or []):
                    dsts=[self._glyph_label(x, glyph_order) for x in getattr(alt, "Alternate", [])]
                    rows.append(f"{src}  →  {' | '.join(dsts)}")
            # GSUB 4: ligature substitution
            elif ltype == 4:
                cov = self._coverage_glyphs(getattr(sub, "Coverage", None), glyph_order)
                for first, ligset in zip(cov, getattr(sub, "LigatureSet", []) or []):
                    for lig in getattr(ligset, "Ligature", []) or []:
                        comps=[self._glyph_label(x, glyph_order) for x in getattr(lig, "Component", [])]
                        dst=self._glyph_label(getattr(lig, "LigGlyph", -1), glyph_order)
                        rows.append(f"{first} + {' + '.join(comps)}  →  {dst}")
        return rows

    def _decode_gpos_lookup(self, lookup, glyph_order):
        rows=[]
        ltype=getattr(lookup, "LookupType", None)

        for sub in getattr(lookup, "SubTable", []) or []:
            # GPOS 1: single adjustment
            if ltype == 1:
                cov=self._coverage_glyphs(getattr(sub, "Coverage", None), glyph_order)
                vr=getattr(sub, "ValueRecord", None)
                if vr is not None:
                    vals=[]
                    for attr in ("XPlacement","YPlacement","XAdvance","YAdvance"):
                        val=getattr(vr, attr, 0) or 0
                        if val:
                            vals.append(f"{attr}={val}")
                    for g in cov:
                        rows.append(f"{g}  [{', '.join(vals) or 'no adjustment'}]")
            # GPOS 2: pair adjustment / kerning
            elif ltype == 2:
                fmt=getattr(sub, "Format", None)
                if fmt == 1:
                    cov=self._coverage_glyphs(getattr(sub, "Coverage", None), glyph_order)
                    for first, pairset in zip(cov, getattr(sub, "PairSet", []) or []):
                        for pair in getattr(pairset, "PairValueRecord", []) or []:
                            second=self._glyph_label(getattr(pair, "SecondGlyph", -1), glyph_order)
                            v1=getattr(pair, "Value1", None)
                            vals=[]
                            if v1:
                                for attr in ("XPlacement","YPlacement","XAdvance","YAdvance"):
                                    val=getattr(v1, attr, 0) or 0
                                    if val:
                                        vals.append(f"{attr}={val}")
                            rows.append(f"{first} + {second}  [{', '.join(vals) or 'no adjustment'}]")
                elif fmt == 2:
                    rows.append("Class-based pair positioning (Format 2)")
                    rows.append(f"Class1Count={getattr(sub,'Class1Count',0)}  Class2Count={getattr(sub,'Class2Count',0)}")
            # GPOS 4/5/6 are mark/anchor related. Give structural detail rather
            # than pretending to convert all anchor semantics into pair strings.
            elif ltype in (4,5,6):
                rows.append(f"Lookup type {ltype}: mark/anchor positioning")
                rows.append(f"Format {getattr(sub,'Format', '?')}")
        return rows

    def decode_lookup(self, table_tag, lookup_index):
        if not self.font or table_tag not in self.font:
            return []
        try:
            table=self.font[table_tag].table
            lookup=table.LookupList.Lookup[lookup_index]
            order=self.font.getGlyphOrder()
            if table_tag == "GSUB":
                return self._decode_gsub_lookup(lookup, order)
            return self._decode_gpos_lookup(lookup, order)
        except Exception as exc:
            return [f"Unable to decode lookup: {exc}"]

    def show_opentype(self):
        if not self.font:
            return

        win = tk.Toplevel(self)
        win.title(f"OpenType Inspector — {self.font_box.get()}")
        win.geometry("1100x720")
        win.minsize(800, 550)

        paned = ttk.PanedWindow(win, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=3)

        ttk.Label(left, text="GSUB / GPOS",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,8))

        tree = ttk.Treeview(left, columns=("kind","value"), show="tree headings")
        tree.heading("#0", text="Feature / Lookup")
        tree.heading("kind", text="Type")
        tree.heading("value", text="Info")
        tree.column("#0", width=180)
        tree.column("kind", width=70)
        tree.column("value", width=90)
        tree.pack(fill="both", expand=True)

        roots={}
        for table_tag in ("GSUB","GPOS"):
            roots[table_tag]=tree.insert("", "end", text=table_tag, values=("table",""))
            for feature in self.layout_features.get(table_tag, []):
                d=self.layout_detail.get((table_tag,feature),{})
                fnode=tree.insert(
                    roots[table_tag], "end", text=feature,
                    values=("feature", len(d.get("lookups",[])))
                )
                for li in d.get("lookups",[]):
                    try:
                        lookup=self.font[table_tag].table.LookupList.Lookup[li]
                        ltype=getattr(lookup,"LookupType","?")
                        tree.insert(
                            fnode, "end", text=f"Lookup {li}",
                            values=(f"Type {ltype}", len(getattr(lookup,"SubTable",[]) or []))
                        )
                    except Exception:
                        tree.insert(
                            fnode, "end", text=f"Lookup {li}",
                            values=("Unreadable", "")
                        )
            tree.item(roots[table_tag], open=True)

        detail=ttk.Frame(right)
        detail.pack(fill="both", expand=True)

        header=ttk.Label(detail, text="Select a feature or lookup",
                         font=("Segoe UI", 12, "bold"))
        header.pack(anchor="w", pady=(0,8))

        text=tk.Text(detail, wrap="none", font=("Consolas", 9), padx=12, pady=12)
        sy=ttk.Scrollbar(detail, orient="vertical", command=text.yview)
        sx=ttk.Scrollbar(detail, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        text.pack(fill="both", expand=True)

        def display(event=None):
            sel=tree.selection()
            if not sel: return
            item=tree.item(sel[0])
            text.delete("1.0","end")
            text.configure(state="normal")

            parent=tree.parent(sel[0])
            grand=tree.parent(parent)

            # Lookup selected.
            if parent and grand:
                table_tag=tree.item(grand)["text"]
                feature=tree.item(parent)["text"]
                lookup_text=item["text"]
                try:
                    li=int(lookup_text.split()[1])
                    lookup=self.font[table_tag].table.LookupList.Lookup[li]
                    ltype=getattr(lookup,"LookupType","?")
                    ext=getattr(lookup,"LookupFlag",0)
                    rows=self.decode_lookup(table_tag,li)

                    header.config(text=f"{table_tag} / {feature} / Lookup {li}")
                    text.insert("end", f"{table_tag} — feature {feature}\n")
                    text.insert("end", f"Lookup index: {li}\n")
                    text.insert("end", f"Lookup type: {ltype}\n")
                    text.insert("end", f"Lookup flag: {ext}\n")
                    text.insert("end", f"Subtables: {len(getattr(lookup,'SubTable',[]) or [])}\n\n")

                    type_names={
                        ("GSUB",1):"Single Substitution",
                        ("GSUB",2):"Multiple Substitution",
                        ("GSUB",3):"Alternate Substitution",
                        ("GSUB",4):"Ligature Substitution",
                        ("GSUB",5):"Contextual Substitution",
                        ("GSUB",6):"Chained Contextual Substitution",
                        ("GSUB",7):"Extension Substitution",
                        ("GSUB",8):"Reverse Chaining Single Substitution",
                        ("GPOS",1):"Single Adjustment",
                        ("GPOS",2):"Pair Adjustment / Kerning",
                        ("GPOS",3):"Cursive Attachment",
                        ("GPOS",4):"Mark-to-Base",
                        ("GPOS",5):"Mark-to-Ligature",
                        ("GPOS",6):"Mark-to-Mark",
                        ("GPOS",7):"Contextual Positioning",
                        ("GPOS",8):"Chained Contextual Positioning",
                        ("GPOS",9):"Extension Positioning",
                    }
                    text.insert("end", type_names.get((table_tag,ltype),"Unknown / extension type")+"\n\n")
                    if rows:
                        text.insert("end","\n".join(rows))
                    else:
                        text.insert("end","No simple decoded records. This lookup may use contextual, class-based, or extension structures.")
                except Exception as exc:
                    header.config(text="Lookup")
                    text.insert("end", f"Error reading lookup: {exc}")
                return

            # Feature selected.
            if parent:
                table_tag=tree.item(parent)["text"]
                feature=tree.item(sel[0])["text"]
                d=self.layout_detail.get((table_tag,feature),{})
                header.config(text=f"{table_tag} / {feature}")
                text.insert("end", f"Feature: {feature}\n")
                text.insert("end", f"Lookup indexes: {d.get('lookups',[])}\n")
                text.insert("end", f"Subtable formats: {d.get('formats',[])}\n\n")
                explanations={
                    "liga":"Standard ligatures","clig":"Contextual ligatures","calt":"Contextual alternates",
                    "kern":"Kerning","mark":"Mark positioning","mkmk":"Mark-to-mark positioning",
                    "curs":"Cursive attachment","ccmp":"Glyph composition/decomposition","locl":"Localized forms",
                    "salt":"Stylistic alternates","swsh":"Swash","cswh":"Contextual swash","frac":"Fractions",
                    "ordn":"Ordinals","numr":"Numerators","dnom":"Denominators","sups":"Superscripts",
                    "subs":"Subscripts"
                }
                text.insert("end", explanations.get(feature,"OpenType layout feature") + "\n")
                text.insert("end","\nExpand a lookup to inspect actual substitutions/positioning.")
                return

            # Table selected.
            table_tag=item["text"]
            header.config(text=f"{table_tag} overview")
            features=self.layout_features.get(table_tag,[])
            text.insert("end",f"{table_tag} feature count: {len(features)}\n\n")
            text.insert("end",", ".join(features))

        tree.bind("<<TreeviewSelect>>", display)

        # Select first feature/lookup if present.
        for root in roots.values():
            children=tree.get_children(root)
            if children:
                tree.selection_set(children[0])
                display()
                break

    def show_opentype(self):
        if not self.font:
            messagebox.showinfo("OpenType Inspector","Load a font first.")
            return

        self.read_layout_features()

        win=tk.Toplevel(self)
        win.title(f"OpenType Inspector — {self.font_box.get()}")
        win.geometry("1050x700")
        win.minsize(800,500)

        paned=ttk.PanedWindow(win,orient="horizontal")
        paned.pack(fill="both",expand=True,padx=10,pady=10)

        left=ttk.Frame(paned)
        right=ttk.Frame(paned)
        paned.add(left,weight=1)
        paned.add(right,weight=3)

        ttk.Label(left,text="Font OpenType Structure",
                  font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(0,8))

        tree=ttk.Treeview(left,columns=("kind","info"),show="tree headings")
        tree.heading("#0",text="Feature / Lookup")
        tree.heading("kind",text="Type")
        tree.heading("info",text="Info")
        tree.column("#0",width=190)
        tree.column("kind",width=80)
        tree.column("info",width=100)
        tree.pack(fill="both",expand=True)

        roots={}
        for tag in ("GSUB","GPOS"):
            present=tag in self.font
            roots[tag]=tree.insert(
                "","end",text=tag,
                values=("table","PRESENT" if present else "absent"))
            if not present:
                continue
            features=self.layout_features.get(tag,[])
            if not features:
                tree.insert(roots[tag],"end",
                            text="(no decoded FeatureRecords)",
                            values=("info","table exists"))
            for feature in features:
                indices=self.layout_detail.get((tag,feature),{}).get("lookups",[])
                fn=tree.insert(
                    roots[tag],"end",text=feature,
                    values=("feature",f"{len(indices)} lookup(s)"))
                for idx in indices:
                    info=self.layout_lookup_info.get((tag,idx),{})
                    tree.insert(
                        fn,"end",text=f"Lookup {idx}",
                        values=(f"Type {info.get('type','?')}",
                                f"{info.get('subtables',0)} subtable(s)"))
            tree.item(roots[tag],open=True)

        detail=ttk.Frame(right)
        detail.pack(fill="both",expand=True)
        title=ttk.Label(detail,text="Select GSUB or GPOS item",
                        font=("Segoe UI",12,"bold"))
        title.pack(anchor="w",pady=(0,8))

        txt=tk.Text(detail,wrap="none",font=("Consolas",9),padx=12,pady=12)
        sy=ttk.Scrollbar(detail,orient="vertical",command=txt.yview)
        sx=ttk.Scrollbar(detail,orient="horizontal",command=txt.xview)
        txt.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        sy.pack(side="right",fill="y")
        sx.pack(side="bottom",fill="x")
        txt.pack(fill="both",expand=True)

        def display(event=None):
            sel=tree.selection()
            if not sel:return
            item=tree.item(sel[0])
            node_text=item["text"]
            parent=tree.parent(sel[0])
            grand=tree.parent(parent)
            txt.delete("1.0","end")

            if not parent:
                tag=node_text
                title.config(text=f"{tag} — whole font table")
                txt.insert("end",f"Table: {tag}\n")
                txt.insert("end",f"Present: {'YES' if tag in self.font else 'NO'}\n")
                txt.insert("end",f"Decoded features: {len(self.layout_features.get(tag,[]))}\n\n")
                if self.layout_features.get(tag):
                    txt.insert("end","Features:\n"+"  ".join(self.layout_features[tag]))
                else:
                    txt.insert("end","No FeatureRecords decoded. The table may use an unusual/malformed structure.")
                return

            if parent and not grand:
                tag=tree.item(parent)["text"]
                feature=node_text
                indices=self.layout_detail.get((tag,feature),{}).get("lookups",[])
                title.config(text=f"{tag} / {feature}")
                txt.insert("end",f"Feature: {feature}\n")
                txt.insert("end",f"Lookup indexes: {indices}\n\n")
                explanations={
                    "liga":"Standard ligatures","clig":"Contextual ligatures",
                    "calt":"Contextual alternates","kern":"Kerning",
                    "mark":"Mark-to-base positioning","mkmk":"Mark-to-mark positioning",
                    "curs":"Cursive attachment","ccmp":"Glyph composition/decomposition",
                    "locl":"Localized forms","salt":"Stylistic alternates",
                    "swsh":"Swash","cswh":"Contextual swash",
                    "frac":"Fractions","ordn":"Ordinals","numr":"Numerators",
                    "dnom":"Denominators","sups":"Superscripts","subs":"Subscripts"}
                txt.insert("end",explanations.get(feature,"OpenType layout feature")+"\n")
                txt.insert("end","\nExpand a Lookup to inspect its actual records.")
                return

            if parent and grand:
                tag=tree.item(grand)["text"]
                feature=tree.item(parent)["text"]
                try:
                    idx=int(node_text.split()[1])
                except Exception:
                    return
                info=self.layout_lookup_info.get((tag,idx),{})
                title.config(text=f"{tag} / {feature} / Lookup {idx}")
                txt.insert("end",f"Table: {tag}\nFeature: {feature}\n")
                txt.insert("end",f"Lookup index: {idx}\n")
                txt.insert("end",f"Lookup type: {info.get('type','?')}\n")
                txt.insert("end",f"Lookup flag: {info.get('flag',0)}\n")
                txt.insert("end",f"Subtables: {info.get('subtables',0)}\n\n")

                type_names={
                    ("GSUB",1):"Single Substitution",
                    ("GSUB",2):"Multiple Substitution",
                    ("GSUB",3):"Alternate Substitution",
                    ("GSUB",4):"Ligature Substitution",
                    ("GSUB",5):"Contextual Substitution",
                    ("GSUB",6):"Chained Contextual Substitution",
                    ("GSUB",7):"Extension Substitution",
                    ("GSUB",8):"Reverse Chaining Single Substitution",
                    ("GPOS",1):"Single Adjustment",
                    ("GPOS",2):"Pair Adjustment / Kerning",
                    ("GPOS",3):"Cursive Attachment",
                    ("GPOS",4):"Mark-to-Base",
                    ("GPOS",5):"Mark-to-Ligature",
                    ("GPOS",6):"Mark-to-Mark",
                    ("GPOS",7):"Contextual Positioning",
                    ("GPOS",8):"Chained Contextual Positioning",
                    ("GPOS",9):"Extension Positioning"}
                txt.insert("end",type_names.get((tag,info.get("type")),"Unknown / complex lookup"))
                txt.insert("end","\n\n")
                rows=self.decode_lookup(tag,idx)
                if rows:
                    txt.insert("end","\n".join(rows))
                else:
                    txt.insert("end","This lookup is structurally present but does not have a simple decoder yet.")

        tree.bind("<<TreeviewSelect>>",display)

        # Initial selection.
        for tag in ("GSUB","GPOS"):
            if tag in roots:
                children=tree.get_children(roots[tag])
                if children:
                    tree.selection_set(children[0])
                    display()
                    break

    def filtered(self):
        q = self.query.get().strip().casefold()
        b = self.block.get()

        result = []
        for x in self.entries:
            if b != "All Blocks" and x["block"] != b:
                continue

            if q:
                fields = [
                    x["name"],
                    f"{x['cp']:04X}",
                    f"U+{x['cp']:04X}",
                    x["char"],
                    x["block"],
                    x["category"],
                ]
                if not any(q in str(v).casefold() for v in fields):
                    continue
            result.append(x)
        return result

    def render(self):
        if not hasattr(self, "canvas"):
            return

        self.canvas.delete("all")
        data = self.filtered()
        mode = self.view.get()

        if mode == "Test String":
            self.render_test_string(data)
        elif mode == "Paragraph":
            self.render_paragraph(data)
        elif mode == "One per line":
            self.render_lines(data)
        else:
            self.render_map(data)

        self.update_info()

    def render_map(self, data):
        w = max(self.canvas.winfo_width(), 900)
        cols = max(4, int(self.columns.get()))
        cell_w = max(75, (w - 30) // cols)
        cell_h = max(105, int(self.size.get()) + 65)
        gap = int(self.spacing.get()) * 4

        self.glyph_items = []

        for i, x in enumerate(data):
            col = i % cols
            row = i // cols
            x0 = 10 + col * cell_w
            y0 = 10 + row * cell_h
            x1 = x0 + cell_w - gap
            y1 = y0 + cell_h - 5
            selected = x["cp"] in self.selected_cps

            self.canvas.create_rectangle(
                x0, y0, x1, y1,
                outline="#2b78d0" if selected else "#cccccc",
                fill="#dcecff" if selected else "#ffffff",
                width=2 if selected else 1
            )
            self.canvas.create_text(
                (x0 + x1) / 2, y0 + self.size.get() / 2 + 7,
                text=x["char"],
                font=(self.font_box.get(), self.size.get()),
                fill="black"
            )

            labels = []
            if self.show_code.get():
                labels.append(f"U+{x['cp']:04X}")
            if self.show_name.get():
                labels.append(x["name"])

            self.canvas.create_text(
                (x0 + x1) / 2, y0 + cell_h - 25,
                text="\n".join(labels),
                font=("Segoe UI", 8), fill="#555555"
            )

            self.glyph_items.append((x0, y0, x1, y1, x))

        rows = (len(data) + cols - 1) // cols
        self.canvas.configure(
            scrollregion=(0, 0, w, max(100, rows * cell_h + 20))
        )
        self.status.config(
            text=f"{self.font_box.get()}  •  {len(data):,} mapped glyphs shown  •  "
                 f"{len(self.unmapped):,} unmapped glyphs  •  "
                 f"{len(self.selected_cps):,} selected"
        )

    def canvas_click(self, event):
        if self.view.get() != "Glyph Map":
            return
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        for x0, y0, x1, y1, glyph in self.glyph_items:
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                # Normal click selects one glyph. Ctrl-click adds/removes
                # glyphs from the multi-selection.
                ctrl = bool(event.state & 0x0004)
                cp = glyph["cp"]
                if ctrl:
                    if cp in self.selected_cps:
                        self.selected_cps.remove(cp)
                    else:
                        self.selected_cps.add(cp)
                else:
                    self.selected_cps = {cp}

                self.selected_glyph = glyph
                self.render()
                self.update_info(glyph)
                return

    def mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def copy_selected(self, glyph):
        # Kept as a compatibility helper for the single-glyph action.
        if glyph:
            self.selected_cps = {glyph["cp"]}
            self.copy_selected_items()

    def copy_selected_items(self):
        if not self.font:
            return
        if not self.selected_cps:
            self.status.config(text="No glyphs selected.")
            return

        # Keep the font's Unicode order so copied text follows the visible map.
        selected = [x for x in self.entries if x["cp"] in self.selected_cps]
        text = " ".join(x["char"] for x in selected)
        self._copy_text(text, f"Copied {len(selected):,} selected character(s)")

    def render_paragraph(self, data):
        chars = " ".join(x["char"] for x in data)
        self.canvas.create_text(
            20, 20, anchor="nw", text=chars,
            width=max(500, self.canvas.winfo_width() - 50),
            font=(self.font_box.get(), self.size.get())
        )
        self.canvas.configure(
            scrollregion=(0, 0, max(1000, self.canvas.winfo_width()), 5000)
        )
        self.status.config(text=f"{len(data):,} characters • paragraph mode")

    def render_lines(self, data):
        chars = "\n".join(x["char"] for x in data)
        self.canvas.create_text(
            25, 20, anchor="nw", text=chars,
            font=(self.font_box.get(), self.size.get())
        )
        line_height = max(24, int(self.size.get() * 1.25))
        self.canvas.configure(
            scrollregion=(0, 0, 1000, max(500, len(data) * line_height + 50))
        )
        self.status.config(text=f"{len(data):,} characters • one per line")

    def render_test_string(self, data):
        chars = " ".join(x["char"] for x in data)
        self.canvas.create_text(
            25, 25, anchor="nw", text=chars,
            width=max(500, self.canvas.winfo_width() - 50),
            font=(self.font_box.get(), self.size.get())
        )
        self.canvas.configure(
            scrollregion=(0, 0, max(1000, self.canvas.winfo_width()), 6000)
        )
        self.status.config(text=f"{len(data):,} characters • test string mode")

    def update_info(self, selected=None):
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")

        family = self.font_box.get()
        if not self.font:
            self.info.insert("end", "No font loaded.")
            self.info.configure(state="disabled")
            return

        self.info.insert("end", f"{family}\n", "title")
        self.info.insert("end", "\nFont file\n", "section")
        self.info.insert("end", f"{self.font_path}\n\n")

        order = self.font.getGlyphOrder()
        self.info.insert("end", "Font statistics\n", "section")
        self.info.insert("end", f"Mapped Unicode glyphs: {len(self.entries):,}\n")
        self.info.insert("end", f"Unmapped glyphs: {len(self.unmapped):,}\n")
        self.info.insert("end", f"Total glyphs: {len(order):,}\n\n")

        self.info.insert("end", "OpenType tables\n", "section")
        self.info.insert("end", ", ".join(self.tables) + "\n")

        if selected:
            self.info.insert("end", "\nSelected glyph\n", "section")
            self.info.insert("end", f"Character: {selected['char']!r}\n")
            self.info.insert("end", f"Unicode: U+{selected['cp']:04X}\n")
            self.info.insert("end", f"Glyph name: {selected['name']}\n")
            self.info.insert("end", f"Block: {selected['block']}\n")
            self.info.insert("end", f"Category: {selected['category']}\n")

            try:
                gid = order.index(selected["name"])
            except ValueError:
                gid = -1
            self.info.insert("end", f"Glyph ID: {gid}\n")

            if "hmtx" in self.font:
                try:
                    advance, lsb = self.font["hmtx"].metrics[selected["name"]]
                    self.info.insert("end", f"Advance width: {advance}\n")
                    self.info.insert("end", f"Left side bearing: {lsb}\n")
                except Exception:
                    pass

            if "glyf" in self.font:
                try:
                    g = self.font["glyf"][selected["name"]]
                    if g.isComposite():
                        self.info.insert("end", "Contours: composite\n")
                        self.info.insert("end", f"Components: {len(g.components)}\n")
                    else:
                        self.info.insert("end", f"Contours: {g.numberOfContours}\n")
                except Exception:
                    pass

            self.info.insert("end", "\nLayout support\n", "section")
            self.info.insert("end", f"GSUB: {'Yes' if 'GSUB' in self.font else 'No'}\n")
            self.info.insert("end", f"GPOS: {'Yes' if 'GPOS' in self.font else 'No'}\n")
            self.info.insert("end", f"GDEF: {'Yes' if 'GDEF' in self.font else 'No'}\n")

        self.info.tag_configure("title", font=("Segoe UI", 13, "bold"))
        self.info.tag_configure("section", font=("Segoe UI", 9, "bold"))
        self.info.configure(state="disabled")

    def get_mapped_characters(self, mode="printable"):
        """Return mapped Unicode characters.
        mode='printable' removes controls/private-use/format controls.
        mode='all' keeps every Unicode mapping except controls that cannot
        sensibly survive a text clipboard.
        """
        if not self.font:
            return []
        cps=set()
        try:
            for sub in self.font["cmap"].tables:
                if getattr(sub, "isUnicode", lambda: False)():
                    cps.update(sub.cmap.keys())
        except Exception:
            pass

        out=[]
        for cp in sorted(cps):
            try:
                ch=chr(cp)
                cat=unicodedata.category(ch)
                if cat in ("Cc","Cs","Co","Cf"):
                    continue
                if mode=="printable" and not ch.isprintable():
                    continue
                out.append(ch)
            except Exception:
                pass
        return out


    def _copy_text(self,text,label):
        if not text:
            self.status.config(text="Nothing to copy."); return
        try:
            self.clipboard_clear(); self.clipboard_append(text,type="STRING"); self.update_idletasks()
            self.status.config(text=f"{label}: {len(text):,} characters")
        except tk.TclError as exc: messagebox.showerror("Clipboard error",str(exc))

    def copy_characters_menu(self):
        menu=tk.Menu(self, tearoff=0)
        menu.add_command(
            label="Copy Printable Characters",
            command=lambda:self._copy_text(
                " ".join(self.get_mapped_characters("printable")),
                "Copied printable Unicode"))
        menu.add_command(
            label="Copy All Mapped Unicode Characters",
            command=lambda:self._copy_text(
                " ".join(self.get_mapped_characters("all")),
                "Copied all mapped Unicode"))
        menu.add_command(
            label="Copy Unicode + Glyph Names",
            command=self.copy_unicode_with_names)
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()


    def copy_unicode_with_names(self):
        if not self.font:
            return
        cmap=self.font.getBestCmap() or {}
        rows=[]
        for cp,glyph in sorted(cmap.items()):
            try:
                ch=chr(cp)
                if unicodedata.category(ch) in ("Cc","Cs","Co","Cf"):
                    continue
                rows.append(f"{ch}  U+{cp:04X}  {glyph}")
            except Exception:
                pass
        self._copy_text("\n".join(rows),"Copied Unicode + glyph names")


    def copy_all(self):
        return self._copy_text(
            " ".join(self.get_mapped_characters("all")),
            "Copied all mapped Unicode")


    def export_characters_txt(self):
        chars=self.get_mapped_characters(True)
        path=filedialog.asksaveasfilename(title="Export Characters",defaultextension=".txt",filetypes=[("Text files","*.txt")])
        if not path:return
        Path(path).write_text(" ".join(chars),encoding="utf-8")
        self.status.config(text=f"Exported {len(chars):,} printable characters")

    def export_unicode_map_txt(self):
        if not self.font:return
        cmap=self.font.getBestCmap() or {}
        path=filedialog.asksaveasfilename(title="Export Unicode Map",defaultextension=".txt",filetypes=[("Text files","*.txt")])
        if not path:return
        with open(path,"w",encoding="utf-8") as f:
            for cp,glyph in sorted(cmap.items()):
                ch=chr(cp)
                if unicodedata.category(ch) in ("Cc","Cs","Co","Cf"):continue
                f.write(f"{ch}\tU+{cp:04X}\t{unicodedata.name(ch,'<unnamed>')}\t{glyph}\n")
        self.status.config(text="Exported Unicode map")

    def export_txt(self): self.export_characters_txt()

    def export_menu(self):
        menu=tk.Menu(self, tearoff=0)
        menu.add_command(label="Export Characters TXT", command=self.export_characters_txt)
        menu.add_command(label="Export Unicode Map TXT", command=self.export_unicode_map_txt)
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

if __name__ == "__main__":
    app = Inspector()
    app.mainloop()
