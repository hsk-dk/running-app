import { describe, expect, it } from "vitest";
import { guardianNote, weekText } from "./family";

describe("weekText", () => {
  it("shows the plan when there is one", () => {
    expect(weekText({ done: 1, total: 4 }, 3)).toBe("1 af 4");
  });
  it("counts runs when there is no plan", () => {
    expect(weekText({ done: 0, total: 0 }, 0)).toBe("Ingen løb endnu");
    expect(weekText(null, 1)).toBe("1 løb");
    expect(weekText({ done: 0, total: 0 }, 3)).toBe("3 løb");
  });
});

describe("guardianNote", () => {
  const g = (over: Partial<Parameters<typeof guardianNote>[0]> = {}) => ({ runs_week: 0, active_days_week: 0, minutes_week: 0, runs_month: 0, minutes_month: 0, last_run_date: "2026-11-10", streak_weeks: 1, ...over });
  const today = "2026-11-14";
  it("waits kindly for a first run", () => {
    expect(guardianNote(g({ last_run_date: null }), today)).toContain("Ingen løb endnu");
  });
  it("encourages a good week and a started one", () => {
    expect(guardianNote(g({ runs_week: 3 }), today)).toContain("god uge");
    expect(guardianNote(g({ runs_week: 2 }), today)).toContain("2 gange");
    expect(guardianNote(g({ runs_week: 1 }), today)).toContain("1 gang");
  });
  it("suggests asking, not pushing, after a quiet spell, and calls a short pause normal", () => {
    expect(guardianNote(g({ last_run_date: "2026-11-12" }), today)).toContain("helt normalt");
    expect(guardianNote(g({ last_run_date: "2026-11-07" }), today)).toContain("7 dage");
    expect(guardianNote(g({ last_run_date: "2026-11-08" }), today)).toContain("helt normalt"); // 6 days
    expect(guardianNote(g({ last_run_date: "2026-10-31" }), today)).toContain("uden pres");
    expect(guardianNote(g({ last_run_date: "2026-10-31" }), today)).toContain("14 dage");
    expect(guardianNote(g({ last_run_date: "2026-11-01" }), today)).toContain("13 dage"); // 13 days: the gentler one
  });
});
