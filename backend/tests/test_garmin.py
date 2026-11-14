"""Garmin as a source: connecting, reading runs, linking them to runs from other sources, and the FIT file behind each."""
import io
import json
import zipfile
from datetime import datetime, timedelta

import pytest

import app.garmin as garmin_module
from app.domain import garmin as domain
from tests.auth_helpers import ADMIN, FAMILY, patch_settings
from tests.conftest import add_activity
from tests.fit_builder import build_fit

KEY = "gc-personal-key-0123456789abcdef"
UTC_START = datetime(2026, 11, 12, 16, 5, 13)


def treadmill_fit(seconds=1500, speed=2.8):
    rows, dist = [], 0.0
    for s in range(seconds + 1):
        rows.append({"t": UTC_START + timedelta(seconds=s), "lat": None, "lng": None, "altitude": None, "hr": 130 + s // 100,
                     "cadence": 80, "distance": dist, "speed": speed})
        dist += speed
    laps = [{"start": UTC_START, "elapsed": 300, "distance": 840.0, "avg_hr": 128, "avg_speed": 2.8, "intensity": 2},
            {"start": UTC_START + timedelta(seconds=300), "elapsed": 120, "distance": 500.0, "avg_hr": 150, "avg_speed": 4.2, "intensity": 0}]
    return build_fit(rows, laps)


def outdoor_fit(seconds=400):
    rows, dist = [], 0.0
    for s in range(seconds + 1):
        rows.append({"t": UTC_START + timedelta(seconds=s), "lat": 55.676 + s * 1e-5, "lng": 12.568, "altitude": 10.0, "hr": 140,
                     "cadence": 82, "distance": dist, "speed": 3.0})
        dist += 3.0
    return build_fit(rows)


def zipped(fit_bytes):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.fit", fit_bytes)
    return buf.getvalue()


def summary(gid, local="2026-11-12 17:05:13", gmt="2026-11-12 16:05:13", kind="treadmill_running", distance=5630.5, duration=2653.7, **extra):
    return {"activityId": gid, "activityName": f"Run {gid}", "startTimeLocal": local, "startTimeGMT": gmt,
            "activityType": {"typeKey": kind}, "distance": distance, "duration": duration, "averageHR": 127.0, "maxHR": 143.0,
            "elevationGain": 12.0, **extra}


# ---- the mapping (pure) --------------------------------------------------------------------------------

def test_a_garmin_activity_becomes_an_app_run_with_utc_and_local_start():
    a = domain.activity_from_summary(summary(25056407215))
    assert a["id"] == -(10**12 + 25056407215) and a["garmin_id"] == 25056407215 and a["sport_type"] == "Run"
    assert (a["start_date"], a["start_date_local"]) == ("2026-11-12T16:05:13Z", "2026-11-12T17:05:13Z")
    assert a["distance"] == 5630.5 and a["moving_time"] == 2654 and a["average_heartrate"] == 127.0 and a["treadmill"] is True
    assert a["name"] == "Run 25056407215" and a["total_elevation_gain"] == 12.0


def test_the_curated_shape_is_understood_too_and_utc_is_worked_out_when_missing():
    a = domain.activity_from_summary({"id": 5, "name": "x", "type": "running", "start_time": "2026-07-01 09:00:00",
                                      "distance_meters": 4000, "duration_seconds": 1800, "avg_hr_bpm": 130})
    assert a["start_date"] == "2026-07-01T07:00:00Z" and a["start_date_local"] == "2026-07-01T09:00:00Z"  # summer time
    assert a["treadmill"] is False


@pytest.mark.parametrize("patch", [{"kind": "cycling"}, {"kind": "walking"}, {"kind": "indoor_rowing"}, {"distance": 0}, {"duration": None},
                                   {"local": "garbage"}, {"local": None}])
def test_other_sports_and_unusable_entries_are_not_runs(patch):
    assert domain.activity_from_summary(summary(1, **patch)) is None


@pytest.mark.parametrize("kind,group", [("walking", "Walk"), ("hiking", "Walk"), ("road_biking", "Ride"), ("cycling", "Ride"), ("indoor_rowing", "Row"),
                                        ("kayaking_v2", "Paddle"), ("lap_swimming", "Swim"), ("strength_training", "Strength"), ("something_new", "Other"), (None, "Other")])
