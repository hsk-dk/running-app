import { useEffect, useMemo, useState } from "react";
import { COMPARISONS, comparisons, cumulative, marathons, nextMilestone, reached } from "../lib/milestones";
import { thinLabels, useWidth } from "../lib/useWidth";
import { Activity, parseDateKey } from "../lib/week";

const H = 240;
const PAD = { l: 14, r: 14, t: 30, b: 28 };
const LIMIT = 500;

const fmt = (v: number, d = 0) => v.toLocaleString("da-DK", { minimumFractionDigits: d, maximumFractionDigits: d });
const month = (date: string) => parseDateKey(date).toLocaleDateString("da-DK", { month: "short", year: "numeric" });

/** Counts up to the target, unless the person has asked for less motion. */
function useCountUp(target: number, ms = 900): number {
  const [value, setValue] = useState(target);
  useEffect(() => {
    if (typeof window === "undefined" || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setValue(target);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      setValue(target * (1 - Math.pow(1 - t, 3)));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, ms]);
  return value;
}

/** All the kilometres, adding up over time, with a mark each time a round number was passed. */
export default function MilestoneCard({ activities }: { activities: Activity[] }) {
  const [box, W] = useWidth<HTMLDivElement>();
  const points = useMemo(() => cumulative(activities), [activities]);
  const total = points.length ? points[points.length - 1].total : 0;
  const shown = useCountUp(total);
  const marks = useMemo(() => reached(points), [points]);
  const next = nextMilestone(total);

  if (points.length < 2) return null;

  const first = parseDateKey(points[0].date).getTime();
  const last = parseDateKey(points[points.length - 1].date).getTime();
  const x = (date: string) => PAD.l + ((parseDateKey(date).getTime() - first) / (last - first || 1)) * (W - PAD.l - PAD.r);
  const y = (v: number) => H - PAD.b - (v / (total || 1)) * (H - PAD.t - PAD.b);
  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.date).toFixed(1)} ${y(p.total).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points[points.length - 1].date).toFixed(1)} ${y(0)} L${x(points[0].date).toFixed(1)} ${y(0)} Z`;

  return (
    <section className="u-card" aria-labelledby="mile-title" style={{ display: "grid", gap: 12 }}>
      <div>
        <p className="now__eyebrow">Samlet distance</p>
        <h2 id="mile-title" className="u-h1" aria-label={`${fmt(total)} kilometer i alt`}>
          {fmt(shown)} km
        </h2>
        <p className="u-card__meta">Det svarer til {fmt(marathons(total), 1)} maratonløb.</p>
      </div>

      <div ref={box}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Kurve over samlet distance fra ${month(points[0].date)} til ${month(points[points.length - 1].date)}, i alt ${fmt(total)} kilometer.`} style={{ display: "block", width: "100%", height: "auto" }}>
        <path d={area} fill="var(--data-1)" fillOpacity={0.14} />
        <path d={line} fill="none" stroke="var(--data-1)" strokeWidth={3} strokeLinejoin="round" strokeLinecap="round" />
        {marks.map((m, i) => {
          const labelled = thinLabels(marks.map((k) => x(k.date)), 56)[i];
          return (
          <g key={m.km}>
            <line x1={x(m.date)} x2={x(m.date)} y1={y(m.km)} y2={H - PAD.b} stroke="var(--data-1)" strokeOpacity={0.4} strokeDasharray="3 4" />
            <circle cx={x(m.date)} cy={y(m.km)} r={6} fill="var(--color-surface)" stroke="var(--data-1)" strokeWidth={3} />
            {labelled && (
              <text x={Math.min(Math.max(x(m.date), 28), W - 28)} y={y(m.km) - 12} textAnchor="middle" fontSize={12} fontWeight={600} fill="var(--color-text)">
                {fmt(m.km)} km
              </text>
            )}
          </g>
          );
        })}
        <text x={PAD.l} y={H - 8} fontSize={11} fill="var(--color-text-muted)">{month(points[0].date)}</text>
        <text x={W - PAD.r} y={H - 8} textAnchor="end" fontSize={11} fill="var(--color-text-muted)">{month(points[points.length - 1].date)}</text>
      </svg>
      </div>

      {next && (
        <div>
          <p className="u-card__meta">Næste mærke: {fmt(next.km)} km, om {fmt(next.remaining, 1)} km.</p>
          <div role="progressbar" aria-valuemin={0} aria-valuemax={next.km} aria-valuenow={Math.round(total)} aria-label={`På vej mod ${fmt(next.km)} kilometer`} style={{ height: 10, borderRadius: 6, background: "var(--data-muted)", overflow: "hidden", marginTop: 6 }}>
            <div style={{ width: `${Math.min(100, (total / next.km) * 100)}%`, height: "100%", background: "var(--data-1)" }} />
          </div>
        </div>
      )}

      <ul className="u-card__meta" style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 4 }}>
        {comparisons(total).map((c, i) => (
          <li key={COMPARISONS[i].label}>
            {c.share >= 1 ? `${fmt(c.share, 1)} gange ` : `${fmt(c.share * 100)} % af `}
            {c.label}
          </li>
        ))}
      </ul>
      {activities.length >= LIMIT && <p className="u-card__meta">Tæller de seneste {LIMIT} løb. Ældre løb er ikke med.</p>}
    </section>
  );
}
