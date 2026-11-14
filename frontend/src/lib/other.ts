import { addDays, dateKey } from "./week";

/** A walk, a ride, rowing and so on: anything recorded that is not a run. */
export type Other = { id: number; date: string | null; kind: string; name: string | null; distance_km: number; duration_min: number };

export const KIND_LABEL: Record<string, string> = {
  Walk: "Gang",
  Ride: "Cykling",
  Row: "Roning",
  Paddle: "Kajak og padling",
  Swim: "Svømning",
  Strength: "Styrke og øvelser",
  Other: "Anden træning",
};
export const kindLabel = (kind: string): string => KIND_LABEL[kind] ?? KIND_LABEL.Other;

/** The days that have other activity, as a set of YYYY-MM-DD. */
export function otherDays(others: Pick<Other, "date">[]): Set<string> {
  return new Set(others.filter((o) => o.date).map((o) => o.date!.slice(0, 10)));
}

/** "Roning (12), Gang (8), Cykling (4)": the most common kinds first, at most `max`, ties in alphabetical order. */
export function kindsText(others: Pick<Other, "kind">[], max = 3): string {
  const counts = new Map<string, number>();
  for (const o of others) counts.set(o.kind, (counts.get(o.kind) ?? 0) + 1);
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || (kindLabel(a[0]) < kindLabel(b[0]) ? -1 : 1))
    .slice(0, max)
    .map(([k, n]) => `${kindLabel(k)} (${n})`)
    .join(", ");
}

/** What other activity there was in the last `days` days. */
export function recentOther(others: Pick<Other, "date" | "duration_min">[], today: Date, days: number): { count: number; hours: number } {
  const from = dateKey(addDays(today, -(days - 1)));
  const to = dateKey(today);
  const mine = others.filter((o) => o.date && o.date.slice(0, 10) >= from && o.date.slice(0, 10) <= to);
  return { count: mine.length, hours: mine.reduce((s, o) => s + o.duration_min, 0) / 60 };
}
