"""Several users: who is calling, data isolation, Strava per person, and routing of webhook events."""
import importlib
import time

import pytest
from fastapi.testclient import TestClient

from tests.conftest import add_activity, add_plan, connect_strava

PROXY_IP = "10.0.0.5"
ADMIN = {"x-authentik-uid": "u-henrik", "x-authentik-username": "henrik", "x-authentik-name": "Henrik", "x-authentik-groups": "homelab-admins|homelab-family"}
FAMILY = {"x-authentik-uid": "u-anna", "x-authentik-username": "anna", "x-authentik-name": "Anna", "x-authentik-groups": "homelab-family"}
OUTSIDER = {"x-authentik-uid": "u-x", "x-authentik-username": "x", "x-authentik-groups": "something-else"}


def _patch_settings(monkeypatch, **values):
    import app.services.strava_service as strava_service
    import app.services.user_service as user_service
    import app.strava as strava_module

    for module in (user_service, strava_service, strava_module):
        for key, value in values.items():
            monkeypatch.setattr(module.settings, key, value)


class FromAddress:
    """Makes every request look like it comes from `host` (TestClient always says 'testclient')."""

    def __init__(self, app, host):
        self.app, self.host = app, host

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope = {**scope, "client": (self.host, 50000)}
        await self.app(scope, receive, send)


@pytest.fixture()
def proxy(db, monkeypatch):
    """The app in proxy mode, called from a trusted address."""
    import app.main

    importlib.reload(app.main)
    _patch_settings(monkeypatch, AUTH_MODE="proxy", TRUSTED_PROXIES=["10.0.0.0/8"], AUTH_OWNER_USERNAME="")
    return TestClient(FromAddress(app.main.app, PROXY_IP), follow_redirects=False)


@pytest.fixture()
def local(db):
    import app.main

    importlib.reload(app.main)
    return TestClient(app.main.app)


# ---- who is calling ------------------------------------------------------------------

def test_local_mode_uses_the_single_local_user(local):
    me = local.get("/api/me").json()
    assert (me["id"], me["role"], me["username"]) == (1, "admin", "owner")


def test_proxy_mode_requires_identity_headers(proxy):
    assert proxy.get("/api/me").status_code == 401


def test_proxy_mode_refuses_untrusted_peers(proxy, monkeypatch):
    _patch_settings(monkeypatch, TRUSTED_PROXIES=["192.168.1.1"])
    r = proxy.get("/api/me", headers=ADMIN)
    assert r.status_code == 403


def test_proxy_mode_with_no_trusted_proxies_refuses_everyone(proxy, monkeypatch):
    _patch_settings(monkeypatch, TRUSTED_PROXIES=[])
    assert proxy.get("/api/me", headers=ADMIN).status_code == 403


def test_deny_by_default_without_a_known_group(proxy):
    r = proxy.get("/api/me", headers=OUTSIDER)
    assert r.status_code == 403


def test_roles_follow_groups(proxy):
    assert proxy.get("/api/me", headers=ADMIN).json()["role"] == "admin"
    assert proxy.get("/api/me", headers=FAMILY).json()["role"] == "family"


def test_group_header_may_use_commas(proxy):
    h = {**FAMILY, "x-authentik-groups": "other, homelab-family"}
    assert proxy.get("/api/me", headers=h).status_code == 200


def test_first_admin_takes_over_the_data_from_before_users(proxy, db):
    add_activity(db, 1, "2020-03-10T08:00:00Z")
    me = proxy.get("/api/me", headers=ADMIN).json()
    assert (me["id"], me["username"], me["display_name"]) == (1, "henrik", "Henrik")
    assert [a["id"] for a in proxy.get("/api/activities", headers=ADMIN).json()] == [1]


def test_a_family_member_does_not_take_over_the_old_data(proxy, db):
    add_activity(db, 1, "2020-03-10T08:00:00Z")
    anna = proxy.get("/api/me", headers=FAMILY).json()
    assert anna["id"] == 2
    assert proxy.get("/api/activities", headers=FAMILY).json() == []
    assert proxy.get("/api/me", headers=ADMIN).json()["id"] == 1  # the admin still finds it afterwards


