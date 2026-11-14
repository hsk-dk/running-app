import { describe, expect, it } from "vitest";
import { loadOver } from "./load";

const run = (date: string, distance_km: number, duration_min = distance_km * 6) => ({ date, distance_km, duration_min });
const TODAY = new Date(2026, 10, 13); // Friday 2026-11-13; this week began Monday 2026-11-09
// one run of `km` on the Monday of each of the weeks before this one: i = 1 is last week (2026-11-02)
const local = (y: number, m: number, d: number) => `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
const mondays = (kms: number[]) => kms.map((km, idx) => { const d = new Date(2026, 10, 9 - 7 * (idx + 1)); return run(local(d.getFullYear(), d.getMonth() + 1, d.getDate()), km); });

describe("loadOver: weeks", () => {
  it("returns twelve Monday-to-Sunday weeks, oldest first, the last one in progress", () => {
    const l = loadOver([run("2026-11-09", 10), run("2026-11-12", 5)], TODAY);
    expect(l.weeks).toHaveLength(12);
    expect(l.weeks[11]).toMatchObject({ start: "2026-11-09", km: 15, runs: 2, longest: 10, current: true });
    expect(l.weeks[0].start).toBe("2026-08-24");
    expect(l.weeks.filter((w) => w.current)).toHaveLength(1);
  });
  it("puts Sunday in its own week", () => {
    const l = loadOver([run("2026-11-08", 7), run("2026-11-09", 3)], TODAY);
    expect(l.weeks[10].km).toBe(7);
    expect(l.weeks[11].km).toBe(3);
  });
});

describe("loadOver: reading the trend", () => {
  it("is steady when last week matches the four before", () => {
    const l = loadOver(mondays([20, 20, 20, 20, 20]), TODAY);
    expect(l.level).toBe("steady");
    expect(l.baseline).toBe(20);
    expect(l.ramp).toBe(1);
  });
  it("sees a build, a jump and a rest week", () => {
    expect(loadOver(mondays([24, 20, 20, 20, 20]), TODAY).level).toBe("build");
    expect(loadOver(mondays([30, 20, 20, 20, 20]), TODAY).level).toBe("jump");
    expect(loadOver(mondays([12, 20, 20, 20, 20]), TODAY).level).toBe("rest");
  });
  it("puts the boundaries at 80, 110 and 130 per cent", () => {
    expect(loadOver(mondays([16, 20, 20, 20, 20]), TODAY).level).toBe("steady");
    expect(loadOver(mondays([22, 20, 20, 20, 20]), TODAY).level).toBe("steady");
    expect(loadOver(mondays([22.2, 20, 20, 20, 20]), TODAY).level).toBe("build");
    expect(loadOver(mondays([26, 20, 20, 20, 20]), TODAY).level).toBe("build");
    expect(loadOver(mondays([26.5, 20, 20, 20, 20]), TODAY).level).toBe("jump");
  });
  it("says nothing without history, or from a tiny baseline", () => {
    expect(loadOver(mondays([20, 20]), TODAY).level).toBe("unknown");
    expect(loadOver(mondays([30, 2, 2, 2, 2]), TODAY).level).toBe("unknown");
    expect(loadOver([], TODAY).level).toBe("unknown");
  });
  it("does not count the week in progress", () => {
    const l = loadOver([...mondays([20, 20, 20, 20, 20]), run("2026-11-09", 60)], TODAY);
    expect(l.level).toBe("steady");
  });
  it("adds the rule-of-thumb note only for a jump", () => {
    expect(loadOver(mondays([30, 20, 20, 20, 20]), TODAY).notes.join(" ")).toContain("tommelfingerregel");
    expect(loadOver(mondays([20, 20, 20, 20, 20]), TODAY).notes.join(" ")).not.toContain("tommelfingerregel");
  });
});

describe("loadOver: rest and rhythm", () => {
  it("counts days since the last run", () => {
    expect(loadOver([run("2026-11-13", 5)], TODAY).restDays).toBe(0);
    expect(loadOver([run("2026-11-10", 5)], TODAY).restDays).toBe(3);
  });
  it("counts consecutive running days and suggests a rest day from five", () => {
    const four = ["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"].map((d) => run(d, 5));
    expect(loadOver(four, TODAY).daysInARow).toBe(4);
    expect(loadOver(four, TODAY).notes.join(" ")).not.toContain("hviledag");
    const five = [...four, run("2026-11-09", 5)];
    const l = loadOver(five, TODAY);
    expect(l.daysInARow).toBe(5);
    expect(l.notes.join(" ")).toContain("5 dage i træk");
  });
  it("still counts a streak that ended yesterday", () => {
    expect(loadOver([run("2026-11-11", 5), run("2026-11-12", 5)], TODAY).daysInARow).toBe(2);
  });
  it("notes four days or more without a run", () => {
    expect(loadOver([run("2026-11-08", 5)], TODAY).notes.join(" ")).toContain("5 dage siden sidste løb");
    expect(loadOver([run("2026-11-10", 5)], TODAY).notes.join(" ")).not.toContain("dage siden"); // three days is an ordinary rest
  });
  it("points out a week dominated by one long run", () => {
    const d = (n: number) => { const x = new Date(2026, 10, 2 + n); return local(x.getFullYear(), x.getMonth() + 1, x.getDate()); };
    const l = loadOver([...mondays([0, 20, 20, 20, 20]).slice(1), run(d(0), 16), run(d(2), 4)], TODAY);
    expect(l.notes.join(" ")).toContain("80 % af sidste uges kilometer");
  });
});
