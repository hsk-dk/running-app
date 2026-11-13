"""A person's Garmin Connect, through Garmin's personal API: their runs, and what each run's FIT file shows."""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone

from app import fit, garmin
from app.config import settings
from app.db import get_conn
from app.domain import fitdata
from app.domain import garmin as domain
from app.errors import ConflictError, NotConnectedError, UpstreamError
from app.repositories import activities as activity_repo
from app.repositories import garmin_accounts, user_state

logger = logging.getLogger(__name__)

OVERLAP_DAYS = 2  # re-read a little before the last sync: a run can be edited after it is uploaded
DUPLICATE_WINDOW_SECONDS = 120
FIT_PER_SYNC = 25  # outdoor runs read up front each sync; the rest are read when opened
_KEY_CHARS = re.compile(r"[A-Za-z0-9._~+/=:-]{8,600}")


# ---- connection --------------------------------------------------------------------------------------

def status(user_id: int) -> dict:
    conn = get_conn()
    try:
        account = garmin_accounts.get(conn, user_id)
        last = user_state.get(conn, user_id, "garmin_last_sync_at")
        error = user_state.get(conn, user_id, "garmin_last_error")
        return {
            "connected": account is not None,
            "last_sync_at": last["value"] if last and last["value"] else None,
            "last_error": error["value"] if error and error["value"] else None,
        }
    finally:
        conn.close()


def clean_key(raw: str) -> str:
    key = (raw or "").strip().strip("\"'`").strip()
    return re.sub(r"^(apikey\s+|bearer\s+)", "", key, flags=re.IGNORECASE).strip()


def connect(user_id: int, key: str) -> dict:
    """Check the key really works (swap it for a token and read the activity list) before saving it."""
    key = clean_key(key)
    if not _KEY_CHARS.fullmatch(key):
        raise ConflictError("Det ligner ikke en Garmin-nøgle. Indsæt kun selve nøglen, uden mellemrum.")
    try:
        bearer, expires = garmin.exchange_key(key)
        garmin.GarminClient(key, bearer, expires).search_activities(0, 1)
    except garmin.GarminAuthError as exc:
        raise ConflictError(str(exc)) from exc
    except Exception as exc:
        raise UpstreamError(f"Kunne ikke nå Garmin: {exc}") from exc
    conn = get_conn()
    try:
        garmin_accounts.upsert(conn, user_id, key, bearer, expires)
        conn.commit()
    finally:
        conn.close()
    return status(user_id)


def disconnect(user_id: int) -> dict:
    conn = get_conn()
    try:
        garmin_accounts.delete(conn, user_id)
        user_state.upsert(conn, user_id, "garmin_last_sync_date", "")
        conn.commit()
    finally:
        conn.close()
    return status(user_id)


def client_for(user_id: int) -> garmin.GarminClient:
    conn = get_conn()
    try:
        account = garmin_accounts.get(conn, user_id)
    finally:
        conn.close()
    if account is None:
        raise NotConnectedError("Garmin er ikke forbundet for denne bruger")

    def save(bearer: str, expires_at: int) -> None:
        c = get_conn()
        try:
            garmin_accounts.update_token(c, user_id, bearer, expires_at)
            c.commit()
        finally:
            c.close()

    return garmin.GarminClient(account["api_key"], account["bearer_token"], account["token_expires_at"], on_token=save)


# ---- reading runs ------------------------------------------------------------------------------------

