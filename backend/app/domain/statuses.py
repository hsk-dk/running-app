from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    """Planned-run statuses. The (Danish) values are stored in the database and shown in the UI."""

    PLANLAGT = "planlagt"
    GENNEMFORT = "gennemført"
    FORKORTET = "forkortet"
    SPRUNGET_OVER = "sprunget over"
    FLYTTET = "flyttet"
    EKSTRA = "ekstra"


# Plain strings for SQL parameters and comparisons with database values.
STATUS_PLANLAGT = Status.PLANLAGT.value
STATUS_GENNEMFORT = Status.GENNEMFORT.value
STATUS_FORKORTET = Status.FORKORTET.value
STATUS_SPRUNGET_OVER = Status.SPRUNGET_OVER.value
STATUS_FLYTTET = Status.FLYTTET.value
STATUS_EKSTRA = Status.EKSTRA.value

# Share of the target an activity must reach.
COMPLETED_RATIO = 0.9
SHORTENED_RATIO = 0.5

# How much a shortened run counts towards adherence (a completed run counts 1.0).
SHORTENED_CREDIT = 0.5


def compute_ratio(target_value: float | None, actual_value: float) -> float:
    if not target_value or target_value <= 0:
        return 0.0
    return actual_value / float(target_value)


def compute_status(target_value: float | None, actual_value: float) -> str:
    ratio = compute_ratio(target_value, actual_value)
    if ratio >= COMPLETED_RATIO:
        return STATUS_GENNEMFORT
    if ratio >= SHORTENED_RATIO:
        return STATUS_FORKORTET
    return STATUS_SPRUNGET_OVER
