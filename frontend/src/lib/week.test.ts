import { describe, expect, it } from "vitest";
import {
  Activity,
  PlannedRun,
  dateKey,
  dayLabel,
  insights,
  isoWeekNumber,
  nextRun,
  parseDateKey,
  runValueLabel,
  summarizeWeek,
  weekDays,
  weekHeadline,
  weekStartOf,
} from "./week";

const THU = new Date(2026, 10, 12); // Thursday 12 November 2026, ISO week 46

function run(over: Partial<PlannedRun>): PlannedRun {
  return {
    id: 1, planned_date: "2026-11-09", session_type: "easy", target_type: "time", target_value: 40,
    optional: false, status: "planlagt", actual_value: null, ...over,
  };
}
const act = (over: Partial<Activity>): Activity => ({
  id: 1, date: "2026-11-11", name: "Løb", distance_km: 5, duration_min: 30, is_extra: true, ...over,
});

describe("dates", () => {
  it("finds Monday of the week, also for Sunday and Monday", () => {
    expect(dateKey(weekStartOf(THU))).toBe("2026-11-09");
    expect(dateKey(weekStartOf(new Date(2026, 10, 15)))).toBe("2026-11-09"); // Sunday
    expect(dateKey(weekStartOf(new Date(2026, 10, 9)))).toBe("2026-11-09"); // Monday
    expect(dateKey(weekStartOf(new Date(2026, 10, 16)))).toBe("2026-11-16");
  });
  it("numbers ISO weeks across a year boundary", () => {
    expect(isoWeekNumber(THU)).toBe(46);
    expect(isoWeekNumber(new Date(2021, 0, 3))).toBe(53);
    expect(isoWeekNumber(new Date(2026, 0, 1))).toBe(1);
  });
  it("round-trips date keys without time zone drift", () => {
    expect(dateKey(parseDateKey("2026-03-29"))).toBe("2026-03-29"); // DST change in Europe
    expect(dateKey(parseDateKey("2026-10-25"))).toBe("2026-10-25");
  });
});

describe("weekDays", () => {
  const plans = [
    run({ id: 1, planned_date: "2026-11-09", status: "gennemført", actual_value: 47 }),
    run({ id: 2, planned_date: "2026-11-11", status: "forkortet", actual_value: 28 }),
    run({ id: 3, planned_date: "2026-11-14", status: "planlagt" }),
    run({ id: 4, planned_date: "2026-11-15", status: "planlagt", session_type: "long", target_value: 90 }),
    run({ id: 5, planned_date: "2026-11-10", status: "flyttet" }),
  ];
  const days = weekDays(plans, [act({ date: "2026-11-12" })], weekStartOf(THU), THU);

  it("gives seven days from Monday", () => {
    expect(days.map((d) => d.date)).toEqual([
      "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-14", "2026-11-15",
    ]);
  });
  it("maps statuses to kinds and ignores moved runs", () => {
    expect(days.map((d) => d.kind)).toEqual(["done", "rest", "shortened", "rest", "rest", "planned", "planned"]);
  });
  it("marks today and future days", () => {
    expect(days[3].isToday).toBe(true);
    expect(days[2].isFuture).toBe(false);
    expect(days[5].isFuture).toBe(true);
  });
  it("attaches unplanned runs to their day only", () => {
    expect(days[3].extras).toHaveLength(1);
    expect(days[2].extras).toHaveLength(0);
  });
  it("a completed run wins over a skipped one on the same day", () => {
    const both = weekDays(
      [run({ id: 1, status: "sprunget over" }), run({ id: 2, status: "gennemført" })],
      [], weekStartOf(THU), THU
    );
    expect(both[0].kind).toBe("done");
  });
  it("a skipped run with nothing else shows as skipped", () => {
    expect(weekDays([run({ status: "sprunget over" })], [], weekStartOf(THU), THU)[0].kind).toBe("skipped");
  });
});

