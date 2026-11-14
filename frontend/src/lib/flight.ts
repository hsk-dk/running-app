/**
 * The flight over your running places: a stylised map where the camera zooms out, flies to the next place and
 * zooms in, with a curved dotted line left behind. Everything here is pure (no canvas, no network): the maths of
 * the camera and the timeline, so it can be tested.
 *
 * Coordinates are "Mercator degrees": x is longitude, y grows southwards (screen direction), so one unit is the
 * same distance in both directions at any latitude.
 */
import { Area } from "./areas";
import { PosterRoute } from "./poster";
import { decodePolyline } from "./route";

export type Point = [number, number];
/** A camera: where it looks (x, y) and how many world units fit across the screen (w). */
export type Camera = { x: number; y: number; w: number };

const RAD = Math.PI / 180;

export function mercator(lon: number, lat: number): Point {
  const clamped = Math.max(-85, Math.min(85, lat));
  return [lon, -(Math.log(Math.tan(Math.PI / 4 + (clamped * RAD) / 2)) / RAD)];
}

export function unmercator(x: number, y: number): { lon: number; lat: number } {
  return { lon: x, lat: (2 * Math.atan(Math.exp(-y * RAD)) - Math.PI / 2) / RAD };
}

// ---- cameras ----------------------------------------------------------------------------------------------

export type Box = { minX: number; minY: number; maxX: number; maxY: number };

export function boxOf(points: Point[]): Box {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const [x, y] of points) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  return { minX, minY, maxX, maxY };
}

/** The camera that shows `box` with `margin` (1.3 = 30 % extra) in a view of the given aspect ratio (width / height). */
export function fitBox(box: Box, aspect: number, margin = 1.35, minWidth = 0.05): Camera {
  const bw = Math.max(box.maxX - box.minX, 1e-9);
  const bh = Math.max(box.maxY - box.minY, 1e-9);
  const w = Math.max(Math.max(bw, bh * aspect) * margin, minWidth);
  return { x: (box.minX + box.maxX) / 2, y: (box.minY + box.maxY) / 2, w };
}

// ---- smooth zoom and pan (van Wijk & Nuij, 2003 - the same curve d3.interpolateZoom uses) ------------------------

export type FlightPath = { at: (t: number) => Camera; length: number };

const RHO = 1.45;

export function flyPath(a: Camera, b: Camera, rho = RHO): FlightPath {
  const rho2 = rho * rho;
  const rho4 = rho2 * rho2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const d2 = dx * dx + dy * dy;
  if (d2 < 1e-12) {
    const S = Math.log(b.w / a.w) / rho;
    return { length: Math.abs(S), at: (t) => ({ x: a.x + t * dx, y: a.y + t * dy, w: a.w * Math.exp(rho * t * S) }) };
  }
  const d1 = Math.sqrt(d2);
  const b0 = (b.w * b.w - a.w * a.w + rho4 * d2) / (2 * a.w * rho2 * d1);
  const b1 = (b.w * b.w - a.w * a.w - rho4 * d2) / (2 * b.w * rho2 * d1);
  const r0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0);
  const r1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1);
  const S = (r1 - r0) / rho;
  const cosh = (v: number) => (Math.exp(v) + Math.exp(-v)) / 2;
  const sinh = (v: number) => (Math.exp(v) - Math.exp(-v)) / 2;
  const tanh = (v: number) => sinh(v) / cosh(v);
  return {
    length: Math.abs(S),
    at: (t) => {
      const s = t * S;
      const u = (a.w / (rho2 * d1)) * (cosh(r0) * tanh(rho * s + r0) - sinh(r0));
      return { x: a.x + u * dx, y: a.y + u * dy, w: (a.w * cosh(r0)) / cosh(rho * s + r0) };
    },
  };
}

// ---- the places ---------------------------------------------------------------------------------------------

export type FlightRoute = { id: number; date: string | null; km: number; points: Point[] };
export type FlightArea = {
  key: string;
  name: string;
  center: Point;
  camera: Camera;
  routes: FlightRoute[];
  km: number;
  firstDate: string | null;
  /** The longest run here, for the caption. */
  longest: { km: number; date: string | null };
};

const MAX_POINTS = 200;
const thin = <T,>(items: T[], limit = MAX_POINTS): T[] => {
  if (items.length <= limit) return items;
  const step = (items.length - 1) / (limit - 1);
  return Array.from({ length: limit }, (_, i) => items[Math.round(i * step)]);
};

export type Town = { name: string; lat: number; lon: number };

const kmBetween = (aLat: number, aLon: number, bLat: number, bLon: number) => {
  const kx = Math.cos((((aLat + bLat) / 2) * Math.PI) / 180);
  return Math.hypot((aLat - bLat) * 111.2, (aLon - bLon) * 111.2 * kx);
};

