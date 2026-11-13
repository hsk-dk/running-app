"""Runna's calendar link: the plan comes from it, and Runna's names are given to the runs. Synthetic feed, no network."""
from datetime import date, timedelta

import pytest

import app.runna as runna_module
from app.domain import runna as domain
from app.domain import timeutil
from tests.auth_helpers import ADMIN, FAMILY
from tests.conftest import add_activity, add_plan

LINK = "https://cal.runna.com/0123456789abcdef0123456789abcdef.ics"


def _day(offset: int) -> str:
    return (timeutil.today() + timedelta(days=offset)).strftime("%Y%m%d")


def feed(*events: str) -> str:
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Runna//EN\r\n" + "".join(events) + "END:VCALENDAR\r\n"


def upcoming(uid: str, offset: int, title: str, description: str = "", seconds: int | None = None) -> str:
    extra = f"X-WORKOUT-ESTIMATED-DURATION:{seconds}\r\n" if seconds else ""
    return (
        f"BEGIN:VEVENT\r\nUID:UPCOMING_PLAN_WORKOUT-{uid}\r\nDTSTAMP:20260101\r\nDTSTART:{_day(offset)}\r\n"
        f"DTEND:{_day(offset + 1)}\r\nSUMMARY:🏃 {title}\r\nDESCRIPTION:{description}\r\n"
        f"X-USER-TIMEZONE:Europe/Copenhagen\r\n{extra}END:VEVENT\r\n"
    )


def completed(uid: str, day_offset: int, time: str, title: str, kind: str = "COMPLETED_PLAN_WORKOUT") -> str:
    return (
        f"BEGIN:VEVENT\r\nUID:{kind}-{uid}\r\nDTSTAMP:20260101T000000\r\nDTSTART:{_day(day_offset)}T{time}\r\n"
        f"DTEND:{_day(day_offset)}T{time}\r\nSUMMARY:🏃 {title}\r\nDESCRIPTION:Distance: 5.00km\\nTime: 38:50\r\n"
        f"X-USER-TIMEZONE:Europe/Copenhagen\r\nEND:VEVENT\r\n"
    )


RACE = upcoming("w9_RACE_0", 2, "5km Race • 5km", "Race • 5km • 30m20s - 32m30s\\n\\n5km race at 6:05-6:30/km\\n\\n📲 View in the Runna app: https://club.runna.com/x", 2100)


# ---- pure parsing ------------------------------------------------------------------------------

def test_parses_events_and_unescapes_text_and_folded_lines():
    text = "BEGIN:VEVENT\nUID:A-1\nSUMMARY:One\\, two\nDESCRIPTION:line1\\nline\n 2\nEND:VEVENT\n"
    [e] = domain.parse_events(text)
    assert e["SUMMARY"] == "One, two" and e["DESCRIPTION"] == "line1\nline2"


def test_an_escaped_backslash_before_n_is_not_a_newline():
    assert domain.parse_events("BEGIN:VEVENT\nUID:A\nSUMMARY:a\\\\nb\nEND:VEVENT")[0]["SUMMARY"] == "a\\nb"


@pytest.mark.parametrize("title,expected", [
    ("5km Race • 5km", "race"), ("5km Easy Run", "easy"), ("3.5km Easy Run", "easy"), ("8km Hotspot Long Run", "long"),
    ("9km Progressive Repeat Long Run", "long"), ("Tempo 2-1", "tempo"), ("200m Repeats", "intervals"),
    ("Taper 400s", "intervals"), ("Walk Run", "easy"), ("Your First Easy Run Back", "easy"), ("Recovery Run", "recovery"),
    ("Something Brand New", "easy"), ("", "easy"),
])
def test_the_session_type_comes_from_runnas_name_and_unknown_names_are_easy(title, expected):
    assert domain.session_type(title) == expected


