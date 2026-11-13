import { describe, expect, it } from "vitest";
import { buildPoster } from "./poster";

// Google's own example polyline (3 points in the US) and small hand-made loops near Copenhagen.
function encode(points: [number, number][]): string {
  let out = "", pLat = 0, pLng = 0;
  const enc = (n: number) => { n = n < 0 ? ~(n << 1) : n << 1; let s = ""; while (n >= 0x20) { s += String.fromCharCode((0x20 | (n & 0x1f)) + 63); n >>= 5; } return s + String.fromCharCode(n + 63); };
  for (const [lat, lng] of points) { const la = Math.round(lat * 1e5), lo = Math.round(lng * 1e5); out += enc(la - pLat) + enc(lo - pLng); pLat = la; pLng = lo; }
  return out;
}
const loop = (lat: number, lng: number, r = 0.01): [number, number][] =>
  Array.from({ length: 24 }, (_, i) => [lat + r * Math.sin((i / 24) * 6.283), lng + r * Math.cos((i / 24) * 6.283)] as [number, number]);
const route = (id: number, lat: number, lng: number, km = 5) => ({ id, date: "2026-01-01", distance_km: km, route: encode(loop(lat, lng)) });

describe("buildPoster", () => {
  it("draws every route on one shared frame, inside the picture", () => {
    const p = buildPoster([route(1, 55.676, 12.568), route(2, 55.68, 12.57), route(3, 55.67, 12.56)], 640, 480, 20);
    expect(p.used).toBe(3);
    expect(p.paths).toHaveLength(3);
    const nums = p.paths.join(" ").match(/-?\d+\.\d/g)!.map(Number);
    expect(Math.min(...nums)).toBeGreaterThanOrEqual(-1);
    expect(Math.max(...nums)).toBeLessThanOrEqual(641);
  });

  it("keeps the places apart: routes in different spots do not land on top of each other", () => {
    const p = buildPoster([route(1, 55.676, 12.568), route(2, 55.69, 12.6)], 640, 480);
    expect(p.paths[0]).not.toBe(p.paths[1]);
  });

  it("leaves out a run far from where the person usually runs, and says so", () => {
    const home = [1, 2, 3, 4, 5].map((i) => route(i, 55.676 + i * 0.001, 12.568));
    const p = buildPoster([...home, route(99, 48.85, 2.35, 12)], 640, 480); // Paris
    expect(p.used).toBe(5);
    expect(p.outside).toBe(1);
    expect(p.totalKm).toBe(25);
  });

  it("ignores empty or one-point routes", () => {
    const p = buildPoster([{ id: 1, date: null, distance_km: 1, route: "" }, { id: 2, date: null, distance_km: 1, route: encode([[55, 12]]) }, route(3, 55.7, 12.5)], 640, 480);
    expect(p.used).toBe(1);
  });

  it("copes with no routes at all", () => {
    expect(buildPoster([], 640, 480)).toEqual({ paths: [], used: 0, outside: 0, totalKm: 0 });
  });

  it("thins very long routes", () => {
    const dense = Array.from({ length: 5000 }, (_, i) => [55.7 + i * 1e-5, 12.5 + Math.sin(i / 50) * 1e-3] as [number, number]);
    const p = buildPoster([{ id: 1, date: null, distance_km: 10, route: encode(dense) }], 640, 480);
    expect(p.paths[0].split("L").length).toBeLessThan(300);
  });
});
