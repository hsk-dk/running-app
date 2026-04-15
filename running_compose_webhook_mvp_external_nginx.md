# Running Compose + Webhook MVP (External Nginx Reverse Proxy Mode)

En deploybar fullstack MVP til din Docker-LXC med:

- **FastAPI backend**
- **React frontend**
- **SQLite volume**
- **Strava webhook verification + event ingestion**
- **Docker Compose deployment**
- **External Nginx reverse proxy mode**
- **Model 1 routing**: ét domæne med frontend på `/` og backend på `/api`

Den offentlige URL bliver:

```text
https://running.useful.dk
```

og Strava webhook endpointet bliver:

```text
https://running.useful.dk/api/webhooks/strava
```

Strava webhook-systemet validerer callback-adressen med en `GET`, og apps skal svare med det forventede challenge-format. Webhook-subscriptions administreres via Strava API, og resource-requests kræver OAuth access tokens. ([developers.strava.com](https://developers.strava.com/docs/webhooks/?utm_source=chatgpt.com))

---

## Målarkitektur

```text
Internet
  -> Nginx reverse proxy på separat Proxmox-server
  -> Docker-LXC med running-app stack
       ├─ frontend container
       └─ backend container

https://running.useful.dk/
  -> frontend

https://running.useful.dk/api/*
  -> backend

https://running.useful.dk/api/webhooks/strava
  -> backend webhook routes
```

---

## Projektstruktur

```text
running-app/
├── compose.yaml
├── .env
├── data/
│   └── sqlite/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── db.py
│       ├── strava.py
│       ├── ingest.py
│       ├── metrics.py
│       ├── planning.py
│       └── webhooks.py
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        └── api.ts
```

---

# 1. Compose deployment

## `compose.yaml`

Vælg én af disse to varianter.

### Variant A — kun lokal binding på Docker-værten
Brug denne hvis Nginx-proxyen kører på **samme host**, eller hvis du laver en ekstra lokal tunnel/forwarding.

```yaml
services:
  backend:
    build:
      context: ./backend
    container_name: running-backend
    restart: unless-stopped
    env_file:
      - .env
    environment:
      APP_BASE_URL: ${APP_BASE_URL}
      DATABASE_PATH: /data/running.db
    volumes:
      - ./data/sqlite:/data
    ports:
      - "127.0.0.1:18000:8000"

  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_BASE: /api
    container_name: running-frontend
    restart: unless-stopped
    ports:
      - "127.0.0.1:18080:80"
    depends_on:
      - backend
```

### Variant B — eksponér til LAN, så separat proxy-server kan nå Docker-LXC'en
Brug denne hvis din eksterne Nginx-proxy på en anden Proxmox-server skal kunne ramme Docker-LXC'ens IP direkte.

```yaml
services:
  backend:
    build:
      context: ./backend
    container_name: running-backend
    restart: unless-stopped
    env_file:
      - .env
    environment:
      APP_BASE_URL: ${APP_BASE_URL}
      DATABASE_PATH: /data/running.db
    volumes:
      - ./data/sqlite:/data
    ports:
      - "18000:8000"

  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_BASE: /api
    container_name: running-frontend
    restart: unless-stopped
    ports:
      - "18080:80"
    depends_on:
      - backend
```

**Min anbefaling hos dig:** Variant B, kombineret med firewall-regler, så kun din Nginx proxy-server må nå port **18000** og **18080**.

---

## `.env`

```env
APP_BASE_URL=https://running.useful.dk
DATABASE_PATH=/data/running.db
CORS_ORIGINS=https://running.useful.dk

STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REFRESH_TOKEN=your_refresh_token
STRAVA_VERIFY_TOKEN=your_webhook_verify_token
STRAVA_ATHLETE_ID=your_athlete_id
STRAVA_PUSH_SUBSCRIPTION_CALLBACK_URL=https://running.useful.dk/api/webhooks/strava
```

Bemærk:
- `STRAVA_VERIFY_TOKEN` bruges til webhook-verificering.
- `STRAVA_REFRESH_TOKEN` bruges til at hente korte access tokens. Strava kræver access tokens til resource requests og refresh-token flow til fornyelse. ([developers.strava.com](https://developers.strava.com/docs/authentication/?utm_source=chatgpt.com))
- `APP_BASE_URL` og `STRAVA_PUSH_SUBSCRIPTION_CALLBACK_URL` skal matche dit offentlige domæne bag den eksterne Nginx proxy.

---

## Færdig Nginx site-konfiguration

Erstat `10.0.0.25` med IP'en på din Docker-LXC.

```nginx
server {
    listen 80;
    server_name running.useful.dk;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name running.useful.dk;

    ssl_certificate /etc/letsencrypt/live/running.useful.dk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/running.useful.dk/privkey.pem;

    client_max_body_size 20m;

    location /api/ {
        proxy_pass http://10.0.0.25:18000/api/;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
    }

    location / {
        proxy_pass http://10.0.0.25:18080/;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

Denne opsætning giver:
- `https://running.useful.dk/` -> frontend
- `https://running.useful.dk/api/*` -> backend
- `https://running.useful.dk/api/webhooks/strava` -> backend webhook routes

---

# 2. Backend

## `backend/requirements.txt`

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
requests==2.32.3
python-dotenv==1.0.1
pandas==2.2.3
```

---

## `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## `backend/app/config.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/running.db")
    CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]

    STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
    STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
    STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN", "")
    STRAVA_VERIFY_TOKEN = os.getenv("STRAVA_VERIFY_TOKEN", "")
    STRAVA_ATHLETE_ID = os.getenv("STRAVA_ATHLETE_ID", "")
    STRAVA_PUSH_SUBSCRIPTION_CALLBACK_URL = os.getenv("STRAVA_PUSH_SUBSCRIPTION_CALLBACK_URL", "")


settings = Settings()
```

---

## `backend/app/db.py`

```python
import sqlite3
from app.config import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    name TEXT,
    sport_type TEXT,
    start_date TEXT,
    timezone_name TEXT,
    distance_m REAL,
    moving_time_s INTEGER,
    elapsed_time_s INTEGER,
    total_elevation_gain REAL,
    average_speed REAL,
    max_speed REAL,
    average_heartrate REAL,
    max_heartrate REAL,
    average_cadence REAL,
    raw_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS derived_metrics (
    activity_id INTEGER PRIMARY KEY,
    start_date TEXT NOT NULL,
    year INTEGER NOT NULL,
    month_key TEXT NOT NULL,
    iso_week_key TEXT NOT NULL,
    distance_km REAL,
    moving_minutes REAL,
    pace_sec_per_km REAL,
    average_heartrate REAL,
    hr_efficiency REAL,
    easy_aerobic_flag INTEGER,
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS planned_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planned_date TEXT NOT NULL,
    session_type TEXT NOT NULL,
    target_minutes INTEGER,
    optional INTEGER DEFAULT 0,
    notes TEXT,
    matched_activity_id INTEGER,
    status TEXT DEFAULT 'planned',
    FOREIGN KEY (matched_activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    object_type TEXT,
    object_id TEXT,
    aspect_type TEXT,
    owner_id TEXT,
    subscription_id TEXT,
    event_time INTEGER,
    payload_json TEXT NOT NULL,
    processed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    processed_at TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn



def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
```

---

## `backend/app/strava.py`

```python
from __future__ import annotations

import requests
from app.config import settings

TOKEN_URL = "https://www.strava.com/oauth/token"
BASE_URL = "https://www.strava.com/api/v3"


class StravaClient:
    def __init__(self):
        self._access_token = None

    def refresh_access_token(self) -> str:
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": settings.STRAVA_CLIENT_ID,
                "client_secret": settings.STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": settings.STRAVA_REFRESH_TOKEN,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        return self._access_token

    def headers(self) -> dict[str, str]:
        if not self._access_token:
            self.refresh_access_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    def get_activities(self, page: int = 1, per_page: int = 50, after_epoch: int | None = None):
        params = {"page": page, "per_page": per_page}
        if after_epoch is not None:
            params["after"] = after_epoch
        response = requests.get(
            f"{BASE_URL}/athlete/activities",
            headers=self.headers(),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def create_push_subscription(self):
        response = requests.post(
            f"{BASE_URL}/push_subscriptions",
            data={
                "client_id": settings.STRAVA_CLIENT_ID,
                "client_secret": settings.STRAVA_CLIENT_SECRET,
                "callback_url": settings.STRAVA_PUSH_SUBSCRIPTION_CALLBACK_URL,
                "verify_token": settings.STRAVA_VERIFY_TOKEN,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def list_push_subscriptions(self):
        response = requests.get(
            f"{BASE_URL}/push_subscriptions",
            params={
                "client_id": settings.STRAVA_CLIENT_ID,
                "client_secret": settings.STRAVA_CLIENT_SECRET,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
```

Strava dokumenterer webhook-verificering med `GET` på callback-adressen, og push-subscriptions administreres via Strava API. ([developers.strava.com](https://developers.strava.com/docs/webhooks/?utm_source=chatgpt.com))

---

## `backend/app/ingest.py`

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from app.db import get_conn
from app.strava import StravaClient



def get_last_synced_start_date():
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM sync_state WHERE key = 'last_synced_start_date'").fetchone()
        return row["value"] if row else None
    finally:
        conn.close()



def set_last_synced_start_date(value: str):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO sync_state (key, value, updated_at)
            VALUES ('last_synced_start_date', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (value,),
        )
        conn.commit()
    finally:
        conn.close()



def upsert_activity(activity: dict):
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO activities (
                id, name, sport_type, start_date, timezone_name,
                distance_m, moving_time_s, elapsed_time_s,
                total_elevation_gain, average_speed, max_speed,
                average_heartrate, max_heartrate, average_cadence,
                raw_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                sport_type=excluded.sport_type,
                start_date=excluded.start_date,
                timezone_name=excluded.timezone_name,
                distance_m=excluded.distance_m,
                moving_time_s=excluded.moving_time_s,
                elapsed_time_s=excluded.elapsed_time_s,
                total_elevation_gain=excluded.total_elevation_gain,
                average_speed=excluded.average_speed,
                max_speed=excluded.max_speed,
                average_heartrate=excluded.average_heartrate,
                max_heartrate=excluded.max_heartrate,
                average_cadence=excluded.average_cadence,
                raw_json=excluded.raw_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                activity["id"],
                activity.get("name"),
                activity.get("sport_type"),
                activity.get("start_date"),
                activity.get("timezone"),
                activity.get("distance"),
                activity.get("moving_time"),
                activity.get("elapsed_time"),
                activity.get("total_elevation_gain"),
                activity.get("average_speed"),
                activity.get("max_speed"),
                activity.get("average_heartrate"),
                activity.get("max_heartrate"),
                activity.get("average_cadence"),
                json.dumps(activity),
            ),
        )
        conn.commit()
    finally:
        conn.close()



def ingest_recent(pages: int = 3):
    client = StravaClient()
    last_synced = get_last_synced_start_date()
    after_epoch = None

    if last_synced:
        dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00")) - timedelta(days=2)
        after_epoch = int(dt.replace(tzinfo=timezone.utc).timestamp())

    newest_seen = None
    upserted = 0

    for page in range(1, pages + 1):
        activities = client.get_activities(page=page, per_page=50, after_epoch=after_epoch)
        if not activities:
            break

        for activity in activities:
            if activity.get("sport_type") != "Run":
                continue
            upsert_activity(activity)
            upserted += 1

            start_date = activity.get("start_date")
            if start_date:
                dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                if newest_seen is None or dt > newest_seen:
                    newest_seen = dt

    if newest_seen is not None:
        set_last_synced_start_date(newest_seen.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))

    return {"upserted": upserted}



def ingest_latest_window(hours_back: int = 72):
    client = StravaClient()
    after_dt = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    after_epoch = int(after_dt.timestamp())

    upserted = 0
    activities = client.get_activities(page=1, per_page=100, after_epoch=after_epoch)
    for activity in activities:
        if activity.get("sport_type") != "Run":
            continue
        upsert_activity(activity)
        upserted += 1

    return {"upserted": upserted, "window_hours": hours_back}
```

---

## `backend/app/metrics.py`

```python
import pandas as pd
from app.db import get_conn



def rebuild_metrics(easy_hr_ceiling: float = 142.0):
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            """
            SELECT id, start_date, distance_m, moving_time_s, average_heartrate
            FROM activities
            WHERE sport_type = 'Run'
            ORDER BY start_date
            """,
            conn,
        )

        if df.empty:
            return {"rebuilt": 0}

        df["start_date"] = pd.to_datetime(df["start_date"], utc=True)
        df["year"] = df["start_date"].dt.year
        df["month_key"] = df["start_date"].dt.strftime("%Y-%m")
        iso = df["start_date"].dt.isocalendar()
        df["iso_week_key"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
        df["distance_km"] = df["distance_m"] / 1000.0
        df["moving_minutes"] = df["moving_time_s"] / 60.0
        df["pace_sec_per_km"] = df["moving_time_s"] / df["distance_km"]
        df["hr_efficiency"] = df["distance_km"] / df["average_heartrate"]
        df["easy_aerobic_flag"] = (
            df["average_heartrate"].notna() & (df["average_heartrate"] <= easy_hr_ceiling)
        ).astype(int)

        conn.execute("DELETE FROM derived_metrics")
        rows = [
            (
                int(r.id),
                r.start_date.isoformat().replace("+00:00", "Z"),
                int(r.year),
                r.month_key,
                r.iso_week_key,
                float(r.distance_km) if pd.notna(r.distance_km) else None,
                float(r.moving_minutes) if pd.notna(r.moving_minutes) else None,
                float(r.pace_sec_per_km) if pd.notna(r.pace_sec_per_km) else None,
                float(r.average_heartrate) if pd.notna(r.average_heartrate) else None,
                float(r.hr_efficiency) if pd.notna(r.hr_efficiency) else None,
                int(r.easy_aerobic_flag),
            )
            for r in df.itertuples()
        ]

        conn.executemany(
            """
            INSERT INTO derived_metrics (
                activity_id, start_date, year, month_key, iso_week_key,
                distance_km, moving_minutes, pace_sec_per_km,
                average_heartrate, hr_efficiency, easy_aerobic_flag
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        return {"rebuilt": len(rows)}
    finally:
        conn.close()



def get_summary():
    conn = get_conn()
    try:
        total_runs = conn.execute("SELECT COUNT(*) AS c FROM derived_metrics").fetchone()["c"]
        row = conn.execute(
            "SELECT COALESCE(SUM(distance_km), 0) AS km, AVG(average_heartrate) AS avg_hr FROM derived_metrics"
        ).fetchone()
        planned = conn.execute("SELECT COUNT(*) AS c FROM planned_runs WHERE optional = 0").fetchone()["c"]
        completed = conn.execute(
            "SELECT COUNT(*) AS c FROM planned_runs WHERE optional = 0 AND status = 'completed'"
        ).fetchone()["c"]
        adherence = int(round((completed / planned) * 100)) if planned else 0

        return {
            "total_runs": total_runs,
            "total_km": round(row["km"] or 0, 2),
            "avg_hr": round(row["avg_hr"], 1) if row["avg_hr"] is not None else None,
            "adherence_pct": adherence,
        }
    finally:
        conn.close()



def get_monthly_volume():
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT month_key AS month, ROUND(SUM(distance_km), 2) AS km
            FROM derived_metrics
            GROUP BY month_key
            ORDER BY month_key
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def get_activities(limit: int = 100):
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                a.id,
                substr(a.start_date, 1, 10) AS date,
                a.name,
                ROUND(a.distance_m / 1000.0, 2) AS distance_km,
                ROUND(a.moving_time_s / 60.0, 1) AS duration_min,
                a.average_heartrate AS avg_hr
            FROM activities a
            WHERE a.sport_type = 'Run'
            ORDER BY a.start_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
```

---

## `backend/app/planning.py`

```python
import pandas as pd
from app.db import get_conn



def list_planned_runs():
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM planned_runs ORDER BY planned_date, id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



def add_planned_run(data: dict):
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO planned_runs (
                planned_date, session_type, target_minutes, optional, notes, status
            ) VALUES (?, ?, ?, ?, ?, 'planned')
            """,
            (
                data["planned_date"],
                data["session_type"],
                data["target_minutes"],
                int(data.get("optional", False)),
                data.get("notes"),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM planned_runs WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()



def recalculate_plan_status(tolerance_days: int = 1):
    conn = get_conn()
    try:
        planned = pd.read_sql_query("SELECT * FROM planned_runs ORDER BY planned_date, id", conn)
        actual = pd.read_sql_query(
            "SELECT id, start_date, moving_time_s FROM activities WHERE sport_type = 'Run' ORDER BY start_date, id",
            conn,
        )

        if planned.empty:
            return {"updated": 0}

        planned["planned_date"] = pd.to_datetime(planned["planned_date"]).dt.tz_localize(None)
        actual["start_date"] = pd.to_datetime(actual["start_date"], utc=True).dt.tz_convert(None)

        used_ids = set()
        updates = []

        for _, p in planned.iterrows():
            window_start = p["planned_date"] - pd.Timedelta(days=tolerance_days)
            window_end = p["planned_date"] + pd.Timedelta(days=tolerance_days + 1)

            candidates = actual[
                (actual["start_date"] >= window_start)
                & (actual["start_date"] < window_end)
                & (~actual["id"].isin(list(used_ids)))
            ].copy()

            if candidates.empty:
                updates.append((None, "skipped", int(p["id"])))
                continue

            candidates["abs_delta"] = (candidates["start_date"] - p["planned_date"]).abs()
            best = candidates.sort_values(["abs_delta", "start_date", "id"]).iloc[0]
            used_ids.add(int(best["id"]))

            actual_minutes = float(best["moving_time_s"]) / 60.0 if best["moving_time_s"] is not None else 0.0
            target = p["target_minutes"]
            ratio = actual_minutes / float(target) if target else 1.0

            if ratio >= 0.9:
                status = "completed"
            elif ratio >= 0.5:
                status = "shortened"
            else:
                status = "skipped"

            updates.append((int(best["id"]), status, int(p["id"])))

        conn.executemany(
            "UPDATE planned_runs SET matched_activity_id = ?, status = ? WHERE id = ?",
            updates,
        )
        conn.commit()
        return {"updated": len(updates)}
    finally:
        conn.close()



def get_weekly_consistency():
    conn = get_conn()
    try:
        df = pd.read_sql_query("SELECT planned_date, optional, status FROM planned_runs ORDER BY planned_date", conn)
        if df.empty:
            return []

        df["planned_date"] = pd.to_datetime(df["planned_date"])
        iso = df["planned_date"].dt.isocalendar()
        df["week"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)

        mandatory = df[df["optional"] == 0].copy()
        rows = []

        for week, g in mandatory.groupby("week"):
            completed = int((g["status"] == "completed").sum())
            shortened = int((g["status"] == "shortened").sum())
            total = int(len(g))

            if total > 0 and completed == total:
                score = "Green"
            elif completed + shortened > 0:
                score = "Yellow"
            else:
                score = "Red"

            rows.append(
                {
                    "week": week,
                    "mandatory_runs": total,
                    "completed": completed,
                    "shortened": shortened,
                    "score": score,
                }
            )

        return rows
    finally:
        conn.close()
```

---

## `backend/app/webhooks.py`

```python
from __future__ import annotations

import json
from app.config import settings
from app.db import get_conn
from app.ingest import ingest_latest_window
from app.metrics import rebuild_metrics
from app.planning import recalculate_plan_status



def verify_subscription(mode: str, token: str, challenge: str):
    if mode != "subscribe":
        return None
    if token != settings.STRAVA_VERIFY_TOKEN:
        return None
    return {"hub.challenge": challenge}



def store_event(payload: dict):
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO webhook_events (
                provider, object_type, object_id, aspect_type,
                owner_id, subscription_id, event_time, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "strava",
                payload.get("object_type"),
                str(payload.get("object_id")) if payload.get("object_id") is not None else None,
                payload.get("aspect_type"),
                str(payload.get("owner_id")) if payload.get("owner_id") is not None else None,
                str(payload.get("subscription_id")) if payload.get("subscription_id") is not None else None,
                payload.get("event_time"),
                json.dumps(payload),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()



def mark_event_processed(event_id: int):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE webhook_events SET processed = 1, processed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (event_id,),
        )
        conn.commit()
    finally:
        conn.close()



def process_event(payload: dict):
    event_id = store_event(payload)

    owner_id = str(payload.get("owner_id", ""))
    object_type = payload.get("object_type")

    if settings.STRAVA_ATHLETE_ID and owner_id and owner_id != settings.STRAVA_ATHLETE_ID:
        mark_event_processed(event_id)
        return {"stored": True, "processed": True, "ignored": True, "reason": "owner_mismatch"}

    if object_type == "activity":
        ingest_result = ingest_latest_window(hours_back=72)
        metrics_result = rebuild_metrics()
        planning_result = recalculate_plan_status(tolerance_days=1)
        mark_event_processed(event_id)
        return {
            "stored": True,
            "processed": True,
            "ingest": ingest_result,
            "metrics": metrics_result,
            "planning": planning_result,
        }

    mark_event_processed(event_id)
    return {"stored": True, "processed": True, "ignored": True, "reason": "unsupported_object_type"}
```

---

## `backend/app/main.py`

```python
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.ingest import ingest_recent
from app.metrics import rebuild_metrics, get_summary, get_monthly_volume, get_activities
from app.planning import list_planned_runs, add_planned_run, recalculate_plan_status, get_weekly_consistency
from app.webhooks import verify_subscription, process_event

init_db()

app = FastAPI(title="Running Compose MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/activities")
def api_activities(limit: int = 100):
    return get_activities(limit=limit)


@app.get("/api/metrics/summary")
def api_summary():
    return get_summary()


@app.get("/api/metrics/monthly-volume")
def api_monthly_volume():
    return get_monthly_volume()


@app.get("/api/planning")
def api_planning():
    return list_planned_runs()


@app.get("/api/planning/weekly-consistency")
def api_weekly_consistency():
    return get_weekly_consistency()


@app.post("/api/planning")
def api_add_planned_run(payload: dict):
    return add_planned_run(payload)


@app.post("/api/admin/ingest")
def api_ingest(pages: int = 3):
    return ingest_recent(pages=pages)


@app.post("/api/admin/rebuild-metrics")
def api_rebuild_metrics():
    return rebuild_metrics()


@app.post("/api/admin/recalculate-plan")
def api_recalculate_plan(tolerance_days: int = 1):
    return recalculate_plan_status(tolerance_days=tolerance_days)


@app.get("/api/webhooks/strava")
def strava_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    result = verify_subscription(hub_mode, hub_verify_token, hub_challenge)
    if result is None:
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    return result


@app.post("/api/webhooks/strava")
async def strava_webhook_event(request: Request):
    payload = await request.json()
    return process_event(payload)
```

---

# 3. Frontend

## `frontend/package.json`

```json
{
  "name": "running-frontend",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.12.7"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.4",
    "vite": "^5.4.2"
  }
}
```

---

## `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

---

## `frontend/nginx.conf`

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri /index.html;
    }
}
```

---

## `frontend/vite.config.ts`

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
});
```

---

## `frontend/src/api.ts`

```ts
const API_BASE = import.meta.env.VITE_API_BASE || "/api";

async function getJson(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getSummary: () => getJson("/metrics/summary"),
  getMonthlyVolume: () => getJson("/metrics/monthly-volume"),
  getActivities: () => getJson("/activities"),
  getPlannedRuns: () => getJson("/planning"),
  getWeeklyConsistency: () => getJson("/planning/weekly-consistency"),
  addPlannedRun: (payload: any) =>
    getJson("/planning", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  runIngest: () => getJson("/admin/ingest", { method: "POST" }),
  runMetrics: () => getJson("/admin/rebuild-metrics", { method: "POST" }),
  runPlanEval: () => getJson("/admin/recalculate-plan", { method: "POST" }),
};
```

---

## `frontend/src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

---

## `frontend/src/App.tsx`

```tsx
import { useEffect, useState } from "react";
import { AreaChart, Area, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart, Bar } from "recharts";
import { api } from "./api";

const shellStyle: React.CSSProperties = {
  minHeight: "100vh",
  padding: 24,
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Inter, sans-serif",
  lineHeight: 1.6,
  color: "#1f2937",
  background: "#C9CFD8 url(https://auth.useful.dk/media/public/background.jpg) center center / cover no-repeat fixed",
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: 0,
  background:
    "radial-gradient(120% 120% at 50% 30%, rgba(0,0,0,0.00) 0%, rgba(0,0,0,0.05) 55%, rgba(0,0,0,0.14) 100%), linear-gradient(to bottom, rgba(0,0,0,0.04), rgba(0,0,0,0.06))",
  pointerEvents: "none",
};

const containerStyle: React.CSSProperties = {
  position: "relative",
  zIndex: 1,
  maxWidth: 1120,
  margin: "0 auto",
  padding: "16px 12px 40px",
  display: "grid",
  gap: 24,
};

const panelStyle: React.CSSProperties = {
  background: "rgba(255, 255, 255, 0.86)",
  backdropFilter: "saturate(110%) blur(6px)",
  borderRadius: 14,
  padding: 24,
  boxShadow: "0 10px 30px rgba(0,0,0,0.20)",
  border: "1px solid rgba(36, 49, 64, 0.10)",
};

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: 10,
  padding: 16,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "12px 16px",
  border: "1px solid #d1d5db",
  borderRadius: 8,
  background: "#ffffff",
  fontSize: 14,
};

const primaryButtonStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: 6,
  border: "1px solid transparent",
  background: "linear-gradient(to bottom right, #9dc0ff, #446ea8)",
  color: "white",
  boxShadow: "0 6px 16px rgba(0,0,0,0.18)",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 500,
};

const secondaryButtonStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: 6,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#6b7280",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 500,
};

function metricTone(status: string) {
  if (status === "Green" || status === "completed") return { bg: "#ecfdf5", border: "#bbf7d0", color: "#166534" };
  if (status === "Yellow" || status === "shortened") return { bg: "#fffbeb", border: "#fde68a", color: "#92400e" };
  if (status === "Red" || status === "skipped") return { bg: "#fef2f2", border: "#fecaca", color: "#991b1b" };
  return { bg: "#f8fafc", border: "#e2e8f0", color: "#475569" };
}

function StatusBadge({ value }: { value: string }) {
  const tone = metricTone(value);
  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        background: tone.bg,
        border: `1px solid ${tone.border}`,
        color: tone.color,
      }}
    >
      {value}
    </span>
  );
}

function SummaryCard({ title, value, subtitle }: { title: string; value: string | number; subtitle: string }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.05em", color: "#6b7280", marginBottom: 6 }}>{title}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "#1e40af" }}>{value}</div>
      <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>{subtitle}</div>
    </div>
  );
}

export default function App() {
  const [summary, setSummary] = useState<any>(null);
  const [monthlyVolume, setMonthlyVolume] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);
  const [plannedRuns, setPlannedRuns] = useState<any[]>([]);
  const [weeklyConsistency, setWeeklyConsistency] = useState<any[]>([]);
  const [form, setForm] = useState({ planned_date: "", session_type: "easy", target_minutes: 30, optional: false, notes: "" });
  const [loading, setLoading] = useState(false);

  async function loadAll() {
    const [s, mv, a, p, wc] = await Promise.all([
      api.getSummary(),
      api.getMonthlyVolume(),
      api.getActivities(),
      api.getPlannedRuns(),
      api.getWeeklyConsistency(),
    ]);
    setSummary(s);
    setMonthlyVolume(mv);
    setActivities(a);
    setPlannedRuns(p);
    setWeeklyConsistency(wc);
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleAdminAction(action: "ingest" | "metrics" | "plan") {
    setLoading(true);
    try {
      if (action === "ingest") await api.runIngest();
      if (action === "metrics") await api.runMetrics();
      if (action === "plan") await api.runPlanEval();
      await loadAll();
    } finally {
      setLoading(false);
    }
  }

  async function handleAddPlannedRun(e: React.FormEvent) {
    e.preventDefault();
    await api.addPlannedRun(form);
    setForm({ planned_date: "", session_type: "easy", target_minutes: 30, optional: false, notes: "" });
    await loadAll();
  }

  return (
    <div style={shellStyle}>
      <div style={overlayStyle} />
      <div style={containerStyle}>
        <header style={{ textAlign: "center", marginBottom: 8 }}>
          <h1 style={{ fontSize: "2.5rem", marginBottom: 8, fontWeight: 800, color: "#243140", letterSpacing: "-0.025em" }}>Running</h1>
          <p style={{ fontSize: "1.125rem", color: "#425061", fontWeight: 400 }}>Training data, plan adherence and consistency.</p>
        </header>

        <main style={panelStyle}>
          <div style={{ display: "grid", gap: 24 }}>
            <section style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#243140" }}>Overview</div>
                <div style={{ fontSize: 14, color: "#425061" }}>External Nginx proxy mode deployment.</div>
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button style={primaryButtonStyle} onClick={() => handleAdminAction("ingest")} disabled={loading}>Sync from Strava</button>
                <button style={secondaryButtonStyle} onClick={() => handleAdminAction("metrics")} disabled={loading}>Rebuild metrics</button>
                <button style={secondaryButtonStyle} onClick={() => handleAdminAction("plan")} disabled={loading}>Evaluate plan</button>
              </div>
            </section>

            <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
              <SummaryCard title="Total runs" value={summary?.total_runs ?? 0} subtitle="All synced runs" />
              <SummaryCard title="Total km" value={summary?.total_km ?? 0} subtitle="Running volume" />
              <SummaryCard title="Average HR" value={summary?.avg_hr ?? "-"} subtitle="Across runs with HR" />
              <SummaryCard title="Adherence" value={`${summary?.adherence_pct ?? 0}%`} subtitle="Mandatory runs completed" />
            </section>

            <section style={{ display: "grid", gridTemplateColumns: "minmax(0, 2fr) minmax(320px, 1fr)", gap: 16 }}>
              <div style={cardStyle}>
                <div style={{ marginBottom: 12, fontWeight: 600, color: "#374151" }}>Monthly volume</div>
                <div style={{ width: "100%", height: 280 }}>
                  <ResponsiveContainer>
                    <AreaChart data={monthlyVolume}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <Tooltip />
                      <Area type="monotone" dataKey="km" stroke="#446ea8" fill="#9dc0ff" fillOpacity={0.22} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div style={cardStyle}>
                <div style={{ marginBottom: 12, fontWeight: 600, color: "#374151" }}>Weekly consistency</div>
                <div style={{ display: "grid", gap: 10 }}>
                  {weeklyConsistency.length === 0 ? (
                    <div style={{ color: "#64748b", fontSize: 14 }}>No planned runs yet.</div>
                  ) : (
                    weeklyConsistency.slice(-6).map((week) => (
                      <div key={week.week} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", padding: 12, borderRadius: 8, background: "#f9fafb", border: "1px solid #e5e7eb" }}>
                        <div>
                          <div style={{ fontWeight: 600 }}>{week.week}</div>
                          <div style={{ fontSize: 13, color: "#64748b" }}>{week.completed}/{week.mandatory_runs} mandatory runs completed</div>
                        </div>
                        <StatusBadge value={week.score} />
                      </div>
                    ))
                  )}
                </div>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
```

---

# 4. Første opstart

```bash
cd running-app
mkdir -p data/sqlite
nano .env

docker compose build
docker compose up -d
```

Lokal kontrol på Docker-LXC'en:

```bash
curl http://127.0.0.1:18000/api/health
curl http://127.0.0.1:18080/
```

Hvis du bruger **Variant B**, test også fra proxy-serveren:

```bash
curl http://10.0.0.25:18000/api/health
curl http://10.0.0.25:18080/
```

Efter Nginx-konfiguration:

```bash
curl https://running.useful.dk/api/health
```

---

# 5. Opret Strava webhook-subscription

Når appen svarer korrekt på:

```text
GET https://running.useful.dk/api/webhooks/strava
```

kan du oprette subscription mod Strava API:

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=$STRAVA_CLIENT_ID \
  -F client_secret=$STRAVA_CLIENT_SECRET \
  -F callback_url=https://running.useful.dk/api/webhooks/strava \
  -F verify_token=$STRAVA_VERIFY_TOKEN
```

Strava dokumenterer, at subscription-oprettelse udløser en `GET` mod callback-adressen for validering. ([developers.strava.com](https://developers.strava.com/docs/webhooks/?utm_source=chatgpt.com))

Liste subscriptions:

```bash
curl "https://www.strava.com/api/v3/push_subscriptions?client_id=$STRAVA_CLIENT_ID&client_secret=$STRAVA_CLIENT_SECRET"
```

---

# 6. Hvad denne version kan

- deployes som compose-stack i din Docker-LXC
- køre bag en ekstern Nginx reverse proxy
- bruge ét domæne med `/` til frontend og `/api` til backend
- modtage Strava webhook verification
- modtage Strava webhook events
- lagre rå webhook-events
- ingest'e nye løb automatisk efter webhook-hit
- genberegne metrics
- opdatere plan-status
- vise frontend i useful.dk-stil

---

# 7. Kendte begrænsninger i MVP

- webhook processing kører synkront i requesten
- ingen auth på admin-endpoints endnu
- ingen background worker/queue endnu
- ingen streams endnu
- SQLite er fin til MVP, men ikke til mere parallel belastning

---

# 8. Næste iteration jeg ville tage

1. admin-auth
2. background worker for webhook processing
3. Strava OAuth login i stedet for statisk refresh token
4. autogenerering af dit 12-ugers program
5. streams og mere avancerede løbemetrics
6. firewall-stramning så kun proxy-serveren må nå 18000 og 18080

---

# 9. Praktisk anbefaling

Brug denne rækkefølge:

1. deploy stacken i Docker-LXC
2. test backend og frontend direkte på LXC-IP og porte
3. læg Nginx site-konfigurationen på proxy-serveren
4. verificer `https://running.useful.dk/api/health`
5. opret Strava webhook subscription
6. kør manuel ingest og rebuild metrics
7. opret planlagte pas
8. test at et nyt eller opdateret Strava-løb udløser webhook-flowet

Det næste mest værdifulde skridt vil være at gøre denne version produktionsklar med **admin-auth og async webhook worker**.