def test_planned_runs_take_distance_from_the_title_else_time_from_the_estimate():
    events = domain.parse_events(feed(
        RACE,
        upcoming("a", 3, "6.5km Easy Run", "6.5km at a conversational pace", 2700),
        upcoming("b", 4, "Taper 400s", "warm up", 2640),
        upcoming("c", 5, "Mystery"),
    ))
    by = {p["external_uid"]: p for p in domain.planned_runs(events)}
    race = by["UPCOMING_PLAN_WORKOUT-w9_RACE_0"]
    assert (race["session_type"], race["target_type"], race["target_value"]) == ("race", "distance", 5.0)
    assert "View in the Runna app" not in race["notes"] and "Race • 5km" in race["notes"]
    assert (by["UPCOMING_PLAN_WORKOUT-a"]["target_type"], by["UPCOMING_PLAN_WORKOUT-a"]["target_value"]) == ("distance", 6.5)
    assert (by["UPCOMING_PLAN_WORKOUT-b"]["target_type"], by["UPCOMING_PLAN_WORKOUT-b"]["target_value"]) == ("time", 44.0)
    assert by["UPCOMING_PLAN_WORKOUT-c"]["target_value"] is None and by["UPCOMING_PLAN_WORKOUT-c"]["notes"] == "Mystery"


def test_only_upcoming_entries_become_planned_runs_and_done_ones_give_names():
    events = domain.parse_events(feed(RACE, completed("g1", -3, "170513", "Taper 400s"), completed("g2", -5, "063000", "Morning", "COMPLETED_NON_PLAN_WORKOUT")))
    assert len(domain.planned_runs(events)) == 1
    names = {c["name"]: c["start_local"] for c in domain.completed_runs(events)}
    assert set(names) == {"Taper 400s", "Morning"} and names["Taper 400s"].endswith("T17:05:13Z")


def test_a_utc_start_is_converted_to_the_persons_local_time():
    ev = "BEGIN:VEVENT\nUID:COMPLETED_PLAN_WORKOUT-x\nDTSTART:20260701T060000Z\nSUMMARY:🏃 Run\nX-USER-TIMEZONE:Europe/Copenhagen\nEND:VEVENT"
    assert domain.completed_runs(domain.parse_events(ev))[0]["start_local"] == "2026-07-01T08:00:00Z"


def test_broken_entries_are_skipped_not_fatal():
    ev = "BEGIN:VEVENT\nUID:UPCOMING_PLAN_WORKOUT-x\nDTSTART:garbage\nSUMMARY:Easy\nEND:VEVENT"
    assert domain.planned_runs(domain.parse_events(ev)) == []
    assert domain.parse_events("not a calendar") == []


# ---- the link ------------------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    "http://cal.runna.com/0123456789abcdef.ics", "https://evil.example/0123456789abcdef.ics",
    "https://cal.runna.com.evil.example/0123456789abcdef.ics", "https://cal.runna.com@evil.example/0123456789abcdef.ics",
    "https://user:pw@cal.runna.com/0123456789abcdef.ics", "https://cal.runna.com:8443/0123456789abcdef.ics",
    "https://cal.runna.com/../etc/passwd", "https://cal.runna.com/0123456789abcdef.ics?x=1", "https://cal.runna.com/short.ics",
    "file:///etc/passwd", "", "javascript:alert(1)",
])
def test_only_runnas_own_calendar_address_is_accepted(bad):
    with pytest.raises(runna_module.RunnaLinkError):
        runna_module.check_url(bad)


def test_a_good_link_passes_and_is_trimmed():
    assert runna_module.check_url(f"  {LINK}  ") == LINK


class FakeResponse:
    def __init__(self, status=200, body=b""):
        self.status_code, self._body = status, body
    def iter_content(self, n):
        for i in range(0, len(self._body), n):
            yield self._body[i:i + n]
    def close(self): pass


