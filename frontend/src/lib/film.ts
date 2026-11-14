import { records } from "./records";

export type FilmRun = { date: string | null; distance_km: number; duration_min: number };

export type FilmSummary = {
  runs: number;
  km: number;
  hours: number;
  activeDays: number;
  lines: string[]; // what the closing scene says, in order, only things that are true
};

const MARATHON_KM = 42.195;
const n0 = (v: number) => Math.round(v).toLocaleString("da-DK");
const n1 = (v: number) => v.toLocaleString("da-DK", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** The facts a year film ends on. Pure. */
export function summarise(all: FilmRun[]): FilmSummary {
  const runs = all.filter((r) => r.distance_km > 0);
  const km = runs.reduce((s, r) => s + r.distance_km, 0);
  const minutes = runs.reduce((s, r) => s + r.duration_min, 0);
  const activeDays = new Set(runs.filter((r) => r.date).map((r) => r.date!.slice(0, 10))).size;
  const lines: string[] = [];
  if (runs.length === 0) return { runs: 0, km: 0, hours: 0, activeDays: 0, lines };
  lines.push(`${runs.length} løb på ${activeDays} ${activeDays === 1 ? "dag" : "dage"}`);
  if (minutes > 0) lines.push(`${n0(km)} km på ${n1(minutes / 60)} timer`);
  const rec = new Map(records(runs).map((r) => [r.key, r]));
  if (rec.get("longest")) lines.push(`Længste løb: ${rec.get("longest")!.value}, ${rec.get("longest")!.detail}`);
  if (rec.get("month") && runs.length >= 10) lines.push(`Travleste måned: ${rec.get("month")!.detail}, ${rec.get("month")!.value}`);
  if (rec.get("week") && runs.length >= 10) lines.push(`Længste uge: ${rec.get("week")!.value}`);
  if (km >= MARATHON_KM) lines.push(`Det svarer til ${n1(km / MARATHON_KM)} maratonløb`);
  return { runs: runs.length, km, hours: minutes / 60, activeDays, lines };
}

/** The number a counter shows `ms` into a count-up of `total` ms, easing out so it settles gently. */
export function countUp(ms: number, total: number, target: number): number {
  if (total <= 0) return target;
  const t = Math.min(1, Math.max(0, ms / total));
  return target * (1 - Math.pow(1 - t, 3));
}

/** How long each closing line takes to appear, and how long the scene rests after the last one. */
export const LINE_STEP_MS = 1000;
export const STATS_REST_MS = 2200;
export const statsMs = (s: FilmSummary): number => s.lines.length * LINE_STEP_MS + STATS_REST_MS;

/** How visible line `i` is `ms` into the closing scene: 0 before its turn, rising to 1 over 500 ms. */
export function lineOpacity(i: number, ms: number): number {
  return Math.min(1, Math.max(0, (ms - i * LINE_STEP_MS) / 500));
}
