import { describe, expect, it } from "vitest";
import { bragText, dayMessage, parentProgressText, planText, progressText, rangeText, unitText } from "./challenge";

const plan = (over = {}) => ({ start_value: 5, step: 1, step_every_days: 7, cap: null, rest_weekdays: [], start_date: "2026-11-02", ...over });

describe("planText", () => {
  it("says the start, the growth and the days off", () => {
    expect(planText(plan(), "stk")).toBe("Start 5 stk., 1 mere hver 7. dag.");
    expect(planText(plan({ step_every_days: 1, step: 2 }), "stk")).toBe("Start 5 stk., 2 mere hver dag.");
    expect(planText(plan({ rest_weekdays: [6, 5] }), "stk")).toBe("Start 5 stk., 1 mere hver 7. dag. Fri lørdag og søndag.");
    expect(planText(plan({ rest_weekdays: [6] }), "sek")).toBe("Start 5 sek., 1 mere hver 7. dag. Fri søndag.");
  });
  it("says so when nothing grows, and when there is a ceiling", () => {
    expect(planText(plan({ step: 0 }), "stk")).toBe("Start 5 stk. Samme mål hver dag.");
    expect(planText(plan({ cap: 30 }), "stk")).toContain("Stopper ved 30 stk.");
    expect(planText(plan({ rest_weekdays: [0, 2, 4] }), "min")).toContain("Fri mandag, onsdag og fredag.");
  });
});

describe("unitText", () => {
  it("abbreviates the three units", () => {
    expect([unitText("stk"), unitText("sek"), unitText("min"), unitText("?")]).toEqual(["stk.", "sek.", "min.", "stk."]);
  });
});

describe("dayMessage", () => {
  const base = { today_target: 10, today_count: null, today_done: false, rest_today: false, not_started: false, streak_days: 0 };
  it("is kind in every case", () => {
    expect(dayMessage({ ...base, not_started: true })).toBe("Starter snart.");
    expect(dayMessage({ ...base, rest_today: true, today_target: null })).toContain("Hvile");
    expect(dayMessage({ ...base, today_done: true, today_count: 10 })).toBe("Dagens mål er klaret. Flot!");
    expect(dayMessage({ ...base, today_done: true, today_count: 14 })).toBe("Du slog dagens mål. Flot!");
    expect(dayMessage({ ...base, today_count: 4 })).toBe("Du er godt i gang: 4 af 10.");
    expect(dayMessage({ ...base, streak_days: 1 })).toBe("1 dag i træk. Hvad bliver det i dag?");
    expect(dayMessage({ ...base, streak_days: 5 })).toBe("5 dage i træk. Hvad bliver det i dag?");
    expect(dayMessage(base)).toBe("Hvad bliver det i dag?");
  });
  it("never uses a word of blame", () => {
    for (const c of [base, { ...base, today_count: 2 }, { ...base, streak_days: 3 }]) expect(dayMessage(c)).not.toMatch(/mangler|fejl|misset|glemt|bagud/i);
  });
});

describe("progressText", () => {
  it("says from where to where and how long, but only when there is progress", () => {
    expect(progressText({ first_count: 5, recent_best: 14, weeks: 4 }, "stk")).toBe("Du er gået fra 5 til 14 stk. på 4 uger.");
    expect(progressText({ first_count: 20, recent_best: 45, weeks: 1 }, "sek")).toBe("Du er gået fra 20 til 45 sek. på 1 uge.");
    expect(progressText({ first_count: 10, recent_best: 10, weeks: 3 }, "stk")).toBe("");
    expect(progressText({ first_count: 10, recent_best: 8, weeks: 3 }, "stk")).toBe(""); // never a "you went down"
    expect(progressText({ first_count: 10, recent_best: null, weeks: 3 }, "stk")).toBe("");
    expect(progressText(null, "stk")).toBe("");
  });
  it("says it for a parent in the third person", () => {
    expect(parentProgressText("Armbøjninger", 5, 14, 4, "stk")).toBe("Armbøjninger: fra 5 til 14 stk. på 4 uger");
    expect(parentProgressText("Planke", null, 14, 4, "sek")).toBe("");
    expect(parentProgressText("Planke", 5, 5, 4, "sek")).toBe("");
  });
});

describe("bragText", () => {
  it("shows the number the person chose to show", () => {
    expect(bragText({ name: "Mads", is_me: false, challenge: "Armbøjninger", unit: "stk", count: 14 })).toBe("Mads: 14 stk. armbøjninger!");
    expect(bragText({ name: "Mads", is_me: true, challenge: "Planke", unit: "sek", count: 60 })).toBe("Du: 60 sek. planke!");
  });
});

describe("rangeText", () => {
  it("is empty without progress or without data", () => {
    expect(rangeText(5, 14, 4, "stk")).toBe("fra 5 til 14 stk. på 4 uger");
    expect(rangeText(5, 5, 4, "stk")).toBe("");
    expect(rangeText(null, 14, 4, "stk")).toBe("");
    expect(rangeText(5, undefined, 4, "stk")).toBe("");
    expect(rangeText(0, 3, 1, "min")).toBe("fra 0 til 3 min. på 1 uge");
  });
});
