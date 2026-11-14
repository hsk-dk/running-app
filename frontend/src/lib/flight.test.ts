import { describe, expect, it } from "vitest";
import { Area } from "./areas";
import { arcPoint, arcPoints, boxOf, buildTour, dwellMs, fitBox, flightAreas, flyPath, mercator, nearestTown, placeLabel, stateAt, startOfArrival, startOfHold, startOfIndoor, indoorMs, unmercator } from "./flight";

function enc(points: [number, number][]): string {
  let out = "", pLat = 0, pLng = 0;
  const e = (n: number) => { n = n < 0 ? ~(n << 1) : n << 1; let s = ""; while (n >= 0x20) { s += String.fromCharCode((0x20 | (n & 0x1f)) + 63); n >>= 5; } return s + String.fromCharCode(n + 63); };
  for (const [lat, lng] of points) { const la = Math.round(lat * 1e5), lo = Math.round(lng * 1e5); out += e(la - pLat) + e(lo - pLng); pLat = la; pLng = lo; }
  return out;
}
const route = (id: number, lat: number, lng: number, date: string) => ({
  id, date, name: null, distance_km: 5, route: enc([[lat, lng], [lat + 0.01, lng + 0.01], [lat + 0.004, lng + 0.016]]),
});
const area = (key: string, name: string, routes: ReturnType<typeof route>[]): Area => ({ key, name, routes, center: [0, 0] });
const TOWNS = [{ name: "Vejle", lat: 55.711, lon: 9.536 }, { name: "Århus", lat: 56.157, lon: 10.211 }];

describe("mercator", () => {
  it("keeps longitude, puts the equator at 0 and north upwards (smaller y)", () => {
    expect(mercator(9.5, 0)[0]).toBe(9.5);
    expect(mercator(9.5, 0)[1]).toBeCloseTo(0, 9);
    expect(mercator(10, 60)[1]).toBeLessThan(mercator(10, 50)[1]);
    expect(mercator(10, 55.7)[1]).toBeCloseTo(-67.36, 1);
  });
  it("round-trips", () => {
    const [x, y] = mercator(12.57, 55.68);
    const back = unmercator(x, y);
    expect(back.lon).toBeCloseTo(12.57, 6);
    expect(back.lat).toBeCloseTo(55.68, 6);
  });
  it("does not blow up at the poles", () => {
    expect(Number.isFinite(mercator(0, 90)[1])).toBe(true);
  });
});

describe("fitBox", () => {
  it("is limited by width or by height, whichever is tighter, and never zoomed in absurdly far", () => {
    const wide = fitBox({ minX: 0, maxX: 10, minY: 0, maxY: 1 }, 2, 1);
    expect(wide.w).toBe(10);
    const tall = fitBox({ minX: 0, maxX: 1, minY: 0, maxY: 10 }, 2, 1);
    expect(tall.w).toBe(20);
    expect(fitBox({ minX: 5, maxX: 5, minY: 5, maxY: 5 }, 1.6, 1.4, 0.05).w).toBe(0.05);
    expect(fitBox({ minX: 0, maxX: 4, minY: 0, maxY: 2 }, 2, 1)).toMatchObject({ x: 2, y: 1 });
  });
});

describe("flyPath", () => {
  const a = { x: 0, y: 0, w: 0.05 };
  const b = { x: 3, y: 1, w: 0.05 };
  it("starts exactly at one camera and ends exactly at the other", () => {
    const f = flyPath(a, b);
    const s = f.at(0), e = f.at(1);
    expect(s.x).toBeCloseTo(0, 6); expect(s.w).toBeCloseTo(0.05, 6);
    expect(e.x).toBeCloseTo(3, 6); expect(e.y).toBeCloseTo(1, 6); expect(e.w).toBeCloseTo(0.05, 6);
  });
  it("zooms out on the way between two far-apart places and back in", () => {
    const f = flyPath(a, b);
    const mid = f.at(0.5);
    expect(mid.w).toBeGreaterThan(1); // much wider than the 0.05 it starts and ends at
    const ws = Array.from({ length: 21 }, (_, i) => f.at(i / 20).w);
    expect(Math.max(...ws)).toBe(ws[ws.indexOf(Math.max(...ws))]);
    expect(ws.indexOf(Math.max(...ws))).toBeGreaterThan(5);
    expect(ws.indexOf(Math.max(...ws))).toBeLessThan(15);
  });
  it("stays level for a short hop and is quicker than a long one", () => {
    const near = flyPath(a, { x: 0.02, y: 0, w: 0.05 });
    expect(near.at(0.5).w).toBeLessThan(0.5);
    expect(near.length).toBeLessThan(flyPath(a, b).length);
  });
  it("handles a pure zoom (same place)", () => {
    const f = flyPath({ x: 1, y: 1, w: 4 }, { x: 1, y: 1, w: 0.05 });
    expect(f.at(0).w).toBeCloseTo(4, 6);
    expect(f.at(1).w).toBeCloseTo(0.05, 6);
    expect(f.at(0.5).x).toBeCloseTo(1, 9);
  });
});

