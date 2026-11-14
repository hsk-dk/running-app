/** Hands a picture to the person: the phone's share sheet when it can take a file, otherwise a download. */
export type ShareEnv = {
  nav?: { share?: (data: any) => Promise<void>; canShare?: (data: any) => boolean };
  doc?: { createElement: (tag: string) => any; body: { appendChild: (n: any) => any; removeChild: (n: any) => any } };
  url?: { createObjectURL: (b: Blob) => string; revokeObjectURL: (u: string) => void };
  file?: (parts: Blob[], name: string, opts: { type: string }) => any;
};

export type Delivery = "shared" | "downloaded" | "cancelled";

const defaultEnv = (): ShareEnv => ({
  nav: typeof navigator !== "undefined" ? (navigator as any) : undefined,
  doc: typeof document !== "undefined" ? (document as any) : undefined,
  url: typeof URL !== "undefined" ? URL : undefined,
  file: typeof File !== "undefined" ? (parts, name, opts) => new File(parts, name, opts) : undefined,
});

export function canShareFiles(blob: Blob, name: string, env: ShareEnv = defaultEnv()): boolean {
  if (!env.nav?.share || !env.nav.canShare || !env.file) return false;
  try {
    return env.nav.canShare({ files: [env.file([blob], name, { type: blob.type || "image/png" })] });
  } catch {
    return false;
  }
}

/** Shares the picture if the device can, else downloads it. Closing the share sheet is not an error. */
export async function deliverImage(blob: Blob, name: string, title: string, env: ShareEnv = defaultEnv()): Promise<Delivery> {
  if (canShareFiles(blob, name, env)) {
    try {
      await env.nav!.share!({ files: [env.file!([blob], name, { type: blob.type || "image/png" })], title });
      return "shared";
    } catch (e: any) {
      if (e && e.name === "AbortError") return "cancelled";
      // any other failure: fall through to the download
    }
  }
  if (!env.doc || !env.url) throw new Error("Kan ikke gemme billedet i denne browser.");
  const href = env.url.createObjectURL(blob);
  const a = env.doc.createElement("a");
  a.href = href;
  a.download = name;
  env.doc.body.appendChild(a);
  a.click();
  env.doc.body.removeChild(a);
  setTimeout(() => env.url!.revokeObjectURL(href), 10000);
  return "downloaded";
}

/** A safe file name from a title: "De seneste 12 måneder" becomes "de-seneste-12-maaneder". */
export function fileSafe(title: string): string {
  const map: Record<string, string> = { æ: "ae", ø: "oe", å: "aa" };
  const s = title.toLowerCase().replace(/[æøå]/g, (c) => map[c]).replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return s || "billede";
}