def test_owner_username_decides_who_takes_over(proxy, monkeypatch):
    _patch_settings(monkeypatch, AUTH_OWNER_USERNAME="henrik")
    other_admin = {**ADMIN, "x-authentik-uid": "u-other", "x-authentik-username": "other"}
    assert proxy.get("/api/me", headers=other_admin).json()["id"] == 2
    assert proxy.get("/api/me", headers=ADMIN).json()["id"] == 1


def test_a_known_user_keeps_their_id_and_gets_a_new_role(proxy):
    first = proxy.get("/api/me", headers=FAMILY).json()
    promoted = proxy.get("/api/me", headers={**FAMILY, "x-authentik-groups": "homelab-admins"}).json()
    assert (promoted["id"], promoted["role"]) == (first["id"], "admin")


def test_health_and_webhook_verification_need_no_login(proxy):
    assert proxy.get("/api/health").status_code == 200
    assert proxy.get("/api/webhooks/strava", params={"hub.mode": "x", "hub.verify_token": "y", "hub.challenge": "z"}).status_code == 403


# ---- isolation ------------------------------------------------------------------------

def _two_users(proxy):
    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)


def test_users_do_not_see_each_others_plans_or_activities(proxy, db):
    _two_users(proxy)
    add_activity(db, 100, "2020-03-10T08:00:00Z")
    conn = db.get_conn()
    try:
        conn.execute("UPDATE activities SET user_id = 2 WHERE id = 100")
        conn.commit()
    finally:
        conn.close()
    a = proxy.post("/api/planning", headers=ADMIN, json={"planned_date": "2100-01-01", "session_type": "easy", "target_value": 30}).json()

    assert [p["id"] for p in proxy.get("/api/planning", headers=ADMIN).json()] == [a["id"]]
    assert proxy.get("/api/planning", headers=FAMILY).json() == []
    assert proxy.get("/api/activities", headers=ADMIN).json() == []
    assert [x["id"] for x in proxy.get("/api/activities", headers=FAMILY).json()] == [100]
    assert proxy.get("/api/activities/100", headers=ADMIN).status_code == 404
    assert proxy.get("/api/activities/100", headers=FAMILY).status_code == 200


def test_a_user_cannot_change_or_delete_someone_elses_plan(proxy):
    _two_users(proxy)
    plan = proxy.post("/api/planning", headers=ADMIN, json={"planned_date": "2100-01-01", "session_type": "easy", "target_value": 30}).json()
    pid = plan["id"]
    body = {"planned_date": "2100-01-02", "session_type": "long", "target_type": "time", "target_value": 60}
    assert proxy.put(f"/api/planning/{pid}", headers=FAMILY, json=body).status_code == 404
    assert proxy.delete(f"/api/planning/{pid}", headers=FAMILY).status_code == 404
    assert proxy.post(f"/api/planning/{pid}/mark-skipped", headers=FAMILY).status_code == 404
    assert proxy.post(f"/api/planning/{pid}/match-activity", headers=FAMILY, json={"activity_id": 1}).status_code == 404
    assert proxy.get("/api/planning", headers=ADMIN).json()[0]["session_type"] == "easy"


def test_matching_one_user_leaves_the_other_untouched(proxy, db):
    _two_users(proxy)
    add_plan(db, "2020-03-10", target_value=30)  # user 1 (default)
    add_activity(db, 1, "2020-03-10T08:00:00Z")  # user 1
    conn = db.get_conn()
    try:
        conn.execute("INSERT INTO planned_runs (planned_date, session_type, target_type, target_value, mandatory, optional, user_id) VALUES ('2020-03-10','easy','time',30,1,0,2)")
        conn.commit()
    finally:
        conn.close()
    proxy.post("/api/planning/evaluate", headers=ADMIN)
    assert [p["status"] for p in proxy.get("/api/planning", headers=ADMIN).json()] == ["gennemført"]
    assert [p["status"] for p in proxy.get("/api/planning", headers=FAMILY).json()] == ["planlagt"]  # not evaluated, no activity


