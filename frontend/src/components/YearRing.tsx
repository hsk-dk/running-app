import { useMemo } from "react";
import { Other, otherDays } from "../lib/other";
import { useWidth } from "../lib/useWidth";
import { MONTHS, buildRing, monthMarks } from "../lib/ring";
import { Activity, parseDateKey } from "../lib/week";
import { buildDays, monthlyTotals, weeklyTotals, yearFacts } from "../lib/year";

const SIZE = 460;
const C = SIZE / 2;
const INNER = 78;
const OUTER = 196;

const km = (v: number, d = 0) => v.toLocaleString("da-DK", { minimumFractionDigits: d, maximumFractionDigits: d });

/** The last twelve months as a ring: one spoke a day, as long as the run. Busy seasons and pauses form a pattern. */
export default function YearRing({ activities, others = [], today = new Date() }: { activities: Activity[]; others?: Other[]; today?: Date }) {
  const otherSet = useMemo(() => otherDays(others), [others]);
  const [box, px] = useWidth<HTMLDivElement>(520);
  // The ring is drawn in a 460-unit box that shrinks on a phone; grow the text by the same factor so it stays readable.
  const grow = Math.max(1, SIZE / Math.min(px, 520));
  const { ring, facts, topMonth } = useMemo(() => {
    const days = buildDays(activities, today);
    const weeks = weeklyTotals(days);
    const months = monthlyTotals(days);
    const top = months.reduce<{ key: string; km: number } | null>((best, m) => (!best || m.km > best.km ? m : best), null);
    return { ring: buildRing(days, C, INNER, OUTER), facts: yearFacts(days, weeks, activities), topMonth: top };
  }, [activities, today]);
  const marks = useMemo(() => monthMarks(ring.spokes), [ring]);

  return (
    <section className="u-card" aria-labelledby="ring-title" style={{ display: "grid", gap: 12 }}>
      <h2 id="ring-title" className="u-h2">Årsringen</h2>
      <p className="u-card__meta">
        Hver streg er en dag, med uret fra øverst. Jo længere streg, jo længere løb.
        {otherSet.size > 0 ? " De små prikker på den indre ring er dage med anden træning: roning, gang, cykling og andet." : ""}
      </p>
      <div ref={box}>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={`Årsring over de seneste 12 måneder: ${km(facts.totalKm)} kilometer fordelt på ${facts.runDays} løbedage.`}
        style={{ display: "block", width: "100%", maxWidth: 520, height: "auto", margin: "0 auto" }}
      >
        <circle cx={C} cy={C} r={INNER - 6} fill="none" stroke="var(--color-border)" strokeWidth={1.5} />
        <circle cx={C} cy={C} r={OUTER + 4} fill="none" stroke="var(--color-border)" strokeWidth={1} strokeDasharray="2 5" />
        {ring.spokes.map((s, i) =>
          s.km > 0 ? (
            <line
              key={s.date}
              className="ring-spoke"
              style={{ ["--len" as any]: s.length, ["--i" as any]: i }}
              x1={s.x0}
              y1={s.y0}
              x2={s.x1}
              y2={s.y1}
              stroke="var(--data-1)"
              strokeWidth={2.6}
              strokeLinecap="round"
            >
              <title>{`${parseDateKey(s.date).toLocaleDateString("da-DK", { day: "numeric", month: "long" })}: ${km(s.km, 1)} km`}</title>
            </line>
          ) : null,
        )}
        {ring.spokes.map((s) =>
          otherSet.has(s.date) ? (
            <circle key={`o-${s.date}`} cx={C + Math.sin(s.angle) * (INNER - 6)} cy={C - Math.cos(s.angle) * (INNER - 6)} r={2.4} fill="var(--data-1)" opacity={0.5}>
              <title>{`${parseDateKey(s.date).toLocaleDateString("da-DK", { day: "numeric", month: "long" })}: anden træning`}</title>
            </circle>
          ) : null,
        )}
        {marks.map((m) => {
          const r = Math.min(OUTER + 18 * Math.min(grow, 1.4), 216);
          return (
            <text
              key={`${m.month}-${m.angle}`}
              x={C + Math.sin(m.angle) * r}
              y={C - Math.cos(m.angle) * r}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={Math.round(11 * grow)}
              fill="var(--color-text-muted)"
            >
              {MONTHS[m.month]}
            </text>
          );
        })}
        <text x={C} y={C - 4} textAnchor="middle" fontSize={Math.round(36 * Math.min(grow, 1.3))} fontWeight={700} fill="var(--color-text)">
          {km(facts.totalKm)}
        </text>
        <text x={C} y={C + 20 * Math.min(grow, 1.3)} textAnchor="middle" fontSize={Math.round(11 * Math.min(grow, 1.3))} fill="var(--color-text-muted)">
          km · seneste 12 mdr
        </text>
        <text x={C} y={C + 38 * Math.min(grow, 1.3)} textAnchor="middle" fontSize={Math.round(11 * Math.min(grow, 1.3))} fill="var(--color-text-muted)">
          {facts.runDays} løbedage
        </text>
      </svg>
      </div>
      <p className="u-card__meta">
        {facts.longestRun && `Længste løb: ${km(facts.longestRun.km, 1)} km. `}
        {topMonth && topMonth.km > 0 && `Travleste måned: ${MONTHS[Number(topMonth.key.slice(5, 7)) - 1]} med ${km(topMonth.km)} km.`}
      </p>
    </section>
  );
}
