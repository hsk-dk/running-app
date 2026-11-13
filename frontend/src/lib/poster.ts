/** Lays many routes over each other on one map, so the places a person runs most show up. Pure and testable. */
import { LatLng, decodePolyline } from "./route";

export type PosterRoute = { id: number; date: string | null; distance_km: number; route: string; name?: string | null; duration_min?: number };
export type Poster = {
  paths: string[];
  used: number;
  /** Routes too far from where the person usually runs (a holiday run would shrink everything else). */
  outside: number;
  totalKm: number;
};

const MAX_POINTS = 220;
const NEAR_KM = 30;

const median = (values: number[]) => {
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const percentile = (sorted: number[], p: number) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(p * (sorted.length - 1))))];

function kmBetween(a: LatLng, b: LatLng): number {
  const kx = Math.cos((((a[0] + b[0]) / 2) * Math.PI) / 180);
  return Math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * kx);
}

function thin(points: LatLng[]): LatLng[] {
  if (points.length <= MAX_POINTS) return points;
  const step = points.length / MAX_POINTS;
  const out: LatLng[] = [];
  for (let i = 0; i < MAX_POINTS; i++) out.push(points[Math.floor(i * step)]);
  out.push(points[points.length - 1]);
  return out;
}

export type PlacedRoute = { route: PosterRoute; points: [number, number][] };
export type PosterLayout = { placed: PlacedRoute[]; outside: number; totalKm: number };

/** The routes projected onto one shared frame (x, y in pixels). `buildPoster` and the playback both start from this. */
export function layoutPoster(routes: PosterRoute[], width: number, height: number, pad = 24): PosterLayout {
  const decoded = routes
    .map((r) => ({ r, pts: thin(decodePolyline(r.route)) }))
    .filter((x) => x.pts.length >= 2);
  if (decoded.length === 0) return { placed: [], outside: 0, totalKm: 0 };

  const centroids = decoded.map(({ pts }) => [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length] as LatLng);
  const home: LatLng = [median(centroids.map((c) => c[0])), median(centroids.map((c) => c[1]))];
  const kept = decoded.filter((_, i) => kmBetween(centroids[i], home) <= NEAR_KM);

  // The frame follows where most points are, so a few long runs do not shrink the picture.
  const lats = kept.flatMap(({ pts }) => pts.map((p) => p[0])).sort((a, b) => a - b);
  const lngs = kept.flatMap(({ pts }) => pts.map((p) => p[1])).sort((a, b) => a - b);
  const [loLat, hiLat] = [percentile(lats, 0.01), percentile(lats, 0.99)];
  const [loLng, hiLng] = [percentile(lngs, 0.01), percentile(lngs, 0.99)];
  const kx = Math.cos(((loLat + hiLat) / 2 * Math.PI) / 180);
  const spanX = Math.max((hiLng - loLng) * kx, 1e-6);
  const spanY = Math.max(hiLat - loLat, 1e-6);
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
  const offX = (width - spanX * scale) / 2;
  const offY = (height - spanY * scale) / 2;

  const placed = kept.map(({ r, pts }) => ({
    route: r,
    points: pts.map((p): [number, number] => [offX + (p[1] - loLng) * kx * scale, offY + (hiLat - p[0]) * scale]),
  }));
  return {
    placed,
    outside: decoded.length - kept.length,
    totalKm: Math.round(kept.reduce((sum, { r }) => sum + r.distance_km, 0) * 10) / 10,
  };
}

export function buildPoster(routes: PosterRoute[], width: number, height: number, pad = 24): Poster {
  const layout = layoutPoster(routes, width, height, pad);
  return {
    paths: layout.placed.map(({ points }) => points.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ")),
    used: layout.placed.length,
    outside: layout.outside,
    totalKm: layout.totalKm,
  };
}