def test_an_activity_id_owned_by_another_user_is_not_overwritten(db):
    from app.repositories import activities as repo

    conn = db.get_conn()
    try:
        db_user2 = conn.execute("INSERT INTO users (external_id, username) VALUES ('b', 'b')").lastrowid
        base = {"id": 7, "name": "Mine", "sport_type": "Run", "start_date": "2020-03-10T08:00:00Z", "distance": 5000, "moving_time": 1500}
        repo.upsert(conn, 1, base)
        repo.upsert(conn, db_user2, {**base, "name": "Stolen"})
        conn.commit()
        assert repo.get(conn, 1, 7)["name"] == "Mine"
        assert repo.get(conn, db_user2, 7) is None
    finally:
        conn.close()


def test_admin_health_checks_all_users_family_checks_own(proxy, db):
    _two_users(proxy)
    assert proxy.get("/api/admin/health", headers=ADMIN).json() == {"ok": True, "mismatch_count": 0}
    assert proxy.get("/api/admin/health", headers=FAMILY).json()["ok"] is True


# ---- sharing preferences --------------------------------------------------------------------

def test_sharing_defaults_to_private_and_can_be_changed(proxy):
    me = proxy.get("/api/me", headers=FAMILY).json()
    assert me["sharing_level"] == "private"
    changed = proxy.put("/api/me", headers=FAMILY, json={"sharing_level": "overview", "display_name": "Anna S."}).json()
    assert (changed["sharing_level"], changed["display_name"]) == ("overview", "Anna S.")
    assert proxy.put("/api/me", headers=FAMILY, json={"sharing_level": "everyone"}).status_code == 422


def test_sharing_is_forced_private_when_family_sharing_is_off(proxy, monkeypatch):
    proxy.put("/api/me", headers=FAMILY, json={"sharing_level": "all"})
    _patch_settings(monkeypatch, FAMILY_SHARING_ENABLED=False)
    me = proxy.get("/api/me", headers=FAMILY).json()
    assert (me["sharing_level"], me["family_sharing_enabled"]) == ("private", False)


# ---- Strava per user ---------------------------------------------------------------------------------

def test_oauth_state_is_signed_and_expires(db):
    from app.errors import ForbiddenError
    from app.services import strava_service

    state = strava_service.make_state(5)
    assert strava_service.read_state(state) == 5
    payload, signature = state.split(".")
    with pytest.raises(ForbiddenError):
        strava_service.read_state(f"{payload}.{signature[:-2]}xx")  # tampered signature
    with pytest.raises(ForbiddenError):
        strava_service.read_state("not-a-state")
    with pytest.raises(ForbiddenError):
        strava_service.read_state(strava_service.make_state(5, now=time.time() - 3600))  # made an hour ago


def test_connect_returns_the_strava_url_with_a_signed_state(proxy, monkeypatch):
    _patch_settings(monkeypatch, STRAVA_CLIENT_ID="123", APP_BASE_URL="https://run.example")
    url = proxy.post("/api/strava/connect", headers=FAMILY).json()["url"]
    assert url.startswith("https://www.strava.com/oauth/authorize?")
    assert "client_id=123" in url and "redirect_uri=https%3A%2F%2Frun.example%2Fapi%2Fstrava%2Fcallback" in url
    assert "activity%3Aread_all" in url


def test_connect_says_so_when_strava_is_not_configured(proxy, monkeypatch):
    _patch_settings(monkeypatch, STRAVA_CLIENT_ID="")
    assert proxy.post("/api/strava/connect", headers=FAMILY).status_code == 409


def _token_payload(athlete_id=555, refresh="r1", access="a1"):
    return {"access_token": access, "refresh_token": refresh, "expires_at": int(time.time()) + 3600, "athlete": {"id": athlete_id}, "scope": "read,activity:read_all"}


