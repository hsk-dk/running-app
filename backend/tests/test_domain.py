import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from app.domain import statuses, timeutil, weekly
from app.domain.runs import actual_value, is_mandatory


# ---- status rules ----------------------------------------------------------

@pytest.mark.parametrize(
    "target, actual, expected",
    [
        (30, 27, "gennemført"),
        (30, 26.9, "forkortet"),
        (30, 15, "forkortet"),
        (30, 14.9, "sprunget over"),
        (None, 30, "sprunget over"),
        (0, 30, "sprunget over"),
    ],
)
def test_compute_status(target, actual, expected):
    assert statuses.compute_status(target, actual) == expected


def test_status_constants_match_enum():
    assert statuses.STATUS_PLANLAGT == statuses.Status.PLANLAGT == "planlagt"
    assert {s.value for s in statuses.Status} >= {
        "planlagt", "gennemført", "forkortet", "sprunget over", "flyttet", "ekstra",
    }


def test_ratio_logic_is_defined_in_one_place():
    app_dir = Path(__file__).resolve().parents[1] / "app"
    offenders = [
        p.name
        for p in app_dir.rglob("*.py")
        if "ratio >= 0.9" in p.read_text() or "ratio >= 0.5" in p.read_text()
    ]
    assert offenders == []


def test_actual_value_units():
    assert actual_value("distance", 10000, 3600) == 10.0
    assert actual_value("time", 10000, 3600) == 60.0
    assert actual_value(None, None, None) == 0.0


def test_is_mandatory_treats_null_as_mandatory():
    assert is_mandatory({"mandatory": None}) is True
    assert is_mandatory({"mandatory": 1}) is True
    assert is_mandatory({"mandatory": 0}) is False


# ---- weekly summary ----------------------------------------------------------

TODAY = date(2020, 3, 12)  # Thursday


def _summary(*pairs):
    return weekly.summarize(list(pairs), TODAY)


def test_window_open_through_last_tolerance_day():
    planned = date(2020, 3, 10)
    assert weekly.window_open(planned, date(2020, 3, 11))
    assert weekly.window_open(planned, date(2020, 3, 11), 1)
    assert not weekly.window_open(planned, date(2020, 3, 12))


def test_summarize_counts_open_planned_as_awaiting_not_relevant():
    s = _summary((date(2020, 3, 12), "planlagt"), (date(2020, 3, 9), "gennemført"))
    assert (s["relevant_runs"], s["awaiting"], s["completed"]) == (1, 1, 1)


def test_summarize_expired_planned_is_relevant():
    s = _summary((date(2020, 3, 9), "planlagt"))
    assert (s["relevant_runs"], s["awaiting"], s["completed"]) == (1, 0, 0)


def test_shortened_run_gives_partial_credit():
    s = _summary((date(2020, 3, 9), "gennemført"), (date(2020, 3, 10), "forkortet"))
    assert weekly.adherence_pct(s) == 75  # (1 + 0.5) / 2


@pytest.mark.parametrize(
    "statuses_, pct, score",
    [
        (["gennemført", "gennemført"], 100, "Grøn"),
        (["gennemført", "forkortet"], 75, "Gul"),
        (["forkortet", "sprunget over"], 25, "Gul"),
        (["sprunget over", "sprunget over"], 0, "Rød"),
    ],
)
def test_adherence_and_score_share_one_summary(statuses_, pct, score):
    s = _summary(*[(date(2020, 3, 9), st) for st in statuses_])
    assert (weekly.adherence_pct(s), weekly.score(s)) == (pct, score)


def test_nothing_due_yet_is_green_with_zero_adherence():
    s = _summary((date(2020, 3, 12), "planlagt"))
    assert weekly.score(s) == "Grøn" and weekly.adherence_pct(s) == 0


def test_iso_week_key():
    assert weekly.iso_week_key(date(2020, 3, 9)) == "2020-W11"
    assert weekly.iso_week_key(date(2021, 1, 3)) == "2020-W53"


# ---- time zone --------------------------------------------------------------

def test_local_date_prefers_strava_local_time():
    row = {"start_date": "2020-03-10T23:30:00Z", "start_date_local": "2020-03-11T00:30:00Z"}
    assert timeutil.activity_local_date(row) == date(2020, 3, 11)


def test_local_date_falls_back_to_converted_utc():
    # 23:30 UTC in winter is already the next day in Copenhagen (UTC+1)
    row = {"start_date": "2020-01-10T23:30:00Z", "start_date_local": None}
    assert timeutil.activity_local_date(row) == date(2020, 1, 11)


def test_local_date_handles_missing_and_bad_values():
    assert timeutil.activity_local_date({"start_date": None, "start_date_local": None}) is None
    assert timeutil.activity_local_date({"start_date": "garbage"}) is None


def test_parse_planned_date_accepts_date_and_datetime():
    assert timeutil.parse_planned_date("2020-03-10") == date(2020, 3, 10)
    assert timeutil.parse_planned_date("2020-03-10T12:00:00") == date(2020, 3, 10)


def test_today_follows_app_timezone(monkeypatch):
    monkeypatch.setattr(timeutil.settings, "APP_TIMEZONE", "Pacific/Auckland")
    auckland = timeutil.local_now()
    monkeypatch.setattr(timeutil.settings, "APP_TIMEZONE", "Pacific/Honolulu")
    honolulu = timeutil.local_now()
    assert auckland.utcoffset() != honolulu.utcoffset()


def test_invalid_timezone_falls_back_to_utc(monkeypatch):
    monkeypatch.setattr(timeutil.settings, "APP_TIMEZONE", "Not/AZone")
    assert timeutil.local_now().utcoffset().total_seconds() == 0


# ---- pandas is gone -----------------------------------------------------------

def test_app_does_not_import_pandas():
    backend = Path(__file__).resolve().parents[1]
    code = "import sys, app.main; sys.exit(1 if 'pandas' in sys.modules else 0)"
    env = {"DATABASE_PATH": "/tmp/unused.db", "PATH": "/usr/bin"}
    result = subprocess.run([sys.executable, "-c", code], cwd=backend, env=env, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_requirements_do_not_list_pandas():
    reqs = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text().lower()
    assert "pandas" not in reqs
