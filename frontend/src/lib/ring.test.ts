import { describe, expect, it } from "vitest";
import { MONTHS, buildRing, monthMarks } from "./ring";
import { DayCell } from "./year";

const day = (date: string, km: number): DayCell => ({ date, km, min: km * 6, runs: km > 0 ? 1 : 0, weekIndex: 0, weekday: 0 });
const run = (n: number, kmOf: (i: number) => number): DayCell[] =>
  Array.from({ length: n }, (_, i) => day(new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10), kmOf(i)));

describe("buildRing", () => {
  it("starts straight up and goes clockwise once around", () => {
    const { spokes } = buildRing(run(365, () => 5), 100, 30, 90);
    expect(spokes[0].angle).toBe(0);
    expect(spokes[0].x0).toBeCloseTo(100); // centred on the vertical axis
    expect(spokes[0].y0).toBeCloseTo(70); // above the centre
    expect(spokes[91].x0).toBeGreaterThan(100); // a quarter turn: to the right
    expect(spokes[364].angle).toBeLessThan(Math.PI * 2);
  });

  it("makes longer runs longer spokes, the longest reaching the outer radius, rest days zero", () => {
    const { spokes } = buildRing(run(365, (i) => (i === 10 ? 20 : i === 11 ? 10 : 0)), 100, 30, 90);
    expect(spokes[10].length).toBeCloseTo(60);
    expect(spokes[11].length).toBeCloseTo(30);
    expect(spokes[12].length).toBe(0);
  });

  it("does not let a short week fill the ring", () => {
    const { spokes, capKm } = buildRing(run(365, (i) => (i === 3 ? 3 : 0)), 100, 30, 90);
    expect(capKm).toBe(5);
    expect(spokes[3].length).toBeCloseTo(36);
  });

  it("uses only the latest days when given more", () => {
    const { spokes } = buildRing(run(400, () => 1), 100, 30, 90, 365);
    expect(spokes).toHaveLength(365);
    expect(spokes[0].date).toBe(run(400, () => 1)[35].date);
  });

  it("finds where each month starts for the labels", () => {
    const { spokes } = buildRing(run(365, () => 1), 100, 30, 90);
    const marks = monthMarks(spokes);
    expect(marks).toHaveLength(12);
    expect(MONTHS[marks[0].month]).toBe("jan");
    expect(marks[1].angle).toBeCloseTo((31 / 365) * Math.PI * 2);
  });

  it("labels a month once when the year starts and ends in it, keeping the longer stretch", () => {
    // 17 days of November, then Dec..Oct, then 13 days of November again
    const start = Date.UTC(2025, 10, 14);
    const days = Array.from({ length: 365 }, (_, i) => day(new Date(start + i * 86_400_000).toISOString().slice(0, 10), 1));
    const marks = monthMarks(buildRing(days, 100, 30, 90).spokes);
    expect(marks.filter((m) => MONTHS[m.month] === "nov")).toHaveLength(1);
    expect(marks).toHaveLength(12);
    expect(marks[0].angle).toBe(0); // the longer, earlier stretch kept its label at the top
  });

  it("copes with no days", () => {
    expect(buildRing([], 100, 30, 90).spokes).toEqual([]);
  });
});
