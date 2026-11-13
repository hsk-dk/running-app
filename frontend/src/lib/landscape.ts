/** Pace curves of many runs stacked as ridges, so interval sessions stand out as waves. Pure and testable. */
import { Profile, smooth, speeds } from "./profile";

export type LandscapeRun = {
  id: number;
  date: string | null;
  name: string | null;
  distance_km: number;
  duration_min: number;
  avg_hr: number | null;
  profile: Profile;
};

export type Ridge = {
  id: number;
  date: string | null;
  name: string;
  label: string;
  /** closed outline for the fill */
  fill: string;
  /** just the top line, for the stroke */
  line: string;
  base: number;
  peakSpeed: number;
  km: number;
  paceSec: number | null;
};

/** The speed (m/s) the tallest ridge reaches: one scale for all runs so they can be compared. */
export function speedCap(runs: LandscapeRun[]): number {
  const all = runs.flatMap((r) => smooth(speeds(r.profile), 5).filter((v): v is number => v !== null && v > 0));
  if (all.length === 0) return 4;
  all.sort((a, b) => a - b);
  return Math.max(3.5, all[Math.min(all.length - 1, Math.floor(all.length * 0.98))]);
}

export function shortName(name: string | null | undefined, max = 26): string {
  const text = (name ?? "Løb").replace(/\s+/g, " ").trim() || "Løb";
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
}

/**
 * One ridge per run, oldest on top. All share a time axis (as long as the longest run) so a session that starts
 * with a warm-up lines up with the others. Rows overlap by `overlap` of their height, as in a joyplot.
 */
export function ridges(runs: LandscapeRun[], width: number, rowHeight: number, left = 0, top = 0, overlap = 0.55): Ridge[] {
  const ordered = [...runs].sort((a, b) => ((a.date ?? "") < (b.date ?? "") ? -1 : a.date === b.date ? a.id - b.id : 1));
  const tMax = Math.max(1, ...ordered.map((r) => r.profile.t[r.profile.t.length - 1] ?? 0));
  const cap = speedCap(ordered);
  const amp = rowHeight * (1 + overlap);
  const usable = width - left;
  return ordered.map((run, i) => {
    // room above the first row for its tallest peak (1.15 x the full amplitude)
    const base = top + amp * 1.18 + i * rowHeight;
    const v = smooth(speeds(run.profile), 5);
    const pts = run.profile.t.map((t, k) => {
      const speed = v[k] ?? 0;
      return [left + (t / tMax) * usable, base - Math.min(Math.max(speed, 0) / cap, 1.15) * amp] as [number, number];
    });
    const end = pts.length ? pts[pts.length - 1][0] : left;
    const line = pts.map((p, k) => `${k === 0 ? "M" : "L"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
    return {
      id: run.id,
      date: run.date,
      name: shortName(run.name),
      label: run.date ?? "",
      line,
      fill: pts.length ? `M${left.toFixed(1)} ${base.toFixed(1)} ${line.replace(/^M/, "L")} L${end.toFixed(1)} ${base.toFixed(1)} Z` : "",
      base,
      peakSpeed: Math.max(0, ...v.filter((x): x is number => x !== null)),
      km: run.distance_km,
      paceSec: run.duration_min > 0 && run.distance_km > 0 ? (run.duration_min * 60) / run.distance_km : null,
    };
  });
}

/** Total height needed for `count` ridges. */
export const landscapeHeight = (count: number, rowHeight: number, top = 0, overlap = 0.55) =>
  top + rowHeight * (1 + overlap) * 1.18 + Math.max(0, count - 1) * rowHeight + 14;
