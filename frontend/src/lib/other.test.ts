import { describe, expect, it } from "vitest";
import { kindLabel, kindsText, otherDays, recentOther } from "./other";

const o = (date: string | null, kind = "Row", duration_min = 20) => ({ date, kind, duration_min });

describe("kindLabel", () => {
  it("names the kinds in Danish and falls back to other training", () => {
    expect(kindLabel("Row")).toBe("Roning");
    expect(kindLabel("Ride")).toBe("Cykling");
    expect(kindLabel("Strength")).toBe("Styrke og øvelser");
    expect(kindLabel("Kitesurf")).toBe("Anden træning");
  });
});

describe("otherDays", () => {
  it("lists each day once and ignores undated entries", () => {
    expect([...otherDays([o("2026-01-02"), o("2026-01-02T08:00:00Z"), o(null), o("2026-01-03")])].sort()).toEqual(["2026-01-02", "2026-01-03"]);
  });
});

describe("kindsText", () => {
  it("puts the most common first, with counts, at most three", () => {
    const list = [...Array(4).fill(o("2026-01-01", "Row")), ...Array(2).fill(o("2026-01-01", "Walk")), o("2026-01-01", "Ride"), o("2026-01-01", "Swim")];
    expect(kindsText(list)).toBe("Roning (4), Gang (2), Cykling (1)");
    expect(kindsText(list, 4)).toBe("Roning (4), Gang (2), Cykling (1), Svømning (1)");
    expect(kindsText([])).toBe("");
  });
  it("breaks ties alphabetically so it never flickers", () => {
    expect(kindsText([o("2026-01-01", "Walk"), o("2026-01-01", "Ride")])).toBe("Cykling (1), Gang (1)");
  });
});

describe("recentOther", () => {
  const today = new Date(2026, 10, 14);
  it("counts the window including today and not the day before it", () => {
    const list = [o("2026-11-14", "Row", 30), o("2026-11-08", "Row", 30), o("2026-11-07", "Row", 30), o("2026-11-15", "Row", 30)];
    expect(recentOther(list, today, 7)).toEqual({ count: 2, hours: 1 });
    expect(recentOther([], today, 7)).toEqual({ count: 0, hours: 0 });
  });
});
