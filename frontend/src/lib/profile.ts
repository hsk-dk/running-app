/** Pure helpers for the tempo and heart-rate profile of a run, and for its laps. */

export type Profile = {
  t: number[];
  d: number[];
  hr?: (number | null)[] | null;
  v?: (number | null)[] | null;
  cad?: (number | null)[] | null;
  alt?: (number | null)[] | null;
};

export type Lap = {
  start_s: number | null;
  duration_s: number;
  distance_m: number | null;
  avg_hr: number | null;
  pace_s_per_km: number | null;
  intensity: string | null;
};

/** Speed in m/s for every sample: the recorded speed where there is one, otherwise from how far it got in how long. */
export function speeds(p: Profile): (number | null)[] {
  return p.t.map((t, i) => {
    const v = p.v?.[i];
    if (v !== null && v !== undefined) return v;
    if (i === 0) return null;
    const dt = t - p.t[i - 1];
    return dt > 0 ? (p.d[i] - p.d[i - 1]) / dt : null;
  });
}

/** A centred moving average that ignores gaps, so per-second noise does not hide the shape of an interval session. */
export function smooth(values: (number | null)[], window = 5): (number | null)[] {
  const half = Math.floor(window / 2);
  return values.map((v, i) => {
    if (v === null) return null;
    let sum = 0;
    let n = 0;
    for (let j = Math.max(0, i - half); j <= Math.min(values.length - 1, i + half); j++) {
      const x = values[j];
      if (x !== null) {
        sum += x;
        n += 1;
      }
    }
    return n ? sum / n : null;
  });
}

/** Seconds per kilometre for a speed, or null when standing still (so a pause is a gap, not a huge number). */
export const paceFromSpeed = (v: number | null): number | null => (v !== null && v > 0.5 ? 1000 / v : null);

export const paceLabel = (secondsPerKm: number): string => {
  const total = Math.round(secondsPerKm);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
};

/** The laps worth showing: more than one, and not just the watch's automatic kilometre laps. */
export function lapsToShow(laps: Lap[]): Lap[] {
  if (laps.length < 2) return [];
  const autoKm = laps.slice(0, -1).every((l) => l.distance_m !== null && l.distance_m >= 950 && l.distance_m <= 1050);
  return autoKm ? [] : laps;
}

/** Nice round tick values between min and max (about `count` of them). */
export function ticks(min: number, max: number, count = 4): number[] {
  if (!(max > min)) return [min];
  const raw = (max - min) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(Math.round(v * 1e6) / 1e6);
  return out;
}
