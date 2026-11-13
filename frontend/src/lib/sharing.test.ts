import { describe, expect, it } from "vitest";
import { SHARING_LEVELS, levelLabel } from "./sharing";

describe("sharing levels", () => {
  it("has the three levels the server knows, private first", () => {
    expect(SHARING_LEVELS.map((l) => l.key)).toEqual(["private", "overview", "all"]);
  });
  it("describes what is NOT shared at the lower levels", () => {
    const text = Object.fromEntries(SHARING_LEVELS.map((l) => [l.key, l.summary]));
    expect(text.overview).toMatch(/Ingen ruter, tider eller puls/);
    expect(text.all).toMatch(/Pulsen deles ikke/);
  });
  it("labels levels and passes unknown ones through", () => {
    expect(levelLabel("overview")).toBe("Overblik");
    expect(levelLabel("custom")).toBe("custom");
  });
});
