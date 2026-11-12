import importlib
from datetime import date

import pytest

from tests.conftest import add_activity, add_plan, get_activity, get_plan


@pytest.fixture()
def matching(db):
    import app.matching

    importlib.reload(app.matching)
    return app.matching


# Dates far in the past so "no match" means the window has expired.
D = "2020-03-10"


def test_exact_match_completes_plan(db, matching):
    plan = add_plan(db, D, target_value=30)
    add_activity(db, 1, f"{D}T08:00:00Z", moving_time_s=1800)

    matching.evaluate_planned_runs()

    p = get_plan(db, plan)
    assert p["matched_activity_id"] == 1
    assert p["status"] == "gennemført"
    assert p["actual_value"] == pytest.approx(30.0)
    assert get_activity(db, 1)["matched_planned_run_id"] == plan
    assert get_activity(db, 1)["is_extra"] == 0


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (1620, "gennemført"),   # 27 min = 90 %
        (1500, "forkortet"),    # 25 min = 83 %
        (900, "forkortet"),     # 15 min = 50 %
        (840, "sprunget over"), # 14 min = 47 %
    ],
)
def test_status_thresholds(db, matching, seconds, expected):
    plan = add_plan(db, D, target_value=30)
    add_activity(db, 1, f"{D}T08:00:00Z", moving_time_s=seconds)

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["status"] == expected


def test_distance_target_uses_km(db, matching):
    plan = add_plan(db, D, target_type="distance", target_value=10)
    add_activity(db, 1, f"{D}T08:00:00Z", distance_m=10000, moving_time_s=3600)

    matching.evaluate_planned_runs()

    p = get_plan(db, plan)
    assert p["actual_value"] == pytest.approx(10.0)
    assert p["status"] == "gennemført"


def test_old_unmatched_plan_is_skipped(db, matching):
    plan = add_plan(db, D)

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["status"] == "sprunget over"


def test_future_unmatched_plan_stays_planned(db, matching):
    plan = add_plan(db, "2100-01-01")

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["status"] == "planlagt"


def test_activity_outside_tolerance_is_not_matched_and_is_extra(db, matching):
    plan = add_plan(db, D)
    add_activity(db, 1, "2020-03-20T08:00:00Z")

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["matched_activity_id"] is None
    assert get_activity(db, 1)["is_extra"] == 1


def test_closest_day_wins(db, matching):
    plan = add_plan(db, "2020-03-10T12:00:00", target_value=30)
    add_activity(db, 1, "2020-03-09T12:00:00Z", moving_time_s=1800)
    add_activity(db, 2, "2020-03-10T12:00:00Z", moving_time_s=1800)

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["matched_activity_id"] == 2


def test_closest_target_wins_on_same_day(db, matching):
    plan = add_plan(db, D, target_value=30)
    add_activity(db, 1, f"{D}T07:00:00Z", moving_time_s=3600)
    add_activity(db, 2, f"{D}T18:00:00Z", moving_time_s=1800)

    matching.evaluate_planned_runs()

    p = get_plan(db, plan)
    assert p["matched_activity_id"] == 2
    assert get_activity(db, 1)["is_extra"] == 1


def test_activity_is_used_by_one_plan_only(db, matching):
    first = add_plan(db, D, target_value=30)
    second = add_plan(db, D, target_value=30)
    add_activity(db, 1, f"{D}T08:00:00Z")

    matching.evaluate_planned_runs()

    assert get_plan(db, first)["matched_activity_id"] == 1
    assert get_plan(db, second)["matched_activity_id"] is None


def test_short_long_run_is_penalised(db, matching):
    plan = add_plan(db, D, session_type="long", target_type="time", target_value=100)
    add_activity(db, 1, f"{D}T07:00:00Z", moving_time_s=60 * 60)  # 60 min, <80 %
    add_activity(db, 2, f"{D}T18:00:00Z", moving_time_s=60 * 95)  # 95 min

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["matched_activity_id"] == 2


def test_non_run_activities_are_ignored(db, matching):
    plan = add_plan(db, D)
    add_activity(db, 1, f"{D}T08:00:00Z", sport_type="Ride")

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["matched_activity_id"] is None


def test_manual_override_is_kept_and_activity_reserved(db, matching):
    add_activity(db, 1, f"{D}T08:00:00Z")
    manual = add_plan(
        db, D, target_value=30, status="gennemført", manual_override=1, matched_activity_id=1
    )
    auto = add_plan(db, D, target_value=30)

    matching.evaluate_planned_runs()

    assert get_plan(db, manual)["matched_activity_id"] == 1
    assert get_plan(db, manual)["status"] == "gennemført"
    assert get_plan(db, auto)["matched_activity_id"] is None


def test_manual_skip_is_not_overwritten(db, matching):
    plan = add_plan(db, D, status="sprunget over", manual_override=1)
    add_activity(db, 1, f"{D}T08:00:00Z")

    matching.evaluate_planned_runs()

    p = get_plan(db, plan)
    assert p["status"] == "sprunget over"
    assert p["matched_activity_id"] is None


