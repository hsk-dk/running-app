export type Shareable = { user_id: number; name: string; shared: boolean; month_km: number | null };

export type Share = { user_id: number; name: string; km: number; pct: number };

/** Each person's part of the month's kilometres, for one bar. Members who share nothing are left out; order is kept (no ranking). */
export function monthShares(members: Shareable[]): Share[] {
  const shown = members.filter((m) => m.shared && (m.month_km ?? 0) > 0);
  const total = shown.reduce((s, m) => s + (m.month_km ?? 0), 0);
  if (total <= 0) return [];
  return shown.map((m) => ({ user_id: m.user_id, name: m.name, km: m.month_km ?? 0, pct: ((m.month_km ?? 0) / total) * 100 }));
}

/** The week line on a member card: progress against the plan, or the number of runs when there is no plan. */
export function weekText(week: { done: number; total: number } | null, runsThisWeek: number): string {
  if (!week || week.total === 0) {
    if (runsThisWeek === 0) return "Ingen løb endnu";
    return runsThisWeek === 1 ? "1 løb" : `${runsThisWeek} løb`;
  }
  return `${week.done} af ${week.total}`;
}