def test_every_other_activity_type_lands_in_a_group(kind, group):
    assert domain.category_of(kind) == group


def test_other_activities_are_kept_without_a_distance_but_never_as_runs():
    a = domain.other_from_summary(summary(2, kind="strength_training", distance=0))
    assert a["sport_type"] == "Strength" and a["distance"] == 0.0 and a["id"] == domain.internal_id(2) and a["treadmill"] is False
    assert domain.other_from_summary(summary(3, kind="treadmill_running")) is None  # that is a run
    assert domain.other_from_summary(summary(4, kind="walking", duration=None)) is None
    assert domain.other_from_summary(summary(5, kind="walking", local="garbage")) is None
    assert domain.other_from_summary("nope") is None


def test_ids_cannot_collide_with_strava_or_smashrun():
    assert domain.internal_id(1) < -(10**11) and domain.garmin_id_of(domain.internal_id(777)) == 777
    assert domain.garmin_id_of(-6482589) is None and domain.garmin_id_of(17000000000) is None  # a Smashrun and a Strava id


# ---- through the app ------------------------------------------------------------------------------------

@pytest.fixture()
def gc(proxy, db, monkeypatch):
    import app.services.garmin_service as svc

    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    state = {"pages": [[summary(1001, kind="treadmill_running"), summary(1002, local="2026-11-10 17:38:57", gmt="2026-11-10 16:38:57", kind="running"), summary(9, kind="cycling")]],
             "calls": [], "bad_key": False, "files": {1001: zipped(treadmill_fit()), 1002: zipped(outdoor_fit())}, "downloads": [], "down": False, "login": 0}

    def exchange(key):
        state["login"] += 1
        if state["bad_key"]:
            raise garmin_module.GarminAuthError("Garmin afviste nøglen.")
        return "bearer-token", 9999999999

    class FakeClient:
        def __init__(self, api_key, bearer=None, expires_at=None, on_token=None):
            self.key = api_key

        def search_activities(self, start=0, limit=100, start_date=None, end_date=None):
            state["calls"].append({"start": start, "limit": limit, "start_date": start_date})
            if state["down"]:
                raise RuntimeError("garmin is down")
            index = start // garmin_module.PAGE_SIZE
            return state["pages"][index] if index < len(state["pages"]) else []

        def download_activity(self, gid):
            state["downloads"].append(gid)
            if state["down"]:
                raise RuntimeError("garmin is down")
            return state["files"].get(gid)

    monkeypatch.setattr(svc.garmin, "exchange_key", exchange)
    monkeypatch.setattr(svc.garmin, "GarminClient", FakeClient)
    return proxy, state, svc


def connect(client, key=KEY, headers=ADMIN):
    return client.post("/api/garmin/key", headers=headers, json={"key": key})


def runs(client, headers=ADMIN):
    return {a["id"]: a for a in client.get("/api/activities", headers=headers).json()}


def test_connecting_saves_the_key_hides_it_and_reads_the_whole_history(gc):
    client, state, _ = gc
    r = connect(client, f'  "{KEY}"  ')
    assert r.status_code == 200 and r.json()["connected"] is True
    assert KEY not in r.text and KEY not in client.get("/api/me", headers=ADMIN).text
    assert state["calls"][0]["start_date"] is None  # the first sync has no date limit
    got = runs(client)
    assert set(got) == {domain.internal_id(1001), domain.internal_id(1002)}  # the bike ride is not a run
    assert client.get("/api/me", headers=FAMILY).json()["garmin"]["connected"] is False


def test_a_key_garmin_does_not_accept_is_refused_with_the_reason_and_nothing_is_saved(gc):
    client, state, _ = gc
    state["bad_key"] = True
    r = connect(client)
    assert r.status_code == 409 and "afviste" in r.json()["detail"]
    assert connect(client, "no spaces allowed!").status_code == 409
    assert connect(client, "short").status_code == 409
    assert client.get("/api/me", headers=ADMIN).json()["garmin"]["connected"] is False


