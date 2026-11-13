"""Connecting Smashrun and syncing from it, against a fake Smashrun (nothing here touches the network)."""
import pytest

import app.smashrun as smashrun_module
from tests.auth_helpers import ADMIN, FAMILY, patch_settings
from tests.conftest import add_activity, connect_strava

RUN = {"activityId": 900, "startDateTimeLocal": "2026-11-10T09:00:00+01:00", "distance": 5.0, "duration": 1500,
       "heartRateAverage": 140, "notes": "Morgentur"}


@pytest.fixture()
def sr(proxy, db, monkeypatch):
    patch_settings(monkeypatch, SMASHRUN_CLIENT_ID="cid", SMASHRUN_CLIENT_SECRET="sec", APP_BASE_URL="https://run.example",
                   APP_SECRET_KEY="k" * 32)
    import app.services.smashrun_service as svc

    for m in (svc, smashrun_module):
        monkeypatch.setattr(m.settings, "SMASHRUN_CLIENT_ID", "cid")
        monkeypatch.setattr(m.settings, "SMASHRUN_CLIENT_SECRET", "sec")
        monkeypatch.setattr(m.settings, "APP_BASE_URL", "https://run.example")
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)

    state = {"runs": [dict(RUN)], "calls": [], "fail": False, "pages": None}

    class FakeClient:
        def __init__(self, refresh_token, access_token=None, access_expires_at=None, on_tokens=None):
            self.who = refresh_token

        def search(self, from_utc=None, page=0, count=100):
            state["calls"].append({"from_utc": from_utc, "page": page, "who": self.who})
            if state["fail"]:
                raise RuntimeError("smashrun is down")
            runs = state["pages"][page] if state["pages"] else (state["runs"] if page == 0 else [])
            return runs

    monkeypatch.setattr(svc.smashrun, "SmashrunClient", FakeClient)
    monkeypatch.setattr(svc.smashrun, "exchange_code", lambda code, redirect_uri: {
        "access_token": "a", "refresh_token": "r", "expires_at": 9999999999})
    return proxy, state, svc


def _link(client, user_headers=ADMIN):
    url = client.post("/api/smashrun/connect", headers=user_headers).json()["url"]
    return dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&"))["state"]


def test_connect_sends_the_person_to_smashrun_with_a_signed_state_and_the_callback_address(sr):
    client, _, _ = sr
    url = client.post("/api/smashrun/connect", headers=ADMIN).json()["url"]
    assert url.startswith("https://secure.smashrun.com/oauth2/authenticate?")
    assert "client_id=cid" in url and "response_type=code" in url and "scope=read_activity" in url
    assert "redirect_uri=https%3A%2F%2Frun.example%2Fapi%2Fsmashrun%2Fcallback" in url


def test_connect_says_so_when_smashrun_is_not_configured(sr, monkeypatch):
    client, _, svc = sr
    monkeypatch.setattr(svc.settings, "SMASHRUN_CLIENT_SECRET", "")
    assert client.post("/api/smashrun/connect", headers=ADMIN).status_code == 409
    assert client.get("/api/me", headers=ADMIN).json()["smashrun"] == {"connected": False, "configured": False}


def test_callback_saves_tokens_for_the_person_in_the_state_and_starts_the_first_sync(sr):
    client, state, _ = sr
    r = client.get("/api/smashrun/callback", params={"code": "c", "state": _link(client, FAMILY)})
    assert r.status_code == 302 and r.headers["location"].endswith("?smashrun=connected")
    assert client.get("/api/me", headers=FAMILY).json()["smashrun"]["connected"] is True
    assert client.get("/api/me", headers=ADMIN).json()["smashrun"]["connected"] is False
    assert state["calls"] and state["calls"][0]["from_utc"] is None  # the first sync reads the whole history
    assert [a["id"] for a in client.get("/api/activities", headers=FAMILY).json()] == [-900]


def test_a_forged_or_denied_callback_is_rejected(sr):
    client, _, _ = sr
    assert client.get("/api/smashrun/callback", params={"code": "c", "state": "forged"}).status_code == 403
    assert client.get("/api/smashrun/callback", params={"error": "access_denied", "state": "forged"}).status_code == 403
    denied = client.get("/api/smashrun/callback", params={"error": "access_denied", "state": _link(client)})
    assert denied.headers["location"].endswith("?smashrun=denied")


def test_sync_adds_new_runs_updates_changed_ones_and_reads_incrementally(sr):
    client, state, _ = sr
    client.get("/api/smashrun/callback", params={"code": "c", "state": _link(client)})
    state["calls"].clear()
    state["runs"] = [dict(RUN, distance=5.2), dict(RUN, activityId=901, startDateTimeLocal="2026-11-11T09:00:00+01:00")]
    result = client.post("/api/admin/ingest", headers=ADMIN).json()["smashrun"]
    assert (result["added"], result["updated"]) == (1, 1)
    assert state["calls"][0]["from_utc"] is not None  # only what changed since last time (with overlap)
    runs = {a["id"]: a["distance_km"] for a in client.get("/api/activities", headers=ADMIN).json()}
    assert runs == {-900: 5.2, -901: 5.0}