def test_redirects_errors_and_non_calendars_are_refused(monkeypatch):
    seen = {}
    monkeypatch.setattr(runna_module.requests, "get", lambda url, **k: seen.update(k) or FakeResponse(302))
    with pytest.raises(runna_module.RunnaLinkError, match="302"):
        runna_module.fetch(LINK)
    assert seen["allow_redirects"] is False  # a redirect must never lead the server somewhere else
    monkeypatch.setattr(runna_module.requests, "get", lambda url, **k: FakeResponse(200, b"<html>hello</html>"))
    with pytest.raises(runna_module.RunnaLinkError, match="ikke en kalender"):
        runna_module.fetch(LINK)
    monkeypatch.setattr(runna_module.requests, "get", lambda url, **k: FakeResponse(200, b"x" * (runna_module.MAX_BYTES + 10)))
    with pytest.raises(runna_module.RunnaLinkError, match="stor"):
        runna_module.fetch(LINK)


# ---- through the app --------------------------------------------------------------------------------

@pytest.fixture()
def rn(proxy, db, monkeypatch):
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    state = {"text": feed(RACE)}
    monkeypatch.setattr(runna_module, "fetch", lambda url: state["text"])
    return proxy, state, db


def _plans(client, headers=ADMIN):
    return client.get("/api/planning", headers=headers).json()


def test_connecting_reads_the_plan_right_away_and_keeps_the_link_out_of_every_answer(rn):
    client, _, _ = rn
    r = client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    assert r.status_code == 200 and r.json()["connected"] is True and r.json()["last_sync_at"]
    assert LINK not in r.text and "0123456789abcdef" not in client.get("/api/me", headers=ADMIN).text
    [plan] = _plans(client)
    assert (plan["session_type"], plan["target_value"]) == ("race", 5.0)
    assert client.get("/api/me", headers=FAMILY).json()["runna"]["connected"] is False


def test_a_bad_link_is_refused_and_nothing_is_saved(rn):
    client, _, _ = rn
    r = client.post("/api/runna/link", headers=ADMIN, json={"url": "https://evil.example/0123456789abcdef.ics"})
    assert r.status_code == 409 and client.get("/api/runna/status", headers=ADMIN).json()["connected"] is False


def test_syncing_again_updates_in_place_and_does_not_duplicate(rn):
    client, state, _ = rn
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    state["text"] = feed(upcoming("w9_RACE_0", 3, "5km Race • 5km", "moved a day", 2100))
    result = client.post("/api/runna/sync", headers=ADMIN).json()
    assert (result["planned_added"], result["planned_updated"]) == (0, 1)
    [plan] = _plans(client)
    assert plan["planned_date"] == (timeutil.today() + timedelta(days=3)).isoformat()


def test_a_future_workout_removed_from_the_plan_is_removed_here_too(rn):
    client, state, _ = rn
    state["text"] = feed(RACE, upcoming("a", 4, "5km Easy Run", "", 1800))
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    assert len(_plans(client)) == 2
    state["text"] = feed(RACE)
    assert client.post("/api/runna/sync", headers=ADMIN).json()["planned_removed"] == 1
    assert len(_plans(client)) == 1


def test_hand_edited_matched_and_past_plans_are_never_removed_or_overwritten(rn):
    client, state, db = rn
    state["text"] = feed(RACE, upcoming("a", 4, "5km Easy Run", "", 1800), upcoming("b", 6, "6km Long Run", "", 3000))
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    plans = {p["planned_date"]: p for p in _plans(client)}
    edited = plans[(timeutil.today() + timedelta(days=4)).isoformat()]
    client.put(f"/api/planning/{edited['id']}", headers=ADMIN, json={
        "planned_date": edited["planned_date"], "session_type": "tempo", "target_type": "time", "target_value": 40, "optional": False, "notes": "mine"})
    state["text"] = feed(upcoming("a", 4, "5km Easy Run", "changed", 1800))  # race and 'b' gone, 'a' still there
    client.post("/api/runna/sync", headers=ADMIN)
    after = {p["id"]: p for p in _plans(client)}
    assert after[edited["id"]]["session_type"] == "tempo" and after[edited["id"]]["notes"] == "mine"  # my edit survives
    assert len(after) == 1  # the race and the long run were cancelled in Runna, and nobody had touched them


