"""Geometric contour and Bézier inspection helpers.

All coordinates are returned in the font's native coordinate system (Y up).
This module is read-only: it never mutates glyphs or font tables.
"""
from __future__ import annotations

from math import hypot
from typing import Any

from fontTools.pens.basePen import BasePen


class SegmentRecordingPen(BasePen):
    """Record normalized line/quadratic/cubic segments from a glyph.

    BasePen expands TrueType implied on-curve points and decomposes components
    through the supplied glyph set, while preserving quadratic and cubic types.
    """

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.contours: list[dict[str, Any]] = []
        self._active: dict[str, Any] | None = None
        self._current: tuple[float, float] | None = None

    def _begin_contour(self, point):
        self._active = {"start": [float(point[0]), float(point[1])], "segments": [], "closed": False}
        self._current = (float(point[0]), float(point[1]))

    def _finish_contour(self, closed: bool):
        if self._active is not None:
            self._active["closed"] = bool(closed)
            self.contours.append(self._active)
        self._active = None
        self._current = None

    def _moveTo(self, point):
        if self._active is not None:
            self._finish_contour(False)
        self._begin_contour(point)

    def _lineTo(self, point):
        if self._active is None or self._current is None:
            self._begin_contour(point)
            return
        end = (float(point[0]), float(point[1]))
        self._active["segments"].append({
            "type": "line", "start": list(self._current), "controls": [], "end": list(end)
        })
        self._current = end

    def _curveToOne(self, p1, p2, p3):
        if self._active is None or self._current is None:
            self._begin_contour(p3)
            return
        c1 = (float(p1[0]), float(p1[1]))
        c2 = (float(p2[0]), float(p2[1]))
        end = (float(p3[0]), float(p3[1]))
        self._active["segments"].append({
            "type": "cubic", "start": list(self._current),
            "controls": [list(c1), list(c2)], "end": list(end)
        })
        self._current = end

    def _qCurveToOne(self, p1, p2):
        if self._active is None or self._current is None:
            self._begin_contour(p2)
            return
        control = (float(p1[0]), float(p1[1]))
        end = (float(p2[0]), float(p2[1]))
        self._active["segments"].append({
            "type": "quadratic", "start": list(self._current),
            "controls": [list(control)], "end": list(end)
        })
        self._current = end

    def _closePath(self):
        if self._active is not None and self._current is not None:
            start = tuple(self._active["start"])
            if hypot(self._current[0] - start[0], self._current[1] - start[1]) > 1e-9:
                self._active["segments"].append({
                    "type": "line", "start": list(self._current), "controls": [], "end": list(start),
                    "closing": True
                })
            self._finish_contour(True)

    def _endPath(self):
        self._finish_contour(False)


def _bezier_point(segment: dict[str, Any], t: float) -> tuple[float, float]:
    p0 = segment["start"]
    p1 = segment["controls"]
    p2 = segment["end"]
    u = 1.0 - t
    if segment["type"] == "line":
        return (u * p0[0] + t * p2[0], u * p0[1] + t * p2[1])
    if segment["type"] == "quadratic":
        c = p1[0]
        return (u*u*p0[0] + 2*u*t*c[0] + t*t*p2[0],
                u*u*p0[1] + 2*u*t*c[1] + t*t*p2[1])
    c1, c2 = p1
    return (u**3*p0[0] + 3*u*u*t*c1[0] + 3*u*t*t*c2[0] + t**3*p2[0],
            u**3*p0[1] + 3*u*u*t*c1[1] + 3*u*t*t*c2[1] + t**3*p2[1])


def _flatten_contour(contour: dict[str, Any], steps: int = 12) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for segment in contour["segments"]:
        count = 1 if segment["type"] == "line" else steps
        for i in range(count + 1):
            point = _bezier_point(segment, i / count)
            if not points or hypot(point[0] - points[-1][0], point[1] - points[-1][1]) > 1e-9:
                points.append(point)
    return points


def _signed_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area2 = 0.0
    for i, point in enumerate(points):
        nxt = points[(i + 1) % len(points)]
        area2 += point[0] * nxt[1] - nxt[0] * point[1]
    return area2 / 2.0


def _orientation(a, b, c, eps=1e-8):
    value = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    if abs(value) <= eps:
        return 0
    return 1 if value > 0 else -1


def _on_segment(a, b, p, eps=1e-8):
    return (min(a[0], b[0])-eps <= p[0] <= max(a[0], b[0])+eps and
            min(a[1], b[1])-eps <= p[1] <= max(a[1], b[1])+eps)


