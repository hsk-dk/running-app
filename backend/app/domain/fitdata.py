"""What a run's FIT file says, boiled down: route, a profile for a chart, kilometre splits and laps.

Pure: it takes plain dicts (already decoded from the file) and returns plain dicts. No file or network access.

A record is {"t": datetime, "lat": deg|None, "lng": deg|None, "distance": m|None, "speed": m/s|None,
"hr": bpm|None, "cadence": steps/min|None, "altitude": m|None}.
A lap is {"start": datetime, "elapsed": s, "distance": m|None, "avg_hr": bpm|None, "avg_speed": m/s|None, "intensity": str|None}.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

MAX_ROUTE_POINTS = 500
MAX_PROFILE_SAMPLES = 300
PARTIAL_KM_MIN_M = 50.0  # a leftover shorter than this is not worth a row
PAUSE_GAP_S = 30.0  # a longer silence with no distance covered is a pause, not running


# ---- polyline (Google's encoding, 5 digits) -----------------------------------------------------------

def _enc(number: int) -> str:
    number = ~(number << 1) if number < 0 else number << 1
    out = ""
    while number >= 0x20:
        out += chr((0x20 | (number & 0x1F)) + 63)
        number >>= 5
    return out + chr(number + 63)


def encode_polyline(points: list[tuple[float, float]]) -> str:
    out, prev_lat, prev_lng = "", 0, 0
    for lat, lng in points:
        la, lo = round(lat * 1e5), round(lng * 1e5)
        out += _enc(la - prev_lat) + _enc(lo - prev_lng)
        prev_lat, prev_lng = la, lo
    return out


def _thin(items: list, limit: int) -> list:
    if len(items) <= limit:
        return items
    step = (len(items) - 1) / (limit - 1)
    return [items[round(i * step)] for i in range(limit)]


def route_polyline(records: list[dict]) -> str | None:
    """The GPS route, or None for a run without positions (a treadmill)."""
    points = [
        (r["lat"], r["lng"])
        for r in records
        if r.get("lat") is not None and r.get("lng") is not None and abs(r["lat"]) <= 90 and abs(r["lng"]) <= 180
    ]
    if len(points) < 2:
        return None
    return encode_polyline(_thin(points, MAX_ROUTE_POINTS))


# ---- distance and time ---------------------------------------------------------------------------------

def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _series(records: list[dict]) -> list[dict]:
    """Records with seconds since start (`s`, pauses removed) and cumulative metres (`d`) on every row."""
    rows = [r for r in records if isinstance(r.get("t"), datetime)]
    rows.sort(key=lambda r: r["t"])
    if not rows:
        return []
    out: list[dict] = []
    moving = 0.0
    dist = 0.0
    prev = None
    for r in rows:
        if r.get("distance") is not None:
            new_dist = float(r["distance"])
        elif prev is not None and r.get("speed") is not None and prev["row"].get("speed") is not None:
            new_dist = dist + float(r["speed"]) * (r["t"] - prev["row"]["t"]).total_seconds()
        elif prev is not None and None not in (r.get("lat"), r.get("lng"), prev["row"].get("lat"), prev["row"].get("lng")):
            new_dist = dist + _haversine_m((prev["row"]["lat"], prev["row"]["lng"]), (r["lat"], r["lng"]))
        else:
            new_dist = dist
        new_dist = max(new_dist, dist)  # distance never goes backwards
        if prev is not None:
            dt = (r["t"] - prev["row"]["t"]).total_seconds()
            if not (dt > PAUSE_GAP_S and new_dist - dist < 1.0):
                moving += max(dt, 0.0)
        dist = new_dist
        entry = {"row": r, "s": moving, "d": dist}
        out.append(entry)
        prev = entry
    return out


def profile(records: list[dict]) -> dict | None:
    """Downsampled series for a chart: seconds, metres, heart rate, speed, cadence, altitude (None where unknown)."""
    series = _series(records)
    if len(series) < 2 or series[-1]["d"] <= 0:
        return None
    sample = _thin(series, MAX_PROFILE_SAMPLES)

    def col(key: str, digits: int):
        vals = [None if e["row"].get(key) is None else round(float(e["row"][key]), digits) for e in sample]
        return vals if any(v is not None for v in vals) else None

    return {
        "t": [round(e["s"]) for e in sample],
        "d": [round(e["d"], 1) for e in sample],
        "hr": col("hr", 0),
        "v": col("speed", 2),
        "cad": col("cadence", 0),
        "alt": col("altitude", 1),
    }


# ---- kilometre splits ------------------------------------------------------------------------------------

def km_splits(records: list[dict]) -> list[dict]:
    """One row per kilometre from the per-second data (same shape as Strava/Smashrun splits, plus average heart rate)."""
    series = _series(records)
    if len(series) < 2 or series[-1]["d"] < PARTIAL_KM_MIN_M:
        return []

    def at(metres: float) -> tuple[float, float | None]:
        """(seconds, altitude) at a distance, interpolated between the two records around it."""
        for i in range(1, len(series)):
            a, b = series[i - 1], series[i]
            if b["d"] >= metres:
                span = b["d"] - a["d"]
                f = 0.0 if span <= 0 else (metres - a["d"]) / span
                alt_a, alt_b = a["row"].get("altitude"), b["row"].get("altitude")
                alt = None if alt_a is None or alt_b is None else alt_a + (alt_b - alt_a) * f
                return a["s"] + (b["s"] - a["s"]) * f, alt
        last = series[-1]
        return last["s"], last["row"].get("altitude")

    total = series[-1]["d"]
    edges = [float(m) for m in range(0, int(total // 1000) * 1000 + 1, 1000)]
    if total - edges[-1] >= PARTIAL_KM_MIN_M:
        edges.append(total)
    out = []
    for i in range(1, len(edges)):
        lo, hi = edges[i - 1], edges[i]
        t0, alt0 = at(lo)
        t1, alt1 = at(hi)
        seconds = t1 - t0
        if seconds <= 0:
            continue
        inside = [e["row"]["hr"] for e in series if lo <= e["d"] <= hi and e["row"].get("hr") is not None]
        metres = hi - lo
        out.append(
            {
                "km": len(out) + 1,
                "distance_m": round(metres, 1),
                "time_s": round(seconds),
                "pace_s_per_km": round(seconds / (metres / 1000.0), 1),
                "elevation_m": None if alt0 is None or alt1 is None else round(alt1 - alt0, 1),
                "partial": metres < 950.0,
                "avg_hr": round(sum(inside) / len(inside)) if inside else None,
            }
        )
    return out


# ---- laps (the steps of an interval workout) -----------------------------------------------------------------

def laps(lap_messages: list[dict], records: list[dict]) -> list[dict]:
    """The watch's own laps. For an interval session these are the work and rest steps."""
    rows = [r for r in records if isinstance(r.get("t"), datetime)]
    t0 = min((r["t"] for r in rows), default=None)
    out = []
    for lap in lap_messages:
        elapsed = lap.get("elapsed")
        if not elapsed or elapsed <= 0:
            continue
        distance = lap.get("distance")
        speed = lap.get("avg_speed")
        pace = None
        if speed and speed > 0.3:
            pace = round(1000.0 / speed, 1)
        elif distance and distance > 0:
            pace = round(elapsed / (distance / 1000.0), 1)
        start = lap.get("start")
        out.append(
            {
                "start_s": round((start - t0).total_seconds()) if isinstance(start, datetime) and t0 else None,
                "duration_s": round(float(elapsed)),
                "distance_m": None if distance is None else round(float(distance), 1),
                "avg_hr": None if lap.get("avg_hr") is None else round(float(lap["avg_hr"])),
                "pace_s_per_km": pace,
                "intensity": lap.get("intensity"),
            }
        )
    return out


def analyze(records: list[dict], lap_messages: list[dict]) -> dict[str, Any]:
    return {
        "route": route_polyline(records),
        "profile": profile(records),
        "splits": km_splits(records),
        "laps": laps(lap_messages, records),
    }
