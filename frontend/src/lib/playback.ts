/** The year played back: runs appear in date order, each one drawn along its route. Pure and testable. */
import { PosterRoute } from "./poster";

export type Slot = { id: number; date: string | null; startMs: number; endMs: number };
export type Timeline = { slots: Slot[]; totalMs: number };

const MIN_SLOT_MS = 350;

/** Oldest first. Longer runs get a little more time, but not in proportion (a marathon is not 8 times a 5 k on screen). */
export function timeline(routes: PosterRoute[], totalMs = 14000): Timeline {
  const ordered = [...routes].sort((a, b) => ((a.date ?? "") < (b.date ?? "") ? -1 : a.date === b.date ? a.id - b.id : 1));
  if (ordered.length === 0) return { slots: [], totalMs: 0 };
  const weights = ordered.map((r) => Math.sqrt(Math.max(r.distance_km, 1)));
  const sum = weights.reduce((a, b) => a + b, 0);
  const budget = Math.max(totalMs, ordered.length * MIN_SLOT_MS);
  let t = 0;
  const slots = ordered.map((r, i) => {
    const length = Math.max(MIN_SLOT_MS, (weights[i] / sum) * budget);
    const slot = { id: r.id, date: r.date, startMs: t, endMs: t + length };
    t += length;
    return slot;
  });
  return { slots, totalMs: t };
}

export type Frame = { doneIds: number[]; currentId: number | null; fraction: number; date: string | null };

export function frameAt(tl: Timeline, ms: number): Frame {
  const doneIds: number[] = [];
  let current: Slot | null = null;
  let date: string | null = null;
  for (const slot of tl.slots) {
    if (ms >= slot.endMs) {
      doneIds.push(slot.id);
      date = slot.date ?? date;
    } else if (ms >= slot.startMs) {
      current = slot;
      date = slot.date ?? date;
      break;
    } else break;
  }
  return {
    doneIds,
    currentId: current ? current.id : null,
    fraction: current ? (ms - current.startMs) / (current.endMs - current.startMs) : 0,
    date,
  };
}

const dist = (a: [number, number], b: [number, number]) => Math.hypot(a[0] - b[0], a[1] - b[1]);

/** The first `fraction` of the route by length, ending exactly at that point (not at the next vertex). */
export function partial(points: [number, number][], fraction: number): [number, number][] {
  if (points.length < 2 || fraction <= 0) return points.slice(0, 1);
  if (fraction >= 1) return points;
  const lengths = points.slice(1).map((p, i) => dist(points[i], p));
  const target = lengths.reduce((a, b) => a + b, 0) * fraction;
  const out: [number, number][] = [points[0]];
  let walked = 0;
  for (let i = 0; i < lengths.length; i++) {
    if (walked + lengths[i] >= target) {
      const f = lengths[i] === 0 ? 0 : (target - walked) / lengths[i];
      out.push([points[i][0] + (points[i + 1][0] - points[i][0]) * f, points[i][1] + (points[i + 1][1] - points[i][1]) * f]);
      return out;
    }
    walked += lengths[i];
    out.push(points[i + 1]);
  }
  return out;
}

export const head = (points: [number, number][], fraction: number): [number, number] => {
  const p = partial(points, fraction);
  return p[p.length - 1];
};
