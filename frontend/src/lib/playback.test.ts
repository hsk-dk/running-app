import { describe, expect, it } from "vitest";
import { frameAt, head, partial, timeline } from "./playback";
import { PosterRoute } from "./poster";

const r = (id: number, date: string, km = 5): PosterRoute => ({ id, date, distance_km: km, route: "" });

describe("timeline", () => {
  it("plays the oldest run first and fills the whole time", () => {
    const tl = timeline([r(2, "2026-06-01"), r(1, "2026-05-01"), r(3, "2026-07-01")], 9000);
    expect(tl.slots.map((s) => s.id)).toEqual([1, 2, 3]);
    expect(tl.slots[0].startMs).toBe(0);
    expect(tl.totalMs).toBeCloseTo(9000, 0);
    expect(tl.slots.every((s, i) => i === 0 || s.startMs === tl.slots[i - 1].endMs)).toBe(true);
  });
  it("gives longer runs more time, but far from in proportion", () => {
    const tl = timeline([r(1, "2026-05-01", 5), r(2, "2026-05-02", 42)], 10000);
    const [a, b] = tl.slots.map((s) => s.endMs - s.startMs);
    expect(b).toBeGreaterThan(a);
    expect(b / a).toBeLessThan(4);
  });
  it("never goes below a readable minimum per run, and copes with none", () => {
    const many = Array.from({ length: 100 }, (_, i) => r(i, `2026-01-${String((i % 28) + 1).padStart(2, "0")}`));
    const tl = timeline(many, 1000);
    expect(tl.slots.every((s) => s.endMs - s.startMs >= 350)).toBe(true);
    expect(timeline([], 5000)).toEqual({ slots: [], totalMs: 0 });
  });
});

describe("frameAt", () => {
  const tl = timeline([r(1, "2026-05-01"), r(2, "2026-06-01")], 2000);
  it("is empty before the start and complete after the end", () => {
    expect(frameAt(tl, 0)).toMatchObject({ doneIds: [], currentId: 1, fraction: 0 });
    expect(frameAt(tl, 99999)).toMatchObject({ doneIds: [1, 2], currentId: null, date: "2026-06-01" });
  });
  it("draws the current run part of the way and keeps finished ones", () => {
    const f = frameAt(tl, 1500);
    expect(f.doneIds).toEqual([1]);
    expect(f.currentId).toBe(2);
    expect(f.fraction).toBeGreaterThan(0.4);
    expect(f.date).toBe("2026-06-01");
  });
});

describe("partial", () => {
  const line: [number, number][] = [[0, 0], [10, 0], [10, 10]];
  it("cuts the route at a share of its length, ending exactly there", () => {
    expect(partial(line, 0.5)).toEqual([[0, 0], [10, 0]]);
    expect(partial(line, 0.25)).toEqual([[0, 0], [5, 0]]);
    expect(partial(line, 0.75)).toEqual([[0, 0], [10, 0], [10, 5]]);
  });
  it("handles the ends and degenerate routes", () => {
    expect(partial(line, 0)).toEqual([[0, 0]]);
    expect(partial(line, 1)).toBe(line);
    expect(partial([[1, 1]], 0.5)).toEqual([[1, 1]]);
    expect(head(line, 0.5)).toEqual([10, 0]);
  });
});
