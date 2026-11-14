import { describe, expect, it } from "vitest";
import { newRecords, paceText, records, weekStory } from "./records";

const run = (date: string, distance_km: number, duration_min = distance_km * 6) => ({ date, distance_km, duration_min });
// five weeks, one run of 10 km each Monday from 2026-09-07, plus a 5 km on Wednesdays
const base = [7, 14, 21, 28].flatMap((d) => [run(`2026-09-${String(d).padStart(2, "0")}`, 10), run(`2026-09-${String(d + 2).padStart(2, "0")}`, 5, 25)]);

describe("paceText", () => {
  it("formats minutes per km and carries seconds that round to 60", () => {
    expect(paceText(5.7)).toBe("5:42 /km");
    expect(paceText(4.999)).toBe("5:00 /km");
  });
});

describe("records", () => {
  it("is empty with too few runs", () => {
    expect(records([run("2026-09-01", 5), run("2026-09-02", 5)])).toEqual([]);
  });
  it("finds the personal bests and says when", () => {
    const r = Object.fromEntries(records(base).map((x) => [x.key, x]));
    expect(r.longest.amount).toBe(10);
    expect(r.week.amount).toBe(15);
    expect(r.month.amount).toBe(60);
    expect(r.streak.amount).toBe(4);
    expect(r.pace.value).toBe("5:00 /km"); // the 5 km in 25 min beats 10 km in 60 min
  });
  it("ignores short runs for pace and breaks a streak on a missing week", () => {
    const sprint = [...base, run("2026-09-30", 1, 3)];
    expect(records(sprint).find((x) => x.key === "pace")!.value).toBe("5:00 /km");
    const gap = [run("2026-09-07", 5), run("2026-09-08", 5), run("2026-09-21", 5), run("2026-09-22", 5), run("2026-09-23", 5)];
    expect(records(gap).find((x) => x.key === "streak")!.amount).toBe(1);
  });
});

describe("newRecords", () => {
  const today = new Date(2026, 9, 6); // 2026-10-06
  it("flags a record set in the last 7 days that beats the earlier best", () => {
    const acts = [...base, run("2026-10-04", 12, 66)];
    const n = newRecords(acts, today).map((r) => r.key);
    expect(n).toContain("longest");
    expect(n).not.toContain("pace");
  });
  it("flags nothing when the old best still stands, or when there is no history", () => {
    expect(newRecords([...base, run("2026-10-04", 6)], today).map((r) => r.key)).not.toContain("longest");
    expect(newRecords([run("2026-10-04", 12), run("2026-10-03", 5), run("2026-10-02", 5), run("2026-10-01", 5), run("2026-10-05", 5)], today)).toEqual([]);
  });
});

describe("weekStory", () => {
  const today = new Date(2026, 9, 7); // Wednesday 2026-10-07; the week began 2026-10-05
  it("says nothing before the first run of the week", () => {
    expect(weekStory(base, today)).toBeNull();
  });
  it("sums the week so far, in Danish", () => {
    expect(weekStory([...base, run("2026-10-05", 8)], today)!.headline).toBe("8 km i 1 løb denne uge.");
    expect(weekStory([...base, run("2026-10-05", 8), run("2026-10-07", 8)], today)!.headline).toBe("16 km i 2 løb denne uge.");
  });
  it("calls out the longest week ever, but only with enough history", () => {
    const big = [...base, run("2026-10-05", 20), run("2026-10-07", 10)];
    expect(weekStory(big, today)!.notes).toContain("Din længste uge nogensinde.");
    expect(weekStory([run("2026-09-30", 5), run("2026-10-05", 20)], today)!.notes).toEqual([]);
  });
  it("never says anything discouraging about a quiet week", () => {
    const w = weekStory([...base, run("2026-10-05", 2)], today)!;
    expect(w.notes).toEqual([]);
  });
});
