/** The week line on a member card: progress against the plan, or the number of runs when there is no plan. */
export function weekText(week: { done: number; total: number } | null, runsThisWeek: number): string {
  if (!week || week.total === 0) {
    if (runsThisWeek === 0) return "Ingen løb endnu";
    return runsThisWeek === 1 ? "1 løb" : `${runsThisWeek} løb`;
  }
  return `${week.done} af ${week.total}`;
}

export type Guardian = { runs_week: number; active_days_week: number; minutes_week: number; runs_month: number; minutes_month: number; last_run_date: string | null; streak_weeks: number };

const dayDiff = (from: string, today: string) => Math.round((Date.parse(`${today}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86400000);

/** One kind sentence for a parent: encouragement when it goes well, a nudge to ask (not to push) when it has been quiet. */
export function guardianNote(g: Guardian, today: string): string {
  if (!g.last_run_date) return "Ingen løb endnu. Når det første kommer, dukker det op her.";
  const quiet = dayDiff(g.last_run_date, today);
  if (g.runs_week >= 3) return "Tre eller flere gange ude i denne uge. Det er en god uge.";
  if (g.runs_week >= 1) return `Ude ${g.runs_week === 1 ? "1 gang" : `${g.runs_week} gange`} i denne uge. Spørg gerne, hvordan det føles.`;
  if (quiet >= 14) return `Der er gået ${quiet} dage siden sidste løb. Spørg gerne, uden pres, om der er noget, der kan gøre det nemmere at komme i gang igen.`;
  if (quiet >= 7) return `Der er gået ${quiet} dage siden sidste løb. En hilsen eller en tur sammen kan hjælpe.`;
  return "Ikke ude endnu i denne uge. Det er helt normalt at holde pauser.";
}
