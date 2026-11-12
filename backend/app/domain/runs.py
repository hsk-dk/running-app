from __future__ import annotations


def actual_value(target_type: str | None, distance_m: float | None, moving_time_s: float | None) -> float:
    """The activity's value in the unit of the plan's target: km for 'distance', minutes otherwise."""
    if (target_type or "time") == "distance":
        return float(distance_m or 0.0) / 1000.0
    return float(moving_time_s or 0.0) / 60.0


def is_mandatory(row) -> bool:
    """`mandatory` is the single source of truth; NULL (legacy rows) means mandatory."""
    value = row["mandatory"]
    return True if value is None else bool(value)
