import { describe, expect, it } from "vitest";
import { pickFirsts } from "./firsts";

const items = (n: number, isNew: number[] = []) => Array.from({ length: n }, (_, i) => ({ key: `k${i}`, is_new: isNew.includes(i) }));
const keys = (l: { key: string }[]) => l.map((x) => x.key);

describe("pickFirsts", () => {
  it("shows everything when there are few", () => {
    expect(pickFirsts(items(3), false)).toEqual({ shown: items(3), hidden: 0 });
    expect(pickFirsts(items(0), false)).toEqual({ shown: [], hidden: 0 });
    expect(pickFirsts(items(4), false).hidden).toBe(0);
  });
  it("does not fold away a single item", () => {
    expect(pickFirsts(items(5), false)).toEqual({ shown: items(5), hidden: 0 });
  });
  it("shows the newest four and says how many are folded when there are many", () => {
    const r = pickFirsts(items(16), false);
    expect(keys(r.shown)).toEqual(["k0", "k1", "k2", "k3"]);
    expect(r.hidden).toBe(12);
    expect(pickFirsts(items(6), false).hidden).toBe(2);
  });
  it("always keeps what is new, even far down, in order", () => {
    const r = pickFirsts(items(16, [9]), false);
    expect(keys(r.shown)).toEqual(["k0", "k1", "k2", "k3", "k9"]);
    expect(r.hidden).toBe(11);
  });
  it("shows everything when asked to", () => {
    expect(pickFirsts(items(16), true)).toEqual({ shown: items(16), hidden: 0 });
  });
  it("takes another limit", () => {
    expect(pickFirsts(items(10), false, 2).shown).toHaveLength(2);
  });
});
