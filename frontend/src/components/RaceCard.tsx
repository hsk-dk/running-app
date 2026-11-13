import { useMemo } from "react";
import { useWidth } from "../lib/useWidth";
import { clock, daysUntil, estimate, findRace, paceOf, parseTargetRange } from "../lib/race";
import { Activity, PlannedRun, parseDateKey } from "../lib/week";


function raceKm(run: PlannedRun): number | null {
  if (run.target_type === "distance" && run.target_value) return run.target_value;
  const m = /(\d+(?:[.,]\d+)?)\s*km/i.exec(run.notes ?? "");
  return m ? Number(m[1].replace(",", ".")) : null;
}

const when = (n: number) => (n === 0 ? "I dag" : n === 1 ? "I morgen" : `Om ${n} dage`);

/** The next planned race: the goal from the plan next to what recent runs, scaled to the distance, point to. */
export default function RaceCard({ activities, plannedRuns, today = new Date() }: { activities: Activity[]; plannedRuns: PlannedRun[]; today?: Date }) {
  const [box, W] = useWidth<HTMLDivElement>(600);
  const race = useMemo(() => findRace(plannedRuns, today), [plannedRuns, today]);
  const km = race ? raceKm(race) : null;
  const goal = race ? parseTargetRange(race.notes) : null;
  const est = useMemo(() => (km ? estimate(activities, km, today) : null), [activities, km, today]);

  if (!race || !km) return null;

  // One time axis for everything we want to show, with a little room at both ends.
  const values = [goal?.lowSec, goal?.highSec, est?.fastSec, est?.typicalSec].filter((v): v is number => typeof v === "number");
  const lo = values.length ? Math.min(...values) * 0.96 : 0;
  const hi = values.length ? Math.max(...values) * 1.04 : 1;
  const x = (sec: number) => 20 + ((sec - lo) / (hi - lo || 1)) * (W - 40);
  const days = daysUntil(race.planned_date, today);
  const date = parseDateKey(race.planned_date).toLocaleDateString("da-DK", { weekday: "long", day: "numeric", month: "long" });
  const H = 164;

  return (
    <section className="u-card" aria-labelledby="race-title" style={{ display: "grid", gap: 12 }}>
      <div>
        <p className="now__eyebrow">{when(days)}</p>
        <h2 id="race-title" className="u-h2">{km.toLocaleString("da-DK")} km-løb, {date}</h2>
      </div>

      <div ref={box}>
      {values.length === 0 ? (
        <p className="u-card__meta">Der er ikke løb nok de seneste otte uger til at give et skøn, og planen oplyser ikke et mål.</p>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Tidsakse med Runnas mål og skøn ud fra dine seneste løb" style={{ display: "block", width: "100%", height: "auto" }}>
          <line x1={20} x2={W - 20} y1={70} y2={70} stroke="var(--color-border)" strokeWidth={2} />
          {goal && (
            <g>
              <rect x={x(goal.lowSec)} y={52} width={Math.max(4, x(goal.highSec) - x(goal.lowSec))} height={36} rx={6} fill="var(--data-2)" fillOpacity={0.22} stroke="var(--data-2)" strokeWidth={2} />
              <text x={Math.min(Math.max((x(goal.lowSec) + x(goal.highSec)) / 2, 70), W - 70)} y={44} textAnchor="middle" fontSize={13} fontWeight={600} fill="var(--data-2)">
                Mål {clock(goal.lowSec)}–{clock(goal.highSec)}
              </text>
            </g>
          )}
          {est && (
            <>
              <g>
                <path d={`M ${x(est.fastSec)} 58 l 8 14 h -16 z`} fill="var(--data-1)" />
                <text x={Math.min(Math.max(x(est.fastSec), 34), W - 34)} y={102} textAnchor="middle" fontSize={13} fill="var(--color-text)">▲ {clock(est.fastSec)}</text>
                <text x={Math.min(Math.max(x(est.fastSec), 34), W - 34)} y={118} textAnchor="middle" fontSize={12} fill="var(--color-text-muted)">hurtigst</text>
              </g>
              {Math.abs(est.typicalSec - est.fastSec) > 1 && (
                <g>
                  <circle cx={x(est.typicalSec)} cy={66} r={7} fill="var(--data-1)" />
                  <text x={Math.min(Math.max(x(est.typicalSec), 34), W - 34)} y={Math.abs(x(est.typicalSec) - x(est.fastSec)) < 70 ? 136 : 102} textAnchor="middle" fontSize={13} fill="var(--color-text)">● {clock(est.typicalSec)}</text>
                  <text x={Math.min(Math.max(x(est.typicalSec), 34), W - 34)} y={Math.abs(x(est.typicalSec) - x(est.fastSec)) < 70 ? 152 : 118} textAnchor="middle" fontSize={12} fill="var(--color-text-muted)">typisk</text>
                </g>
              )}
            </>
          )}
        </svg>
      )}
      </div>

      <ul className="u-card__meta" style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 4 }}>
        {goal && <li>Planens mål: {clock(goal.lowSec)} til {clock(goal.highSec)} ({paceOf(goal.lowSec, km)} til {paceOf(goal.highSec, km)} pr. km).</li>}
        {est && (
          <li>
            Dine {est.runs} seneste løb på mindst {Math.max(3, km * 0.6).toLocaleString("da-DK", { maximumFractionDigits: 1 })} km, regnet om til {km.toLocaleString("da-DK")} km, peger på{" "}
            {clock(est.fastSec)}{Math.abs(est.typicalSec - est.fastSec) > 1 ? ` til ${clock(est.typicalSec)}` : ""}.
          </li>
        )}
        {goal && est && est.fastSec > goal.highSec && (
          <li>Målet er hurtigere end dine træningsløb viser. Et løb køres typisk hårdere end træning, så skønnet er forsigtigt.</li>
        )}
        {goal && est && est.fastSec <= goal.highSec && <li>Dit hurtigste løb peger ind mod målet.</li>}
      </ul>
      <p className="u-card__meta">Et skøn efter Riegels formel, ikke en garanti. Dagsform, bane og vejr betyder mere.</p>
    </section>
  );
}
