import { Activity, addDays, dateKey, parseDateKey, weekStartOf } from "./week";

type Run = Pick<Activity, "date" | "distance_km" | "duration_min">;

export type RecordKey = "longest" | "pace" | "week" | "month" | "streak";
export type RecordItem = { key: RecordKey; label: string; value: string; detail: string; date: string; amount: number; better: "high" | "low" };

const km = (v: number, d = 1) => v.toLocaleString("da-DK", { minimumFractionDigits: d, maximumFractionDigits: d });
export const paceText = (minPerKm: number) => {
  let m = Math.floor(minPerKm);
  let s = Math.round((minPerKm - m) * 60);
  if (s === 60) { m += 1; s = 0; }
  return `${m}:${String(s).padStart(2, "0")} /km`;
};
const monthName = (date: string) => parseDateKey(date).toLocaleDateString("da-DK", { month: "long", year: "numeric" });
const dayName = (date: string) => parseDateKey(date).toLocaleDateString("da-DK", { day: "numeric", month: "long", year: "numeric" });

/** The fastest pace only counts runs of this length or more: a short dash says nothing about fitness. */
export const PACE_MIN_KM = 5;
/** Below this many runs there is nothing to call a record. */
export const MIN_RUNS = 5;

function weeks(runs: Run[]): Map<string, { km: number; last: string }> {
  const out = new Map<string, { km: number; last: string }>();
  for (const r of runs) {
    if (!r.date) continue;
    const key = dateKey(weekStartOf(parseDateKey(r.date)));
    const w = out.get(key) ?? { km: 0, last: r.date.slice(0, 10) };
    w.km += r.distance_km;
    if (r.date.slice(0, 10) > w.last) w.last = r.date.slice(0, 10);
    out.set(key, w);
  }
  return out;
}

/** Your personal bests. Each one says when it was set. Pure. */
export function records(all: Run[]): RecordItem[] {
  const runs = all.filter((r) => r.date && r.distance_km > 0);
  if (runs.length < MIN_RUNS) return [];
  const out: RecordItem[] = [];

  const longest = runs.reduce((a, b) => (b.distance_km > a.distance_km ? b : a));
  out.push({ key: "longest", label: "Længste løb", value: `${km(longest.distance_km)} km`, detail: dayName(longest.date!), date: longest.date!.slice(0, 10), amount: longest.distance_km, better: "high" });

  const fast = runs.filter((r) => r.distance_km >= PACE_MIN_KM && r.duration_min > 0);
  if (fast.length) {
    const best = fast.reduce((a, b) => (b.duration_min / b.distance_km < a.duration_min / a.distance_km ? b : a));
    const pace = best.duration_min / best.distance_km;
    out.push({ key: "pace", label: `Hurtigste tempo (mindst ${PACE_MIN_KM} km)`, value: paceText(pace), detail: `${km(best.distance_km)} km, ${dayName(best.date!)}`, date: best.date!.slice(0, 10), amount: pace, better: "low" });
  }

  const wk = weeks(runs);
  const bestWeek = [...wk.entries()].reduce((a, b) => (b[1].km > a[1].km ? b : a));
  out.push({ key: "week", label: "Længste uge", value: `${km(bestWeek[1].km)} km`, detail: `Ugen fra ${dayName(bestWeek[0])}`, date: bestWeek[1].last, amount: bestWeek[1].km, better: "high" });

  const months = new Map<string, { km: number; last: string }>();
  for (const r of runs) {
    const key = r.date!.slice(0, 7);
    const m = months.get(key) ?? { km: 0, last: r.date!.slice(0, 10) };
    m.km += r.distance_km;
    if (r.date!.slice(0, 10) > m.last) m.last = r.date!.slice(0, 10);
    months.set(key, m);
  }
  const bestMonth = [...months.entries()].reduce((a, b) => (b[1].km > a[1].km ? b : a));
  out.push({ key: "month", label: "Travleste måned", value: `${km(bestMonth[1].km, 0)} km`, detail: monthName(`${bestMonth[0]}-01`), date: bestMonth[1].last, amount: bestMonth[1].km, better: "high" });

  // longest run of consecutive weeks with at least one run
  const keys = [...wk.keys()].sort();
  let best = 0, cur = 0, bestEnd = keys[0], prev: string | null = null;
  for (const k of keys) {
    cur = prev !== null && dateKey(addDays(parseDateKey(prev), 7)) === k ? cur + 1 : 1;
    if (cur > best) { best = cur; bestEnd = k; }
    prev = k;
  }
  out.push({ key: "streak", label: "Uger i træk med løb", value: `${best}`, detail: `Sluttede i ugen fra ${dayName(bestEnd)}`, date: wk.get(bestEnd)!.last, amount: best, better: "high" });
  return out;
}