def _segments_intersect(a, b, c, d) -> bool:
    o1, o2 = _orientation(a, b, c), _orientation(a, b, d)
    o3, o4 = _orientation(c, d, a), _orientation(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return ((o1 == 0 and _on_segment(a, b, c)) or
            (o2 == 0 and _on_segment(a, b, d)) or
            (o3 == 0 and _on_segment(c, d, a)) or
            (o4 == 0 and _on_segment(c, d, b)))


def _line_segments(points, closed):
    points = list(points)
    if closed and len(points) > 1 and hypot(points[-1][0]-points[0][0], points[-1][1]-points[0][1]) < 1e-8:
        points.pop()  # Do not create a zero-length edge at an already repeated start point.
    pairs = [(points[i], points[i+1], i) for i in range(max(0, len(points)-1))]
    if closed and len(points) > 2:
        pairs.append((points[-1], points[0], len(points)-1))
    return pairs


def analyze_glyph_contours(glyph, glyph_set) -> dict[str, Any]:
    """Return normalized segments, contour winding, and conservative diagnostics."""
    pen = SegmentRecordingPen(glyph_set)
    glyph.draw(pen)
    if pen._active is not None:
        pen._finish_contour(False)

    contours = []
    flattened: list[list[tuple[float, float]]] = []
    diagnostics: list[dict[str, Any]] = []
    total_segments = 0
    for index, contour in enumerate(pen.contours):
        points = _flatten_contour(contour)
        area = _signed_area(points) if contour["closed"] else None
        direction = None if area is None or abs(area) < 1e-7 else ("counter-clockwise" if area > 0 else "clockwise")
        segment_types = {kind: sum(1 for s in contour["segments"] if s["type"] == kind)
                         for kind in ("line", "quadratic", "cubic")}
        degenerate = [i for i, s in enumerate(contour["segments"])
                      if hypot(s["end"][0]-s["start"][0], s["end"][1]-s["start"][1]) < 1e-7
                      and all(hypot(c[0]-s["start"][0], c[1]-s["start"][1]) < 1e-7 for c in s["controls"])]
        if not contour["closed"]:
            diagnostics.append({"severity": "warning", "code": "OPEN_CONTOUR", "contour": index,
                                "message": "Contour ends without a closePath operation."})
        if contour["closed"] and abs(area or 0) < 1e-7:
            diagnostics.append({"severity": "warning", "code": "ZERO_AREA_CONTOUR", "contour": index,
                                "message": "Closed contour has zero or near-zero signed area."})
        if degenerate:
            diagnostics.append({"severity": "warning", "code": "DEGENERATE_SEGMENT", "contour": index,
                                "segments": degenerate,
                                "message": "One or more segments have coincident endpoints and controls."})
        contours.append({
            "index": index, "start": contour["start"], "closed": contour["closed"], "direction": direction,
            "signedArea": area, "segmentCount": len(contour["segments"]),
            "segmentTypes": segment_types, "segments": contour["segments"]
        })
        flattened.append(points)
        total_segments += len(contour["segments"])

    # Conservative boundary-intersection scan. This detects crossings, not filled-area overlap.
    line_data = [_line_segments(points, pen.contours[i]["closed"]) for i, points in enumerate(flattened)]
    self_intersections = 0
    cross_pairs: set[tuple[int, int]] = set()
    intersection_checks = 0
    max_checks = 250_000
    for ci, lines in enumerate(line_data):
        for i, (a, b, ai) in enumerate(lines):
            for c, d, bi in lines[i+1:]:
                if bi <= ai + 1 or (pen.contours[ci]["closed"] and ai == 0 and bi == len(lines)-1):
                    continue
                intersection_checks += 1
                if intersection_checks > max_checks:
                    break
                if _segments_intersect(a, b, c, d):
                    self_intersections += 1
            if intersection_checks > max_checks:
                break
        if intersection_checks > max_checks:
            break
    if intersection_checks <= max_checks:
        for ci in range(len(line_data)):
            for cj in range(ci+1, len(line_data)):
                for a, b, _ in line_data[ci]:
                    for c, d, _ in line_data[cj]:
                        intersection_checks += 1
                        if intersection_checks > max_checks:
                            break
                        if _segments_intersect(a, b, c, d):
                            cross_pairs.add((ci, cj))
                    if intersection_checks > max_checks:
                        break
                if intersection_checks > max_checks:
                    break
            if intersection_checks > max_checks:
                break

    if self_intersections:
        diagnostics.append({"severity": "warning", "code": "SELF_INTERSECTION", "count": self_intersections,
                            "message": "Contour boundary has one or more non-adjacent self-intersections."})
    if cross_pairs:
        diagnostics.append({"severity": "warning", "code": "CONTOUR_INTERSECTION", "pairs": [list(p) for p in sorted(cross_pairs)],
                            "message": "Two or more contour boundaries intersect. This is not a filled-area overlap test."})
    return {
        "coordinateSystem": "font-units-y-up",
        "signedAreaMethod": "12-step sampled Bézier approximation",
        "intersectionMethod": "12-step flattened boundary segment test; not a filled-area overlap test",
        "contourCount": len(contours),
        "segmentCount": total_segments,
        "segmentTypeTotals": {
            "line": sum(c["segmentTypes"]["line"] for c in contours),
            "quadratic": sum(c["segmentTypes"]["quadratic"] for c in contours),
            "cubic": sum(c["segmentTypes"]["cubic"] for c in contours),
        },
        "selfIntersectionCount": self_intersections,
        "intersectingContourPairs": [list(p) for p in sorted(cross_pairs)],
        "diagnostics": diagnostics,
        "intersectionScanTruncated": intersection_checks > max_checks,
        "contours": contours,
    }
