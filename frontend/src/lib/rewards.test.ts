import { describe, expect, it } from "vitest";
import { Shelf, compactShelf, nextPerGroup, rewardText, starSlots } from "./rewards";

const e = (key: string, isNew = false) => ({ key, group: "løb", icon: "🏃", title: key, description: "", date: "2026-11-01", is_new: isNew });
const a = (key: string, group: string) => ({ key, group, icon: "⭐", title: key, hint: "" });

describe("nextPerGroup", () => {
  it("picks the first one ahead in each group, in a steady order", () => {
    const got = nextPerGroup([a("km_15", "løb"), a("km_21", "løb"), a("stars_10", "stjerner"), a("challenge_7", "udfordring")]);
    expect(got.map((b) => b.key)).toEqual(["km_15", "challenge_7", "stars_10"]);
    expect(nextPerGroup([])).toEqual([]);
  });
});

describe("compactShelf", () => {
  const shelf: Shelf = { earned: ["a", "b", "c", "d", "e", "f"].map((k) => e(k)), ahead: [a("x", "løb"), a("y", "løb"), a("z", "stjerner")], total: 9 };
  it("shows the newest three earned and the next one in each group", () => {
    const c = compactShelf(shelf, false);
    expect(c.earned.map((b) => b.key)).toEqual(["a", "b", "c"]);
    expect(c.ahead.map((b) => b.key)).toEqual(["x", "z"]);
    expect(c.foldedEarned).toBe(3);
  });
  it("keeps what is new, even when it is far down", () => {
    const withNew: Shelf = { ...shelf, earned: ["a", "b", "c", "d", "e", "f"].map((k) => e(k, k === "e")) };
    expect(compactShelf(withNew, false).earned.map((b) => b.key)).toEqual(["a", "b", "c", "e"]);
  });
  it("shows everything when expanded", () => {
    const c = compactShelf(shelf, true);
    expect(c.earned).toHaveLength(6);
    expect(c.ahead).toHaveLength(3);
    expect(c.foldedEarned).toBe(0);
  });
  it("shows a short shelf whole", () => {
    expect(compactShelf({ earned: [e("a")], ahead: [], total: 1 }, false)).toEqual({ earned: [e("a")], ahead: [], foldedEarned: 0 });
  });
});

describe("starSlots", () => {
  const week = (earned: number, bonus: number) => ({ cap: 5, earned, bonus, days: [] });
  it("fills the week's slots and shows the rest as empty rings", () => {
    expect(starSlots(week(2, 0))).toEqual({ filled: 2, empty: 3, extra: 0 });
    expect(starSlots(week(0, 0))).toEqual({ filled: 0, empty: 5, extra: 0 });
  });
  it("counts a bonus star and shows anything over the slots as extra", () => {
    expect(starSlots(week(3, 1))).toEqual({ filled: 4, empty: 1, extra: 0 });
    expect(starSlots(week(5, 2))).toEqual({ filled: 5, empty: 0, extra: 2 });
  });
});

describe("rewardText", () => {
  it("says how far there is to go, in the singular too, and when it is reached", () => {
    expect(rewardText({ name: "Biograftur", cost: 40, stars: 12, reached: false, remaining: 28 })).toBe("12 af 40 stjerner til Biograftur. Der mangler 28.");
    expect(rewardText({ name: "Biograftur", cost: 40, stars: 39, reached: false, remaining: 1 })).toBe("39 af 40 stjerner til Biograftur. Der mangler 1 stjerne.");
    expect(rewardText({ name: "Biograftur", cost: 40, stars: 40, reached: true, remaining: 0 })).toBe("Biograftur: målet er nået! Spørg en forælder.");
  });
});
