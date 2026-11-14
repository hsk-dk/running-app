import { describe, expect, it, vi } from "vitest";
import { canShareFiles, deliverImage, fileSafe } from "./shareImage";

const blob = { type: "image/png" } as Blob;
const file = (parts: Blob[], name: string) => ({ name, parts });

function env(over: any = {}) {
  const link: any = { click: vi.fn() };
  const body = { appendChild: vi.fn(), removeChild: vi.fn() };
  return {
    link,
    body,
    e: {
      nav: undefined,
      doc: { createElement: vi.fn(() => link), body },
      url: { createObjectURL: vi.fn(() => "blob:x"), revokeObjectURL: vi.fn() },
      file,
      ...over,
    },
  };
}

describe("deliverImage", () => {
  it("shares the file when the device can share files", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    const { e } = env({ nav: { share, canShare: () => true } });
    expect(await deliverImage(blob, "a.png", "Titel", e)).toBe("shared");
    expect(share).toHaveBeenCalledTimes(1);
    expect(share.mock.calls[0][0].files[0].name).toBe("a.png");
    expect(share.mock.calls[0][0].title).toBe("Titel");
  });
  it("downloads when sharing files is not possible", async () => {
    const { e, link, body } = env({ nav: { share: vi.fn(), canShare: () => false } });
    expect(await deliverImage(blob, "a.png", "T", e)).toBe("downloaded");
    expect(link.download).toBe("a.png");
    expect(link.href).toBe("blob:x");
    expect(link.click).toHaveBeenCalledTimes(1);
    expect(body.appendChild).toHaveBeenCalled();
    expect(body.removeChild).toHaveBeenCalled();
  });
  it("downloads when there is no share at all, or canShare throws", async () => {
    expect(await deliverImage(blob, "a.png", "T", env().e)).toBe("downloaded");
    const { e } = env({ nav: { share: vi.fn(), canShare: () => { throw new Error("x"); } } });
    expect(await deliverImage(blob, "a.png", "T", e)).toBe("downloaded");
  });
  it("treats closing the share sheet as cancelled, and does not download", async () => {
    const abort = Object.assign(new Error("closed"), { name: "AbortError" });
    const { e, link } = env({ nav: { share: vi.fn().mockRejectedValue(abort), canShare: () => true } });
    expect(await deliverImage(blob, "a.png", "T", e)).toBe("cancelled");
    expect(link.click).not.toHaveBeenCalled();
  });
  it("falls back to a download when sharing fails for another reason", async () => {
    const { e, link } = env({ nav: { share: vi.fn().mockRejectedValue(new Error("nope")), canShare: () => true } });
    expect(await deliverImage(blob, "a.png", "T", e)).toBe("downloaded");
    expect(link.click).toHaveBeenCalledTimes(1);
  });
  it("says so when nothing can be done", async () => {
    await expect(deliverImage(blob, "a.png", "T", { nav: undefined, doc: undefined, url: undefined, file })).rejects.toThrow("Kan ikke gemme");
  });
});

describe("canShareFiles / fileSafe", () => {
  it("needs share, canShare and a file constructor", () => {
    expect(canShareFiles(blob, "a.png", { nav: { share: vi.fn() }, file })).toBe(false);
    expect(canShareFiles(blob, "a.png", { nav: { share: vi.fn(), canShare: () => true } })).toBe(false);
  });
  it("makes a plain file name", () => {
    expect(fileSafe("De seneste 12 måneder")).toBe("de-seneste-12-maaneder");
    expect(fileSafe("2026")).toBe("2026");
    expect(fileSafe("  ---  ")).toBe("billede");
  });
});
