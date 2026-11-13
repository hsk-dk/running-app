/** A contact sheet: every route in its own tile, drawn as large as the tile allows. Pure and testable. */
import { PosterRoute } from "./poster";
import { decodePolyline, projectRoute } from "./route";

export type Tile = {
  id: number;
  date: string | null;
  km: number;
  name: string | null;
  /** seconds per kilometre, when the duration is known */
  pace: number | null;
  d: string;
  start: [number, number];
  end: [number, number];
};

const MAX_POINTS = 160;

function thin<T>(items: T[]): T[] {
  if (items.length <= MAX_POINTS) return items;
  const step = (items.length - 1) / (MAX_POINTS - 1);
  return Array.from({ length: MAX_POINTS }, (_, i) => items[Math.round(i * step)]);
}

/** Newest first. Routes that cannot be drawn (fewer than two points) are left out. */
export function contactSheet(routes: PosterRoute[], width: number, height: number, pad = 14): Tile[] {
  const tiles: Tile[] = [];
  for (const r of routes) {
    const pts = projectRoute(thin(decodePolyline(r.route)), width, height, pad);
    if (pts.length < 2) continue;
    tiles.push({
      id: r.id,
      date: r.date,
      km: r.distance_km,
      name: r.name ?? null,
      pace: r.duration_min && r.distance_km > 0 ? (r.duration_min * 60) / r.distance_km : null,
      d: pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" "),
      start: pts[0],
      end: pts[pts.length - 1],
    });
  }
  return tiles.sort((a, b) => ((a.date ?? "") < (b.date ?? "") ? 1 : -1));
}

/** How many tiles fit in a row: at least two, and none narrower than `minTile`. */
export function columnsFor(width: number, minTile = 150, gap = 12): number {
  return Math.max(2, Math.floor((width + gap) / (minTile + gap)));
}