describe("summarizeWeek and headline", () => {
  const plans = [
    run({ id: 1, planned_date: "2026-11-09", status: "gennemført" }),
    run({ id: 2, planned_date: "2026-11-11", status: "forkortet" }),
    run({ id: 3, planned_date: "2026-11-14", status: "planlagt" }),
    run({ id: 4, planned_date: "2026-11-15", status: "planlagt" }),
    run({ id: 5, planned_date: "2026-11-12", status: "planlagt", optional: true }),
  ];
  const days = weekDays(plans, [], weekStartOf(THU), THU);
  const summary = summarizeWeek(days);

  it("counts mandatory runs only, and shortened runs as done", () => {
    expect(summary).toEqual({ total: 4, done: 2, shortened: 1, skipped: 0, open: 2 });
  });
  it("says how many are done and when the next one is", () => {
    expect(weekHeadline(summary, nextRun(plans, THU), THU)).toBe("2 af 4 løb i hus. Næste løb er i dag.");
  });
  it("counts an optional run as the next thing planned", () => {
    expect(nextRun(plans, THU)?.id).toBe(5); // optional run today is still the next thing planned
  });
  it("names the weekday for runs later in the week", () => {
    expect(weekHeadline(summary, run({ planned_date: "2026-11-14" }), THU)).toBe("2 af 4 løb i hus. Næste løb er lørdag.");
  });
  it("handles an empty week", () => {
    expect(weekHeadline({ total: 0, done: 0, shortened: 0, skipped: 0, open: 0 }, null, THU)).toBe(
      "Ingen vigtige løb planlagt i denne uge."
    );
  });
  it("says the week is done or over when nothing is open", () => {
    expect(weekHeadline({ total: 3, done: 3, shortened: 0, skipped: 0, open: 0 }, null, THU)).toBe("3 af 3 løb i hus. Ugen er klaret.");
    expect(weekHeadline({ total: 3, done: 2, shortened: 0, skipped: 1, open: 0 }, null, THU)).toBe("2 af 3 løb i hus. Ugen er slut.");
  });
});

describe("nextRun and dayLabel", () => {
  it("ignores runs in the past and runs that are not planned", () => {
    const plans = [
      run({ id: 1, planned_date: "2026-11-10", status: "planlagt" }), // yesterday-ish, still 'planlagt' (window open)
      run({ id: 2, planned_date: "2026-11-13", status: "gennemført" }),
      run({ id: 3, planned_date: "2026-11-14", status: "planlagt" }),
    ];
    expect(nextRun(plans, THU)?.id).toBe(3);
  });
  it("returns null when nothing is left", () => {
    expect(nextRun([run({ status: "gennemført" })], THU)).toBeNull();
  });
  it("labels today, tomorrow, weekdays and dates further away", () => {
    expect(dayLabel("2026-11-12", THU)).toBe("i dag");
    expect(dayLabel("2026-11-13", THU)).toBe("i morgen");
    expect(dayLabel("2026-11-15", THU)).toBe("søndag");
    expect(dayLabel("2026-11-22", THU)).toBe("søndag d. 22.");
  });
});

describe("insights", () => {
  it("only reports a rise in distance, never a fall (the month is not over)", () => {
    expect(insights({ km_prev_month: 80, km_change_pct: 12.4 })).toEqual(["Du har allerede løbet 12 % mere end hele sidste måned."]);
    expect(insights({ km_prev_month: 80, km_change_pct: -33 })).toEqual([]);
    expect(insights({ km_prev_month: 80, km_change_pct: 3 })).toEqual([]);
    expect(insights({ km_prev_month: 0, km_change_pct: null })).toEqual([]);
  });
  it("reports heart rate changes of two beats or more", () => {
    expect(insights({ avg_hr_change: -3.2 })).toEqual(["Gennemsnitspulsen er 3 slag lavere end sidste måned."]);
    expect(insights({ avg_hr_change: 2 })).toEqual(["Gennemsnitspulsen er 2 slag højere end sidste måned."]);
    expect(insights({ avg_hr_change: 0.4 })).toEqual([]);
  });
  it("copes with missing data", () => {
    expect(insights(null)).toEqual([]);
    expect(insights({})).toEqual([]);
  });
});

describe("runValueLabel", () => {
  it("shows actual of target in the unit of the target", () => {
    expect(runValueLabel(run({ target_value: 45, actual_value: 47 }))).toBe("47 af 45 min");
    expect(runValueLabel(run({ target_type: "distance", target_value: 10, actual_value: 8.24 }))).toBe("8,2 af 10 km");
  });
  it("shows the target as planned when nothing is matched", () => {
    expect(runValueLabel(run({ target_value: 30, actual_value: null }))).toBe("30 min planlagt");
  });
});
