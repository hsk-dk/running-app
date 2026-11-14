import { describe, expect, it } from "vitest";
import { ALL, LAST_YEAR, defaultFilmPeriod, inPeriod, periodLabel, yearsOf } from "./period";

const TODAY = new Date(2026, 10, 14);

describe("inPeriod", () => {
  it("lets everything through for all, dated or not", () => {
    expect(inPeriod("2020-01-01", ALL, TODAY)).toBe(true);
    expect(inPeriod(null, ALL, TODAY)).toBe(true);
  });
  it("keeps a calendar year to that year, and runs without a date out of it", () => {
    expect(inPeriod("2026-01-01", "2026", TODAY)).toBe(true);
    expect(inPeriod("2026-12-31T23:00:00Z", "2026", TODAY)).toBe(true);
    expect(inPeriod("2025-12-31", "2026", TODAY)).toBe(false);
    expect(inPeriod(null, "2026", TODAY)).toBe(false);
  });
  it("takes the last 365 days, including today and not tomorrow", () => {
    expect(inPeriod("2025-11-14", LAST_YEAR, TODAY)).toBe(true);
    expect(inPeriod("2025-11-13", LAST_YEAR, TODAY)).toBe(false);
    expect(inPeriod("2026-11-14", LAST_YEAR, TODAY)).toBe(true);
    expect(inPeriod("2026-11-15", LAST_YEAR, TODAY)).toBe(false);
  });
});

describe("years and labels", () => {
  it("lists the years that have runs, newest first, once each", () => {
    expect(yearsOf(["2025-03-01", null, "2026-01-01", "2025-12-01", undefined])).toEqual(["2026", "2025"]);
    expect(yearsOf([])).toEqual([]);
  });
  it("names a period in words", () => {
    expect(periodLabel(ALL)).toBe("Alle dine løb");
    expect(periodLabel(LAST_YEAR)).toBe("De seneste 12 måneder");
    expect(periodLabel("2026")).toBe("2026");
  });
  it("starts a film on the newest year with enough runs", () => {
    const many = (y: string, n: number) => Array.from({ length: n }, (_, i) => `${y}-01-${String(i + 1).padStart(2, "0")}`);
    expect(defaultFilmPeriod([...many("2026", 6), ...many("2025", 20)])).toBe("2026");
    expect(defaultFilmPeriod([...many("2026", 2), ...many("2025", 20)])).toBe("2025");
    expect(defaultFilmPeriod(many("2026", 2))).toBe(LAST_YEAR);
    expect(defaultFilmPeriod([])).toBe(LAST_YEAR);
  });
});
