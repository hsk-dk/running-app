"""Runs can come from several sources. The same run from two sources must only count once."""
import json

from app.repositories import activities as repo
from tests.conftest import add_activity


def _conn(db):
    return db.get_conn()


def test_existing_runs_are_strava_runs_with_their_id_as_source_id(db):
    add_activity(db, 111, "2026-11-10T08:00:00Z")
    c = _conn(db)
    row = c.execute("SELECT source, source_id FROM activities WHERE id = 111").fetchone()
    c.close()
    assert (row["source"], row["source_id"]) == ("strava", None)  # raw insert; upsert fills source_id


def test_migration_backfills_source_id_on_old_databases(db):
    add_activity(db, 111, "2026-11-10T08:00:00Z")
    c = _conn(db)
    c.execute("UPDATE activities SET source_id = NULL")
    c.commit()
    db._migration_9_sources(c)  # idempotent: columns already exist
    row = c.execute("SELECT source, source_id FROM activities WHERE id = 111").fetchone()
    c.close()
    assert (row["source"], row["source_id"]) == ("strava", "111")


def test_upsert_records_where_a_run_came_from(db):
    c = _conn(db)
    repo.upsert(c, 1, {"id": -42, "sport_type": "Run", "start_date": "2026-11-10T08:00:00Z", "distance": 5000, "moving_time": 1500}, source="smashrun")
    repo.upsert(c, 1, {"id": 43, "sport_type": "Run", "start_date": "2026-11-11T08:00:00Z", "distance": 5000, "moving_time": 1500})
    c.commit()
    rows = {r["id"]: (r["source"], r["source_id"]) for r in c.execute("SELECT * FROM activities")}
    c.close()
    assert rows == {-42: ("smashrun", "-42"), 43: ("strava", "43")}


def test_find_near_matches_the_same_run_within_the_window_only(db):
    add_activity(db, 1, "2026-11-10T08:00:00Z")
    add_activity(db, 2, "2026-11-10T09:00:00Z", user_id=2)
    c = _conn(db)
    assert repo.find_near(c, 1, "2026-11-10T08:01:30Z")["id"] == 1  # 90 s apart
    assert repo.find_near(c, 1, "2026-11-10T08:03:00Z") is None  # 180 s apart
    assert repo.find_near(c, 1, "2026-11-10T09:00:00Z") is None  # the other user's run is not mine
    c.close()


def test_find_near_can_be_limited_to_a_source_and_picks_the_closest(db):
    add_activity(db, 1, "2026-11-10T08:00:00Z")
    c = _conn(db)
    repo.upsert(c, 1, {"id": -2, "sport_type": "Run", "start_date": "2026-11-10T08:00:50Z", "distance": 5000, "moving_time": 1500}, source="smashrun")
    c.commit()
    assert repo.find_near(c, 1, "2026-11-10T08:00:40Z")["id"] == -2
    assert repo.find_near(c, 1, "2026-11-10T08:00:40Z", source="strava")["id"] == 1
    c.close()
