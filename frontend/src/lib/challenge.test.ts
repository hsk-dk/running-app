import { describe, expect, it } from "vitest";
import { dayMessage, planText, unitText } from "./challenge";

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