const beats = (a: RecordItem, b: RecordItem) => (a.better === "high" ? a.amount > b.amount + 1e-9 : a.amount < b.amount - 1e-9);

/** Records set in the last `days` days: they beat everything that came before. */
export function newRecords(all: Run[], today: Date, days = 7): RecordItem[] {
  const cutoff = dateKey(addDays(today, -days));
  const before = records(all.filter((r) => r.date && r.date.slice(0, 10) <= cutoff));
  if (before.length === 0) return []; // not enough history: the first runs are not "records"
  const prior = new Map(before.map((r) => [r.key, r]));
  return records(all).filter((r) => {
    const old = prior.get(r.key);
    return r.date > cutoff && (!old || beats(r, old));
  });
}

export type WeekStory = { headline: string; notes: string[] };

/** The week so far in a sentence, plus what is true and worth saying about it. Never says anything discouraging. */
export function weekStory(all: Run[], today: Date): WeekStory | null {
  const runs = all.filter((r) => r.date && r.distance_km > 0);
  const start = weekStartOf(today);
  const startKey = dateKey(start);
  const todayKey = dateKey(today);
  const mine = runs.filter((r) => r.date!.slice(0, 10) >= startKey && r.date!.slice(0, 10) <= todayKey);
  if (mine.length === 0) return null;
  const total = mine.reduce((s, r) => s + r.distance_km, 0);
  const headline = `${km(total, 0)} km i ${mine.length === 1 ? "1 løb" : `${mine.length} løb`} denne uge.`;
  const notes: string[] = [];

  const earlier = [...weeks(runs.filter((r) => r.date!.slice(0, 10) < startKey)).entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1));
  if (earlier.length >= 4) {
    const higher = earlier.filter(([, w]) => w.km >= total);
    if (higher.length === 0) notes.push("Din længste uge nogensinde.");
    else {
      const lastKey = higher[higher.length - 1][0];
      const gapWeeks = Math.round((start.getTime() - parseDateKey(lastKey).getTime()) / (7 * 86400000));
      if (gapWeeks >= 8) notes.push(`Din længste uge siden ${monthName(lastKey)}.`);
    }
    const recent = earlier.slice(-4);
    const avg = recent.reduce((s, [, w]) => s + w.km, 0) / recent.length;
    if (avg > 0 && total >= avg * 1.2 && !notes.length) notes.push(`Mere end dit gennemsnit de seneste 4 uger (${km(avg, 0)} km).`);
  }
  const longestWeek = mine.reduce((a, b) => (b.distance_km > a.distance_km ? b : a));
  const before8 = runs.filter((r) => r.date!.slice(0, 10) < startKey && r.date!.slice(0, 10) >= dateKey(addDays(start, -56)));
  if (before8.length >= 4 && mine.length > 1 && longestWeek.distance_km > Math.max(...before8.map((r) => r.distance_km))) {
    notes.push(`Dit længste løb i 8 uger: ${km(longestWeek.distance_km)} km.`);
  }
  return { headline, notes };
}
