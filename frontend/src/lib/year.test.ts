import { describe, expect, it } from "vitest";
import { Activity } from "./week";
import { baseChange, buildDays, completeWeeks, levelFn, monthlyTotals, rollingAverage, weeklyTotals, yearFacts } from "./year";
import { decodePolyline, projectRoute, toPath } from "./route";

const TODAY = new Date(2026, 10, 12); // Thursday 12 November 2026
const act = (date: string, km: number, min = km * 6, id = Math.random()): Activity => ({
  id, date, name: "Løb", distance_km: km, duration_min: min, is_extra: false,
});

describe("buildDays", () => {
  const days = buildDays([act("2026-11-12", 10), act("2026-11-12", 5), act("2026-11-09", 8)], TODAY);
  it("starts on a Monday and ends today", () => {
    expect(days[0].weekday).toBe(0);
    expect(days[days.length - 1].date).toBe("2026-11-12");
  });
  it("covers a full year of weeks", () => {
    expect(days.length).toBeGreaterThanOrEqual(365);
    expect(days.length).toBeLessThanOrEqual(371);
  });
  it("adds runs on the same day together", () => {
    const d = days.find((x) => x.date === "2026-11-12")!;
    expect([d.km, d.runs]).toEqual([15, 2]);
  });
  it("ignores activities without a date or outside the window", () => {
    const d2 = buildDays([{ ...act("2020-01-01", 99), date: null }, act("2020-01-01", 99)], TODAY);
    expect(d2.reduce((s, d) => s + d.km, 0)).toBe(0);
  });
});

describe("levelFn", () => {
  it("uses quartiles of run days and level 0 for rest days", () => {
    const f = levelFn([0, 0, 2, 4, 6, 8]);
    expect([0, 2, 4, 6, 8].map(f)).toEqual([0, 1, 2, 3, 4]);
  });
  it("gives a lone run day the lowest level", () => {
    expect(levelFn([5])(5)).toBe(1);
  });
  it("copes with no runs at all", () => {
    expect(levelFn([0, 0])(5)).toBe(0);
  });
});

describe("weeks, months and facts", () => {
  const acts = [act("2026-11-09", 10), act("2026-11-12", 5), act("2026-11-02", 20), act("2026-10-20", 7)];
  const days = buildDays(acts, TODAY);
  const weeks = weeklyTotals(days);
  it("sums weeks Monday to Sunday", () => {
    const last = weeks[weeks.length - 1];
    expect([last.weekStart, last.km, last.runs]).toEqual(["2026-11-09", 15, 2]);
    expect(weeks[weeks.length - 2].km).toBe(20);
  });
  it("leaves out the current week until Sunday", () => {
    expect(completeWeeks(weeks, TODAY).at(-1)?.weekStart).toBe("2026-11-02");
    expect(completeWeeks(weeks, new Date(2026, 10, 15)).at(-1)?.weekStart).toBe("2026-11-09");
  });
  it("totals months in order", () => {
    const m = monthlyTotals(days);
    expect(m.at(-1)).toEqual({ key: "2026-11", km: 35 });
    expect(m.at(-2)).toEqual({ key: "2026-10", km: 7 });
  });
  it("finds the busiest week, the longest run and the longest streak of weeks", () => {
    const f = yearFacts(days, weeks, acts);
    expect(f.totalKm).toBe(42);
    expect(f.runDays).toBe(4);
    expect(f.busiestWeek).toEqual({ km: 20, weekStart: "2026-11-02" });
    expect(f.longestRun).toMatchObject({ km: 20, date: "2026-11-02" });
    expect(f.longestWeekStreak).toBe(2); // 2 and 9 November; 20 October is a week on its own
  });
  it("reports no records when there are no runs", () => {
    const empty = buildDays([], TODAY);
    const f = yearFacts(empty, weeklyTotals(empty), []);
    expect([f.totalKm, f.runDays, f.busiestWeek, f.longestRun, f.longestWeekStreak]).toEqual([0, 0, null, null, 0]);
  });
});

describe("rollingAverage and baseChange", () => {
  it("averages over the last four weeks, fewer at the start", () => {
    expect(rollingAverage([10, 20, 30, 40, 50])).toEqual([10, 15, 20, 25, 35]);
  });
  it("needs at least eight weeks", () => {
    expect(baseChange([20, 21, 22, 23, 24, 25, 26])).toBeNull();
  });
  it("reports a real change and ignores a small one", () => {
    expect(baseChange([20, 20, 20, 20, 30, 30, 30, 30])).toEqual({ pct: 50, weeks: 4 });
    expect(baseChange([20, 20, 20, 20, 21, 20, 21, 20])).toBeNull();
  });
  it("does not divide by zero", () => {
    expect(baseChange([0, 0, 0, 0, 5, 5, 5, 5])).toBeNull();
  });
});

describe("route", () => {
  const encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"; // Google's documented example
  it("decodes a polyline", () => {
    expect(decodePolyline(encoded)).toEqual([[38.5, -120.2], [40.7, -120.95], [43.252, -126.453]]);
  });
  it("keeps what was decoded from a truncated string and returns [] for an empty one", () => {
    expect(decodePolyline("")).toEqual([]);
    expect(decodePolyline(encoded.slice(0, 12)).length).toBeLessThan(3);
  });
  it("fits the route inside the box with padding and keeps north up", () => {
    const pts = projectRoute(decodePolyline(encoded), 300, 200, 20);
    for (const [x, y] of pts) {
      expect(x).toBeGreaterThanOrEqual(19.9); expect(x).toBeLessThanOrEqual(280.1);
      expect(y).toBeGreaterThanOrEqual(19.9); expect(y).toBeLessThanOrEqual(180.1);
    }
    expect(pts[2][1]).toBeLessThan(pts[0][1]); // the northernmost point is nearer the top
  });
  it("needs at least two points", () => {
    expect(projectRoute([[1, 1]], 100, 100)).toEqual([]);
    expect(toPath([[1, 2], [3.14159, 4]])).toBe("M1.0 2.0 L3.1 4.0");
  });
});
