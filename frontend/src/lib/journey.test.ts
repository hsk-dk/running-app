import { describe, expect, it } from "vitest";
import { journey } from "./journey";

const run = (date: string, distance_km: number) => ({ date, distance_km });
const TODAY = new Date(2026, 10, 14); // 2026-11-14

describe("journey", () => {
  it("is nothing before a real run", () => {
    expect(journey([], TODAY)).toBeNull();
    expect(journey([run("2026-11-01", 0.5), { date: null, distance_km: 5 }], TODAY)).toBeNull();
  });
  it("starts counting weeks at one", () => {
    expect(journey([run("2026-11-14", 2)], TODAY)!.weeksIn).toBe(1);
    expect(journey([run("2026-11-08", 2)], TODAY)!.weeksIn).toBe(1);
    expect(journey([run("2026-11-07", 2)], TODAY)!.weeksIn).toBe(2);
    expect(journey([run("2026-03-13", 2)], TODAY)!.weeksIn).toBe(36);
  });
  it("says how far you have come when you have grown, and just how long you have been going otherwise", () => {
    const grown = journey([run("2026-09-01", 2), run("2026-10-01", 4), run("2026-11-10", 6)], TODAY)!;
    expect(grown.headline).toBe("Du er gået fra 2,0 km til 6,0 km på 11 uger.");
    expect(grown.recentLongest).toBe(6);
    const flat = journey([run("2026-09-01", 5), run("2026-10-01", 5), run("2026-11-10", 5.5)], TODAY)!;
    expect(flat.headline).toBe("Uge 11 i gang: 3 løb og 15,5 km i alt.");
    const small = journey([run("2026-10-01", 2), run("2026-10-05", 2.2), run("2026-11-10", 2.4)], TODAY)!;
    expect(small.headline).toContain("i gang"); // 20 % more is not "gone from"
  });
  it("calls growth only when it is at least half a kilometre, and not from only one or two runs", () => {
    expect(journey([run("2026-10-01", 1.2), run("2026-10-10", 1.4), run("2026-11-10", 1.6)], TODAY)!.headline).toContain("i gang"); // +0.4 km
    expect(journey([run("2026-10-01", 1.0), run("2026-11-10", 5)], TODAY)!.headline).toContain("i gang"); // two runs
  });
  it("looks four weeks back, not three", () => {
    const j = journey([run("2026-09-01", 2), run("2026-10-01", 3), run("2026-10-18", 7)], TODAY)!; // 27 days ago
    expect(j.recentLongest).toBe(7);
    expect(journey([run("2026-09-01", 2), run("2026-10-01", 3), run("2026-10-17", 7)], TODAY)!.recentLongest).toBe(0); // 28 days ago
  });
  it("needs a run in the last four weeks to speak of progress", () => {
    const stopped = journey([run("2026-01-01", 2), run("2026-01-10", 3), run("2026-01-20", 6)], TODAY)!;
    expect(stopped.recentLongest).toBe(0);
    expect(stopped.headline).toContain("i gang");
  });
  it("lists every month from the first, with the longest run, and empty months in between", () => {
    const j = journey([run("2026-09-05", 2), run("2026-09-20", 3), run("2026-11-02", 5)], TODAY)!;
    expect(j.months).toEqual([{ key: "2026-09", longest: 3, runs: 2 }, { key: "2026-10", longest: 0, runs: 0 }, { key: "2026-11", longest: 5, runs: 1 }]);
  });
  it("shows at most the last twelve months", () => {
    const j = journey([run("2025-01-05", 2), run("2026-11-05", 5)], TODAY)!;
    expect(j.months).toHaveLength(12);
    expect(j.months[11].key).toBe("2026-11");
  });
  it("is a beginner for the first runs and weeks, and says something kind about rest", () => {
    const j = journey([run("2026-11-01", 2), run("2026-11-08", 3)], TODAY)!;
    expect(j.beginner).toBe(true);
    expect(j.note).toContain("hviledage");
  });
  it("stops being a beginner after enough runs and enough weeks, and then says no reassurance", () => {
    const many = Array.from({ length: 25 }, (_, i) => run(`2026-0${3 + Math.floor(i / 10)}-${String(1 + (i % 10) * 2).padStart(2, "0")}`, 5));
    const j = journey(many, TODAY)!;
    expect(j.beginner).toBe(false);
    expect(j.note).toBe("");
    expect(journey(many.slice(0, 19), TODAY)!.beginner).toBe(true); // 19 runs is still few
    expect(journey([...many.slice(0, 25), run("2026-11-10", 5)], new Date(2026, 4, 20))!.beginner).toBe(true); // 12 weeks or fewer in
  });
});