/** The nearest town in a short list, with how far away it is, or null when none is within `maxKm`. */
export function nearestTown(towns: Town[], lat: number, lon: number, maxKm = 30): { name: string; km: number } | null {
  let best: { name: string; km: number } | null = null;
  for (const t of towns) {
    const km = kmBetween(lat, lon, t.lat, t.lon);
    if (km <= maxKm && (!best || km < best.km)) best = { name: t.name, km };
  }
  return best;
}

/**
 * A quiet place name: the name the runs share if they have one, otherwise "near" the closest known town, otherwise the
 * generic name. Never a street or an exact position.
 */
export function placeLabel(areaName: string, isGeneric: boolean, lat: number, lon: number, towns: Town[]): string {
  if (!isGeneric) return areaName;
  const town = nearestTown(towns, lat, lon, 30);
  if (!town) return areaName;
  return town.km <= 6 ? town.name : `nær ${town.name}`;
}

/** Oldest place first: the flight tells the story in the order you started running in each place. */
export function flightAreas(areas: Area[], aspect: number, towns: Town[] = []): FlightArea[] {
  const out: FlightArea[] = [];
  for (const area of areas) {
    const routes: FlightRoute[] = [];
    for (const r of area.routes) {
      const pts = decodePolyline(r.route);
      if (pts.length < 2) continue;
      routes.push({ id: r.id, date: r.date, km: r.distance_km, points: thin(pts).map(([lat, lon]) => mercator(lon, lat)) });
    }
    if (routes.length === 0) continue;
    routes.sort((a, b) => ((a.date ?? "") < (b.date ?? "") ? -1 : 1));
    const box = boxOf(routes.flatMap((r) => r.points));
    const center: Point = [(box.minX + box.maxX) / 2, (box.minY + box.maxY) / 2];
    const { lat, lon } = unmercator(center[0], center[1]);
    const generic = /^Område \d+$/.test(area.name);
    out.push({
      key: area.key,
      name: placeLabel(area.name, generic, lat, lon, towns),
      center,
      camera: fitBox(box, aspect, 1.45, 0.045),
      routes,
      km: routes.reduce((s, r) => s + r.km, 0),
      firstDate: routes[0].date,
      longest: routes.reduce((best, r) => (r.km > best.km ? { km: r.km, date: r.date } : best), { km: 0, date: null as string | null }),
    });
  }
  return out.sort((a, b) => ((a.firstDate ?? "") < (b.firstDate ?? "") ? -1 : 1));
}

/** The camera that shows every place at once (at least a few degrees wide, so one place still looks like a map). */
export function overviewCamera(areas: FlightArea[], aspect: number): Camera {
  const box = boxOf(areas.map((a) => a.center));
  const cam = fitBox(box, aspect, 1.6, 3);
  return cam;
}

// ---- the curved line between two places ----------------------------------------------------------------------------

/** A point on a gently curved arc from a to b: the middle bulges sideways by `bulge` of the distance. */
export function arcPoint(a: Point, b: Point, t: number, bulge = 0.18): Point {
  const mx = (a[0] + b[0]) / 2;
  const my = (a[1] + b[1]) / 2;
  const nx = -(b[1] - a[1]) * bulge;
  const ny = (b[0] - a[0]) * bulge;
  const cx = mx + nx;
  const cy = my + ny;
  const u = 1 - t;
  return [u * u * a[0] + 2 * u * t * cx + t * t * b[0], u * u * a[1] + 2 * u * t * cy + t * t * b[1]];
}

export function arcPoints(a: Point, b: Point, upTo = 1, steps = 40): Point[] {
  const n = Math.max(1, Math.ceil(steps * upTo));
  return Array.from({ length: n + 1 }, (_, i) => arcPoint(a, b, (i / n) * upTo));
}

// ---- the timeline ---------------------------------------------------------------------------------------------------

export type Segment =
  | { kind: "fly"; from: Camera; to: Camera; path: FlightPath; startMs: number; endMs: number; fromArea: number | null; toArea: number | null }
  | { kind: "dwell"; camera: Camera; startMs: number; endMs: number; area: number }
  | { kind: "hold"; camera: Camera; startMs: number; endMs: number }
  /** The runs with no GPS route: no place on the map, so the map steps back and a treadmill track takes over. */
  | { kind: "indoor"; camera: Camera; startMs: number; endMs: number };

export type Tour = { segments: Segment[]; totalMs: number; overview: Camera };

/** The runs that have no route. */
export type Indoor = { runs: number; km: number; min: number };

export type TourOptions = {
  indoor?: Indoor | null;
  /** 1 is the normal pace; 2 makes everything twice as fast (the year film). */
  speed?: number;
};

const FLY_MIN_MS = 1700;
const FLY_MAX_MS = 4600;
const FLY_PER_UNIT = 1150;
const DWELL_BASE_MS = 2200;
const DWELL_PER_ROUTE_MS = 260;
const DWELL_MAX_MS = 5600;
const HOLD_MS = 5000;
/** The opening: the whole picture, every place marked, before the camera sets off. */
const INTRO_MS = 2400;

