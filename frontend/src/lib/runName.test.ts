import { describe, expect, it } from "vitest";
import { cleanRunName, shortWeek } from "./runName";

describe("cleanRunName", () => {
  it("drops the plan code and cuts a broken parenthesis", () => {
    expect(cleanRunName("W9 Tue Easy Run - 5km Easy Run (")).toBe("Easy Run · 5km Easy Run");
  });
  it("keeps a town and a complete parenthesis", () => {
    expect(cleanRunName("Herning - W9 Sun Race - 5km Race (5km)")).toBe("Herning · Race · 5km Race (5km)");
  });
  it("leaves ordinary names alone", () => {
    expect(cleanRunName("Morgentur")).toBe("Morgentur");
    expect(cleanRunName("Struer - Run to The Beat 2026")).toBe("Struer · Run to The Beat 2026");
  });
  it("copes with empty names and a name that is only the code", () => {
    expect(cleanRunName(null)).toBe("");
    expect(cleanRunName("W3 Fri ")).toBe("W3 Fri");
  });
});

describe("shortWeek", () => {
  it("shortens an ISO week key", () => {
    expect(shortWeek("2026-W47")).toBe("U47");
    expect(shortWeek("2026-W05")).toBe("U5");
    expect(shortWeek("")).toBe("-");
  });
});
