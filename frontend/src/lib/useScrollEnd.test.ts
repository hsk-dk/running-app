import { describe, expect, it } from "vitest";
import { niceMax } from "./useScrollEnd";

describe("niceMax", () => {
  it("fits the data without a lot of empty space", () => {
    expect(niceMax(21)).toEqual({ max: 30, step: 10 });
    expect(niceMax(62)).toEqual({ max: 80, step: 20 });
    expect(niceMax(3)).toEqual({ max: 20, step: 5 });
    expect(niceMax(100, 100)).toEqual({ max: 100, step: 25 });
  });
});