def test_garmin_being_down_while_connecting_is_a_502_with_the_reason(gc):
    client, state, _ = gc
    state["down"] = True
    r = connect(client)
    assert r.status_code == 502 and "garmin is down" in r.json()["detail"]


def test_a_run_already_stored_from_another_source_is_linked_not_added_twice(gc):
    client, _, _ = gc
    # the same treadmill run from Smashrun: the wall-clock start is within two minutes
    add_activity(db_of(client), -555, "2026-11-12T16:05:40Z", distance_m=5600, moving_time_s=2640, name="Smashrun copy")
    c = db_of(client).get_conn(); c.execute("UPDATE activities SET start_date_local = '2026-11-12T17:05:40Z', source = 'smashrun' WHERE id = -555"); c.commit(); c.close()
    connect(client)
    got = runs(client)
    assert -555 in got and domain.internal_id(1001) not in got  # no second copy
    c = db_of(client).get_conn(); linked = c.execute("SELECT garmin_id FROM activities WHERE id = -555").fetchone()[0]; c.close()
    assert linked == 1001


def db_of(client):
    import app.db as dbmod
    return dbmod


def test_syncing_again_adds_only_what_is_new_and_reads_incrementally(gc):
    client, state, _ = gc
    connect(client)
    state["calls"].clear()
    state["pages"] = [[summary(1003, local="2026-11-13 08:00:00", gmt="2026-11-13 07:00:00", kind="running"), summary(1001)]]
    result = client.post("/api/admin/ingest", headers=ADMIN).json()["garmin"]
    assert (result["added"], result["updated"]) == (1, 1)
    assert state["calls"][0]["start_date"] is not None  # only a little before the last sync, not the whole history
    assert len(runs(client)) == 3


def test_every_page_is_read(gc, monkeypatch):
    client, state, svc = gc
    monkeypatch.setattr(garmin_module, "PAGE_SIZE", 2)
    state["pages"] = [[summary(1, local="2026-01-01 08:00:00", gmt="2026-01-01 07:00:00"), summary(2, local="2026-01-02 08:00:00", gmt="2026-01-02 07:00:00")],
                      [summary(3, local="2026-01-03 08:00:00", gmt="2026-01-03 07:00:00")]]
    connect(client)
    assert [c["start"] for c in state["calls"][1:]] == [0, 2]  # the validation call, then both pages
    assert len(runs(client)) == 3


def test_outdoor_runs_get_their_file_read_at_once_and_treadmill_runs_wait_until_opened(gc):
    client, state, _ = gc
    connect(client)
    assert state["downloads"] == [1002]  # the outdoor run only
    detail = client.get(f"/api/activities/{domain.internal_id(1002)}", headers=ADMIN).json()
    assert detail["route"]  # the GPS route came from the file
    assert client.get(f"/api/activities/{domain.internal_id(1001)}", headers=ADMIN).json()["route"] is None


def test_opening_a_treadmill_run_reads_its_file_once_and_gives_profile_laps_and_splits(gc):
    client, state, _ = gc
    connect(client)
    rid = domain.internal_id(1001)
    p = client.get(f"/api/activities/{rid}/profile", headers=ADMIN).json()
    assert p["available"] is True and p["source"] is True
    assert p["profile"]["hr"][0] == 130 and p["profile"]["d"][-1] == pytest.approx(4200, abs=5)
    assert [round(l["duration_s"]) for l in p["laps"]] == [300, 120] and p["laps"][1]["avg_hr"] == 150
    client.get(f"/api/activities/{rid}/profile", headers=ADMIN)
    assert state["downloads"].count(1001) == 1  # kept after the first read
    splits = client.get(f"/api/activities/{rid}/splits", headers=ADMIN).json()
    assert splits["available"] is True and [s["km"] for s in splits["splits"]] == [1, 2, 3, 4, 5]
    assert splits["splits"][0]["avg_hr"] is not None and splits["splits"][-1]["partial"] is True
    assert state["downloads"].count(1001) == 1


