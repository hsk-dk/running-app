import { addDays, dateKey } from "./week";

/** "all", "last365", or a calendar year such as "2026". */
export type Period = string;

export const ALL: Period = "all";
export const LAST_YEAR: Period = "last365";

/** Does a date (YYYY-MM-DD…) fall in the period? Runs without a date only belong to "all". */
export function inPeriod(date: string | null | undefined, period: Period, today: Date): boolean {
  if (period === ALL) return true;
  if (!date) return false;
  const day = date.slice(0, 10);
  if (period === LAST_YEAR) return day >= dateKey(addDays(today, -365)) && day <= dateKey(today);
  return day.slice(0, 4) === period;
}

/** The calendar years that have runs, newest first. */
export function yearsOf(dates: (string | null | undefined)[]): string[] {
  return [...new Set(dates.filter((d): d is string => !!d).map((d) => d.slice(0, 4)))].sort().reverse();
}

export function periodLabel(period: Period): string {
  if (period === ALL) return "Alle dine løb";
  if (period === LAST_YEAR) return "De seneste 12 måneder";
  return period;
}

/** The period a film should start on: the newest calendar year with at least `min` runs, else the last 12 months. */
export function defaultFilmPeriod(dates: (string | null | undefined)[], min = 5): Period {
  const counts = new Map<string, number>();
  for (const d of dates) if (d) counts.set(d.slice(0, 4), (counts.get(d.slice(0, 4)) ?? 0) + 1);
  const years = [...counts.keys()].sort().reverse();
  return years.find((y) => (counts.get(y) ?? 0) >= min) ?? LAST_YEAR;
}