def test_a_hand_edited_plan_survives_even_when_runna_drops_it(rn):
    client, state, _ = rn
    state["text"] = feed(upcoming("a", 4, "5km Easy Run", "", 1800))
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    [plan] = _plans(client)
    client.put(f"/api/planning/{plan['id']}", headers=ADMIN, json={
        "planned_date": plan["planned_date"], "session_type": "tempo", "target_type": "time", "target_value": 40, "optional": False, "notes": "mine"})
    state["text"] = feed()  # Runna no longer has it
    result = client.post("/api/runna/sync", headers=ADMIN).json()
    assert result["planned_removed"] == 0 and [p["notes"] for p in _plans(client)] == ["mine"]


def test_a_plan_already_matched_to_a_run_survives_when_runna_drops_it(rn):
    client, state, db = rn
    state["text"] = feed(upcoming("a", 0, "5km Easy Run", "", 1800))
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    add_activity(db, 7, f"{timeutil.today().isoformat()}T08:00:00Z", distance_m=5000, moving_time_s=1750, user_id=1)
    client.post("/api/admin/ingest", headers=ADMIN)
    assert _plans(client)[0]["matched_activity_id"] == 7
    state["text"] = feed()
    assert client.post("/api/runna/sync", headers=ADMIN).json()["planned_removed"] == 0
    assert len(_plans(client)) == 1


def test_a_day_the_person_planned_themselves_is_not_overwritten_by_the_import(rn):
    client, _, db = rn
    add_plan(db, (timeutil.today() + timedelta(days=2)).isoformat(), session_type="easy")  # same day as the race
    result = client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    assert result.status_code == 200
    plans = _plans(client)
    assert len(plans) == 1 and plans[0]["session_type"] == "easy"


def test_runs_get_runnas_name_only_when_they_have_none(rn):
    client, state, db = rn
    d = timeutil.today() - timedelta(days=3)
    add_activity(db, 1, f"{d.isoformat()}T15:05:20Z", name="", user_id=1)  # no name; local start differs from UTC
    c = db.get_conn(); c.execute("UPDATE activities SET start_date_local = ? WHERE id = 1", (f"{d.isoformat()}T17:05:13Z",)); c.commit(); c.close()
    add_activity(db, 2, f"{(d - timedelta(days=1)).isoformat()}T05:00:00Z", name="Already named", user_id=1)
    c = db.get_conn(); c.execute("UPDATE activities SET start_date_local = ? WHERE id = 2", (f"{(d - timedelta(days=1)).isoformat()}T07:00:00Z",)); c.commit(); c.close()
    state["text"] = feed(
        completed("g1", -3, "170800", "Taper 400s"),  # 2 min 47 s after the local start: the same run
        completed("g2", -4, "070000", "Renamed by Runna"),
        completed("g3", -3, "090000", "A different run hours earlier"),
    )
    result = client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    names = {a["id"]: a["name"] for a in client.get("/api/activities", headers=ADMIN).json()}
    assert names[1] == "Taper 400s" and names[2] == "Already named"
    assert client.post("/api/runna/sync", headers=ADMIN).json()["named"] == 0  # nothing left to name


def test_each_person_has_their_own_plan_and_link(rn):
    client, _, _ = rn
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    assert len(_plans(client, ADMIN)) == 1 and _plans(client, FAMILY) == []