def fit_status(rid):
    import app.db as dbmod
    c = dbmod.get_conn()
    try:
        return c.execute("SELECT fit_status FROM activities WHERE id = ?", (rid,)).fetchone()[0]
    finally:
        c.close()


def test_a_run_garmin_has_no_file_for_is_marked_and_not_asked_again(gc):
    client, state, _ = gc
    connect(client)
    state["files"][1001] = None
    rid = domain.internal_id(1001)
    assert fit_status(rid) is None  # not read yet
    p = client.get(f"/api/activities/{rid}/profile", headers=ADMIN).json()
    assert p["available"] is True and p["profile"] is None and p["laps"] == []
    assert fit_status(rid) == "none"
    client.get(f"/api/activities/{rid}/profile", headers=ADMIN)
    assert state["downloads"].count(1001) == 1


def test_a_successful_read_is_marked_ok(gc):
    client, _, _ = gc
    connect(client)
    rid = domain.internal_id(1001)
    client.get(f"/api/activities/{rid}/profile", headers=ADMIN)
    assert fit_status(rid) == "ok"


def test_a_route_a_run_already_has_is_not_replaced_by_a_later_read(gc):
    client, _, _ = gc
    connect(client)  # the outdoor run's file was read at once and gave it a route
    rid = domain.internal_id(1002)
    import app.db as dbmod
    c = dbmod.get_conn(); c.execute("UPDATE activities SET route_polyline = 'KEEPME', fit_status = NULL WHERE id = ?", (rid,)); c.commit(); c.close()
    client.get(f"/api/activities/{rid}/profile", headers=ADMIN)  # reads the file again
    assert client.get(f"/api/activities/{rid}", headers=ADMIN).json()["route"] == "KEEPME"


def test_splits_asked_for_first_are_read_from_the_file_without_the_profile_having_been_opened(gc):
    client, state, _ = gc
    connect(client)
    rid = domain.internal_id(1001)
    s = client.get(f"/api/activities/{rid}/splits", headers=ADMIN).json()
    assert s["available"] is True and len(s["splits"]) == 5 and s["splits"][0]["avg_hr"] is not None
    assert state["downloads"].count(1001) == 1 and fit_status(rid) == "ok"


def test_garmin_trouble_while_opening_a_run_is_not_remembered(gc):
    client, state, _ = gc
    connect(client)
    rid = domain.internal_id(1001)
    state["down"] = True
    assert client.get(f"/api/activities/{rid}/profile", headers=ADMIN).json()["available"] is False
    assert client.get(f"/api/activities/{rid}/splits", headers=ADMIN).json()["available"] is False
    state["down"] = False
    assert client.get(f"/api/activities/{rid}/profile", headers=ADMIN).json()["profile"] is not None


def test_a_damaged_file_is_marked_unusable_instead_of_failing_every_time(gc):
    client, state, _ = gc
    connect(client)
    state["files"][1001] = zipped(b"this is not a fit file")
    rid = domain.internal_id(1001)
    assert client.get(f"/api/activities/{rid}/profile", headers=ADMIN).json()["profile"] is None
    client.get(f"/api/activities/{rid}/profile", headers=ADMIN)
    assert state["downloads"].count(1001) == 1


def test_a_run_from_another_source_without_a_garmin_link_has_no_profile(gc):
    client, _, db = gc
    add_activity(db, 77, "2026-01-01T08:00:00Z")
    r = client.get("/api/activities/77/profile", headers=ADMIN).json()
    assert (r["available"], r["source"], r["profile"]) == (True, False, None)
    assert client.get("/api/activities/999/profile", headers=ADMIN).status_code == 404


def test_the_route_poster_includes_routes_read_from_files(gc):
    client, _, _ = gc
    connect(client)
    assert [r["id"] for r in client.get("/api/activities/routes", headers=ADMIN).json()] == [domain.internal_id(1002)]


def test_each_person_only_sees_their_own_garmin_runs_and_profiles(gc):
    client, _, _ = gc
    connect(client, headers=ADMIN)
    assert runs(client, FAMILY) == {}
    rid = domain.internal_id(1001)
    assert client.get(f"/api/activities/{rid}/profile", headers=FAMILY).status_code == 404
    assert client.get(f"/api/activities/{rid}/splits", headers=FAMILY).status_code == 404


