/**
 * A run's name as Runna writes it ("W9 Tue Easy Run - 5km Easy Run (") is cut off by Garmin and starts with a plan
 * code. For people it is shortened: no "W9 Tue", no broken parenthesis, " · " between the parts.
 * "Herning - W9 Sun Race - 5km Race (5km)" -> "Herning · Race · 5km Race (5km)".
 */
export function cleanRunName(name: string | null | undefined): string {
  let s = (name ?? "").trim();
  if (!s) return "";
  s = s.replace(/(^|\s-\s)W\d+\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+/, "$1");
  const open = (s.match(/\(/g) ?? []).length;
  const close = (s.match(/\)/g) ?? []).length;
  if (open > close) s = s.slice(0, s.lastIndexOf("(")).trim();
  s = s.replace(/\s+-\s+/g, " · ").replace(/[\s·-]+$/, "").trim();
  return s || (name ?? "").trim();
}

/** "2026-W47" -> "U47" */
export function shortWeek(weekKey: string | null | undefined): string {
  const m = /W(\d+)$/.exec(weekKey ?? "");
  return m ? `U${Number(m[1])}` : "-";
}
