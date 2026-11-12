/** Pure helpers for the "År" view. No React and no network. All dates are local calendar dates. */
import { Activity, addDays, dateKey, parseDateKey, weekStartOf } from "./week";

export type DayCell = { date: string; km: number; min: number; runs: number; weekIndex: number; weekday: number };

/** One cell per day from the Monday of the week 52 weeks back, up to and including `end`. */
export function buildDays(activities: Activity[], end: Date): DayCell[] {
  const start = weekStartOf(addDays(end, -364));
  const byDate = new Map<string, { km: number; min: number; runs: number }>();
  for (const a of activities) {
    if (!a.date) continue;
    const cur = byDate.get(a.date) ?? { km: 0, min: 0, runs: 0 };
    cur.km += a.distance_km;
    cur.min += a.duration_min;
    cur.runs += 1;
    byDate.set(a.date, cur);
  }
  const cells: DayCell[] = [];
  const endKey = dateKey(end);
  for (let i = 0; ; i++) {
    const d = addDays(start, i);
    const key = dateKey(d);
    if (key > endKey) break;
    const v = byDate.get(key) ?? { km: 0, min: 0, runs: 0 };
    cells.push({ date: key, km: round1(v.km), min: Math.round(v.min), runs: v.runs, weekIndex: Math.floor(i / 7), weekday: i % 7 });
  }
  return cells;
}

const round1 = (v: number) => Math.round(v * 10) / 10;

/** Colour level 0-4 for a value, by the quartiles of the days that have a run. */
export function levelFn(values: number[]): (v: number) => 0 | 1 | 2 | 3 | 4 {
  const pos = values.filter((v) => v > 0).sort((a, b) => a - b);
  if (pos.length === 0) return () => 0;
  // Upper bound of levels 1-3 at the 25th, 50th and 75th percentile, so the largest values reach level 4.
  const q = [0.25, 0.5, 0.75].map((f) => pos[Math.max(0, Math.ceil(pos.length * f) - 1)]);
  return (v) => (v <= 0 ? 0 : v <= q[0] ? 1 : v <= q[1] ? 2 : v <= q[2] ? 3 : 4);
}

export type WeekTotal = { weekStart: string; km: number; min: number; runs: number };

export function weeklyTotals(days: DayCell[]): WeekTotal[] {
  const weeks: WeekTotal[] = [];
  for (const d of days) {
    if (!weeks[d.weekIndex]) weeks[d.weekIndex] = { weekStart: "", km: 0, min: 0, runs: 0 };
    const w = weeks[d.weekIndex];
    if (d.weekday === 0) w.weekStart = d.date;
    w.km = round1(w.km + d.km);
    w.min += d.min;
    w.runs += d.runs;
  }
  return weeks;
}

/** Weeks that are over. The current week counts once its last day (Sunday) is today or past. */
export function completeWeeks(weeks: WeekTotal[], today: Date): WeekTotal[] {
  const todayKey = dateKey(today);
  return weeks.filter((w) => w.weekStart !== "" && dateKey(addDays(parseDateKey(w.weekStart), 6)) <= todayKey);
}

export function rollingAverage(values: number[], window = 4): number[] {
  return values.map((_, i) => {
    const slice = values.slice(Math.max(0, i - window + 1), i + 1);
    return slice.reduce((a, b) => a + b, 0) / slice.length;
  });
}

export type MonthTotal = { key: string; km: number };

export function monthlyTotals(days: DayCell[]): MonthTotal[] {
  const out: MonthTotal[] = [];
  for (const d of days) {
    const key = d.date.slice(0, 7);
    if (!out.length || out[out.length - 1].key !== key) out.push({ key, km: 0 });
    out[out.length - 1].km = round1(out[out.length - 1].km + d.km);
  }
  return out;
}

export type YearFacts = {
  totalKm: number;
  runDays: number;
  busiestWeek: { km: number; weekStart: string } | null;
  longestRun: { km: number; date: string; name: string } | null;
  longestWeekStreak: number;
};

export function yearFacts(days: DayCell[], weeks: WeekTotal[], activities: Activity[]): YearFacts {
  const inRange = new Set(days.map((d) => d.date));
  const runs = activities.filter((a) => a.date && inRange.has(a.date));
  let busiest: YearFacts["busiestWeek"] = null;
  for (const w of weeks) if (w.km > 0 && (!busiest || w.km > busiest.km)) busiest = { km: w.km, weekStart: w.weekStart };
  let longest: YearFacts["longestRun"] = null;
  for (const a of runs) if (!longest || a.distance_km > longest.km) longest = { km: a.distance_km, date: a.date as string, name: a.name ?? "Løb" };
  let streak = 0;
  let best = 0;
  for (const w of weeks) {
    streak = w.runs > 0 ? streak + 1 : 0;
    best = Math.max(best, streak);
  }
  return {
    totalKm: round1(days.reduce((s, d) => s + d.km, 0)),
    runDays: days.filter((d) => d.runs > 0).length,
    busiestWeek: busiest,
    longestRun: longest,
    longestWeekStreak: best,
  };
}

/** "Din base er 18 % højere ..." only when there are enough weeks and the change is real. */
export function baseChange(weeklyKm: number[]): { pct: number; weeks: number } | null {
  if (weeklyKm.length < 8) return null;
  const avg = rollingAverage(weeklyKm, 4);
  const first = avg[3];
  const last = avg[avg.length - 1];
  if (first <= 0 || last <= 0) return null;
  const pct = Math.round((last / first - 1) * 100);
  return Math.abs(pct) >= 5 ? { pct, weeks: avg.length - 4 } : null;
}