def test_family_sees_profile_and_splits_without_heart_rate_and_only_when_everything_is_shared(gc):
    client, _, _ = gc
    connect(client, headers=FAMILY)
    rid = domain.internal_id(1001)
    for path in (f"/api/family/2/activities/{rid}/profile", f"/api/family/2/activities/{rid}/splits"):
        assert client.get(path, headers=ADMIN).status_code == 403  # private by default
    client.put("/api/me", headers=FAMILY, json={"sharing_level": "overview"})
    assert client.get(f"/api/family/2/activities/{rid}/profile", headers=ADMIN).status_code == 403
    client.put("/api/me", headers=FAMILY, json={"sharing_level": "all"})
    p = client.get(f"/api/family/2/activities/{rid}/profile", headers=ADMIN).json()
    assert p["profile"]["hr"] is None and p["profile"]["v"] and all(l["avg_hr"] is None for l in p["laps"])
    s = client.get(f"/api/family/2/activities/{rid}/splits", headers=ADMIN).json()
    assert s["splits"] and all(x["avg_hr"] is None for x in s["splits"])
    own = client.get(f"/api/activities/{rid}/profile", headers=FAMILY).json()
    assert own["profile"]["hr"] is not None  # you still see your own heart rate


def test_garmin_refusing_the_key_during_a_sync_shows_its_reason(gc):
    client, state, svc = gc
    connect(client)

    def refuse(*a, **k): raise garmin_module.GarminAuthError("Garmin afviser adgangen. Er nøglen udløbet eller slettet?")
    svc_client = svc.garmin.GarminClient
    svc_client.search_activities = refuse
    r = client.post("/api/admin/ingest", headers=ADMIN)
    assert r.status_code == 502 and "udløbet" in r.json()["detail"]
    assert "udløbet" in client.get("/api/admin/status", headers=ADMIN).json()["last_error"]["value"]


def test_disconnecting_forgets_the_key_but_keeps_the_runs(gc):
    client, _, _ = gc
    connect(client)
    assert client.delete("/api/garmin/connection", headers=ADMIN).json()["connected"] is False
    assert len(runs(client)) == 2


# ---- the real client, with Garmin's HTTP replaced ----------------------------------------------------------

class Resp:
    def __init__(self, status=200, payload=None, text="", content=b""):
        self.status_code, self._p, self.text, self.content = status, payload, text, content
        self.ok = status < 400
    def json(self): return self._p


def jwt(exp):
    import base64
    body = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"h.{body}.s"


def test_the_key_is_swapped_for_a_token_the_way_garmins_own_client_does_it(monkeypatch):
    sent = {}
    monkeypatch.setattr(garmin_module.requests, "post", lambda url, headers, timeout: sent.update(url=url, headers=headers) or Resp(text=jwt(1900000000) + "\n"))
    token, exp = garmin_module.exchange_key("KEY123456")
    assert token == jwt(1900000000) and exp == 1900000000
    assert sent["url"] == "https://personal.connectapi.garmin.com/personalapitoken-service/personal-api/personal-api-key/token"
    assert sent["headers"]["Authorization"] == "ApiKey KEY123456"


@pytest.mark.parametrize("status", [400, 401, 403])
def test_a_refused_key_is_an_auth_error(monkeypatch, status):
    monkeypatch.setattr(garmin_module.requests, "post", lambda *a, **k: Resp(status))
    with pytest.raises(garmin_module.GarminAuthError):
        garmin_module.exchange_key("KEY123456")


def test_the_client_asks_for_a_new_token_when_one_is_about_to_run_out_and_retries_once_on_401(monkeypatch):
    import time
    posts, gets = [], []
    monkeypatch.setattr(garmin_module.requests, "post", lambda url, headers, timeout: posts.append(1) or Resp(text=jwt(int(time.time()) + 86400)))
    answers = iter([Resp(401), Resp(200, [])])
    monkeypatch.setattr(garmin_module.requests, "get", lambda url, params, headers, timeout: gets.append((url, params, headers)) or next(answers))
    saved = []
    client = garmin_module.GarminClient("KEY123456", "old", int(time.time()) + 100, on_token=lambda *t: saved.append(t))  # < 1 h left
    assert client.search_activities(0, 50, start_date="2026-11-01") == []
    assert len(posts) == 2 and len(saved) == 2  # one because it was nearly out, one because of the 401
    assert gets[0][1] == {"start": 0, "limit": 50, "startDate": "2026-11-01"}
    assert gets[0][0].endswith("/activitylist-service/activities/search/activities") and gets[0][2]["Authorization"].startswith("Bearer ")


