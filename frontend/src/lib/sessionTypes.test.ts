import { describe, expect, it } from "vitest";
import { SESSION_TYPES, sessionTypeOptions } from "./sessionTypes";

describe("session types", () => {
  it("offers every type the importers and the AI can produce", () => {
    expect(SESSION_TYPES.map((t) => t.value)).toEqual(["easy", "long", "tempo", "intervals", "recovery", "race"]);
  });
  it("keeps an unknown current value selectable instead of silently replacing it", () => {
    expect(sessionTypeOptions("easy")).toHaveLength(6);
    expect(sessionTypeOptions("hills").at(-1)).toEqual({ value: "hills", label: "hills" });
  });
});
