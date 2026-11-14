import { describe, expect, it } from "vitest";
import { LINE_STEP_MS, STATS_REST_MS, countUp, lineOpacity, shareStats, statsMs, summarise, withOthers } from "./film";

const run = (date: string | null, distance_km: number, duration_min = distance_km * 6) => ({ date, distance_km, duration_min });
const year = Array.from({ length: 40 }, (_, i) => run(`2026-${String(1 + (i % 12)).padStart(2, "0")}-${String(1 + Math.floor(i / 12) * 7).padStart(2, "0")}`, 10 + (i % 5)));

describe("summarise", () => {
  it("says nothing for no runs", () => {
    expect(summarise([])).toEqual({ runs: 0, km: 0, hours: 0, activeDays: 0, lines: [] });
    expect(summarise([run("2026-01-01", 0)]).lines).toEqual([]);
  });
  it("counts runs, days, kilometres and hours", () => {
    const s = summarise([run("2026-01-01", 10, 60), run("2026-01-01", 5, 30), run("2026-01-02", 5, 30)]);
    expect(s).toMatchObject({ runs: 3, km: 20, hours: 2, activeDays: 2 });
    expect(s.lines[0]).toBe("3 løb på 2 dage");
    expect(s.lines[1]).toBe("20 km på 2,0 timer");
  });
  it("leaves out the hours when no run has a duration", () => {
    expect(summarise([run("2026-01-01", 10, 0)]).lines.join("|")).not.toContain("timer");
  });
  it("speaks of a single day in the singular", () => {
    expect(summarise([run("2026-01-01", 5)]).lines[0]).toBe("1 løb på 1 dag");
  });
  it("adds the long run, the busiest month, the longest week and the marathons when there is enough to say", () => {
    const l = summarise(year).lines;
    expect(l.some((x) => x.startsWith("Længste løb: 14,0 km"))).toBe(true);
    expect(l.some((x) => x.startsWith("Travleste måned:"))).toBe(true);
    expect(l.some((x) => x.startsWith("Længste uge:"))).toBe(true);
    expect(l.some((x) => /^Det svarer til \d+,\d maratonløb$/.test(x))).toBe(true);
  });
  it("leaves out month and week for a handful of runs, and the marathon below one", () => {
    const l = summarise([run("2026-01-01", 5), run("2026-01-03", 6), run("2026-01-05", 7), run("2026-01-07", 8), run("2026-01-09", 9)]).lines.join("|");
    expect(l).not.toContain("Travleste");
    expect(l).not.toContain("maraton");
  });
});

describe("the closing scene's timing", () => {
  it("brings in one line at a time and rests at the end", () => {
    expect(lineOpacity(0, 0)).toBe(0);
    expect(lineOpacity(0, 250)).toBeCloseTo(0.5, 6);
    expect(lineOpacity(0, 500)).toBe(1);
    expect(lineOpacity(2, 2 * LINE_STEP_MS - 1)).toBe(0);
    expect(lineOpacity(2, 2 * LINE_STEP_MS + 500)).toBe(1);
    expect(statsMs({ runs: 1, km: 1, hours: 1, activeDays: 1, lines: ["a", "b", "c"] })).toBe(3 * LINE_STEP_MS + STATS_REST_MS);
  });
});

describe("countUp", () => {
  it("rises from 0 to the target and stays there", () => {
    expect(countUp(0, 1000, 500)).toBe(0);
    expect(countUp(1000, 1000, 500)).toBe(500);
    expect(countUp(5000, 1000, 500)).toBe(500);
    expect(countUp(-5, 1000, 500)).toBe(0);
    expect(countUp(500, 1000, 500)).toBeGreaterThan(250); // eased: faster at first
    expect(countUp(10, 0, 500)).toBe(500);
  });
});

describe("short runs in the film", () => {
  it("are not counted, and a year of only warm-ups says nothing", () => {
    expect(summarise([run("2026-01-01", 10), run("2026-01-02", 0.7)]).runs).toBe(1);
    expect(shareStats([run("2026-01-01", 10), run("2026-01-02", 0.7)])[0].value).toBe("1");
    expect(summarise([run("2026-01-01", 0.9)]).lines).toEqual([]);
  });
});

describe("shareStats", () => {
  it("is empty without runs", () => {
    expect(shareStats([])).toEqual([]);
    expect(shareStats([run("2026-01-01", 0)])).toEqual([]);
  });
  it("gives runs, the longest run and the marathons once there are enough kilometres", () => {
    const s = shareStats(year);
    expect(s.map((x) => x.label)).toEqual(["løb", "længste løb", "maratonløb"]);
    expect(s[0].value).toBe("40");
    expect(s[1].value).toBe("14,0 km");
  });
  it("gives hours instead of marathons for a short stretch, and nothing about hours without durations", () => {
    expect(shareStats([run("2026-01-01", 10, 60), run("2026-01-02", 5, 30)]).map((x) => [x.value, x.label])).toEqual([["2", "løb"], ["10,0 km", "længste løb"], ["1,5", "timer"]]);
    expect(shareStats([run("2026-01-01", 10, 0)]).map((x) => x.label)).toEqual(["løb", "længste løb"]);
  });
});

describe("withOthers", () => {
  const base = summarise(year);
  it("adds one closing line about other training, and nothing when there is none", () => {
    const o = (kind: string) => ({ kind });
    const w = withOthers(base, [o("Row"), o("Row"), o("Walk")]);
    expect(w.lines.at(-1)).toBe("Dertil 3 andre aktiviteter: Roning (2), Gang (1)");
    expect(w.lines).toHaveLength(base.lines.length + 1);
    expect(withOthers(base, [o("Row")]).lines.at(-1)).toBe("Dertil 1 anden aktivitet: Roning (1)");
    expect(withOthers(base, [])).toBe(base);
  });
  it("does not bring a film to life that has no runs", () => {
    expect(withOthers(summarise([]), [{ kind: "Row" }]).lines).toEqual([]);
  });
});
