/**
 * Pure helpers for the "Nu" and "Uge" views. No React and no network, so they are easy to test.
 * Dates are local calendar dates ("YYYY-MM-DD"), matching how the backend stores planned dates.
 */

export type PlannedRun = {
  id: number;
  planned_date: string;
  session_type: string;
  target_type: "time" | "distance" | string;
  target_value: number | null;
  optional: boolean;
  status: string;
  actual_value: number | null;
  matched_activity_id?: number | null;
  display_target?: string;
  display_actual?: string;
  notes?: string | null;
};

export type Activity = {
  id: number;
  date: string | null;
  name: string | null;
  distance_km: number;
  duration_min: number;
  is_extra: boolean;
};

export type DayKind = "done" | "shortened" | "skipped" | "planned" | "rest";

export type DayState = {
  date: string; // YYYY-MM-DD
  weekday: number; // 0 = Monday
  kind: DayKind;
  isToday: boolean;
  isFuture: boolean;
  runs: PlannedRun[];
  extras: Activity[];
};

const DONE = "gennemført";
const SHORTENED = "forkortet";
const SKIPPED = "sprunget over";
const MOVED = "flyttet";
const PLANNED = "planlagt";

export function dateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function parseDateKey(value: string): Date {
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function addDays(d: Date, days: number): Date {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  copy.setDate(copy.getDate() + days);
  return copy;
}

/** Monday of the week containing `d` (weeks start on Monday). */
export function weekStartOf(d: Date): Date {
  const offset = (d.getDay() + 6) % 7;
  return addDays(d, -offset);
}

export function isoWeekNumber(d: Date): number {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  return Math.ceil(((t.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

const WEEKDAYS = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"];
export const weekdayName = (weekday: number) => WEEKDAYS[weekday];
export const weekdayShort = (weekday: number) => WEEKDAYS[weekday].slice(0, 3);

/** One entry per day Monday-Sunday: what happened or is planned, and the unplanned runs. */
export function weekDays(
  plannedRuns: PlannedRun[],
  activities: Activity[],
  weekStart: Date,
  today: Date
): DayState[] {
  const todayKey = dateKey(today);
  const days: DayState[] = [];
  for (let i = 0; i < 7; i++) {
    const date = dateKey(addDays(weekStart, i));
    const runs = plannedRuns.filter((p) => p.planned_date.slice(0, 10) === date && p.status !== MOVED);
    const extras = activities.filter((a) => a.date === date && a.is_extra);

    let kind: DayKind = "rest";
    if (runs.some((r) => r.status === DONE)) kind = "done";
    else if (runs.some((r) => r.status === SHORTENED)) kind = "shortened";
    else if (runs.some((r) => r.status === PLANNED)) kind = "planned";
    else if (runs.some((r) => r.status === SKIPPED)) kind = "skipped";

    days.push({ date, weekday: i, kind, isToday: date === todayKey, isFuture: date > todayKey, runs, extras });
  }
  return days;
}

export type WeekSummary = {
  total: number; // mandatory planned runs this week (moved runs excluded)
  done: number; // completed or shortened
  shortened: number;
  skipped: number;
  open: number; // still to come
};

export function summarizeWeek(days: DayState[]): WeekSummary {
  const mandatory = days.flatMap((d) => d.runs).filter((r) => !r.optional);
  const count = (status: string) => mandatory.filter((r) => r.status === status).length;
  return {
    total: mandatory.length,
    done: count(DONE) + count(SHORTENED),
    shortened: count(SHORTENED),
    skipped: count(SKIPPED),
    open: count(PLANNED),
  };
}

/** The next run that is still to be done, today included. */
export function nextRun(plannedRuns: PlannedRun[], today: Date): PlannedRun | null {
  const todayKey = dateKey(today);
  const upcoming = plannedRuns
    .filter((p) => p.status === PLANNED && p.planned_date.slice(0, 10) >= todayKey)
    .sort((a, b) => a.planned_date.localeCompare(b.planned_date) || a.id - b.id);
  return upcoming[0] ?? null;
}

/** "I dag", "I morgen" or the weekday name ("lørdag"). */
export function dayLabel(plannedDate: string, today: Date): string {
  const diff = Math.round((parseDateKey(plannedDate).getTime() - parseDateKey(dateKey(today)).getTime()) / 86400000);
  if (diff === 0) return "i dag";
  if (diff === 1) return "i morgen";
  const wd = (parseDateKey(plannedDate).getDay() + 6) % 7;
  return diff > 1 && diff < 7 ? WEEKDAYS[wd] : `${WEEKDAYS[wd]} d. ${parseDateKey(plannedDate).getDate()}.`;
}

/** The sentence at the top of "Nu": says how the week is going before any number. */
export function weekHeadline(summary: WeekSummary, next: PlannedRun | null, today: Date): string {
  if (summary.total === 0) return "Ingen vigtige løb planlagt i denne uge.";
  const base = `${summary.done} af ${summary.total} løb i hus.`;
  if (summary.open === 0) {
    return summary.done === summary.total ? `${base} Ugen er klaret.` : `${base} Ugen er slut.`;
  }
  if (next) return `${base} Næste løb er ${dayLabel(next.planned_date, today)}.`;
  return base;
}

/**
 * Short, true statements about the month. Each one only appears when there is something to say.
 * The month so far is compared with the whole previous month, so a fall early in the month says nothing:
 * only "already more than all of last month" is shown.
 */
export function insights(summary: any): string[] {
  const out: string[] = [];
  const kmPrev = Number(summary?.km_prev_month ?? 0);
  const pct = summary?.km_change_pct;
  if (kmPrev > 0 && typeof pct === "number" && pct >= 5) {
    out.push(`Du har allerede løbet ${Math.round(pct)} % mere end hele sidste måned.`);
  }
  const hr = summary?.avg_hr_change;
  if (typeof hr === "number" && Math.abs(hr) >= 2) {
    const n = Math.round(Math.abs(hr));
    out.push(`Gennemsnitspulsen er ${n} slag ${hr < 0 ? "lavere" : "højere"} end sidste måned.`);
  }
  return out;
}

/** "47 af 45 min" / "8,2 af 10 km" for a planned run, or just the target when nothing was matched. */
export function runValueLabel(run: PlannedRun): string {
  const unit = run.target_type === "distance" ? "km" : "min";
  const fmt = (v: number) => v.toLocaleString("da-DK", { maximumFractionDigits: unit === "km" ? 1 : 0 });
  const target = run.target_value ?? 0;
  if (run.actual_value == null) return `${fmt(target)} ${unit} planlagt`;
  return `${fmt(run.actual_value)} af ${fmt(target)} ${unit}`;
}
