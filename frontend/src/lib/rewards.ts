export type BadgeEarned = { key: string; group: string; icon: string; title: string; description: string; date: string; is_new: boolean };
export type BadgeAhead = { key: string; group: string; icon: string; title: string; hint: string };
export type Shelf = { earned: BadgeEarned[]; ahead: BadgeAhead[]; total: number };

export type StarDay = { date: string; stars: number };
export type StarWeek = { cap: number; earned: number; bonus: number; days: StarDay[] };
export type Reward = { id: number; name: string; cost: number; stars: number; reached: boolean; remaining: number; recent: { name: string; cost: number; date: string }[] };
export type Stars = { total: number; week: StarWeek; reward: Reward | null };

export const GROUP_LABEL: Record<string, string> = { løb: "Løb", udfordring: "Udfordringer", stjerner: "Stjerner" };
export const GROUP_ORDER = ["løb", "udfordring", "stjerner"];

/** The first badge still ahead in each group: what to look forward to, without a wall of grey. */
export function nextPerGroup(ahead: BadgeAhead[]): BadgeAhead[] {
  const seen = new Set<string>();
  const out: BadgeAhead[] = [];
  for (const b of ahead) {
    if (!seen.has(b.group)) {
      seen.add(b.group);
      out.push(b);
    }
  }
  return out.sort((a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group));
}

/** The compact shelf: the newest few earned and the next one ahead in each group. Expanded: everything. */
export function compactShelf(shelf: Shelf, expanded: boolean, earnedShown = 3): { earned: BadgeEarned[]; ahead: BadgeAhead[]; foldedEarned: number } {
  if (expanded) return { earned: shelf.earned, ahead: shelf.ahead, foldedEarned: 0 };
  const earned = shelf.earned.filter((b, i) => i < earnedShown || b.is_new);
  return { earned, ahead: nextPerGroup(shelf.ahead), foldedEarned: shelf.earned.length - earned.length };
}

/** The five (or so) slots of the week: a filled star for each earned, an empty ring for the rest, never more slots than the cap. */
export function starSlots(week: StarWeek): { filled: number; empty: number; extra: number } {
  const total = week.earned + week.bonus;
  const filled = Math.min(total, week.cap);
  return { filled, empty: Math.max(0, week.cap - filled), extra: Math.max(0, total - week.cap) };
}

/** What the family reads about the reward: "12 af 40 stjerner til Biograftur", or that it can be given. */
export function rewardText(r: Pick<Reward, "name" | "cost" | "stars" | "reached" | "remaining">): string {
  if (r.reached) return `${r.name}: målet er nået! Spørg en forælder.`;
  return `${r.stars} af ${r.cost} stjerner til ${r.name}. ${r.remaining === 1 ? "Der mangler 1 stjerne." : `Der mangler ${r.remaining}.`}`;
}