describe("nearestTown and placeLabel", () => {
  it("finds the closest town within range", () => {
    expect(nearestTown(TOWNS, 55.72, 9.53)?.name).toBe("Vejle");
    expect(nearestTown(TOWNS, 56.0, 10.0, 10)).toBeNull();
    expect(nearestTown([], 55, 9)).toBeNull();
  });
  it("uses the runs' own place name, else 'nær' a town if it is some way off, else the generic name", () => {
    expect(placeLabel("Horsens", false, 55.86, 9.85, TOWNS)).toBe("Horsens");
    expect(placeLabel("Område 2", true, 55.712, 9.54, TOWNS)).toBe("Vejle");
    expect(placeLabel("Område 2", true, 55.8, 9.7, TOWNS)).toBe("nær Vejle");
    expect(placeLabel("Område 3", true, 40.0, 9.0, TOWNS)).toBe("Område 3");
  });
});

describe("arcs", () => {
  it("run from one place to the other and bulge to one side", () => {
    const a: [number, number] = [0, 0], b: [number, number] = [10, 0];
    expect(arcPoint(a, b, 0)).toEqual(a);
    expect(arcPoint(a, b, 1)).toEqual(b);
    expect(Math.abs(arcPoint(a, b, 0.5)[1])).toBeGreaterThan(0.5);
  });
  it("can be drawn part of the way", () => {
    const pts = arcPoints([0, 0], [10, 0], 0.5);
    expect(pts[0]).toEqual([0, 0]);
    expect(pts[pts.length - 1][0]).toBeCloseTo(arcPoint([0, 0], [10, 0], 0.5)[0], 6);
  });
});

describe("the tour with treadmill runs and a faster pace", () => {
  const fa = flightAreas([area("a1", "Vejle", [route(1, 55.71, 9.53, "2026-08-01"), route(2, 55.712, 9.535, "2026-09-01")]), area("a0", "Horsens", [route(3, 55.86, 9.85, "2026-04-01")])], 1.6, TOWNS);
  const indoor = { runs: 30, km: 180, min: 1000 };

  it("adds a treadmill stop between flying back and the final picture, and nothing without treadmill runs", () => {
    const t = buildTour(fa, 1.6, { indoor });
    expect(t.segments.map((s) => s.kind)).toEqual(["hold", "fly", "dwell", "fly", "dwell", "fly", "indoor", "hold"]);
    expect(buildTour(fa, 1.6, { indoor: { runs: 0, km: 0, min: 0 } }).segments.map((s) => s.kind)).not.toContain("indoor");
    expect(buildTour(fa, 1.6, { indoor: null }).segments.map((s) => s.kind)).not.toContain("indoor");
  });
  it("keeps the map as it was during the treadmill stop and has no gaps", () => {
    const t = buildTour(fa, 1.6, { indoor });
    const seg = t.segments.find((s) => s.kind === "indoor")!;
    const st = stateAt(t, (seg.startMs + seg.endMs) / 2);
    expect(st.segment.kind).toBe("indoor");
    expect(st.camera.w).toBeCloseTo(t.overview.w, 3);
    expect(st.reached).toBe(Infinity);
    t.segments.forEach((s, i) => { if (i) expect(s.startMs).toBeCloseTo(t.segments[i - 1].endMs, 6); });
    expect(startOfIndoor(t)).toBe(seg.startMs);
    expect(startOfIndoor(buildTour(fa, 1.6))).toBeNull();
  });
  it("stays longer for more runs, up to a limit", () => {
    expect(indoorMs({ runs: 100, km: 1, min: 1 })).toBeGreaterThan(indoorMs({ runs: 5, km: 1, min: 1 }));
    expect(indoorMs({ runs: 100000, km: 1, min: 1 })).toBe(7000);
  });
  it("runs faster when asked, and treats a bad speed as normal", () => {
    const normal = buildTour(fa, 1.6, { indoor }).totalMs;
    expect(buildTour(fa, 1.6, { indoor, speed: 2 }).totalMs).toBeCloseTo(normal / 2, 3);
    expect(buildTour(fa, 1.6, { indoor, speed: 0 }).totalMs).toBe(normal);
    expect(buildTour(fa, 1.6, { indoor, speed: -3 }).totalMs).toBe(normal);
  });
  it("remembers the longest run at each place", () => {
    const vejle = fa.find((a) => a.name === "Vejle")!;
    expect(vejle.longest.km).toBeGreaterThan(0);
    expect(vejle.longest.date === "2026-08-01" || vejle.longest.date === "2026-09-01").toBe(true);
  });
});