export function flightMs(path: FlightPath): number {
  return Math.min(FLY_MAX_MS, Math.max(FLY_MIN_MS, path.length * FLY_PER_UNIT));
}

export const INDOOR_BASE_MS = 3200;
export const INDOOR_PER_RUN_MS = 45;
export const INDOOR_MAX_MS = 7000;
export const indoorMs = (i: Indoor): number => Math.min(INDOOR_MAX_MS, INDOOR_BASE_MS + i.runs * INDOOR_PER_RUN_MS);

export const dwellMs = (area: FlightArea): number => Math.min(DWELL_MAX_MS, DWELL_BASE_MS + area.routes.length * DWELL_PER_ROUTE_MS);

/** Overview -> place 1 -> place 2 -> ... -> overview -> (the treadmill) -> the whole picture. */
export function buildTour(areas: FlightArea[], aspect: number, options: TourOptions = {}): Tour {
  const speed = options.speed && options.speed > 0 ? options.speed : 1;
  const indoor = options.indoor && options.indoor.runs > 0 ? options.indoor : null;
  const overview = overviewCamera(areas, aspect);
  const segments: Segment[] = [];
  let t = 0;
  let at: Camera = overview;
  let fromArea: number | null = null;
  if (areas.length > 0) {
    segments.push({ kind: "hold", camera: overview, startMs: 0, endMs: INTRO_MS / speed });
    t = INTRO_MS / speed;
  }
  areas.forEach((area, i) => {
    const path = flyPath(at, area.camera);
    const fly = flightMs(path) / speed;
    segments.push({ kind: "fly", from: at, to: area.camera, path, startMs: t, endMs: t + fly, fromArea, toArea: i });
    t += fly;
    const stay = dwellMs(area) / speed;
    segments.push({ kind: "dwell", camera: area.camera, startMs: t, endMs: t + stay, area: i });
    t += stay;
    at = area.camera;
    fromArea = i;
  });
  const back = flyPath(at, overview);
  const backMs = flightMs(back) / speed;
  segments.push({ kind: "fly", from: at, to: overview, path: back, startMs: t, endMs: t + backMs, fromArea, toArea: null });
  t += backMs;
  if (indoor) {
    const len = indoorMs(indoor) / speed;
    segments.push({ kind: "indoor", camera: overview, startMs: t, endMs: t + len });
    t += len;
  }
  segments.push({ kind: "hold", camera: overview, startMs: t, endMs: t + HOLD_MS / speed });
  t += HOLD_MS / speed;
  return { segments, totalMs: t, overview };
}

export const smooth = (t: number) => t * t * (3 - 2 * t);

export type State = {
  camera: Camera;
  segment: Segment;
  /** 0..1 through the current segment */
  progress: number;
  /** the place the camera is at, or flying away from; null during the first flight in */
  area: number | null;
  /** how many places have been reached, so that many pins and routes are shown (Infinity after the last flight) */
  reached: number;
  /** lines between places: whole ones plus the fraction of the one being drawn (1.5 = one line and half of the next) */
  linesDrawn: number;
};

export function stateAt(tour: Tour, ms: number): State {
  const t = Math.max(0, Math.min(tour.totalMs, ms));
  const seg = tour.segments.find((s) => t < s.endMs) ?? tour.segments[tour.segments.length - 1];
  const progress = seg.endMs === seg.startMs ? 1 : Math.min(1, (t - seg.startMs) / (seg.endMs - seg.startMs));
  if (seg.kind === "fly") {
    const camera = seg.path.at(smooth(progress));
    if (seg.toArea === null) return { camera, segment: seg, progress, area: seg.fromArea, reached: Infinity, linesDrawn: Infinity };
    // flying in: the places before the destination are reached, and the line towards it is drawn on the way
    const lines = seg.fromArea === null ? 0 : seg.fromArea + smooth(progress);
    return { camera, segment: seg, progress, area: seg.fromArea, reached: seg.toArea, linesDrawn: lines };
  }
  if (seg.kind === "dwell") {
    return { camera: seg.camera, segment: seg, progress, area: seg.area, reached: seg.area + 1, linesDrawn: seg.area };
  }
  return { camera: seg.camera, segment: seg, progress, area: null, reached: Infinity, linesDrawn: Infinity }; // hold and indoor
}

/** The start of the flight that ends at place `i`, so a jump to it still arrives by flying. */
export function startOfArrival(tour: Tour, i: number): number {
  const seg = tour.segments.find((s) => s.kind === "fly" && s.toArea === i);
  return seg ? seg.startMs : 0;
}

export function startOfIndoor(tour: Tour): number | null {
  const seg = tour.segments.find((s) => s.kind === "indoor");
  return seg ? seg.startMs : null;
}

/** Where the "hold" at the end begins: the whole picture. */
export function startOfHold(tour: Tour): number {
  const seg = [...tour.segments].reverse().find((s) => s.kind === "hold");
  return seg ? seg.startMs : tour.totalMs;
}
