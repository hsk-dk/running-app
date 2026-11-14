"""Builds the two small map files the flight map needs, from Natural Earth (public domain, naturalearthdata.com).

  python tools/build_map_data.py ne_50m_admin_0_countries.geojson ne_10m_populated_places_simple.geojson

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


def main(countries_path, places_path):
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
        if BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3] and p["adm0_a3"] in ("DNK", "SWE", "NOR", "DEU"):
            towns.append({"name": p["name"], "lat": round(lat, 3), "lon": round(lon, 3)})
    towns.sort(key=lambda t: t["name"])
    (OUT / "europe-towns.json").write_text(json.dumps(towns, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(rings)} land rings, {sum(len(r) // 2 for r in rings)} points; {len(towns)} towns")


if __name__ == "__main__":
    main(*sys.argv[1:3])
