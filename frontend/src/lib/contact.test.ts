import { describe, expect, it } from "vitest";
import { columnsFor, contactSheet } from "./contact";
import { PosterRoute } from "./poster";

function enc(points: [number, number][]): string {
  let out = "", pLat = 0, pLng = 0;
  const e = (n: number) => { n = n < 0 ? ~(n << 1) : n << 1; let s = ""; while (n >= 0x20) { s += String.fromCharCode((0x20 | (n & 0x1f)) + 63); n >>= 5; } return s + String.fromCharCode(n + 63); };
  for (const [lat, lng] of points) { const la = Math.round(lat * 1e5), lo = Math.round(lng * 1e5); out += e(la - pLat) + e(lo - pLng); pLat = la; pLng = lo; }
  return out;
}
const loop = (lat: number, lng: number, r: number) => Array.from({ length: 30 }, (_, i) => [lat + r * Math.sin((i / 30) * 6.283), lng + r * Math.cos((i / 30) * 6.283)] as [number, number]);
const route = (id: number, date: string, r: number, extra: Partial<PosterRoute> = {}): PosterRoute => ({ id, date, distance_km: 5, duration_min: 30, route: enc(loop(55.7, 9.5, r)), ...extra });

describe("contactSheet", () => {
  it("draws each route as large as its own tile allows, whatever its real size", () => {
    const tiles = contactSheet([route(1, "2026-05-01", 0.001), route(2, "2026-05-02", 0.02)], 160, 120, 14);
    for (const t of tiles) {
      const nums = t.d.match(/-?\d+\.\d/g)!.map(Number);
      expect(Math.min(...nums)).toBeGreaterThanOrEqual(13);
      expect(Math.max(...nums)).toBeLessThanOrEqual(147);
    }
    const spans = tiles.map((t) => { const xs = t.d.match(/[ML](-?\d+\.\d) /g)!.map((m) => Number(m.slice(1))); return Math.max(...xs) - Math.min(...xs); });
    expect(Math.abs(spans[0] - spans[1])).toBeLessThan(2); // a tiny loop and a big one fill their tiles alike
  });
  it("puts the newest first and gives pace and the run's own name", () => {
    const tiles = contactSheet([route(1, "2026-05-01", 0.01, { name: "A" }), route(2, "2026-06-01", 0.01, { name: "B", duration_min: 25, distance_km: 5 })], 160, 120);
    expect(tiles.map((t) => t.id)).toEqual([2, 1]);
    expect(tiles[0].pace).toBe(300);
    expect(tiles[0].name).toBe("B");
  });
  it("leaves out routes it cannot draw and has no pace without a duration", () => {
    const tiles = contactSheet([{ id: 9, date: null, distance_km: 1, route: "" }, route(3, "2026-05-01", 0.01, { duration_min: 0 })], 160, 120);
    expect(tiles).toHaveLength(1);
    expect(tiles[0].pace).toBeNull();
  });
});

describe("columnsFor", () => {
  it("fits as many tiles as the width allows, at least two", () => {
    expect(columnsFor(900)).toBe(5);
    expect(columnsFor(330)).toBe(2);
    expect(columnsFor(100)).toBe(2);
  });
});