def test_callback_saves_the_account_for_the_user_in_the_state(proxy, monkeypatch):
    import app.services.strava_service as strava_service

    _patch_settings(monkeypatch, APP_BASE_URL="https://run.example")
    monkeypatch.setattr(strava_service.strava, "exchange_code", lambda code: _token_payload())
    monkeypatch.setattr(strava_service, "after_connect", lambda user_id: None)  # the first sync is tested separately
    proxy.get("/api/me", headers=ADMIN)
    anna_id = proxy.get("/api/me", headers=FAMILY).json()["id"]

    r = proxy.get("/api/strava/callback", params={"code": "abc", "state": strava_service.make_state(anna_id)})

    assert r.status_code == 302 and r.headers["location"] == "https://run.example/?strava=connected"
    assert proxy.get("/api/strava/status", headers=FAMILY).json() == {"connected": True, "configured": False, "athlete_id": "555"}
    assert proxy.get("/api/strava/status", headers=ADMIN).json()["connected"] is False


def test_callback_rejects_a_forged_state(proxy):
    r = proxy.get("/api/strava/callback", params={"code": "abc", "state": "forged.value"})
    assert r.status_code == 403


def test_callback_handles_a_denied_request(proxy, monkeypatch):
    import app.services.strava_service as strava_service

    _patch_settings(monkeypatch, APP_BASE_URL="https://run.example")
    r = proxy.get("/api/strava/callback", params={"error": "access_denied", "state": strava_service.make_state(1)})
    assert r.headers["location"] == "https://run.example/?strava=denied"


def test_a_strava_account_can_only_belong_to_one_user(proxy, monkeypatch):
    import app.services.strava_service as strava_service

    monkeypatch.setattr(strava_service.strava, "exchange_code", lambda code: _token_payload(athlete_id=777))
    monkeypatch.setattr(strava_service, "after_connect", lambda user_id: None)
    proxy.get("/api/me", headers=ADMIN)
    anna_id = proxy.get("/api/me", headers=FAMILY).json()["id"]
    assert proxy.get("/api/strava/callback", params={"code": "c", "state": strava_service.make_state(1)}).status_code == 302
    clash = proxy.get("/api/strava/callback", params={"code": "c", "state": strava_service.make_state(anna_id)})
    assert clash.status_code == 409


def test_disconnect_removes_the_tokens(proxy, db):
    proxy.get("/api/me", headers=ADMIN)
    connect_strava(db, user_id=1, athlete_id="9")
    assert proxy.get("/api/strava/status", headers=ADMIN).json()["connected"] is True
    assert proxy.delete("/api/strava/connection", headers=ADMIN).json()["connected"] is False


def test_syncing_without_a_strava_account_says_so(proxy):
    proxy.get("/api/me", headers=ADMIN)
    r = proxy.post("/api/admin/ingest", headers=FAMILY)
    assert r.status_code == 409 and r.json()["code"] == "strava_not_connected"


def test_new_tokens_from_strava_are_saved(db, monkeypatch):
    """Strava rotates the refresh token on every refresh. The new one must be kept."""
    import app.strava as strava_module
    from app.services import sync_service

    connect_strava(db, user_id=1, athlete_id="1")

    class Response:
        ok = True
        status_code = 200

        def json(self):
            return {"access_token": "new-access", "refresh_token": "new-refresh", "expires_at": int(time.time()) + 3600}

    monkeypatch.setattr(strava_module.requests, "post", lambda *a, **k: Response())
    client = sync_service.client_for(1)
    client.refresh_access_token()

    conn = db.get_conn()
    try:
        row = conn.execute("SELECT refresh_token, access_token FROM strava_accounts WHERE user_id = 1").fetchone()
    finally:
        conn.close()
    assert (row["refresh_token"], row["access_token"]) == ("new-refresh", "new-access")