def test_a_runna_outage_is_recorded_and_reported_with_its_reason(rn, monkeypatch):
    client, _, _ = rn
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    def down(url): raise runna_module.RunnaLinkError("Runna svarede 404. Er linket stadig slået til i Runna?")
    monkeypatch.setattr(runna_module, "fetch", down)
    assert client.post("/api/runna/sync", headers=ADMIN).status_code == 409
    assert "404" in client.get("/api/runna/status", headers=ADMIN).json()["last_error"]


def test_admin_sync_runs_runna_and_its_plan_is_matched_to_runs(rn):
    client, state, db = rn
    d = timeutil.today()
    state["text"] = feed(upcoming("a", 0, "5km Easy Run", "", 1800))
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    add_activity(db, 7, f"{d.isoformat()}T08:00:00Z", distance_m=5000, moving_time_s=1750, user_id=1)
    result = client.post("/api/admin/ingest", headers=ADMIN).json()
    assert "runna" in result
    plan = _plans(client)[0]
    assert plan["matched_activity_id"] == 7 and plan["status"] == "gennemført"


def test_disconnecting_forgets_the_link_but_keeps_the_plan(rn):
    client, _, _ = rn
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    assert client.delete("/api/runna/link", headers=ADMIN).json()["connected"] is False
    assert len(_plans(client)) == 1


# ---- plan workouts that are already done (history) ------------------------------------------------------------

def done(uid, day_offset, time, title, actual_km="5.63", planned="5km easy run at a conversational pace", kind="COMPLETED_PLAN_WORKOUT"):
    desc = f"📊 Summary:\\nDistance: {actual_km}km\\nTime: 44:13\\nAvg Pace: 7:51 /km\\n\\n📋 Description:\\n{planned}\\n\\n♻️ Laps:\\n2.00 km @ 7:44 /km\\n📲 View in the Runna app: https://club.runna.com/x"
    return (
        f"BEGIN:VEVENT\r\nUID:{kind}-{uid}\r\nDTSTAMP:20260101T000000\r\nDTSTART:{_day(day_offset)}T{time}\r\n"
        f"DTEND:{_day(day_offset)}T{time}\r\nSUMMARY:🏃 {title}\r\nDESCRIPTION:{desc}\r\nX-USER-TIMEZONE:Europe/Copenhagen\r\nEND:VEVENT\r\n"
    )


def test_a_done_workout_becomes_a_planned_run_with_the_distance_in_its_name_as_target():
    events = domain.parse_events(feed(
        done("garmin-25033488515", -2, "173857", "5km Easy Run", actual_km="5.01"),
        done("garmin-25056407215", -1, "170513", "Taper 400s", actual_km="5.63", planned="2km warm up\\n\\n5 reps of:\\n• 400m at 9.9kph"),
    ))
    easy, taper = domain.completed_plan_runs(events)
    assert (easy["session_type"], easy["target_type"], easy["target_value"]) == ("easy", "distance", 5.0)  # planned 5 km, ran 5.01
    assert easy["planned_date"] == (timeutil.today() - timedelta(days=2)).isoformat() and easy["garmin_id"] == 25033488515
    assert (taper["session_type"], taper["target_value"]) == ("intervals", 5.63)  # no distance in the name: what was run stands in
    assert taper["notes"].startswith("2km warm up") and "5 reps of:" in taper["notes"]
    assert "Laps" not in taper["notes"] and "View in the Runna app" not in taper["notes"] and "Summary" not in taper["notes"]


def test_only_done_plan_workouts_count_and_ones_without_any_distance_are_skipped():
    events = domain.parse_events(feed(
        RACE,  # upcoming: handled elsewhere
        done("garmin-1", -3, "090000", "Morning", kind="COMPLETED_NON_PLAN_WORKOUT"),  # not part of the plan
        done("garmin-2", -4, "090000", "Mystery Session", actual_km="x"),  # no distance anywhere
        done("garmin-3", -5, "090000", "3.5km Easy Run"),
    ))
    assert [r["external_uid"] for r in domain.completed_plan_runs(events)] == ["COMPLETED_PLAN_WORKOUT-garmin-3"]