describe("the tour", () => {
  const areas = [
    area("a1", "Vejle", [route(1, 55.71, 9.53, "2026-08-01"), route(2, 55.712, 9.535, "2026-09-01")]),
    area("a0", "Horsens", [route(3, 55.86, 9.85, "2026-04-01")]),
  ];
  const fa = flightAreas(areas, 1.6, TOWNS);
  const tour = buildTour(fa, 1.6);

  it("tells the story oldest place first", () => {
    expect(fa.map((a) => a.name)).toEqual(["Horsens", "Vejle"]);
    expect(fa[0].routes.length).toBe(1);
  });
  it("has no gaps: intro, fly, stay, fly, stay, fly back, hold", () => {
    expect(tour.segments.map((s) => s.kind)).toEqual(["hold", "fly", "dwell", "fly", "dwell", "fly", "hold"]);
    expect(tour.segments[0].startMs).toBe(0);
    tour.segments.forEach((s, i) => { if (i) expect(s.startMs).toBe(tour.segments[i - 1].endMs); });
    expect(tour.totalMs).toBe(tour.segments[tour.segments.length - 1].endMs);
  });
  it("opens on the whole picture with every place shown, before setting off", () => {
    const open = stateAt(tour, 100);
    expect(open.segment.kind).toBe("hold");
    expect(open.reached).toBe(Infinity);
    expect(open.camera.w).toBeCloseTo(tour.overview.w, 3);
    expect(stateAt(tour, tour.segments[0].endMs + 1).segment.kind).toBe("fly");
  });
  it("stays longer where there are more runs", () => {
    expect(dwellMs(fa[1])).toBeGreaterThan(dwellMs(fa[0]));
  });
  it("starts zoomed out, is zoomed in at a place, and finishes zoomed out showing everything", () => {
    expect(stateAt(tour, 0).camera.w).toBeCloseTo(tour.overview.w, 3);
    const dwell = tour.segments[2];
    const inPlace = stateAt(tour, (dwell.startMs + dwell.endMs) / 2);
    expect(inPlace.camera.w).toBeCloseTo(fa[0].camera.w, 6);
    expect(inPlace.area).toBe(0);
    const end = stateAt(tour, tour.totalMs);
    expect(end.camera.w).toBeCloseTo(tour.overview.w, 3);
    expect(end.reached).toBe(Infinity);
  });
  it("draws the line to the next place while flying and keeps the finished ones", () => {
    const fly = tour.segments[3];
    const mid = stateAt(tour, (fly.startMs + fly.endMs) / 2);
    expect(mid.reached).toBe(1);
    expect(mid.linesDrawn).toBeGreaterThan(0);
    expect(mid.linesDrawn).toBeLessThan(1);
    expect(stateAt(tour, fly.endMs - 1).linesDrawn).toBeGreaterThan(0.95);
    expect(stateAt(tour, tour.segments[4].startMs + 10).linesDrawn).toBe(1);
  });
  it("lets you jump to a place and still arrive by flying", () => {
    const t = startOfArrival(tour, 1);
    expect(stateAt(tour, t).segment.kind).toBe("fly");
    expect(startOfArrival(tour, 99)).toBe(0);
    expect(stateAt(tour, startOfHold(tour)).segment.kind).toBe("hold");
  });
  it("survives a single place, no places, and times outside the tour", () => {
    const one = buildTour([fa[0]], 1.6);
    expect(one.segments.map((s) => s.kind)).toEqual(["hold", "fly", "dwell", "fly", "hold"]);
    expect(flightAreas([], 1.6)).toEqual([]);
    expect(stateAt(tour, -50).camera.w).toBeCloseTo(tour.overview.w, 3);
    expect(stateAt(tour, 1e9).segment.kind).toBe("hold");
  });
  it("shows a generic area under the nearest town's name, quietly", () => {
    const generic = flightAreas([area("g", "Område 1", [route(7, 55.712, 9.54, "2026-05-01")])], 1.6, TOWNS);
    expect(generic[0].name).toBe("Vejle");
  });
  it("boxes points", () => {
    expect(boxOf([[1, 5], [3, 2]])).toEqual({ minX: 1, maxX: 3, minY: 2, maxY: 5 });
  });
});