def test_a_fresh_access_token_is_reused_without_asking_strava(db, monkeypatch):
    import app.strava as strava_module
    from app.services import sync_service

    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO strava_accounts (user_id, athlete_id, refresh_token, access_token, access_expires_at) VALUES (1, '1', 'r', 'still-good', ?)",
            (int(time.time()) + 3600,),
        )
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(strava_module.requests, "post", lambda *a, **k: pytest.fail("should not refresh"))
    assert sync_service.client_for(1).headers() == {"Authorization": "Bearer still-good"}


def test_the_token_from_the_environment_moves_to_the_first_user_once(db, monkeypatch):
    from app.services import strava_service

    _patch_settings(monkeypatch, STRAVA_REFRESH_TOKEN="env-token", STRAVA_ATHLETE_ID="42")
    assert strava_service.ensure_legacy_account() is True
    assert strava_service.ensure_legacy_account() is False  # already moved
    assert strava_service.status(1)["athlete_id"] == "42"


# ---- webhook events go to the right user ------------------------------------------------------------

@pytest.fixture()
def family_webhooks(proxy, db, monkeypatch):
    import app.services.sync_service as sync_service

    proxy.get("/api/me", headers=ADMIN)
    proxy.get("/api/me", headers=FAMILY)
    connect_strava(db, user_id=1, athlete_id="11")
    connect_strava(db, user_id=2, athlete_id="22")

    class FakeStrava:
        def __init__(self, refresh_token, access_token=None, access_expires_at=None, on_tokens=None):
            self.who = refresh_token

        def get_activity(self, activity_id):
            return {"id": activity_id, "name": "Run", "sport_type": "Run", "start_date": "2026-11-10T08:00:00Z", "distance": 5000, "moving_time": 1500}

    monkeypatch.setattr(sync_service, "StravaClient", FakeStrava)
    return proxy, db


def _activity_owners(db):
    conn = db.get_conn()
    try:
        return {r["id"]: r["user_id"] for r in conn.execute("SELECT id, user_id FROM activities")}
    finally:
        conn.close()


def test_an_event_ingests_into_the_owner_of_that_strava_account(family_webhooks):
    client, db = family_webhooks
    client.post("/api/webhooks/strava", json={"object_type": "activity", "object_id": 900, "aspect_type": "create", "owner_id": 22, "event_time": 1})
    client.post("/api/webhooks/strava", json={"object_type": "activity", "object_id": 901, "aspect_type": "create", "owner_id": 11, "event_time": 2})
    assert _activity_owners(db) == {900: 2, 901: 1}


def test_a_delete_event_only_removes_the_owners_activity(family_webhooks):
    client, db = family_webhooks
    client.post("/api/webhooks/strava", json={"object_type": "activity", "object_id": 900, "aspect_type": "create", "owner_id": 22, "event_time": 1})
    client.post("/api/webhooks/strava", json={"object_type": "activity", "object_id": 900, "aspect_type": "delete", "owner_id": 11, "event_time": 2})
    assert _activity_owners(db) == {900: 2}  # athlete 11 cannot delete athlete 22's run
    client.post("/api/webhooks/strava", json={"object_type": "activity", "object_id": 900, "aspect_type": "delete", "owner_id": 22, "event_time": 3})
    assert _activity_owners(db) == {}


def test_status_counts_only_own_events_for_family_and_all_for_admin(family_webhooks):
    client, _ = family_webhooks
    client.post("/api/webhooks/strava", json={"object_type": "activity", "object_id": 900, "aspect_type": "create", "owner_id": 22, "event_time": 1})
    client.post("/api/webhooks/strava", json={"object_type": "activity", "object_id": 901, "aspect_type": "create", "owner_id": 11, "event_time": 2})
    client.post("/api/webhooks/strava", json={"object_type": "activity", "object_id": 902, "aspect_type": "create", "owner_id": 11, "event_time": 3})
    assert client.get("/api/admin/status", headers=FAMILY).json()["webhook_event_count"] == 1
    assert client.get("/api/admin/status", headers=ADMIN).json()["webhook_event_count"] == 3
