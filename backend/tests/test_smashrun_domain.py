import pytest

from app.domain.smashrun import activity_from_summary, internal_id, smashrun_id

SUMMARY = {
    "activityId": 6482589,
    "startDateTimeLocal": "2026-11-12T17:05:13.000+01:00",
    "distance": 5.63,
    "duration": 2654,
    "heartRateAverage": 127,
    "heartRateMax": 143,
    "cadenceAverage": 81,
    "terrain": "treadmill",
    "notes": "W9 Thu Taper Intervals\nfelt ok",
}


def test_maps_a_summary_to_an_app_activity_in_metres_with_utc_and_local_start():
    a = activity_from_summary(SUMMARY)
    assert a["id"] == -6482589 and a["sport_type"] == "Run"
    assert a["start_date"] == "2026-11-12T16:05:13Z"  # UTC
    assert a["start_date_local"] == "2026-11-12T17:05:13Z"  # wall clock, labelled like Strava does
    assert a["distance"] == pytest.approx(5630.0) and a["moving_time"] == 2654
    assert a["average_heartrate"] == 127 and a["max_heartrate"] == 143
    assert a["name"] == "W9 Thu Taper Intervals"
    assert a["terrain"] == "treadmill"


def test_ids_are_negated_so_they_cannot_collide_with_strava():
    assert internal_id(5) == -5 and internal_id("5") == -5 and smashrun_id(-5) == 5 and smashrun_id(5) == 5


def test_a_missing_offset_is_treated_as_utc_and_summer_time_is_respected():
    a = activity_from_summary({**SUMMARY, "startDateTimeLocal": "2026-07-01T09:00:00"})
    assert a["start_date"] == "2026-07-01T09:00:00Z"
    b = activity_from_summary({**SUMMARY, "startDateTimeLocal": "2026-07-01T09:00:00+02:00"})
    assert b["start_date"] == "2026-07-01T07:00:00Z" and b["start_date_local"] == "2026-07-01T09:00:00Z"


@pytest.mark.parametrize("patch", [{"activityId": None}, {"startDateTimeLocal": None}, {"startDateTimeLocal": "nope"},
                                   {"distance": 0}, {"distance": None}, {"duration": 0}, {"duration": "x"}])
def test_unusable_runs_are_skipped(patch):
    broken = {**SUMMARY, **patch}
    broken = {k: v for k, v in broken.items() if not (k == "activityId" and v is None)}
    assert activity_from_summary(broken) is None


def test_no_notes_means_no_name_and_non_dicts_are_ignored():
    assert activity_from_summary({k: v for k, v in SUMMARY.items() if k != "notes"})["name"] is None
    assert activity_from_summary(None) is None and activity_from_summary("x") is None
