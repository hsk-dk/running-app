export type ChallengePlan = { start_value: number; step: number; step_every_days: number; cap: number | null; rest_weekdays: number[]; start_date: string };
export type ChallengeDay = { date: string; target: number | null; count: number | null; status: string };
export type ChallengeProgress = { first_count: number; recent_best: number | null; weeks: number };
export type ChallengeHistoryDay = { date: string; target: number | null; count: number | null };
export type Challenge = {
  id: number;
  name: string;
  unit: string;
  today_target: number | null;
  today_count: number | null;
  today_done: boolean;
  rest_today: boolean;
  not_started: boolean;
  streak_days: number;
  done_week: number;
  planned_week: number;
  best_day: number;
  new_best_today: boolean;
  shared_today: boolean;
  progress: ChallengeProgress | null;
  history: ChallengeHistoryDay[];
  total: number;
  week: ChallengeDay[];
  plan: ChallengePlan;
};

export const WEEKDAY_NAMES = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"];
export const WEEKDAY_SHORT = ["M", "T", "O", "T", "F", "L", "S"];

export const unitText = (unit: string): string => (unit === "sek" ? "sek." : unit === "min" ? "min." : "stk.");

/** The plan in words: "Start 5 stk., 1 mere hver 7. dag. Fri lørdag og søndag." */
export function planText(plan: ChallengePlan, unit: string): string {
  const u = unitText(unit);
  const end = (t: string) => (t.endsWith(".") ? t : `${t}.`);
  let text = `Start ${plan.start_value} ${u}`;
  if (plan.step > 0) text += `, ${plan.step} mere hver ${plan.step_every_days === 1 ? "" : `${plan.step_every_days}. `}dag`;
  text = end(text);
  if (plan.step === 0) text += " Samme mål hver dag.";
  if (plan.cap) text += ` ${end(`Stopper ved ${plan.cap} ${u}`)}`;
  if (plan.rest_weekdays.length > 0) text += ` Fri ${listWords([...plan.rest_weekdays].sort((a, b) => a - b).map((d) => WEEKDAY_NAMES[d]))}.`;
  return text;
}

function listWords(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} og ${items[items.length - 1]}`;
}

/** What to say about the day: encouraging, never reproachful. */
export function dayMessage(c: Pick<Challenge, "today_target" | "today_count" | "today_done" | "rest_today" | "not_started" | "streak_days">): string {
  if (c.not_started) return "Starter snart.";
  if (c.rest_today) return "Fridag i dag. Hvile er en del af planen.";
  if (c.today_done) return c.today_count !== null && c.today_target !== null && c.today_count > c.today_target ? "Du slog dagens mål. Flot!" : "Dagens mål er klaret. Flot!";
  if (c.today_count && c.today_target) return `Du er godt i gang: ${c.today_count} af ${c.today_target}.`;
  return c.streak_days > 0 ? `${c.streak_days} ${c.streak_days === 1 ? "dag" : "dage"} i træk. Hvad bliver det i dag?` : "Hvad bliver det i dag?";
}

const weeksText = (w: number) => `${w} ${w === 1 ? "uge" : "uger"}`;

/** "fra 5 til 14 stk. på 4 uger", or "" when there is no progress to speak of (never a "you went down"). */
export function rangeText(first: number | null | undefined, best: number | null | undefined, weeks: number | null | undefined, unit: string): string {
  if (first == null || best == null || weeks == null || best <= first) return "";
  return `fra ${first} til ${best} ${unitText(unit)} på ${weeksText(weeks)}`;
}

/** "Du er gået fra 5 til 14 stk. på 4 uger." */
export function progressText(p: ChallengeProgress | null, unit: string): string {
  const r = p ? rangeText(p.first_count, p.recent_best, p.weeks, unit) : "";
  return r ? `Du er gået ${r}.` : "";
}

/** The same for a parent, in the third person. */
export function parentProgressText(name: string, firstCount: number | null, recentBest: number | null, weeks: number | null, unit: string): string {
  const r = rangeText(firstCount, recentBest, weeks, unit);
  return r ? `${name}: ${r}` : "";
}

export type Brag = { user_id: number; name: string; is_me: boolean; challenge: string; unit: string; count: number; date: string };

/** What the family reads when someone chose to show off: "Mads: 14 stk. Armbøjninger!" */
export function bragText(b: Pick<Brag, "name" | "is_me" | "challenge" | "unit" | "count">): string {
  return `${b.is_me ? "Du" : b.name}: ${b.count} ${unitText(b.unit)} ${b.challenge.charAt(0).toLowerCase()}${b.challenge.slice(1)}!`;
}
