export type BadgeEarned = { key: string; group: string; icon: string; title: string; description: string; date: string; is_new: boolean };
export type BadgeAhead = { key: string; group: string; icon: string; title: string; hint: string };
export type Shelf = { earned: BadgeEarned[]; ahead: BadgeAhead[]; total: number };

export type StarDay = { date: string; stars: number };
export type StarWeek = { cap: number; earned: number; bonus: number; days: StarDay[] };
export type Reward = {
  id: number;
  name: string;
  cost: number;
  stars: number;
  reached: boolean;
  remaining: number;
  recent: { name: string; cost: number; date: string }[];
  people?: number;
  per_week?: number;
  estimated?: boolean;
  weeks_left?: number | null;
};
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

const dk = (v: number) => v.toLocaleString("da-DK", { maximumFractionDigits: 1 });

/** How long to go at the current pace: "ca. 3 uger", "mindre end en uge", or that it is only a guess so far. */
export const perWeekText = (v: number): string => v.toLocaleString("da-DK", { maximumFractionDigits: 1 });

export function paceText(r: Pick<Reward, "reached" | "per_week" | "estimated" | "weeks_left">): string {
  if (r.reached) return "";
  if (r.weeks_left == null || !r.per_week) return "Der er ikke kommet stjerner endnu, så jeg kan ikke sige, hvornår det bliver.";
  const weeks = r.weeks_left < 1 ? "mindre end en uge" : `ca. ${Math.ceil(r.weeks_left)} ${Math.ceil(r.weeks_left) === 1 ? "uge" : "uger"}`;
  return r.estimated ? `Hvis I får omkring ${dk(r.per_week)} stjerner om ugen, tager det ${weeks}.` : `Med jeres tempo (omkring ${dk(r.per_week)} stjerner om ugen) tager det ${weeks}.`;
}

/** A small cheer on the way, so there is something to enjoy between the rewards. */
export function milestoneText(stars: number, cost: number): string {
  if (cost <= 0) return "";
  const share = stars / cost;
  if (share >= 1) return "";
  if (share >= 0.75) return "Næsten der!";
  if (share >= 0.5) return "Over halvvejs!";
  if (share >= 0.25) return "Godt på vej!";
  return "";
}

export const INTERVAL_WEEKS = [1, 2, 3, 4, 6];

/** What the reward should cost to come about every `weeks` weeks at this pace, never below 5. */
export function suggestCost(perWeek: number, weeks: number): number {
  return Math.max(5, Math.round(perWeek * weeks));
}

/** A rule of thumb in words: a reward for children this age is best every two to three weeks. */
export function intervalNote(weeks: number): string {
  if (weeks <= 1) return "Meget ofte: belønningen mister hurtigt sin værdi, så hold den lille.";
  if (weeks <= 3) return "Et godt tempo: det er tæt nok på til at holde lysten, og det er stadig noget særligt.";
  if (weeks <= 4) return "Lidt længe for de yngste, men fint, hvis belønningen er større.";
  return "Længe at vente. Overvej en lille mellemstation undervejs.";
}
