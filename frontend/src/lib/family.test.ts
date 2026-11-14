import { describe, expect, it } from "vitest";
import { monthShares, weekText } from "./family";

const m = (id: number, name: string, shared: boolean, km: number | null) => ({ user_id: id, name, shared, month_km: km });

describe("monthShares", () => {
  it("splits the month between those who share, keeping the order", () => {
    const s = monthShares([m(1, "Henrik", true, 60), m(2, "Anna", true, 20), m(3, "Cecilie", false, null), m(4, "Bo", true, 20)]);
    expect(s.map((x) => x.name)).toEqual(["Henrik", "Anna", "Bo"]);
    expect(s.map((x) => x.pct)).toEqual([60, 20, 20]);
  });
  it("leaves out people with no kilometres and returns nothing when nobody ran", () => {
    expect(monthShares([m(1, "A", true, 0), m(2, "B", true, null)])).toEqual([]);
    expect(monthShares([m(1, "A", true, 0), m(2, "B", true, 10)]).map((x) => x.name)).toEqual(["B"]);
  });
  it("does not count a private member's kilometres even if they were sent", () => {
    expect(monthShares([m(1, "A", false, 99), m(2, "B", true, 10)])[0].pct).toBe(100);
  });
});

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
