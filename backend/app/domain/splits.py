"""Kilometer splits from Strava's ``splits_metric``. Pure: no database, no network."""
from __future__ import annotations

from typing import Any

# A split shorter than this is the leftover at the end of a run, not a real kilometre.
FULL_KM_M = 950.0


def parse_splits(raw: Any) -> list[dict]:
    """Turn Strava's splits_metric list into one dict per kilometre. Bad entries are skipped."""
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            distance = float(item.get("distance") or 0)
            time_s = float(item.get("moving_time") or item.get("elapsed_time") or 0)
        except (TypeError, ValueError):
            continue
        if distance <= 0 or time_s <= 0:
            continue
        elevation = item.get("elevation_difference")
        try:
            elevation = round(float(elevation), 1) if elevation is not None else None
        except (TypeError, ValueError):
            elevation = None
        out.append(
            {
                "km": len(out) + 1,
                "distance_m": round(distance, 1),
                "time_s": round(time_s),
                "pace_s_per_km": round(time_s / (distance / 1000.0), 1),
                "elevation_m": elevation,
                "partial": distance < FULL_KM_M,
            }
        )
    return out
