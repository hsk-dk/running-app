"""Several users: who is calling, and data isolation."""
import importlib
import time

import pytest
from fastapi.testclient import TestClient

from tests.auth_helpers import ADMIN, FAMILY, OUTSIDER, patch_settings
from tests.conftest import add_activity, add_plan

_patch_settings = patch_settings


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


def test_health_needs_no_login(proxy):
    assert proxy.get("/api/health").status_code == 200


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


# ---- the signed link that travels with a connect request ---------------------------------------------------

def test_oauth_state_is_signed_and_expires(db):
    from app.errors import ForbiddenError
    from app.services import oauth_state

    state = oauth_state.make_state(5)
    assert oauth_state.read_state(state) == 5
    payload, signature = state.split(".")
    with pytest.raises(ForbiddenError):
        oauth_state.read_state(f"{payload}.{signature[:-2]}xx")  # tampered signature
    with pytest.raises(ForbiddenError):
        oauth_state.read_state("not-a-state")
    with pytest.raises(ForbiddenError):
        oauth_state.read_state(oauth_state.make_state(5, now=time.time() - 3600))  # made an hour ago
