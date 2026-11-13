import { describe, expect, it } from "vitest";
import { thinLabels } from "./useWidth";

describe("thinLabels", () => {
  it("drops a label that would sit on top of the previous one", () => {
    expect(thinLabels([10, 40, 80, 100, 200], 54)).toEqual([true, false, true, false, true]);
  });
  it("keeps everything that is far enough apart, and copes with nothing", () => {
    expect(thinLabels([0, 60, 120], 54)).toEqual([true, true, true]);
    expect(thinLabels([], 54)).toEqual([]);
  });
});
