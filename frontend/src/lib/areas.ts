/** Groups routes by where they were run, so each place gets its own map. Pure and testable. */
import { PosterRoute } from "./poster";
import { LatLng, decodePolyline } from "./route";

export type Area = { key: string; name: string; routes: PosterRoute[]; center: LatLng };

const RADIUS_KM = 5;

function kmBetween(a: LatLng, b: LatLng): number {
  const kx = Math.cos((((a[0] + b[0]) / 2) * Math.PI) / 180);
  return Math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * kx);
}

function centroid(route: PosterRoute): LatLng | null {
  const pts = decodePolyline(route.route);
  if (pts.length < 2) return null;
  return [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length];
}

/** "Horsens - W7 Sun Easy Run" -> "Horsens". Only a plain place-like word counts, not "W7" or a date. */
export function placePrefix(name: string | null | undefined): string | null {
  const text = (name ?? "").trim();
  const word = "[A-Za-zÆØÅæøåÉéÜü]+";
  const dashed = new RegExp(`^(${word}(?: ${word})?)\\s+[-–]\\s+`).exec(text);
  // Garmin's own default names: "Horsens Løb", "Aarhus Løbetur", "Vejle Gang"
  const garmin = new RegExp(`^(${word}(?: ${word})?)\\s+(?:Løb|Løbetur|Gåtur|Gang|Cykling|Cykeltur|Trail|Trailløb|Intervaller)$`, "i").exec(text);
  const m = dashed ?? (garmin && !/^(Morgen|Formiddag|Middag|Eftermiddag|Aften|Nat)$/i.test(garmin[1]) ? garmin : null);
  return m && m[1].length >= 3 && !/^[WSK]\d/i.test(m[1]) ? m[1] : null;
}

/** The place most of the runs are named after, or null when the names do not agree. */
export function areaName(routes: PosterRoute[]): string | null {
  const counts = new Map<string, number>();
  for (const r of routes) {
    const p = placePrefix(r.name);
    if (p) counts.set(p, (counts.get(p) ?? 0) + 1);
  }
  const best = [...counts.entries()].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0];
  return best && best[1] * 2 >= routes.length ? best[0] : null;
}

/** Routes whose centres lie within a few kilometres of each other belong to the same area. Biggest area first. */
export function clusterRoutes(routes: PosterRoute[], radiusKm = RADIUS_KM): Area[] {
  const groups: { sum: LatLng; n: number; routes: PosterRoute[] }[] = [];
  const ordered = [...routes].sort((a, b) => ((a.date ?? "") < (b.date ?? "") ? -1 : 1));
  for (const route of ordered) {
    const c = centroid(route);
    if (!c) continue;
    let best: { g: (typeof groups)[number]; d: number } | null = null;
    for (const g of groups) {
      const d = kmBetween([g.sum[0] / g.n, g.sum[1] / g.n], c);
      if (d <= radiusKm && (!best || d < best.d)) best = { g, d };
    }
    if (best) {
      best.g.sum = [best.g.sum[0] + c[0], best.g.sum[1] + c[1]];
      best.g.n += 1;
      best.g.routes.push(route);
    } else {
      groups.push({ sum: c, n: 1, routes: [route] });
    }
  }
  const areas = groups
    .sort((a, b) => b.routes.length - a.routes.length)
    .map((g, i): Area => ({
      key: `area-${i}`,
      name: areaName(g.routes) ?? `Område ${i + 1}`,
      routes: g.routes,
      center: [g.sum[0] / g.n, g.sum[1] / g.n],
    }));
  // two areas that got the same name (two clusters in one town) are told apart by a number
  const seen = new Map<string, number>();
  return areas.map((a) => {
    const n = (seen.get(a.name) ?? 0) + 1;
    seen.set(a.name, n);
    return n > 1 ? { ...a, name: `${a.name} ${n}` } : a;
  });
}
