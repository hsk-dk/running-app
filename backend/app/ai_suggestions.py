from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta

import requests

from app.config import settings
from app.db import get_conn

logger = logging.getLogger(__name__)

_OLLAMA_TIMEOUT = 120


def _get_recent_activities(weeks: int = 6) -> list[dict]:
    cutoff = datetime.now() - timedelta(weeks=weeks)
    cutoff_str = cutoff.strftime("%Y-%m-%dT00:00:00")

    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                start_date,
                name,
                distance_m,
                moving_time_s,
                average_heartrate,
                total_elevation_gain
            FROM activities
            WHERE sport_type = 'Run'
              AND start_date >= ?
            ORDER BY start_date
            """,
            (cutoff_str,),
        ).fetchall()

        result = []
        for row in rows:
            dt_str = str(row["start_date"])[:10]
            distance_km = round(float(row["distance_m"] or 0) / 1000.0, 2)
            duration_min = round(float(row["moving_time_s"] or 0) / 60.0, 1)
            result.append(
                {
                    "date": dt_str,
                    "name": row["name"] or "",
                    "distance_km": distance_km,
                    "duration_min": duration_min,
                    "avg_hr": (
                        round(float(row["average_heartrate"]), 1)
                        if row["average_heartrate"] is not None
                        else None
                    ),
                    "elevation_m": (
                        round(float(row["total_elevation_gain"]), 0)
                        if row["total_elevation_gain"] is not None
                        else None
                    ),
                }
            )
        return result
    finally:
        conn.close()


def _get_weekly_summary(activities: list[dict]) -> list[dict]:
    weeks: dict[str, dict] = {}
    for a in activities:
        d = datetime.strptime(a["date"], "%Y-%m-%d")
        iso = d.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        if key not in weeks:
            weeks[key] = {
                "week": key,
                "runs": 0,
                "total_km": 0.0,
                "total_min": 0.0,
                "avg_hr_values": [],
            }
        weeks[key]["runs"] += 1
        weeks[key]["total_km"] += a["distance_km"]
        weeks[key]["total_min"] += a["duration_min"]
        if a["avg_hr"] is not None:
            weeks[key]["avg_hr_values"].append(a["avg_hr"])

    result = []
    for w in weeks.values():
        hr_values = w.pop("avg_hr_values")
        w["avg_hr"] = round(sum(hr_values) / len(hr_values), 1) if hr_values else None
        w["total_km"] = round(w["total_km"], 2)
        w["total_min"] = round(w["total_min"], 1)
        result.append(w)
    return sorted(result, key=lambda x: x["week"])


def _get_current_planned_runs() -> list[dict]:
    today = date.today()
    three_weeks = today + timedelta(weeks=3)

    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT planned_date, session_type, target_type, target_value,
                   mandatory, status, notes
            FROM planned_runs
            WHERE planned_date BETWEEN ? AND ?
            ORDER BY planned_date
            """,
            (today.isoformat(), three_weeks.isoformat()),
        ).fetchall()

        return [
            {
                "planned_date": row["planned_date"],
                "session_type": row["session_type"],
                "target_type": row["target_type"] or "time",
                "target_value": row["target_value"],
                "mandatory": bool(row["mandatory"]),
                "status": row["status"],
                "notes": row["notes"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def _next_monday() -> date:
    today = date.today()
    days_ahead = 7 - today.weekday()
    return today + timedelta(days=days_ahead)


def _build_prompt(
    activities: list[dict],
    weekly_summary: list[dict],
    existing_plan: list[dict],
) -> str:
    next_monday = _next_monday()
    week_dates = [next_monday + timedelta(days=i) for i in range(7)]
    week_str = f"{week_dates[0].isoformat()} (Monday) to {week_dates[6].isoformat()} (Sunday)"

    recent_lines = []
    for a in activities[-20:]:
        hr_part = f", avg HR: {a['avg_hr']} bpm" if a["avg_hr"] else ""
        elev_part = f", elevation: {a['elevation_m']}m" if a["elevation_m"] else ""
        recent_lines.append(
            f"  - {a['date']}: {a['distance_km']} km in {a['duration_min']} min{hr_part}{elev_part}"
        )

    weekly_lines = []
    for w in weekly_summary[-6:]:
        hr_part = f", avg HR: {w['avg_hr']} bpm" if w["avg_hr"] else ""
        weekly_lines.append(
            f"  - {w['week']}: {w['runs']} runs, {w['total_km']} km, {w['total_min']} min{hr_part}"
        )

    plan_lines = []
    if existing_plan:
        for p in existing_plan:
            tgt = f"{p['target_value']} {'km' if p['target_type'] == 'distance' else 'min'}"
            plan_lines.append(
                f"  - {p['planned_date']}: {p['session_type']} ({tgt}), status={p['status']}"
            )

    parts = [
        "You are an experienced running coach. Based on the athlete's recent Strava training data below, "
        "generate a personalised training plan for next week.",
        "",
        f"## Next week: {week_str}",
        "",
        "## Recent activities (last 6 weeks, most recent last):",
    ]
    if recent_lines:
        parts.extend(recent_lines)
    else:
        parts.append("  (no recent activities)")

    parts += [
        "",
        "## Weekly volume summary (last 6 weeks):",
    ]
    if weekly_lines:
        parts.extend(weekly_lines)
    else:
        parts.append("  (no data)")

    if plan_lines:
        parts += [
            "",
            "## Already scheduled sessions in the coming weeks:",
        ]
        parts.extend(plan_lines)

    parts += [
        "",
        "## Instructions:",
        "- Suggest 3-5 training sessions for next week, scaled to the athlete's recent volume and fitness.",
        "- Use progressive overload principles but avoid sudden volume spikes >10%.",
        "- Include at least one easy/recovery run and one longer run if volume warrants it.",
        "- Use session types from this list: easy, tempo, long, intervals, recovery.",
        "- Provide target as either distance (km) or time (minutes).",
        "- day_offset: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday.",
        "- mandatory: true for key sessions, false for optional/easy sessions.",
        "",
        "Respond ONLY with a single valid JSON object (no markdown, no explanation):",
        "{",
        '  "summary": "Brief coaching rationale for the week (1-2 sentences)",',
        '  "suggestions": [',
        "    {",
        '      "day_offset": 1,',
        '      "session_type": "easy",',
        '      "target_type": "time",',
        '      "target_value": 45,',
        '      "mandatory": true,',
        '      "notes": "Easy aerobic run at conversational pace"',
        "    }",
        "  ]",
        "}",
    ]

    return "\n".join(parts)


def _call_ollama(prompt: str) -> str:
    response = requests.post(
        f"{settings.OLLAMA_URL}/api/generate",
        json={
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=_OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def _extract_json_text(raw_text: str) -> str:
    """Strip optional markdown code fences and return bare JSON text."""
    text = raw_text.strip()
    for fence in ("```json", "```"):
        if fence in text:
            start = text.index(fence) + len(fence)
            end = text.index("```", start) if "```" in text[start:] else len(text)
            return text[start:end].strip()
    return text


def _parse_suggestions(raw_text: str, next_monday: date) -> tuple[list[dict], str]:
    """Return (suggestions, summary) parsed from the LLM JSON response."""
    text = _extract_json_text(raw_text)
    data = json.loads(text)
    summary = data.get("summary", "")
    suggestions_raw = data.get("suggestions", [])

    result = []
    for s in suggestions_raw:
        day_offset = int(s.get("day_offset", 0))
        day_offset = max(0, min(6, day_offset))
        planned_date = next_monday + timedelta(days=day_offset)

        target_value = s.get("target_value")
        if target_value is not None:
            target_value = float(target_value)

        result.append(
            {
                "planned_date": planned_date.isoformat(),
                "session_type": str(s.get("session_type", "easy")),
                "target_type": str(s.get("target_type", "time")),
                "target_value": target_value,
                "mandatory": bool(s.get("mandatory", True)),
                "notes": str(s.get("notes", "")) if s.get("notes") else None,
            }
        )
    return result, summary


def generate_suggestions() -> dict:
    activities = _get_recent_activities(weeks=6)
    weekly_summary = _get_weekly_summary(activities)
    existing_plan = _get_current_planned_runs()
    next_monday = _next_monday()

    prompt = _build_prompt(activities, weekly_summary, existing_plan)

    try:
        raw_response = _call_ollama(prompt)
    except requests.exceptions.ConnectionError:
        logger.warning("Ollama not available (connection refused)")
        return {
            "available": False,
            "error": "AI service not available. Make sure Ollama is running.",
            "suggestions": [],
            "summary": None,
        }
    except requests.exceptions.Timeout:
        logger.warning("Ollama timed out")
        return {
            "available": False,
            "error": "AI service timed out. Try again or increase timeout.",
            "suggestions": [],
            "summary": None,
        }
    except Exception:
        logger.exception("Ollama call failed")
        return {
            "available": False,
            "error": "AI service encountered an unexpected error.",
            "suggestions": [],
            "summary": None,
        }

    try:
        suggestions, summary = _parse_suggestions(raw_response, next_monday)
    except Exception:
        logger.warning("Failed to parse AI response. Raw: %s", raw_response)
        return {
            "available": True,
            "error": "Could not parse AI response. The model may need to be prompted differently.",
            "suggestions": [],
            "summary": None,
        }

    return {
        "available": True,
        "error": None,
        "model": settings.OLLAMA_MODEL,
        "next_week_start": next_monday.isoformat(),
        "summary": summary,
        "suggestions": suggestions,
    }
