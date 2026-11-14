import { describe, expect, it } from "vitest";
import { areaName, clusterRoutes, placePrefix } from "./areas";
import { PosterRoute } from "./poster";

function enc(points: [number, number][]): string {
  let out = "", pLat = 0, pLng = 0;
  const e = (n: number) => { n = n < 0 ? ~(n << 1) : n << 1; let s = ""; while (n >= 0x20) { s += String.fromCharCode((0x20 | (n & 0x1f)) + 63); n >>= 5; } return s + String.fromCharCode(n + 63); };
  for (const [lat, lng] of points) { const la = Math.round(lat * 1e5), lo = Math.round(lng * 1e5); out += e(la - pLat) + e(lo - pLng); pLat = la; pLng = lo; }
  return out;
}
const route = (id: number, lat: number, lng: number, name: string | null, date = "2026-05-01"): PosterRoute => ({
  id, date, name, distance_km: 5, route: enc([[lat, lng], [lat + 0.005, lng + 0.005], [lat + 0.002, lng + 0.009]]),
});

describe("placePrefix", () => {
  it("recognises Garmin default names", () => {
    expect(placePrefix("Horsens Løb")).toBe("Horsens");
    expect(placePrefix("Aarhus Løbetur")).toBe("Aarhus");
    expect(placePrefix("Ny Vejle Gang")).toBe("Ny Vejle");
    expect(placePrefix("Morgen Løb")).toBeNull(); // a time of day is not a place
    expect(placePrefix("Løb")).toBeNull();
    expect(placePrefix("Horsens Løb langt")).toBeNull();
  });
  it("takes the place before ' - ' and ignores plan codes and dates", () => {
    expect(placePrefix("Horsens - W7 Sun Easy Run")).toBe("Horsens");
    expect(placePrefix("Brønderslev - S3.5 - 5(700m-30s)")).toBe("Brønderslev");
    expect(placePrefix("Vejle - W6 Mon Hills - Hill Repeats (4km")).toBe("Vejle");
    expect(placePrefix("W9 Thu Taper Intervals - Taper 4")).toBeNull();
    expect(placePrefix("S5 - 16(250m-60s)")).toBeNull();
    expect(placePrefix("Morgentur")).toBeNull();
    expect(placePrefix(null)).toBeNull();
  });
});

describe("areaName", () => {
  it("needs most of the runs to agree", () => {
    expect(areaName([route(1, 55, 9, "Horsens - a"), route(2, 55, 9, "Horsens - b"), route(3, 55, 9, "Vejle - c")])).toBe("Horsens");
    expect(areaName([route(1, 55, 9, "Horsens - a"), route(2, 55, 9, "Vejle - b"), route(3, 55, 9, null)])).toBeNull();
  });
});

describe("clusterRoutes", () => {
  it("puts nearby routes together and far ones apart, biggest area first, named from the runs", () => {
    const horsens = [1, 2, 3].map((i) => route(i, 55.86 + i * 0.002, 9.85, "Horsens - W1"));
    const vejle = [4, 5].map((i) => route(i, 55.71 + i * 0.001, 9.53, "Vejle - W2"));
    const areas = clusterRoutes([...vejle, ...horsens]);
    expect(areas.map((a) => [a.name, a.routes.length])).toEqual([["Horsens", 3], ["Vejle", 2]]);
  });
  it("numbers an area that has no agreed name, and tells two clusters of one town apart", () => {
    const a = clusterRoutes([route(1, 55.0, 9.0, null), route(2, 56.0, 10.0, null)]);
    expect(a.map((x) => x.name)).toEqual(["Område 1", "Område 2"]);
    const twin = clusterRoutes([route(1, 55.0, 9.0, "Horsens - a"), route(2, 55.5, 9.0, "Horsens - b")]);
    expect(twin.map((x) => x.name).sort()).toEqual(["Horsens", "Horsens 2"]);
  });
  it("skips routes that cannot be placed and copes with none", () => {
    expect(clusterRoutes([{ id: 1, date: null, distance_km: 1, route: "" }])).toEqual([]);
    expect(clusterRoutes([])).toEqual([]);
  });
});