def test_downloads_return_the_zip_or_none_and_errors_are_clear(monkeypatch):
    import time
    monkeypatch.setattr(garmin_module.requests, "post", lambda *a, **k: Resp(text=jwt(int(time.time()) + 86400)))
    client = garmin_module.GarminClient("KEY123456")
    monkeypatch.setattr(garmin_module.requests, "get", lambda *a, **k: Resp(200, content=b"PK-zip"))
    assert client.download_activity(5) == b"PK-zip"
    monkeypatch.setattr(garmin_module.requests, "get", lambda *a, **k: Resp(404))
    assert client.download_activity(5) is None
    monkeypatch.setattr(garmin_module.requests, "get", lambda *a, **k: Resp(403))
    with pytest.raises(garmin_module.GarminAuthError, match="udløbet"):
        client.download_activity(5)
    monkeypatch.setattr(garmin_module.requests, "get", lambda *a, **k: Resp(429))
    with pytest.raises(RuntimeError, match="for mange"):
        client.download_activity(5)


# ---- reading every run's file in batches ------------------------------------------------------------------

def test_read_details_reads_the_files_in_batches_newest_first_until_nothing_is_left(gc):
    client, state, _ = gc
    state["pages"] = [[summary(2000 + i, local=f"2026-11-{i + 1:02d} 17:05:13", gmt=f"2026-11-{i + 1:02d} 16:05:13", kind="treadmill_running") for i in range(5)]]
    state["files"].update({2000 + i: zipped(treadmill_fit(200)) for i in range(5)})
    connect(client)
    assert state["downloads"] == []  # treadmill runs wait until asked for
    first = client.post("/api/garmin/read-details?limit=2", headers=ADMIN).json()
    assert first == {"read": 2, "failed": 0, "remaining": 3}
    assert state["downloads"] == [2004, 2003]  # the newest two
    second = client.post("/api/garmin/read-details?limit=10", headers=ADMIN).json()
    assert second == {"read": 3, "failed": 0, "remaining": 0}
    assert client.post("/api/garmin/read-details", headers=ADMIN).json() == {"read": 0, "failed": 0, "remaining": 0}
    assert len(client.get("/api/activities/profiles", headers=ADMIN).json()) == 5


def test_read_details_gives_up_early_when_garmin_does_not_answer_and_loses_nothing(gc):
    client, state, _ = gc
    state["pages"] = [[summary(3000 + i, local=f"2026-11-{i + 1:02d} 17:05:13", gmt=f"2026-11-{i + 1:02d} 16:05:13", kind="treadmill_running") for i in range(6)]]
    connect(client)
    state["down"] = True
    r = client.post("/api/garmin/read-details?limit=10", headers=ADMIN).json()
    assert r["read"] == 0 and r["failed"] == 3 and r["remaining"] == 6  # stopped after three misses, nothing marked
    state["down"] = False
    state["files"].update({3000 + i: zipped(treadmill_fit(100)) for i in range(6)})
    assert client.post("/api/garmin/read-details?limit=10", headers=ADMIN).json()["read"] == 6


def test_read_details_needs_a_connected_garmin_and_is_per_person(gc):
    client, _, _ = gc
    assert client.post("/api/garmin/read-details", headers=ADMIN).status_code == 409  # not connected
    connect(client, headers=ADMIN)
    assert client.post("/api/garmin/read-details", headers=FAMILY).status_code == 409
    assert client.post("/api/garmin/read-details?limit=0", headers=ADMIN).status_code == 422


# ---- everything that is not a run ---------------------------------------------------------------------------

