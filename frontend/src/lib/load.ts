import { Activity, addDays, dateKey, parseDateKey, weekStartOf } from "./week";

type Run = Pick<Activity, "date" | "distance_km" | "duration_min">;

export type LoadWeek = { start: string; km: number; min: number; runs: number; longest: number; current: boolean };
export type LoadLevel = "rest" | "steady" | "build" | "jump" | "unknown";
export type Load = {
  weeks: LoadWeek[]; // oldest first, the last one is the week in progress
  baseline: number | null; // average km of the four weeks before the last finished week
  ramp: number | null; // the last finished week relative to that baseline
  level: LoadLevel;
  headline: string;
  notes: string[];
  restDays: number; // days since the last run (0 = ran today)
  daysInARow: number; // consecutive days with a run, ending today or yesterday
};

export const WEEKS_SHOWN = 12;
/** Fewer than this many km a week as a baseline says nothing about a jump. */
const MIN_BASELINE_KM = 5;

const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
const km0 = (v: number) => Math.round(v).toLocaleString("da-DK");

/** Weekly volume for the last weeks, Monday to Sunday, and a plain reading of the trend. Pure. */
export function loadOver(all: Run[], today: Date, count = WEEKS_SHOWN): Load {
  const runs = all.filter((r) => r.date && r.distance_km > 0);
  const thisWeek = weekStartOf(today);
  const weeks: LoadWeek[] = [];
  for (let i = count - 1; i >= 0; i--) {
    const start = addDays(thisWeek, -7 * i);
    const from = dateKey(start);
    const to = dateKey(addDays(start, 6));
    const mine = runs.filter((r) => r.date!.slice(0, 10) >= from && r.date!.slice(0, 10) <= to);
    weeks.push({
      start: from,
      km: sum(mine.map((r) => r.distance_km)),
      min: sum(mine.map((r) => r.duration_min)),
      runs: mine.length,
      longest: mine.reduce((m, r) => Math.max(m, r.distance_km), 0),
      current: i === 0,
    });
  }

  // rest: days since the last run, and a run of consecutive days
  const days = new Set(runs.map((r) => r.date!.slice(0, 10)));
  let restDays = 0;
  let cursor = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  while (!days.has(dateKey(cursor)) && restDays < 365 && days.size > 0) {
    cursor = addDays(cursor, -1);
    restDays += 1;
  }
  let daysInARow = 0;
  let d = days.has(dateKey(today)) ? new Date(today.getFullYear(), today.getMonth(), today.getDate()) : addDays(today, -1);
  while (days.has(dateKey(d))) {
    daysInARow += 1;
    d = addDays(d, -1);
  }

  const finished = weeks.filter((w) => !w.current);
  const last = finished[finished.length - 1];
  const before = finished.slice(-5, -1);
  const active = before.filter((w) => w.runs > 0);
  const baseline = before.length === 4 && active.length >= 3 ? sum(before.map((w) => w.km)) / 4 : null;
  const ramp = baseline !== null && baseline >= MIN_BASELINE_KM && last ? last.km / baseline : null;

  let level: LoadLevel = "unknown";
  let headline = "Der er for få uger til at sige noget om belastningen endnu.";
  if (ramp !== null) {
    if (ramp < 0.8) {
      level = "rest";
      headline = "Sidste uge var roligere end dit gennemsnit: en god uge til at hvile.";
    } else if (ramp <= 1.1) {
      level = "steady";
      headline = "Din træning er stabil: sidste uge lå på linje med de fire før.";
    } else if (ramp <= 1.3) {
      level = "build";
      headline = `Du bygger op: sidste uge var ${Math.round((ramp - 1) * 100)} % over dit gennemsnit.`;
    } else {
      level = "jump";
      headline = `Stor stigning: sidste uge var ${Math.round((ramp - 1) * 100)} % over dit gennemsnit.`;
    }
  }

  const notes: string[] = [];
  if (level === "jump") notes.push("En tommelfingerregel er at holde stigningen fra uge til uge under ca. 10-30 %. Det er ikke en lægelig vurdering.");
  if (daysInARow >= 5) notes.push(`${daysInARow} dage i træk med løb: planlæg en hviledag.`);
  else if (restDays >= 4 && days.size > 0) notes.push(`${restDays} dage siden sidste løb.`);
  if (last && last.km > 0 && last.runs >= 2 && last.longest / last.km > 0.5) {
    notes.push(`Dit længste løb udgjorde ${Math.round((last.longest / last.km) * 100)} % af sidste uges kilometer.`);
  }
  if (baseline !== null) notes.push(`Gennemsnit de fire uger før: ${km0(baseline)} km om ugen.`);

  return { weeks, baseline, ramp, level, headline, notes, restDays, daysInARow };
}
