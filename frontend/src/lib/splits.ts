/** Helpers for the kilometre-splits chart. Pure, so they can be tested without a browser. */
export type Split = {
  km: number;
  distance_m: number;
  time_s: number;
  pace_s_per_km: number;
  elevation_m: number | null;
  partial: boolean;
  /** Average heart rate in the kilometre, when the source has it. Never sent for other people's runs. */
  avg_hr?: number | null;
};

/** 5:32 for 332 seconds. */
export function paceLabel(secondsPerKm: number): string {
  const total = Math.round(secondsPerKm);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

/** Index of the fastest and slowest full kilometre, or null when there are fewer than two to compare. */
export function extremes(splits: Split[]): { fastest: number; slowest: number } | null {
  const full = splits.map((s, i) => ({ s, i })).filter((x) => !x.s.partial);
  if (full.length < 2) return null;
  const sorted = [...full].sort((a, b) => a.s.pace_s_per_km - b.s.pace_s_per_km);
  const fastest = sorted[0].i;
  const slowest = sorted[sorted.length - 1].i;
  return sorted[0].s.pace_s_per_km === sorted[sorted.length - 1].s.pace_s_per_km ? null : { fastest, slowest };
}

/**
 * Bar widths in percent: faster is longer, so a quick kilometre reads as "more". The scale starts at 40% so
 * even the slowest bar stays readable, and is relative to this run (a flat run gives equal bars).
 * The leftover is clamped to the same range.
 */
export function barWidths(splits: Split[]): number[] {
  if (splits.length === 0) return [];
  // Only full kilometres set the scale; the leftover at the end is a different distance and must not look "fastest".
  const basis = splits.filter((s) => !s.partial);
  const paces = (basis.length > 0 ? basis : splits).map((s) => s.pace_s_per_km);
  const fast = Math.min(...paces);
  const slow = Math.max(...paces);
  if (fast === slow) return splits.map(() => 100);
  return splits.map((s) => Math.min(100, Math.max(40, 40 + 60 * ((slow - s.pace_s_per_km) / (slow - fast)))));
}
