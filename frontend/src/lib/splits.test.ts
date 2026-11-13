import { describe, expect, it } from "vitest";
import { Split, barWidths, extremes, paceLabel } from "./splits";

const mk = (km: number, pace: number, partial = false): Split => ({
  km, distance_m: partial ? 400 : 1000, time_s: pace, pace_s_per_km: pace, elevation_m: 0, partial,
});

describe("paceLabel", () => {
  it("formats minutes and padded seconds", () => {
    expect(paceLabel(332)).toBe("5:32");
    expect(paceLabel(300)).toBe("5:00");
    expect(paceLabel(359.6)).toBe("6:00");
  });
});

describe("extremes", () => {
  it("finds fastest and slowest full kilometre and ignores the leftover", () => {
    expect(extremes([mk(1, 330), mk(2, 300), mk(3, 345), mk(4, 200, true)])).toEqual({ fastest: 1, slowest: 2 });
  });
  it("is null with fewer than two full km or all equal", () => {
    expect(extremes([mk(1, 300)])).toBeNull();
    expect(extremes([mk(1, 300), mk(2, 300)])).toBeNull();
    expect(extremes([mk(1, 300), mk(2, 280, true)])).toBeNull();
  });
});

describe("barWidths", () => {
  it("makes the fastest 100 and the slowest 40", () => {
    expect(barWidths([mk(1, 300), mk(2, 360), mk(3, 330)])).toEqual([100, 40, 70]);
  });
  it("does not let a short leftover set the scale", () => {
    expect(barWidths([mk(1, 300), mk(2, 360), mk(3, 200, true)])).toEqual([100, 40, 100]);
  });
  it("gives equal bars for an even run and nothing for no splits", () => {
    expect(barWidths([mk(1, 300), mk(2, 300)])).toEqual([100, 100]);
    expect(barWidths([])).toEqual([]);
  });
});