def test_rematch_is_idempotent(db, matching):
    plan = add_plan(db, D)
    add_activity(db, 1, f"{D}T08:00:00Z")

    matching.evaluate_planned_runs()
    first = get_plan(db, plan)
    matching.evaluate_planned_runs()
    second = get_plan(db, plan)

    for key in ("matched_activity_id", "status", "actual_value", "match_score"):
        assert first[key] == second[key]


# ---- weekly consistency ----------------------------------------------------

WEEK = ["2020-03-09", "2020-03-11", "2020-03-13"]  # Mon, Wed, Fri of one ISO week


def _week(rows, key="2020-W11"):
    return next(r for r in rows if r["week"] == key)


def test_consistency_empty(db, matching):
    assert matching.get_weekly_consistency() == []


def test_consistency_green_when_all_completed(db, matching):
    for d in WEEK:
        add_plan(db, d, status="gennemført")

    w = _week(matching.get_weekly_consistency())

    assert w["score"] == "Grøn"
    assert (w["completed"], w["relevant_runs"], w["mandatory_runs"]) == (3, 3, 3)


def test_consistency_yellow_when_partly_completed(db, matching):
    add_plan(db, WEEK[0], status="gennemført")
    add_plan(db, WEEK[1], status="forkortet")
    add_plan(db, WEEK[2], status="sprunget over")

    w = _week(matching.get_weekly_consistency())

    assert w["score"] == "Gul"
    assert (w["completed"], w["shortened"]) == (1, 1)


def test_consistency_red_when_nothing_done(db, matching):
    for d in WEEK:
        add_plan(db, d, status="sprunget over")

    assert _week(matching.get_weekly_consistency())["score"] == "Rød"


def test_consistency_ignores_optional_runs(db, matching):
    add_plan(db, WEEK[0], status="gennemført")
    add_plan(db, WEEK[1], status="sprunget over", mandatory=0)

    w = _week(matching.get_weekly_consistency())

    assert w["mandatory_runs"] == 1
    assert w["score"] == "Grøn"


def test_consistency_future_planned_does_not_count(db, matching):
    add_plan(db, "2100-01-05", status="planlagt")

    w = _week(matching.get_weekly_consistency(), key="2100-W01")

    assert w["relevant_runs"] == 0
    assert w["score"] == "Grøn"


# ---- local calendar dates and time zones ---------------------------------------

def _add_local(db, id, utc, local, **kw):
    import json

    conn = db.get_conn()
    try:
        conn.execute(
            """INSERT INTO activities (id, name, sport_type, start_date, start_date_local,
                                       distance_m, moving_time_s, raw_json)
               VALUES (?, 'Run', 'Run', ?, ?, ?, ?, ?)""",
            (id, utc, local, kw.get("distance_m", 5000), kw.get("moving_time_s", 1800), json.dumps({})),
        )
        conn.commit()
    finally:
        conn.close()


def test_run_after_local_midnight_matches_on_local_date(db, matching):
    # 23:30 UTC the evening before is 00:30 local: the local date is the planned date (0 days away)
    plan = add_plan(db, D)
    _add_local(db, 1, "2020-03-09T23:30:00Z", "2020-03-10T00:30:00Z")

    matching.evaluate_planned_runs()

    p = get_plan(db, plan)
    assert p["matched_activity_id"] == 1
    assert "0 dag(e)" in p["match_reason"]
    assert p["matched_activity_date"] == "2020-03-10"


def test_whole_last_tolerance_day_is_inside_window(db, matching):
    # Planned Tue, run late Wed evening: one calendar day away, so inside tolerance=1
    plan = add_plan(db, D)
    _add_local(db, 1, "2020-03-11T21:30:00Z", "2020-03-11T22:30:00Z")

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["matched_activity_id"] == 1


def test_two_calendar_days_away_is_outside_window(db, matching):
    plan = add_plan(db, D)
    _add_local(db, 1, "2020-03-12T00:10:00Z", "2020-03-12T01:10:00Z")

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["matched_activity_id"] is None


def test_plan_stays_open_through_last_tolerance_day(db, matching, monkeypatch):
    from app.domain import timeutil

    plan = add_plan(db, D)
    monkeypatch.setattr(timeutil, "today", lambda: date(2020, 3, 11))
    matching.evaluate_planned_runs()
    assert get_plan(db, plan)["status"] == "planlagt"

    monkeypatch.setattr(timeutil, "today", lambda: date(2020, 3, 12))
    matching.evaluate_planned_runs()
    assert get_plan(db, plan)["status"] == "sprunget over"


def test_invalid_plan_date_does_not_break_evaluation(db, matching):
    bad = add_plan(db, "not-a-date")
    good = add_plan(db, D)
    add_activity(db, 1, f"{D}T08:00:00Z")

    matching.evaluate_planned_runs()

    assert get_plan(db, good)["matched_activity_id"] == 1
    assert get_plan(db, bad)["matched_activity_id"] is None


def test_planned_datetime_string_uses_date_part(db, matching):
    plan = add_plan(db, f"{D}T23:59:00")
    add_activity(db, 1, f"{D}T08:00:00Z")

    matching.evaluate_planned_runs()

    assert get_plan(db, plan)["matched_activity_id"] == 1
