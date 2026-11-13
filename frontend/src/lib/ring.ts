/** Geometry for the year ring: every day is a spoke around a circle, its length is the kilometres. Pure. */
import { DayCell } from "./year";

export type Spoke = { date: string; km: number; angle: number; x0: number; y0: number; x1: number; y1: number; length: number; month: number };

export const MONTHS = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];

/** The most recent `count` days laid out clockwise from the top. The longest run reaches the outer radius. */
export function buildRing(days: DayCell[], center: number, inner: number, outer: number, count = 365): { spokes: Spoke[]; capKm: number } {
  const slice = days.slice(-count);
  const capKm = Math.max(5, ...slice.map((d) => d.km)); // a short week should not look like a marathon
  const spokes = slice.map((d, i) => {
    const angle = (i / slice.length) * Math.PI * 2; // 0 = straight up, clockwise
    const length = (Math.min(d.km, capKm) / capKm) * (outer - inner);
    const dx = Math.sin(angle);
    const dy = -Math.cos(angle);
    return {
      date: d.date,
      km: d.km,
      angle,
      length,
      month: Number(d.date.slice(5, 7)) - 1,
      x0: center + dx * inner,
      y0: center + dy * inner,
      x1: center + dx * (inner + length),
      y1: center + dy * (inner + length),
    };
  });
  return { spokes, capKm };
}

/**
 * Where each month starts around the circle, for the labels. A year that starts and ends in the same month
 * would label it twice side by side; only the longer stretch keeps its label.
 */
export function monthMarks(spokes: Spoke[]): { month: number; angle: number }[] {
  const marks: { month: number; angle: number; days: number }[] = [];
  for (const s of spokes) {
    const last = marks[marks.length - 1];
    if (last && last.month === s.month) last.days += 1;
    else marks.push({ month: s.month, angle: s.angle, days: 1 });
  }
  if (marks.length > 1 && marks[0].month === marks[marks.length - 1].month) {
    marks.splice(marks[0].days >= marks[marks.length - 1].days ? marks.length - 1 : 0, 1);
  }
  return marks.map(({ month, angle }) => ({ month, angle }));
}
