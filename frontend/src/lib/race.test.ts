import { describe, expect, it } from "vitest";
import { clock, daysUntil, estimate, findRace, paceOf, parseTargetRange, riegel } from "./race";
import { Activity, PlannedRun } from "./week";

const TODAY = new Date("2026-11-13T12:00:00");
const act = (date: string, km: number, min: number): Activity => ({ id: 1, date, name: null, distance_km: km, duration_min: min, is_extra: false });
const plan = (date: string, type: string): PlannedRun => ({ id: 1, planned_date: date, session_type: type, target_type: "distance", target_value: 5, optional: false, status: "planlagt", actual_value: null });

describe("riegel", () => {
  it("scales a time to another distance", () => {
    expect(riegel(25, 5, 10)).toBeCloseTo(25 * Math.pow(2, 1.06), 6);
    expect(riegel(30, 5, 5)).toBe(30);
  });
});

describe("parseTargetRange", () => {
  it("reads Runna's goal range", () => {
    expect(parseTargetRange("Race • 5km • 30m20s - 32m30s\n\n5km race at 6:05-6:30/km")).toEqual({ lowSec: 1820, highSec: 1950 });
  });
  it("gives null for anything else", () => {
    expect(parseTargetRange(null)).toBeNull();
    expect(parseTargetRange("easy run")).toBeNull();
    expect(parseTargetRange("40m00s - 30m00s")).toBeNull();
  });
});

describe("findRace", () => {
  it("picks the next race and ignores past races and other sessions", () => {
    const runs = [plan("2026-11-01", "race"), plan("2026-11-14", "easy"), plan("2026-12-20", "race"), plan("2026-11-15", "race")];
    expect(findRace(runs, TODAY)?.planned_date).toBe("2026-11-15");
    expect(findRace([plan("2026-11-01", "race")], TODAY)).toBeNull();
    expect(findRace([plan("2026-11-13", "race")], TODAY)?.planned_date).toBe("2026-11-13"); // today counts
  });
  it("counts days", () => {
    expect(daysUntil("2026-11-15", TODAY)).toBe(2);
    expect(daysUntil("2026-11-13", TODAY)).toBe(0);
  });
});

describe("estimate", () => {
  it("scales recent runs of a useful length to the race distance", () => {
    const e = estimate([act("2026-11-10", 5, 38.8), act("2026-11-05", 8, 62), act("2026-10-30", 6, 46)], 5, TODAY)!;
    expect(e.runs).toBe(3);
    expect(e.fastSec).toBeLessThanOrEqual(e.typicalSec);
    const all = [riegel(38.8 * 60, 5, 5), riegel(62 * 60, 8, 5), riegel(46 * 60, 6, 5)];
    expect(e.fastSec).toBeCloseTo(Math.min(...all), 6); // the quickest once scaled to the race distance
    expect(e.typicalSec).toBeCloseTo([...all].sort((a, b) => a - b)[1], 6); // the middle one
  });
  it("ignores old runs and runs that are too short", () => {
    expect(estimate([act("2026-08-01", 5, 30), act("2026-11-10", 2, 12)], 5, TODAY)).toBeNull();
  });
  it("gives the middle one as typical", () => {
    const e = estimate([act("2026-11-10", 5, 30), act("2026-11-09", 5, 32), act("2026-11-08", 5, 40)], 5, TODAY)!;
    expect(e.fastSec).toBeCloseTo(1800, 0);
    expect(e.typicalSec).toBeCloseTo(1920, 0);
  });
  it("copes with nothing", () => {
    expect(estimate([], 5, TODAY)).toBeNull();
  });
});

describe("clock", () => {
  it("formats minutes and hours", () => {
    expect(clock(1820)).toBe("30:20");
    expect(clock(3725)).toBe("1:02:05");
    expect(clock(59.6)).toBe("1:00");
    expect(paceOf(1800, 5)).toBe("6:00");
  });
});