def ingest_recent(user_id: int, full: bool = False) -> dict:
    """New runs are added; a run already stored from another source (Smashrun, Strava) is linked to its Garmin
    activity instead of being added twice. Outdoor runs get their FIT file read right away."""
    client = client_for(user_id)
    today = date.today()

    conn = get_conn()
    try:
        last = user_state.get(conn, user_id, "garmin_last_sync_date")
    finally:
        conn.close()
    start_date = None
    if not full and last and last["value"]:
        start_date = (date.fromisoformat(last["value"]) - timedelta(days=OVERLAP_DAYS)).isoformat()

    added = updated = linked = skipped = 0
    wanted: list[int] = []  # outdoor runs whose file we want to read now
    offset = 0
    while True:
        batch = client.search_activities(start=offset, limit=garmin.PAGE_SIZE, start_date=start_date)
        for summary in batch:
            activity = domain.activity_from_summary(summary, settings.APP_TIMEZONE)
            if activity is None:
                skipped += 1
                continue
            conn = get_conn()
            try:
                existing = activity_repo.get(conn, user_id, activity["id"])
                target_id = activity["id"]
                if existing is not None:
                    activity_repo.upsert(conn, user_id, activity, source=domain.SOURCE, source_id=str(activity["garmin_id"]))
                    updated += 1
                else:
                    twin = activity_repo.find_near_local(conn, user_id, activity["start_date_local"], DUPLICATE_WINDOW_SECONDS)
                    if twin is not None:
                        target_id = twin["id"]
                        if twin["garmin_id"] is None:
                            activity_repo.set_garmin_id(conn, user_id, twin["id"], activity["garmin_id"])
                            linked += 1
                        else:
                            target_id = None  # already linked to a Garmin activity: nothing to do
                    else:
                        activity_repo.upsert(conn, user_id, activity, source=domain.SOURCE, source_id=str(activity["garmin_id"]))
                        activity_repo.set_garmin_id(conn, user_id, activity["id"], activity["garmin_id"])
                        added += 1
                conn.commit()
                if target_id is not None and not activity["treadmill"]:
                    wanted.append(target_id)
            finally:
                conn.close()
        if len(batch) < garmin.PAGE_SIZE:
            break
        offset += garmin.PAGE_SIZE

    read = 0
    for activity_id in wanted:
        if read >= FIT_PER_SYNC:
            break
        conn = get_conn()
        try:
            row = activity_repo.get(conn, user_id, activity_id)
        finally:
            conn.close()
        if row is not None and row["fit_status"] is None and read_fit(user_id, row, client) is not None:
            read += 1

    result = {"source": "garmin", "added": added, "linked": linked, "updated": updated, "skipped": skipped, "fit_read": read}
    conn = get_conn()
    try:
        user_state.upsert(conn, user_id, "garmin_last_sync_date", today.isoformat())
        stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        user_state.upsert(conn, user_id, "garmin_last_sync_at", stamp)
        user_state.upsert(conn, user_id, "last_sync_at", stamp)
        user_state.upsert(conn, user_id, "last_ingest_result", json.dumps(result, ensure_ascii=False))
        user_state.upsert(conn, user_id, "garmin_last_error", "")
        user_state.upsert(conn, user_id, "last_error", "")
        conn.commit()
    finally:
        conn.close()
    return result


def after_connect(user_id: int) -> None:
    """First sync after connecting: the whole history. Runs in the background and records failures."""
    from app.services import planning_service  # imported late: heavier

    try:
        ingest_recent(user_id, full=True)
        planning_service.evaluate_and_sync(user_id)
    except Exception as exc:  # nobody is waiting for the answer
        logger.exception("First Garmin sync failed")
        c = get_conn()
        try:
            user_state.upsert(c, user_id, "garmin_last_error", str(exc))
            user_state.upsert(c, user_id, "last_error", str(exc))
            c.commit()
        finally:
            c.close()


# ---- the FIT file of one run ---------------------------------------------------------------------------------

def read_fit(user_id: int, row, client: garmin.GarminClient | None = None) -> dict | None:
    """Download and read the run's FIT file once, and keep what it says. None if the file cannot be had right now
    (nothing is saved, so it is tried again later); a run Garmin has no usable file for is marked and left alone."""
    if row["garmin_id"] is None:
        return None
    client = client or client_for(user_id)
    try:
        content = client.download_activity(row["garmin_id"])
    except NotConnectedError:
        return None
    except Exception:
        logger.warning("Could not download the Garmin file for activity %s", row["id"], exc_info=True)
        return None

    if content is None:
        analysis, status = None, "none"
    else:
        try:
            records, laps = fit.parse(content)
            analysis, status = fitdata.analyze(records, laps), "ok"
        except fit.FitError:
            logger.warning("Garmin file for activity %s could not be read", row["id"], exc_info=True)
            analysis, status = None, "none"

    conn = get_conn()
    try:
        activity_repo.set_fit_result(
            conn, user_id, row["id"], status=status,
            route=analysis["route"] if analysis else None,
            profile_json=json.dumps(analysis["profile"]) if analysis and analysis["profile"] else None,
            laps_json=json.dumps(analysis["laps"]) if analysis else None,
            splits_json=json.dumps(analysis["splits"]) if analysis and analysis["splits"] else None,
        )
        conn.commit()
    finally:
        conn.close()
    return analysis or {"route": None, "profile": None, "splits": [], "laps": []}


def get_profile(user_id: int, activity_id: int, include_hr: bool = True) -> dict:
    """The run's profile and laps, reading the FIT file the first time it is asked for."""
    from app.errors import NotFoundError

    conn = get_conn()
    try:
        row = activity_repo.get(conn, user_id, activity_id)
    finally:
        conn.close()
    if row is None or row["sport_type"] != "Run":
        raise NotFoundError(f"Activity {activity_id} not found")
    if row["garmin_id"] is None:
        return {"available": True, "source": False, "profile": None, "laps": []}  # not a Garmin-linked run: nothing to show

    if row["fit_status"] is None:
        if read_fit(user_id, row) is None:
            return {"available": False, "source": True, "profile": None, "laps": []}  # Garmin could not be asked right now
        conn = get_conn()
        try:
            row = activity_repo.get(conn, user_id, activity_id)
        finally:
            conn.close()

    profile = json.loads(row["profile_json"]) if row["profile_json"] else None
    laps = json.loads(row["laps_json"]) if row["laps_json"] else []
    if not include_hr:
        if profile:
            profile = {**profile, "hr": None}
        laps = [{**lap, "avg_hr": None} for lap in laps]
    return {"available": True, "source": True, "profile": profile, "laps": laps}
