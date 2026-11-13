import { describe, expect, it } from "vitest";
import { cumulative, comparisons, marathons, nextMilestone, reached } from "./milestones";

const runs = [
  { date: "2026-03-01", distance_km: 60 },
  { date: "2026-01-10", distance_km: 45 },
  { date: null, distance_km: 99 },
  { date: "2026-05-02", distance_km: 120 },
];

describe("milestones", () => {
  it("adds up in date order and ignores runs without a date", () => {
    expect(cumulative(runs)).toEqual([
      { date: "2026-01-10", total: 45 },
      { date: "2026-03-01", total: 105 },
      { date: "2026-05-02", total: 225 },
    ]);
  });
  it("marks the first day each milestone was passed", () => {
    expect(reached(cumulative(runs))).toEqual([
      { km: 50, date: "2026-03-01" },
      { km: 100, date: "2026-03-01" },
    ]);
  });
  it("says what is next and how far", () => {
    expect(nextMilestone(225)).toEqual({ km: 250, remaining: 25 });
    expect(nextMilestone(250)).toEqual({ km: 500, remaining: 250 });
    expect(nextMilestone(99999)).toBeNull();
  });
  it("compares with a marathon and a few journeys", () => {
    expect(marathons(84.39)).toBe(2);
    const c = comparisons(150);
    expect(c[0].share).toBeCloseTo(0.5);
    expect(c.every((x) => x.label.includes("ca."))).toBe(true);
  });
  it("copes with nothing", () => {
    expect(cumulative([])).toEqual([]);
    expect(reached([])).toEqual([]);
  });
});
