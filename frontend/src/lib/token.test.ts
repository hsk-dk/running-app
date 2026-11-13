import { describe, expect, it } from "vitest";
import { daysLeft, tokenNotice } from "./token";

const NOON = new Date("2026-11-13T12:00:00");

describe("daysLeft", () => {
  it("counts whole days including the last day", () => {
    expect(daysLeft("2026-11-13", NOON)).toBe(1);
    expect(daysLeft("2026-11-20", NOON)).toBe(8);
  });
  it("is null when there is no usable date", () => {
    expect(daysLeft(null, NOON)).toBeNull();
    expect(daysLeft("not a date", NOON)).toBeNull();
  });
});

describe("tokenNotice", () => {
  it("says nothing for an app connection, no connection, or plenty of time", () => {
    expect(tokenNotice(undefined, NOON)).toBeNull();
    expect(tokenNotice({ mode: "oauth", expires_at: null }, NOON)).toBeNull();
    expect(tokenNotice({ mode: "token", expires_at: "2027-01-31" }, NOON)).toBeNull();
  });
  it("warns in the last two weeks and errors when expired", () => {
    expect(tokenNotice({ mode: "token", expires_at: "2026-11-20" }, NOON)).toMatchObject({ level: "warning" });
    expect(tokenNotice({ mode: "token", expires_at: "2026-11-13" }, NOON)?.text).toMatch(/1 dag/);
    expect(tokenNotice({ mode: "token", expires_at: "2026-11-01", expired: true }, NOON)).toMatchObject({ level: "error" });
  });
});
