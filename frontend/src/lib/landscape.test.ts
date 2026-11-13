import { describe, expect, it } from "vitest";
import { LandscapeRun, landscapeHeight, ridges, shortName, speedCap } from "./landscape";

const run = (id: number, date: string, speeds: number[], extra: Partial<LandscapeRun> = {}): LandscapeRun => ({
  id, date, name: "Run", distance_km: 5, duration_min: 30, avg_hr: 130,
  profile: { t: speeds.map((_, i) => i * 10), d: speeds.map((_, i) => i * 20), v: speeds }, ...extra,
});

describe("speedCap", () => {
  it("is one shared scale, never below a sensible minimum, and survives no data", () => {
    expect(speedCap([run(1, "2026-01-01", [2.8, 2.8, 2.8])])).toBe(3.5);
    expect(speedCap([run(1, "2026-01-01", [2.8, 4.5, 4.5, 2.8])])).toBeCloseTo(3.93, 1); // smoothed, so a little under the raw peak
    expect(speedCap([run(1, "2026-01-01", [2, 6, 6, 6, 6, 6, 6, 2])])).toBeCloseTo(6, 0);
    expect(speedCap([])).toBe(4);
  });
});

describe("shortName", () => {
  it("shortens long names and has a fallback", () => {
    expect(shortName("W9 Thu Taper Intervals - Taper 4", 20)).toBe("W9 Thu Taper Interv…");
    expect(shortName("Taper 400s")).toBe("Taper 400s");
    expect(shortName(null)).toBe("Løb");
    expect(shortName("   ")).toBe("Løb");
  });
});

describe("ridges", () => {
  const runs = [run(2, "2026-06-01", [2.8, 4.2, 1.4, 4.2, 2.8]), run(1, "2026-05-01", [2.8, 2.8, 2.8, 2.8, 2.8])];
  it("puts the oldest on top and stacks the rows downwards", () => {
    const out = ridges(runs, 400, 40, 60, 0);
    expect(out.map((r) => r.id)).toEqual([1, 2]);
    expect(out[1].base - out[0].base).toBeCloseTo(40, 6);
  });
  it("lets an interval session rise and fall while an even run stays flat", () => {
    const [even, interval] = ridges(runs, 400, 40, 60, 0);
    const ys = (line: string) => line.match(/ (-?\d+\.\d)/g)!.map((m) => Number(m.trim()));
    expect(new Set(ys(even.line)).size).toBe(1);
    expect(new Set(ys(interval.line)).size).toBeGreaterThan(2);
    expect(interval.peakSpeed).toBeGreaterThan(even.peakSpeed);
  });
  it("shares one time axis, so a shorter run ends before the right edge", () => {
    const short = run(3, "2026-07-01", [2.8, 2.8]);
    const out = ridges([...runs, short], 400, 40, 0, 0);
    const lastX = (line: string) => Number(line.split("L").pop()!.trim().split(" ")[0]);
    expect(lastX(out[2].line)).toBeLessThan(lastX(out[0].line));
    expect(lastX(out[0].line)).toBeCloseTo(400, 0);
  });
  it("closes the outline for the fill and keeps every point inside the box", () => {
    const [r] = ridges([runs[0]], 400, 40, 60, 0);
    expect(r.fill.startsWith("M60.0")).toBe(true);
    expect(r.fill.endsWith("Z")).toBe(true);
  });
  it("gives pace per kilometre and copes with a run without a profile", () => {
    expect(ridges([runs[0]], 400, 40)[0].paceSec).toBe(360);
    const broken = run(9, "2026-08-01", [], { duration_min: 0 });
    const [b] = ridges([broken], 400, 40);
    expect(b.fill).toBe("");
    expect(b.paceSec).toBeNull();
  });
  it("leaves room above the first row for its tallest peak, so nothing is cut off", () => {
    const fast = run(1, "2026-05-01", [6, 6, 6, 6]); // well above the shared scale: peaks at 1.15 x the amplitude
    const [r] = ridges([fast], 400, 40, 0, 0);
    const ys = r.line.match(/ (-?\d+\.\d)/g)!.map((m) => Number(m.trim()));
    expect(Math.min(...ys)).toBeGreaterThanOrEqual(0);
    expect(landscapeHeight(1, 40, 0)).toBeGreaterThan(r.base);
  });
  it("reports the height the rows need", () => {
    expect(landscapeHeight(1, 40)).toBeGreaterThan(40);
    expect(landscapeHeight(10, 40)).toBeGreaterThan(landscapeHeight(5, 40));
  });
});