def test_a_done_workout_from_another_source_has_no_garmin_id():
    ev = domain.parse_events(feed(done("strava-77", -2, "090000", "5km Easy Run")))
    assert domain.completed_plan_runs(ev)[0]["garmin_id"] is None


def test_history_is_added_when_there_is_a_run_to_match_and_the_plan_page_shows_it_done(rn):
    client, state, db = rn
    day = timeutil.today() - timedelta(days=3)
    add_activity(db, 11, f"{day.isoformat()}T08:00:00Z", distance_m=5010, moving_time_s=2286, user_id=1)
    state["text"] = feed(done("garmin-11", -3, "100000", "5km Easy Run", actual_km="5.01"))
    result = client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    assert result.status_code == 200
    [plan] = _plans(client)
    assert (plan["planned_date"], plan["session_type"], plan["status"], plan["matched_activity_id"]) == (day.isoformat(), "easy", "gennemført", 11)
    sync = client.post("/api/runna/sync", headers=ADMIN).json()
    assert (sync["history_added"], sync["history_kept"]) == (0, 1)  # run again: nothing new, nothing doubled
    assert len(_plans(client)) == 1


def test_history_without_a_run_to_match_is_left_out_so_it_is_not_marked_as_skipped(rn):
    client, state, db = rn
    state["text"] = feed(done("garmin-12", -3, "100000", "5km Easy Run"))
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    assert _plans(client) == []
    assert client.post("/api/runna/sync", headers=ADMIN).json()["history_no_run"] == 1


def test_a_day_that_already_has_a_plan_does_not_get_a_second_one_from_history(rn):
    client, state, db = rn
    day = timeutil.today() - timedelta(days=4)
    add_activity(db, 13, f"{day.isoformat()}T08:00:00Z", distance_m=5000, moving_time_s=1800, user_id=1)
    add_plan(db, day.isoformat(), session_type="tempo")  # the person planned it themselves
    state["text"] = feed(done("garmin-13", -4, "100000", "5km Easy Run"))
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    plans = _plans(client)
    assert len(plans) == 1 and plans[0]["session_type"] == "tempo"
    assert client.post("/api/runna/sync", headers=ADMIN).json()["history_same_day"] == 1


def test_a_workout_that_was_imported_as_upcoming_and_is_now_done_is_not_doubled(rn):
    client, state, db = rn
    day = timeutil.today() - timedelta(days=1)
    add_activity(db, 14, f"{day.isoformat()}T08:00:00Z", distance_m=5000, moving_time_s=1800, user_id=1)
    state["text"] = feed(upcoming("w9_EASY_0", -1, "5km Easy Run", "", 1800))  # still upcoming when first read
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    state["text"] = feed(done("garmin-14", -1, "100000", "5km Easy Run"))  # Runna has since moved it to done
    client.post("/api/runna/sync", headers=ADMIN)
    assert len(_plans(client)) == 1


def test_a_hand_edited_history_row_is_left_alone_by_later_syncs(rn):
    client, state, db = rn
    day = timeutil.today() - timedelta(days=3)
    add_activity(db, 15, f"{day.isoformat()}T08:00:00Z", distance_m=5000, moving_time_s=1800, user_id=1)
    state["text"] = feed(done("garmin-15", -3, "100000", "5km Easy Run"))
    client.post("/api/runna/link", headers=ADMIN, json={"url": LINK})
    [plan] = _plans(client)
    client.put(f"/api/planning/{plan['id']}", headers=ADMIN, json={
        "planned_date": plan["planned_date"], "session_type": "tempo", "target_type": "distance", "target_value": 4.0, "optional": False, "notes": "mine"})
    client.post("/api/runna/sync", headers=ADMIN)
    [after] = _plans(client)
    assert (after["session_type"], after["notes"]) == ("tempo", "mine")
