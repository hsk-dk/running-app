/** The week line on a member card: progress against the plan, or the number of runs when there is no plan. */
export function weekText(week: { done: number; total: number } | null, runsThisWeek: number): string {
  if (!week || week.total === 0) {
    if (runsThisWeek === 0) return "Ingen løb endnu";
    return runsThisWeek === 1 ? "1 løb" : `${runsThisWeek} løb`;
  }
  return `${week.done} af ${week.total}`;
}
