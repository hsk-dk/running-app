export type FirstItem = { key: string; label: string; date: string; is_new: boolean };

/** How many to show before folding the rest away. Someone who started in 2008 has a long list; a beginner has a short one. */
export const FIRSTS_SHOWN = 4;

/**
 * The achievements to show, newest first. When there are many, only the newest few (and anything marked new) are shown,
 * and the rest is folded away: hiding a single one would be silly, so a list that is just a little over the limit is shown whole.
 */
export function pickFirsts<T extends { is_new: boolean }>(newestFirst: T[], expanded: boolean, limit = FIRSTS_SHOWN): { shown: T[]; hidden: number } {
  if (expanded || newestFirst.length <= limit + 1) return { shown: newestFirst, hidden: 0 };
  const shown = newestFirst.filter((item, i) => i < limit || item.is_new);
  return { shown, hidden: newestFirst.length - shown.length };
}
