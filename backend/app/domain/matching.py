"""Pure scoring of how well an activity fits a planned run (no database access)."""
from __future__ import annotations

from datetime import date
from typing import Mapping

from app.domain.runs import actual_value as compute_actual_value


def candidate_score(
    planned_row: Mapping,
    activity_row: Mapping,
    planned_date: date,
    activity_date: date,
) -> tuple[tuple[float, float, int, str, int], float, str]:
    day_diff = abs((activity_date - planned_date).days)

    target_value = planned_row["target_value"]
    actual_value = compute_actual_value(
        planned_row["target_type"], activity_row["distance_m"], activity_row["moving_time_s"]
    )

    if target_value is not None and float(target_value) > 0:
        value_diff = abs(actual_value - float(target_value))
    else:
        value_diff = 9999.0

    long_penalty = 0
    long_reason = ""
    if (planned_row["session_type"] or "").lower() == "long":
        target_amount = float(target_value or 0.0)
        if target_amount > 0 and actual_value < (target_amount * 0.8):
            long_penalty = 50
            long_reason = " + straf for kort langtur"

    score_tuple = (
        float(day_diff),
        float(value_diff),
        int(long_penalty),
        str(activity_row["start_date"]),
        int(activity_row["id"]),
    )

    flat_score = float(day_diff * 1000) + float(value_diff * 10) + float(long_penalty)

    if target_value is not None and float(target_value) > 0:
        unit = "km" if planned_row["target_type"] == "distance" else "min"
        reason = (
            f"Valgt pga. datoafstand {day_diff} dag(e) og målafvigelse "
            f"{round(value_diff, 2)} {unit}{long_reason}"
        )
    else:
        reason = f"datoafstand={day_diff} dag(e), intet måltal{long_reason}"

    return score_tuple, flat_score, reason
