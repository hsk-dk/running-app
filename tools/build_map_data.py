"""Builds the two small map files the flight map needs, from Natural Earth (public domain, naturalearthdata.com).

  python tools/build_map_data.py ne_50m_admin_0_countries.geojson ne_10m_populated_places_simple.geojson \\
      ne_10m_admin_0_countries.geojson cities.json

The last two are optional: the 10 m countries give a detailed coast around Denmark (denmark-coast.json), and cities.json
(github.com/lutangar/cities.json, built from GeoNames, CC BY 4.0) gives every Danish town over 1000 inhabitants for place names.

Writes frontend/src/assets/europe-land.json (simplified land outlines) and europe-towns.json (a few big towns for
a fallback place name). Nothing here is fetched by the app: the files are checked in, so no location ever leaves the browser.
"""
import json
import math
import sys
from pathlib import Path

BBOX = (-12.0, 34.0, 34.0, 72.0)  # lon min, lat min, lon max, lat max: Europe without Svalbard
TOLERANCE = 0.02  # degrees: coarse on purpose, the map is a stylised backdrop, not a chart
MIN_RING_AREA = 0.004  # square degrees: drops specks of rock
COAST_BBOX = (6.5, 53.6, 15.8, 58.4)  # Denmark and its neighbouring coasts
COAST_TOLERANCE = 0.0012  # degrees, about 130 m: a clean coast without the 10 m file's jaggedness
COAST_MIN_AREA = 0.00002  # square degrees: keeps small islands, drops rocks
OUT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "assets"


def rdp(points, eps):
    """Ramer-Douglas-Peucker, iterative. A closed ring is split at the point farthest from its start first, because the
    'line' from a ring's first point to its last has no length."""
    if len(points) < 3:
        return points
    if points[0] == points[-1]:
        far = max(range(1, len(points) - 1), key=lambda i: math.hypot(points[i][0] - points[0][0], points[i][1] - points[0][1]))
        return rdp(points[: far + 1], eps) + rdp(points[far:], eps)[1:]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = points[a], points[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        far, idx = 0.0, None
        for i in range(a + 1, b):
            px, py = points[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > far:
                far, idx = d, i
        if idx is not None and far > eps:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(points, keep) if k]


def area(ring):
    return abs(sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))) / 2


def inside(ring):
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return max(xs) >= BBOX[0] and min(xs) <= BBOX[2] and max(ys) >= BBOX[1] and min(ys) <= BBOX[3]


def clip(ring, box):
    """Sutherland-Hodgman clip of a polygon to a box, so a country that continues far outside it costs nothing."""
    def edge(points, inside_fn, cross_fn):
        out = []
        for i, cur in enumerate(points):
            prev = points[i - 1]
            if inside_fn(cur):
                if not inside_fn(prev):
                    out.append(cross_fn(prev, cur))
                out.append(cur)
            elif inside_fn(prev):
                out.append(cross_fn(prev, cur))
        return out

    x0, y0, x1, y1 = box
    pts = ring[:-1] if ring[0] == ring[-1] else ring
    for inside_fn, cross_fn in (
        (lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
        (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1)),
    ):
        if not pts:
            break
        pts = edge(pts, inside_fn, cross_fn)
    return pts + [pts[0]] if pts else []


def build_coast(path):
    """A detailed coast for Denmark only, in thousandths of a degree."""
    rings = []
    for feature in json.load(open(path))["features"]:
        geom = feature["geometry"]
        polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for polygon in polygons:
            outer = polygon[0]
            xs, ys = [p[0] for p in outer], [p[1] for p in outer]
            if max(xs) < COAST_BBOX[0] or min(xs) > COAST_BBOX[2] or max(ys) < COAST_BBOX[1] or min(ys) > COAST_BBOX[3]:
                continue
            clipped = clip([(x, y) for x, y in outer], COAST_BBOX)
            if len(clipped) < 4 or area(clipped) < COAST_MIN_AREA:
                continue
            simple = rdp(clipped, COAST_TOLERANCE)
            if len(simple) >= 4:
                rings.append([round(v * 1000) for p in simple for v in p])
    (OUT / "denmark-coast.json").write_text(json.dumps({"scale": 1000, "bbox": list(COAST_BBOX), "rings": rings}, separators=(",", ":")))
    print(f"{len(rings)} coast rings, {sum(len(r) // 2 for r in rings)} points")


def main(countries_path, places_path, coast_path=None, cities_path=None):
    countries = json.load(open(countries_path))
    rings = []
    for feature in countries["features"]:
        geom = feature["geometry"]
        polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for polygon in polygons:
            outer = polygon[0]  # holes are lakes inside a country: not needed for the look
            if not inside(outer) or area(outer) < MIN_RING_AREA:
                continue
            simple = rdp([(x, y) for x, y in outer], TOLERANCE)
            if len(simple) >= 4:
                rings.append([round(v * 100) for p in simple for v in p])  # hundredths of a degree, flat [lon, lat, ...]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "europe-land.json").write_text(json.dumps({"scale": 100, "rings": rings}, separators=(",", ":")))

    places = json.load(open(places_path))
    towns = []
    for f in places["features"]:
        p = f["properties"]
        lon, lat = p["longitude"], p["latitude"]
        skip = ("DNK",) if cities_path else ()  # GeoNames has far more Danish towns
        if BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3] and p["adm0_a3"] in ("SWE", "NOR", "DEU", "DNK") and p["adm0_a3"] not in skip:
            towns.append({"name": p["name"], "lat": round(lat, 3), "lon": round(lon, 3)})
    if cities_path:
        for c in json.load(open(cities_path)):
            if c["country"] == "DK":
                towns.append({"name": c["name"], "lat": round(float(c["lat"]), 3), "lon": round(float(c["lng"]), 3)})
    if coast_path:
        build_coast(coast_path)
    towns.sort(key=lambda t: t["name"])
    (OUT / "europe-towns.json").write_text(json.dumps(towns, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(rings)} land rings, {sum(len(r) // 2 for r in rings)} points; {len(towns)} towns")


if __name__ == "__main__":
    main(*sys.argv[1:5])
