import { describe, expect, it } from "vitest";
import { weekText } from "./family";

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
