/** Days left of a personal Smashrun token, or null when it does not run out (or we do not know). */
export function daysLeft(expiresAt: string | null | undefined, today: Date = new Date()): number | null {
  if (!expiresAt) return null;
  const end = new Date(`${expiresAt}T23:59:59`);
  if (Number.isNaN(end.getTime())) return null;
  return Math.ceil((end.getTime() - today.getTime()) / 86_400_000);
}

export const WARN_DAYS = 14;

/** What to tell the person about their personal token: nothing, a warning, or that it has run out. */
export function tokenNotice(
  s: { mode?: string | null; expires_at?: string | null; expired?: boolean } | undefined,
  today: Date = new Date(),
): { level: "warning" | "error"; text: string } | null {
  if (!s || s.mode !== "token") return null;
  if (s.expired) return { level: "error", text: "Dit Smashrun-token er udløbet, så der hentes ingen nye løb. Indsæt et nyt." };
  const days = daysLeft(s.expires_at, today);
  if (days !== null && days <= WARN_DAYS) {
    return { level: "warning", text: `Dit Smashrun-token udløber om ${Math.max(days, 0)} ${days === 1 ? "dag" : "dage"}. Indsæt et nyt, før det sker.` };
  }
  return null;
}
