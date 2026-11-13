/** Total distance over time, with the moments worth marking. Pure. */
export const MILESTONES = [50, 100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000];

export type Point = { date: string; total: number };

export function cumulative(activities: { date: string | null; distance_km: number }[]): Point[] {
  const sorted = activities.filter((a) => a.date).sort((a, b) => (a.date! < b.date! ? -1 : a.date! > b.date! ? 1 : 0));
  let total = 0;
  const out: Point[] = [];
  for (const a of sorted) {
    total += a.distance_km;
    out.push({ date: a.date!, total: Math.round(total * 10) / 10 });
  }
  return out;
}

/** The first day each milestone was passed. */
export function reached(points: Point[]): { km: number; date: string }[] {
  const out: { km: number; date: string }[] = [];
  for (const km of MILESTONES) {
    const hit = points.find((p) => p.total >= km);
    if (hit) out.push({ km, date: hit.date });
  }
  return out;
}

export function nextMilestone(totalKm: number): { km: number; remaining: number } | null {
  const km = MILESTONES.find((m) => m > totalKm);
  return km ? { km, remaining: Math.round((km - totalKm) * 10) / 10 } : null;
}

export const MARATHON_KM = 42.195;

/** Everyday comparisons. Distances are rough ("ca.") and labelled that way on screen. */
export const COMPARISONS = [
  { label: "København til Aarhus (ca. 300 km)", km: 300 },
  { label: "Caminoen, Camino Francés (ca. 780 km)", km: 780 },
];

export function comparisons(totalKm: number): { label: string; share: number }[] {
  return COMPARISONS.map((c) => ({ label: c.label, share: totalKm / c.km }));
}

export const marathons = (totalKm: number) => Math.round((totalKm / MARATHON_KM) * 10) / 10;
