import { describe, expect, it } from "vitest";
import { chipClass, statusVariant } from "./status";

describe("statusVariant", () => {
  it.each([
    ["gennemført", "good"], ["Grøn", "good"], ["Matchet", "good"],
    ["forkortet", "warn"], ["Gul", "warn"],
    ["sprunget over", "bad"], ["Rød", "bad"], ["Afbrudt", "bad"],
    ["flyttet", "info"], ["Ikke planlagt", "info"], ["Afventer", "info"],
    ["valgfri", "optional"], ["Valgfri", "optional"],
    ["planlagt", "neutral"], ["Manuel", "neutral"],
  ])("%s is %s", (word, variant) => {
    expect(statusVariant(word)).toBe(variant);
  });
  it("ignores case and surrounding spaces, and falls back to neutral", () => {
    expect(statusVariant("  GENNEMFØRT ")).toBe("good");
    expect(statusVariant("noget nyt")).toBe("neutral");
  });
  it("builds class names, with neutral as the plain chip", () => {
    expect(chipClass("neutral")).toBe("u-chip");
    expect(chipClass("warn")).toBe("u-chip u-chip--warn");
  });
});