def test_other_activities_are_stored_and_listed_but_never_counted_as_runs(gc):
    client, state, _ = gc
    state["pages"] = [[
        summary(1001, kind="treadmill_running"),
        summary(9, kind="cycling", local="2026-11-11 08:00:00", gmt="2026-11-11 07:00:00"),
        summary(10, kind="indoor_rowing", local="2026-11-09 15:00:00", gmt="2026-11-09 14:00:00", distance=2700),
        summary(11, kind="strength_training", local="2026-11-08 21:00:00", gmt="2026-11-08 20:00:00", distance=0),
    ]]
    connect(client)
    assert set(runs(client)) == {domain.internal_id(1001)}  # still only the run
    got = client.get("/api/activities/other", headers=ADMIN).json()
    assert [(x["kind"], x["date"]) for x in got] == [("Ride", "2026-11-11"), ("Row", "2026-11-09"), ("Strength", "2026-11-08")]  # newest first
    assert got[2]["distance_km"] == 0 and got[1]["distance_km"] == 2.7
    assert set(got[0]) == {"id", "date", "kind", "name", "distance_km", "duration_min"}  # no heart rate, no route
    # a run endpoint and the summary are untouched by them
    assert [r["id"] for r in client.get("/api/activities/routes", headers=ADMIN).json()] == []
    assert len(client.get("/api/activities/indoor", headers=ADMIN).json()) == 1
    assert client.get("/api/me", headers=FAMILY).json()["garmin"]["connected"] is False
    assert client.get("/api/activities/other", headers=FAMILY).json() == []


def test_syncing_again_does_not_duplicate_other_activities_and_reports_them(gc):
    client, state, _ = gc
    state["pages"] = [[summary(1001, kind="treadmill_running"), summary(9, kind="walking", local="2026-11-11 08:00:00", gmt="2026-11-11 07:00:00")]]
    connect(client)
    result = client.post("/api/admin/ingest", headers=ADMIN).json()["garmin"]
    assert result["others"] == 1 and result["skipped"] == 0
    assert len(client.get("/api/activities/other", headers=ADMIN).json()) == 1


def test_a_walk_at_the_same_time_as_a_run_is_not_merged_into_it(gc):
    client, state, _ = gc
    state["pages"] = [[summary(1001, kind="treadmill_running"), summary(9, kind="walking")]]  # the same start time as the run
    connect(client)
    assert set(runs(client)) == {domain.internal_id(1001)}
    assert [x["kind"] for x in client.get("/api/activities/other", headers=ADMIN).json()] == ["Walk"]


def test_the_other_endpoint_validates_its_limit_and_skips_runs_from_strava_years_only_by_type(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    add_activity(db, 1, "2026-11-01T08:00:00Z", sport_type="Ride", distance_m=20000)
    add_activity(db, 2, "2026-11-02T08:00:00Z", sport_type="Run")
    add_activity(db, 3, "2026-11-03T08:00:00Z", sport_type="Yoga")
    add_activity(db, 4, "2026-11-04T08:00:00Z", sport_type="Kitesurf")
    got = proxy.get("/api/activities/other", headers=ADMIN).json()
    assert [(x["id"], x["kind"]) for x in got] == [(4, "Other"), (3, "Strength"), (1, "Ride")]
    assert len(proxy.get("/api/activities/other?limit=1", headers=ADMIN).json()) == 1
    assert proxy.get("/api/activities/other?limit=0", headers=ADMIN).status_code == 422


def test_a_user_synced_before_other_activities_existed_gets_one_full_read_and_then_incremental_ones(gc):
    import app.db as db_module
    client, state, _ = gc
    connect(client)
    conn = db_module.get_conn()  # as if the last sync had been done by the older version: no marker
    conn.execute("DELETE FROM user_state WHERE key = 'garmin_others_read'")
    conn.commit(); conn.close()
    state["calls"].clear()
    client.post("/api/admin/ingest", headers=ADMIN)
    assert state["calls"][0]["start_date"] is None  # the whole history, once
    state["calls"].clear()
    client.post("/api/admin/ingest", headers=ADMIN)
    assert state["calls"][0]["start_date"] is not None  # and from then on only what is new
