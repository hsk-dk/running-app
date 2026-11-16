import { describe, expect, it } from "vitest";
import { COUNTS_LABEL, INTERVAL_WEEKS, Shelf, countsNote, starsNote, whatsNew, perWeekText, compactShelf, intervalNote, milestoneText, nextPerGroup, paceText, rewardText, starSlots, suggestCost } from "./rewards";

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

describe("paceText", () => {
  const r = (over = {}) => ({ reached: false, per_week: 7, estimated: false, weeks_left: 2.2, ...over });
  it("says how long, rounding up, with the measured pace", () => {
    expect(paceText(r())).toBe("Med jeres tempo (omkring 7 stjerner om ugen) tager det ca. 3 uger.");
    expect(paceText(r({ weeks_left: 1 }))).toBe("Med jeres tempo (omkring 7 stjerner om ugen) tager det ca. 1 uge.");
    expect(paceText(r({ weeks_left: 0.4 }))).toContain("mindre end en uge");
  });
  it("is honest that it is only a guess when nothing has been measured", () => {
    expect(paceText(r({ estimated: true, per_week: 9 }))).toBe("Hvis I får omkring 9 stjerner om ugen, tager det ca. 3 uger.");
  });
  it("says nothing when it is reached, and admits it when nothing is earned", () => {
    expect(paceText(r({ reached: true }))).toBe("");
    expect(paceText(r({ weeks_left: null, per_week: 0 }))).toContain("ikke kommet stjerner");
  });
});

describe("decimals are Danish", () => {
  it("writes a comma and at most one decimal", () => {
    expect(perWeekText(4.5)).toBe("4,5");
    expect(perWeekText(7)).toBe("7");
    expect(perWeekText(2.04)).toBe("2");
  });
  it("uses the comma in the sentence about the pace", () => {
    expect(paceText({ reached: false, per_week: 4.5, estimated: false, weeks_left: 4.2 })).toBe("Med jeres tempo (omkring 4,5 stjerner om ugen) tager det ca. 5 uger.");
  });
});

describe("milestoneText", () => {
  it("cheers at a quarter, a half and three quarters, and not at the start or the end", () => {
    expect([0, 5, 10, 20, 30, 39, 40].map((s) => milestoneText(s, 40))).toEqual(["", "", "Godt på vej!", "Over halvvejs!", "Næsten der!", "Næsten der!", ""]);
    expect(milestoneText(5, 0)).toBe("");
  });
});

describe("suggestCost and intervalNote", () => {
  it("scales with the pace and the wait, never below five", () => {
    expect(suggestCost(9, 3)).toBe(27);
    expect(suggestCost(7.5, 2)).toBe(15);
    expect(suggestCost(0.5, 1)).toBe(5);
    expect(INTERVAL_WEEKS).toEqual([1, 2, 3, 4, 6]);
  });
  it("advises on how often", () => {
    expect(intervalNote(1)).toContain("mister hurtigt");
    expect(intervalNote(2)).toContain("godt tempo");
    expect(intervalNote(3)).toContain("godt tempo");
    expect(intervalNote(4)).toContain("Lidt længe");
    expect(intervalNote(6)).toContain("mellemstation");
  });
});

describe("countsNote", () => {
  it("says whose stars fill the bar", () => {
    expect(countsNote("children")).toContain("børnenes stjerner");
    expect(countsNote(undefined)).toContain("børnenes stjerner");
    expect(countsNote("all")).toContain("Alle i familien");
    expect(Object.keys(COUNTS_LABEL)).toEqual(["children", "all"]);
  });
});

describe("starsNote", () => {
  it("cheers when every star of the week is there, instead of saying 'at most'", () => {
    expect(starsNote(5, 5, true)).toBe("🎉 Alle ugens stjerner! Flot arbejde.");
    expect(starsNote(6, 5, false)).toContain("Alle ugens stjerner");
  });
  it("says what a star is for, shorter for a child, and what there is so far", () => {
    expect(starsNote(0, 5, true)).toBe("Ingen stjerner endnu denne uge. En stjerne for hver dag, du er aktiv i 15 minutter, og hver dag, du klarer din udfordring.");
    expect(starsNote(1, 5, false)).toBe("1 stjerne denne uge. En stjerne for hver dag, du er aktiv i mindst 15 minutter, og hver dag, du klarer din udfordring.");
    expect(starsNote(3, 5, true)).toContain("3 stjerner denne uge.");
    expect(starsNote(3, 5, true)).not.toMatch(/højst|forsvinder/);
  });
});

describe("whatsNew", () => {
  it("is nothing the first time, so a new user is not showered with old news", () => {
    expect(whatsNew(null, { stars: 12, badges: ["a", "b"] })).toEqual({ stars: 0, badges: [] });
  });
  it("is what has been added since", () => {
    expect(whatsNew({ stars: 3, badges: ["a"] }, { stars: 5, badges: ["a", "b", "c"] })).toEqual({ stars: 2, badges: ["b", "c"] });
    expect(whatsNew({ stars: 3, badges: ["a"] }, { stars: 3, badges: ["a"] })).toEqual({ stars: 0, badges: [] });
  });
  it("never reports fewer stars", () => {
    expect(whatsNew({ stars: 9, badges: [] }, { stars: 4, badges: [] }).stars).toBe(0);
  });
});
