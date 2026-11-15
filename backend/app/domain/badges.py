"""Badges ('mærker'): a shelf of things you have done. Every badge is about you and your own start, never about anyone else. Pure.

Most come from what the app already knows: the first times of running (domain/firsts), the milestones of daily challenges, and
the stars. A badge is earned once, on the day it was first reached, and never lost.
"""
from __future__ import annotations

from datetime import date, timedelta

NEW_DAYS = 7
STAR_STEPS = (1, 10, 25, 50, 100)

# key, group, icon, title, what it says when earned, what it says while it is still ahead
CATALOGUE: list[tuple[str, str, str, str, str, str]] = [
    ("first_run", "løb", "🏃", "Første skridt", "Du løb dit første løb.", "Løb dit første løb."),
    ("km_3", "løb", "🥉", "Tre kilometer", "Du løb 3 km i ét løb.", "Løb 3 km i ét løb."),
    ("km_5", "løb", "🥈", "Fem kilometer", "Du løb 5 km i ét løb.", "Løb 5 km i ét løb."),
    ("km_8", "løb", "🥈", "Otte kilometer", "Du løb 8 km i ét løb.", "Løb 8 km i ét løb."),
    ("km_10", "løb", "🥇", "Ti kilometer", "Du løb 10 km i ét løb.", "Løb 10 km i ét løb."),
    ("km_15", "løb", "🥇", "Femten kilometer", "Du løb 15 km i ét løb.", "Løb 15 km i ét løb."),
    ("km_21", "løb", "🏅", "Halvmaraton", "Du løb en halv maraton.", "Løb en halv maraton (21 km)."),
    ("week_3", "løb", "📅", "Tre i ugen", "Du løb tre gange i samme uge.", "Løb tre gange i samme uge."),
    ("runs_10", "løb", "🔟", "Ti løb", "Du har løbet 10 gange.", "Løb 10 gange i alt."),
    ("runs_25", "løb", "🎽", "Femogtyve løb", "Du har løbet 25 gange.", "Løb 25 gange i alt."),
    ("runs_50", "løb", "🎽", "Halvtreds løb", "Du har løbet 50 gange.", "Løb 50 gange i alt."),
    ("runs_100", "løb", "💯", "Hundrede løb", "Du har løbet 100 gange.", "Løb 100 gange i alt."),
    ("streak_4", "løb", "🔥", "Fire uger i træk", "Du var ude fire uger i træk.", "Vær ude mindst én gang om ugen i fire uger."),
    ("streak_8", "løb", "🔥", "Otte uger i træk", "Du var ude otte uger i træk.", "Vær ude mindst én gang om ugen i otte uger."),
    ("streak_12", "løb", "🔥", "Tolv uger i træk", "Du var ude tolv uger i træk.", "Vær ude mindst én gang om ugen i tolv uger."),
    ("streak_26", "løb", "🌋", "Et halvt år i træk", "Du var ude 26 uger i træk.", "Vær ude mindst én gang om ugen i 26 uger."),
    ("streak_52", "løb", "🌋", "Et helt år i træk", "Du var ude 52 uger i træk.", "Vær ude mindst én gang om ugen i 52 uger."),
    ("challenge_7", "udfordring", "💪", "Syv dage i træk", "Du klarede din udfordring syv dage i træk.", "Klar en daglig udfordring syv dage i træk."),
    ("challenge_14", "udfordring", "💪", "Fjorten dage i træk", "Du klarede din udfordring 14 dage i træk.", "Klar en daglig udfordring 14 dage i træk."),
    ("challenge_30", "udfordring", "🏆", "Tredive dage i træk", "Du klarede din udfordring 30 dage i træk.", "Klar en daglig udfordring 30 dage i træk."),
    ("challenge_best", "udfordring", "🚀", "Ny bedste dag", "Du slog din egen bedste dag.", "Slå din egen bedste dag i en udfordring."),
    ("challenge_double", "udfordring", "✨", "Fordoblet", "Du nåede det dobbelte af, hvad du startede med.", "Nå det dobbelte af dit startmål i en udfordring."),
    ("stars_1", "stjerner", "⭐", "Første stjerne", "Du fik din første stjerne.", "Få din første stjerne."),
    ("stars_10", "stjerner", "⭐", "Ti stjerner", "Du har samlet 10 stjerner.", "Samle 10 stjerner."),
    ("stars_25", "stjerner", "🌟", "Femogtyve stjerner", "Du har samlet 25 stjerner.", "Samle 25 stjerner."),
    ("stars_50", "stjerner", "🌟", "Halvtreds stjerner", "Du har samlet 50 stjerner.", "Samle 50 stjerner."),
    ("stars_100", "stjerner", "🌠", "Hundrede stjerner", "Du har samlet 100 stjerner.", "Samle 100 stjerner."),
]

KEYS = [c[0] for c in CATALOGUE]


def star_dates(stars_by_day: dict[date, int]) -> dict[int, date]:
    """The day the running total of stars first reached each step (1, 10, 25, 50, 100)."""
    out: dict[int, date] = {}
    running = 0
    for day in sorted(stars_by_day):
        running += stars_by_day[day]
        for step in STAR_STEPS:
            if running >= step and step not in out:
                out[step] = day
    return out


def reached(firsts: list[dict], challenge: dict, stars_by_day: dict[date, int]) -> dict[str, date]:
    """The day each badge was first earned. `firsts` is [{key, date}], `challenge` has streaks {7|14|30: date}, best and double dates."""
    out: dict[str, date] = {f["key"]: f["date"] for f in firsts if f["key"] in KEYS}
    for n, day in (challenge.get("streaks") or {}).items():
        if f"challenge_{n}" in KEYS:
            out[f"challenge_{n}"] = day
    if challenge.get("best"):
        out["challenge_best"] = challenge["best"]
    if challenge.get("double"):
        out["challenge_double"] = challenge["double"]
    for step, day in star_dates(stars_by_day).items():
        out[f"stars_{step}"] = day
    return out


def shelf(firsts: list[dict], challenge: dict, stars_by_day: dict[date, int], today: date) -> dict:
    """The shelf: what is earned (newest first) and what is still ahead (in the order of the catalogue)."""
    when = reached(firsts, challenge, stars_by_day)
    earned, ahead = [], []
    for key, group, icon, title, said, hint in CATALOGUE:
        if key in when:
            earned.append({"key": key, "group": group, "icon": icon, "title": title, "description": said, "date": when[key],
                           "is_new": today - when[key] < timedelta(days=NEW_DAYS)})
        else:
            ahead.append({"key": key, "group": group, "icon": icon, "title": title, "hint": hint})
    earned.sort(key=lambda b: (b["date"], KEYS.index(b["key"])), reverse=True)
    return {"earned": earned, "ahead": ahead, "total": len(CATALOGUE)}
