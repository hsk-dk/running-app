import { isRun } from "./runs";
import { addDays, dateKey, parseDateKey } from "./week";

type Run = { date: string | null; distance_km: number; duration_min?: number };

export type JourneyMonth = { key: string; longest: number; runs: number; minutes: number };

export type Journey = {
  firstDate: string;
  weeksIn: number; // the first week is week 1
  runs: number;
  km: number;
  minutes: number; // all the time spent running, for the view without kilometres
  firstKm: number; // the first run
  recentLongest: number; // the longest run in the last four weeks, 0 if none
  months: JourneyMonth[]; // from the first month to this one, at most 12, months without runs included
  beginner: boolean;
  headline: string;
  note: string;
};

export const MONTHS_SHOWN = 12;
/** Someone is "new" while they have few runs or have only just started. */
export const BEGINNER_RUNS = 20;
export const BEGINNER_WEEKS = 12;

const n1 = (v: number) => v.toLocaleString("da-DK", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Your own start to today, and nothing else: no one to compare with. Pure. */
export function journey(all: Run[], today: Date): Journey | null {
  const runs = all.filter((r) => r.date && isRun(r)).sort((a, b) => (a.date! < b.date! ? -1 : a.date! > b.date! ? 1 : 0));
  if (runs.length === 0) return null;
  const first = runs[0];
  const firstDate = first.date!.slice(0, 10);
  const days = Math.max(0, Math.round((parseDateKey(dateKey(today)).getTime() - parseDateKey(firstDate).getTime()) / 86400000));
  const weeksIn = Math.floor(days / 7) + 1;
  const km = runs.reduce((s, r) => s + r.distance_km, 0);
  const minutes = runs.reduce((s, r) => s + (r.duration_min ?? 0), 0);

  const byMonth = new Map<string, JourneyMonth>();
  for (const r of runs) {
    const key = r.date!.slice(0, 7);
    const m = byMonth.get(key) ?? { key, longest: 0, runs: 0, minutes: 0 };
    m.longest = Math.max(m.longest, r.distance_km);
    m.runs += 1;
    m.minutes += r.duration_min ?? 0;
    byMonth.set(key, m);
  }
  const months: JourneyMonth[] = [];
  let y = Number(firstDate.slice(0, 4));
  let mo = Number(firstDate.slice(5, 7));
  const endKey = dateKey(today).slice(0, 7);
  for (;;) {
    const key = `${y}-${String(mo).padStart(2, "0")}`;
    if (key > endKey) break;
    months.push(byMonth.get(key) ?? { key, longest: 0, runs: 0, minutes: 0 });
    mo += 1;
    if (mo > 12) { mo = 1; y += 1; }
  }

  const since = dateKey(addDays(today, -27));
  const recent = runs.filter((r) => r.date!.slice(0, 10) >= since);
  const recentLongest = recent.reduce((m, r) => Math.max(m, r.distance_km), 0);
  const beginner = runs.length < BEGINNER_RUNS || weeksIn <= BEGINNER_WEEKS;

  const grown = runs.length >= 3 && recentLongest >= first.distance_km * 1.3 && recentLongest - first.distance_km >= 0.5;
  const headline = grown
    ? `Du er gået fra ${n1(first.distance_km)} km til ${n1(recentLongest)} km på ${weeksIn} ${weeksIn === 1 ? "uge" : "uger"}.`
    : `Uge ${weeksIn} i gang: ${runs.length} ${runs.length === 1 ? "løb" : "løb"} og ${n1(km)} km i alt.`;
  const note = beginner ? "Det er helt normalt at holde hviledage mellem løbene. Det vigtigste er at blive ved." : "";

  return { firstDate, weeksIn, runs: runs.length, km, minutes, firstKm: first.distance_km, recentLongest, months: months.slice(-MONTHS_SHOWN), beginner, headline, note };
}

/** "35 min", "1 t 5 min", "2 t": time in words, for the view that counts minutes and not kilometres. */
export function minutesText(total: number): string {
  const m = Math.max(0, Math.round(total));
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest === 0 ? `${h} t` : `${h} t ${rest} min`;
}

/** The sentence for a child: how long you have been at it and how much time you spent, never how far or how fast. */
export function childHeadline(j: Pick<Journey, "weeksIn" | "runs" | "minutes">): string {
  return `Uge ${j.weeksIn} i gang: ${j.runs} ${j.runs === 1 ? "gang" : "gange"} ude og ${minutesText(j.minutes)} i bevægelse.`;
}