def test_a_run_already_stored_from_strava_is_not_added_twice(sr, db):
    client, _, _ = sr
    add_activity(db, 555, "2026-11-10T08:00:30Z", distance_m=5000, moving_time_s=1500)  # same run, 30 s apart
    client.get("/api/smashrun/callback", params={"code": "c", "state": _link(client)})
    assert [a["id"] for a in client.get("/api/activities", headers=ADMIN).json()] == [555]
    status = client.get("/api/admin/status", headers=ADMIN).json()
    assert '"duplicates": 1' in status["last_ingest_result"]["value"]


def test_every_page_is_read_and_unusable_runs_are_counted_not_fatal(sr, monkeypatch):
    client, state, svc = sr
    monkeypatch.setattr(svc.smashrun, "PAGE_SIZE", 2)
    state["pages"] = [
        [dict(RUN, activityId=1, startDateTimeLocal="2026-11-01T09:00:00+01:00"), {"activityId": 2, "distance": 0}],
        [dict(RUN, activityId=3, startDateTimeLocal="2026-11-02T09:00:00+01:00")],
    ]
    client.get("/api/smashrun/callback", params={"code": "c", "state": _link(client)})
    assert [c["page"] for c in state["calls"]] == [0, 1]
    assert sorted(a["id"] for a in client.get("/api/activities", headers=ADMIN).json()) == [-3, -1]


def test_one_failing_source_does_not_stop_the_other(sr, monkeypatch):
    client, state, _ = sr
    client.get("/api/smashrun/callback", params={"code": "c", "state": _link(client)})
    connect_strava_for_admin = __import__("tests.conftest", fromlist=["x"]).connect_strava
    return_value = connect_strava_for_admin
    import app.services.sync_service as sync_service

    class DeadStrava:
        def __init__(self, *a, **k): pass
        def get_activities(self, **k): raise RuntimeError("Strava: Application Inactive")

    monkeypatch.setattr(sync_service, "StravaClient", DeadStrava)
    import app.db as dbmod
    c = dbmod.get_conn(); c.execute("INSERT INTO strava_accounts (user_id, athlete_id, refresh_token) VALUES (1, '1', 'r')"); c.commit(); c.close()
    body = client.post("/api/admin/ingest", headers=ADMIN).json()
    assert "smashrun" in body and "Inactive" in body["errors"]["strava"]
    assert "Inactive" in client.get("/api/admin/status", headers=ADMIN).json()["last_error"]["value"]


def test_failure_when_smashrun_is_the_only_source_is_reported(sr):
    client, state, _ = sr
    client.get("/api/smashrun/callback", params={"code": "c", "state": _link(client)})
    state["fail"] = True
    r = client.post("/api/admin/ingest", headers=ADMIN)
    assert r.status_code == 502 and "smashrun is down" in r.json()["detail"]


def test_disconnecting_forgets_the_tokens_but_keeps_the_runs(sr):
    client, _, _ = sr
    client.get("/api/smashrun/callback", params={"code": "c", "state": _link(client)})
    assert client.delete("/api/smashrun/connection", headers=ADMIN).json()["connected"] is False
    assert [a["id"] for a in client.get("/api/activities", headers=ADMIN).json()] == [-900]


def test_each_person_only_syncs_their_own_account(sr):
    client, state, _ = sr
    client.get("/api/smashrun/callback", params={"code": "c", "state": _link(client, FAMILY)})
    assert client.get("/api/activities", headers=ADMIN).json() == []
    assert len(client.get("/api/activities", headers=FAMILY).json()) == 1


class FakeResponse:
    def __init__(self, status=200, payload=None): self.status_code, self._p, self.ok, self.text = status, payload or {}, status < 400, "x"
    def json(self): return self._p


def test_the_client_refreshes_an_expired_token_once_and_reports_the_new_tokens(monkeypatch):
    monkeypatch.setattr(smashrun_module.settings, "SMASHRUN_CLIENT_ID", "cid")
    monkeypatch.setattr(smashrun_module.settings, "SMASHRUN_CLIENT_SECRET", "sec")
    posted, saved, sent = [], [], []
    monkeypatch.setattr(smashrun_module.requests, "post", lambda url, data, timeout: posted.append(data) or FakeResponse(payload={"access_token": "new", "expires_in": 1000}))
    monkeypatch.setattr(smashrun_module.requests, "get", lambda url, params, headers, timeout: sent.append((url, params, headers)) or FakeResponse(payload=[{"activityId": 1}]))
    client = smashrun_module.SmashrunClient("refresh", "old", 1, on_tokens=lambda *t: saved.append(t))
    client.search(from_utc=5)
    client.search()
    assert len(posted) == 1 and posted[0]["grant_type"] == "refresh_token" and posted[0]["refresh_token"] == "refresh"
    assert saved[0][:2] == ("refresh", "new")  # Smashrun sends no new refresh token: the old one is kept
    assert sent[0][2]["Authorization"] == "Bearer new" and sent[0][1]["fromDateUTC"] == 5
    assert sent[0][0].endswith("/my/activities/search/extended")
