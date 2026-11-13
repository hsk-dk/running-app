/** A rough idea of what a race could take, from recent runs. An estimate, never a promise. Pure. */
import { Activity, PlannedRun, dateKey, parseDateKey } from "./week";

export const RIEGEL = 1.06;

/** Riegel: a run of `fromKm` in `timeMin` scaled to `toKm`. */
export function riegel(timeMin: number, fromKm: number, toKm: number, exponent = RIEGEL): number {
  return timeMin * Math.pow(toKm / fromKm, exponent);
}

/** "30m20s - 32m30s" in a Runna description, as seconds. */
export function parseTargetRange(notes: string | null | undefined): { lowSec: number; highSec: number } | null {
  const m = /(\d+)m(\d+)s\s*[-–]\s*(\d+)m(\d+)s/.exec(notes ?? "");
  if (!m) return null;
  const lowSec = Number(m[1]) * 60 + Number(m[2]);
  const highSec = Number(m[3]) * 60 + Number(m[4]);
  return lowSec > 0 && highSec >= lowSec ? { lowSec, highSec } : null;
}

/** The next planned race, today or later. */
export function findRace(plannedRuns: PlannedRun[], today: Date): PlannedRun | null {
  const key = dateKey(today);
  return (
    plannedRuns
      .filter((r) => r.session_type === "race" && r.planned_date >= key)
      .sort((a, b) => (a.planned_date < b.planned_date ? -1 : 1))[0] ?? null
  );
}

export function daysUntil(plannedDate: string, today: Date): number {
  const a = parseDateKey(plannedDate).getTime();
  const b = parseDateKey(dateKey(today)).getTime();
  return Math.round((a - b) / 86_400_000);
}

export type Estimate = { fastSec: number; typicalSec: number; runs: number };

/**
 * Scales runs from the last eight weeks that are long enough to say something, to the race distance.
 * `fast` comes from the quickest of them, `typical` from the middle one. Training is usually easier than a race,
 * so both tend to be on the cautious side.
 */
export function estimate(activities: Activity[], targetKm: number, today: Date, weeks = 8): Estimate | null {
  const since = dateKey(new Date(today.getTime() - weeks * 7 * 86_400_000));
  const minKm = Math.max(3, targetKm * 0.6);
  const scaled = activities
    .filter((a) => a.date && a.date >= since && a.distance_km >= minKm && a.duration_min > 0)
    .map((a) => riegel(a.duration_min * 60, a.distance_km, targetKm))
    .sort((x, y) => x - y);
  if (scaled.length === 0) return null;
  const mid = Math.floor(scaled.length / 2);
  const typical = scaled.length % 2 ? scaled[mid] : (scaled[mid - 1] + scaled[mid]) / 2;
  return { fastSec: scaled[0], typicalSec: typical, runs: scaled.length };
}

/** 1820 -> "30:20", 3725 -> "1:02:05". */
export function clock(totalSeconds: number): string {
  const s = Math.round(totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}` : `${m}:${String(r).padStart(2, "0")}`;
}

export const paceOf = (seconds: number, km: number) => clock(seconds / km);
