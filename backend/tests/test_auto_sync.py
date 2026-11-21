"""The automatic sync: everyone with a source is asked on a timer, a failing person less and less often, nobody twice at once."""
import threading

import pytest

from app.errors import NotConnectedError

# The app modules are imported inside the tests, not here: other tests reload app.config, and importing the services while the
# tests are collected would bind them to the settings of before the first reload.


@pytest.fixture(autouse=True)
def _fresh_settings(db):
    """Every test here starts from a reloaded app.config, like the other tests, so the services bind to the same settings."""
    return db


def _modules():
    import app.main  # noqa: F401  (imports the whole app in the usual order, so every module binds to the same settings)
    from app.services import admin_service, auto_sync

    return admin_service, auto_sync


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(run, users=lambda: [1, 2], interval=1800, clock=None):
    _, auto_sync = _modules()
    return auto_sync.AutoSync(interval, run=run, users=users, clock=clock or Clock())


def test_everyone_is_synced_one_at_a_time_without_waiting_for_a_running_sync():
    calls = []
    syncer = make(lambda user_id, wait: calls.append((user_id, wait)) or {"ok": True})
    done = syncer.tick()
    assert calls == [(1, False), (2, False)]  # wait=False: the automatic round never queues behind a person
    assert done == {"synced": [1, 2], "skipped": [], "failed": [], "nothing": []}


def test_someone_with_no_source_is_not_a_failure_and_is_asked_again_next_round():
    def run(user_id, wait):
        if user_id == 2:
            raise NotConnectedError("Ingen datakilde er forbundet")
        return {"ok": True}

    clock = Clock()
    syncer = make(run, clock=clock)
    assert syncer.tick() == {"synced": [1], "skipped": [], "failed": [], "nothing": [2]}
    clock.now += 1800
    assert syncer.tick()["nothing"] == [2] and syncer.tick()["failed"] == []  # no backoff for that


def test_a_sync_that_is_already_running_is_skipped_not_failed():
    syncer = make(lambda user_id, wait: None)  # None: busy
    assert syncer.tick() == {"synced": [], "skipped": [1, 2], "failed": [], "nothing": []}


def test_one_persons_failure_never_stops_the_round_and_that_person_is_left_alone_for_a_while():
    calls = []

    def run(user_id, wait):
        calls.append(user_id)
        if user_id == 1:
            raise RuntimeError("Garmin afviste nøglen")
        return {"ok": True}

    clock = Clock()
    syncer = make(run, clock=clock, interval=1800)
    assert syncer.tick() == {"synced": [2], "skipped": [], "failed": [1], "nothing": []}  # user 2 was still synced
    calls.clear()
    clock.now += 1800
    assert syncer.tick() == {"synced": [2], "skipped": [1], "failed": [], "nothing": []}  # one round later: 1 is left alone (waits 2 x 1800 s)
    assert calls == [2]
    clock.now += 1800 * 2
    syncer.tick()
    assert 1 in calls  # after the wait, asked again


def test_the_wait_doubles_with_each_failure_up_to_six_hours_and_a_success_clears_it():
    _, auto_sync = _modules()
    state = {"fail": True}

    def run(user_id, wait):
        if state["fail"]:
            raise RuntimeError("down")
        return {"ok": True}

    clock = Clock()
    syncer = make(run, users=lambda: [1], clock=clock, interval=1800)
    waits = []
    for _ in range(6):
        t0 = clock.now
        syncer.tick()
        waits.append(syncer._failures[1][1] - t0)
        clock.now = syncer._failures[1][1]  # the moment it is due again
    assert waits[:3] == [3600, 7200, 14400] and waits[3:] == [auto_sync.MAX_BACKOFF_SECONDS] * 3
    state["fail"] = False
    assert syncer.tick()["synced"] == [1]
    assert 1 not in syncer._failures


def test_a_new_person_is_picked_up_without_a_restart():
    ids = [1]
    syncer = make(lambda user_id, wait: {"ok": True}, users=lambda: list(ids))
    assert syncer.tick()["synced"] == [1]
    ids.append(5)
    assert syncer.tick()["synced"] == [1, 5]


def test_an_interval_of_zero_switches_it_off_and_nothing_starts():
    syncer = make(lambda user_id, wait: {"ok": True}, interval=0)
    syncer.start()
    assert syncer._thread is None
    syncer.stop()


def test_the_settings_turn_minutes_into_seconds_and_a_bad_value_into_off(monkeypatch):
    _, auto_sync = _modules()
    monkeypatch.setattr(auto_sync.settings, "SYNC_INTERVAL_MINUTES", 30)
    assert auto_sync.from_settings().interval == 1800
    monkeypatch.setattr(auto_sync.settings, "SYNC_INTERVAL_MINUTES", -5)
    assert auto_sync.from_settings().interval == 0
    monkeypatch.setattr(auto_sync.settings, "SYNC_INTERVAL_MINUTES", 0)
    assert auto_sync.from_settings().interval == 0


def test_the_timer_runs_a_round_and_stops_cleanly(monkeypatch):
    _, auto_sync = _modules()
    monkeypatch.setattr(auto_sync, "FIRST_RUN_DELAY_SECONDS", 0)
    done = threading.Event()
    syncer = make(lambda user_id, wait: done.set() or {"ok": True}, users=lambda: [1], interval=0.05)
    syncer.interval = 0.05
    syncer.start()
    assert done.wait(2)
    syncer.stop()
    assert syncer._thread is None


# ---- one sync per person at a time -----------------------------------------------------------------------------

def test_only_one_sync_per_person_runs_at_a_time(monkeypatch):
    admin_service, _ = _modules()
    monkeypatch.setattr(admin_service, "_run_ingest", lambda user_id: {"ran": user_id})
    lock = admin_service._lock_for(77)
    lock.acquire()
    try:
        assert admin_service.run_ingest(77, wait=False) is None  # busy: the automatic round gives up
        assert admin_service.run_ingest(78, wait=False) == {"ran": 78}  # somebody else is not held up
    finally:
        lock.release()
    assert admin_service.run_ingest(77, wait=False) == {"ran": 77}


def test_the_lock_is_released_when_a_sync_fails(monkeypatch):
    admin_service, _ = _modules()
    def boom(user_id):
        raise RuntimeError("down")

    monkeypatch.setattr(admin_service, "_run_ingest", boom)
    with pytest.raises(RuntimeError):
        admin_service.run_ingest(91)
    monkeypatch.setattr(admin_service, "_run_ingest", lambda user_id: {"ran": user_id})
    assert admin_service.run_ingest(91, wait=False) == {"ran": 91}  # not stuck
