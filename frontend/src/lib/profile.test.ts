import { describe, expect, it } from "vitest";
import { Lap, lapsToShow, paceFromSpeed, paceLabel, smooth, speeds, ticks } from "./profile";

const lap = (distance: number | null, extra: Partial<Lap> = {}): Lap => ({ start_s: 0, duration_s: 300, distance_m: distance, avg_hr: null, pace_s_per_km: null, intensity: null, ...extra });

describe("speeds", () => {
  it("uses the recorded speed, and otherwise works it out from distance and time", () => {
    expect(speeds({ t: [0, 10, 20], d: [0, 25, 60], v: [2, null, 3.5] })).toEqual([2, 2.5, 3.5]);
    expect(speeds({ t: [0, 10, 20], d: [0, 25, 60] })).toEqual([null, 2.5, 3.5]);
  });
  it("is null for a repeated timestamp instead of dividing by zero", () => {
    expect(speeds({ t: [0, 0], d: [0, 5] })).toEqual([null, null]);
  });
});

describe("smooth", () => {
  it("averages neighbours, keeps gaps as gaps, and ignores them in the average", () => {
    expect(smooth([1, 2, 3, 4, 5], 3)).toEqual([1.5, 2, 3, 4, 4.5]);
    expect(smooth([2, null, 4], 3)).toEqual([2, null, 4]); // a gap is not bridged by a narrow window
    expect(smooth([2, null, 4], 5)).toEqual([3, null, 3]); // but a wider window averages what is there, skipping the gap
    expect(smooth([], 3)).toEqual([]);
  });
});

describe("pace", () => {
  it("is seconds per km, and a gap when standing still", () => {
    expect(paceFromSpeed(3.125)).toBe(320);
    expect(paceFromSpeed(0.2)).toBeNull();
    expect(paceFromSpeed(null)).toBeNull();
    expect(paceLabel(332)).toBe("5:32");
  });
});

describe("lapsToShow", () => {
  it("hides automatic kilometre laps and single laps, and shows interval steps", () => {
    expect(lapsToShow([lap(1000), lap(1003), lap(1000), lap(420)])).toEqual([]);
    expect(lapsToShow([lap(5000)])).toEqual([]);
    const steps = [lap(800), lap(400), lap(90), lap(400)];
    expect(lapsToShow(steps)).toEqual(steps);
    expect(lapsToShow([])).toEqual([]);
  });
});

describe("ticks", () => {
  it("picks round values inside the range", () => {
    expect(ticks(0, 10, 5)).toEqual([0, 2, 4, 6, 8, 10]);
    expect(ticks(118, 162, 4)).toEqual([120, 140, 160]);
  });
  it("copes with a flat range", () => {
    expect(ticks(5, 5)).toEqual([5]);
  });
});
