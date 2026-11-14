import { describe, expect, it } from "vitest";
import { MIN_RUN_KM, isRun } from "./runs";

describe("isRun", () => {
  it("counts a kilometre and more, and not a warm-up or an aborted recording", () => {
    expect(MIN_RUN_KM).toBe(1);
    expect(isRun({ distance_km: 1 })).toBe(true);
    expect(isRun({ distance_km: 0.99 })).toBe(false);
    expect(isRun({ distance_km: 0.714 })).toBe(false);
    expect(isRun({ distance_km: 0 })).toBe(false);
  });
});
