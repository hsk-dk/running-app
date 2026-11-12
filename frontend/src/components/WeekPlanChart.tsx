import { ReactNode, useMemo, useState } from "react";
import {
  Activity,
  DayState,
  PlannedRun,
  addDays,
  isoWeekNumber,
  runValueLabel,
  summarizeWeek,
  weekDays,
  weekStartOf,
  weekdayName,
  weekdayShort,
} from "../lib/week";

const W = 760;
const LEFT = 8;
const B = 210; // baseline
const H = 140; // height of a planned frame (100 % of the target)
const MAX_RATIO = 1.35;

type Kind = DayState["kind"];

const STATUS_TEXT: Record<Kind, string> = {
  done: "Gennemført",
  shortened: "Forkortet",
  skipped: "Sprunget over",
  planned: "Planlagt",
  rest: "Hviledag",
};
const STATUS_COLOR: Record<Kind, string> = {
  done: "var(--text-good)",
  shortened: "var(--text-warn)",
  skipped: "var(--text-bad)",
  planned: "var(--color-text-muted)",
  rest: "var(--color-text-muted)",
};

const primaryRun = (d: DayState): PlannedRun | undefined => d.runs.find((r) => !r.optional) ?? d.runs[0];

function rangeLabel(start: Date): string {
  const end = addDays(start, 6);
  // da-DK already puts a full stop after the day number ("9."), so none is added here.
  const fmt = (d: Date, month: boolean) =>
    d.toLocaleDateString("da-DK", month ? { day: "numeric", month: "long" } : { day: "numeric" });
  return start.getMonth() === end.getMonth() ? `${fmt(start, false)}–${fmt(end, true)}` : `${fmt(start, true)} – ${fmt(end, true)}`;
}

/** The week as plan against reality: a dashed frame for what was planned, a filled bar for what was run. */
export default function WeekPlanChart({
  plannedRuns,
  activities,
  today = new Date(),
  badge,
}: {
  plannedRuns: PlannedRun[];
  activities: Activity[];
  today?: Date;
  badge?: ReactNode;
}) {
  const [offset, setOffset] = useState(0);
  const start = useMemo(() => addDays(weekStartOf(today), offset * 7), [today, offset]);
  const days = useMemo(() => weekDays(plannedRuns, activities, start, today), [plannedRuns, activities, start, today]);
  const week = summarizeWeek(days);
  const weekNumber = isoWeekNumber(start);
  const colW = (W - LEFT * 2) / 7;

  const label =
    `Uge ${weekNumber}, ${rangeLabel(start)}. ` +
    days
      .map((d) => {
        const r = primaryRun(d);
        return `${weekdayName(d.weekday)}: ${r ? `${STATUS_TEXT[d.kind].toLowerCase()}, ${runValueLabel(r)}` : "hviledag"}${d.extras.length ? `, ${d.extras.length} ekstra løb` : ""}`;
      })
      .join(". ") + ".";

  return (
    <section className="u-card" aria-labelledby="week-title" style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 id="week-title" className="u-h2" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            Uge {weekNumber}
            {offset === 0 && badge}
          </h2>
          <p className="u-card__meta">
            {rangeLabel(start)} · {week.total === 0 ? "ingen obligatoriske løb" : `${week.done} af ${week.total} obligatoriske løb i hus`}
            {week.shortened > 0 ? `, heraf ${week.shortened} forkortet` : ""}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" className="u-btn u-btn--secondary" onClick={() => setOffset(offset - 1)}>
            ← Forrige uge
          </button>
          <button type="button" className="u-btn u-btn--secondary" onClick={() => setOffset(0)} disabled={offset === 0}>
            I dag
          </button>
          <button type="button" className="u-btn u-btn--secondary" onClick={() => setOffset(offset + 1)}>
            Næste uge →
          </button>
        </div>
      </div>

      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${W} 285`} role="img" aria-label={label} style={{ display: "block", width: "100%", minWidth: 620, height: "auto" }}>
          <line x1={LEFT} y1={B} x2={W - LEFT} y2={B} stroke="var(--color-border-control)" />
          {days.map((d) => {
            const cx = LEFT + d.weekday * colW + colW / 2;
            const run = primaryRun(d);
            const bw = 44;
            const target = run?.target_value ?? 0;
            const ratio = run && run.actual_value != null && target > 0 ? Math.min(run.actual_value / target, MAX_RATIO) : 0;
            const extraMin = Math.round(d.extras.reduce((s, a) => s + a.duration_min, 0));
            const top = run ? B - Math.max(H, ratio * H) : B;
            const shift = d.extras.length > 0 && run ? -26 : 0;
            return (
              <g key={d.date}>
                {run && (
                  <rect x={cx + shift - bw / 2 - 4} y={B - H} width={bw + 8} height={H} rx={6} fill="none" stroke="var(--color-text-muted)" strokeWidth={1.5} strokeDasharray="4 4" />
                )}
                {run && ratio > 0 && (
                  <rect x={cx + shift - bw / 2} y={B - ratio * H} width={bw} height={ratio * H} rx={5} fill="var(--data-1)" opacity={d.kind === "shortened" ? 0.75 : 1} />
                )}
                {run && d.kind === "skipped" && (
                  <text x={cx + shift} y={B - 8} textAnchor="middle" fontSize={16} fontWeight={700} fill="var(--text-bad)">×</text>
                )}
                {run && (
                  <text x={cx + shift} y={top - 8} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--color-text)">
                    {runValueLabel(run)}
                  </text>
                )}
                {d.extras.length > 0 && (
                  <>
                    <rect x={cx + (run ? 26 : 0) - 22} y={B - 0.45 * H} width={44} height={0.45 * H} rx={5} fill="var(--data-fill)" fillOpacity={0.3} stroke="var(--data-1)" strokeWidth={1.5} strokeDasharray="3 3" />
                    <text x={cx + (run ? 26 : 0)} y={B - 0.45 * H - 8} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--color-text)">
                      {extraMin} min
                    </text>
                  </>
                )}
                <text x={cx} y={B + 20} textAnchor="middle" fontSize={12} fontWeight={d.isToday ? 800 : 600} fill="var(--color-text)">
                  {weekdayShort(d.weekday)}
                </text>
                {d.isToday && <rect x={cx - 11} y={B + 24} width={22} height={3} rx={1.5} fill="var(--data-1)" />}
                <text x={cx} y={B + 42} textAnchor="middle" fontSize={11} fontWeight={700} fill={d.kind === "rest" && d.extras.length ? "var(--data-1)" : STATUS_COLOR[d.kind]}>
                  {d.kind === "rest" && d.extras.length ? "Ekstra løb" : STATUS_TEXT[d.kind]}
                </text>
                {run?.optional && (
                  <text x={cx} y={B + 57} textAnchor="middle" fontSize={10} fill="var(--color-text-muted)">valgfri</text>
                )}
              </g>
            );
          })}
          <rect x={W - 190} y={4} width={14} height={10} rx={2} fill="none" stroke="var(--color-text-muted)" strokeDasharray="3 3" />
          <text x={W - 170} y={13} fontSize={11} fill="var(--color-text-muted)">Planlagt</text>
          <rect x={W - 100} y={4} width={14} height={10} rx={2} fill="var(--data-1)" />
          <text x={W - 80} y={13} fontSize={11} fill="var(--color-text-muted)">Løbet</text>
        </svg>
      </div>

      <details>
        <summary style={{ cursor: "pointer", color: "var(--color-action-strong)", fontSize: 14 }}>Vis som tabel</summary>
        <div style={{ overflowX: "auto", marginTop: 8 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--color-text-muted)" }}>
                <th style={{ padding: "6px 8px" }}>Dag</th>
                <th style={{ padding: "6px 8px" }}>Plan og resultat</th>
                <th style={{ padding: "6px 8px" }}>Status</th>
                <th style={{ padding: "6px 8px" }}>Ekstra</th>
              </tr>
            </thead>
            <tbody>
              {days.map((d) => {
                const r = primaryRun(d);
                return (
                  <tr key={d.date} style={{ borderTop: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "6px 8px" }}>{weekdayName(d.weekday)}</td>
                    <td style={{ padding: "6px 8px" }}>{r ? `${r.session_type}, ${runValueLabel(r)}` : "–"}</td>
                    <td style={{ padding: "6px 8px" }}>{STATUS_TEXT[d.kind]}</td>
                    <td style={{ padding: "6px 8px" }}>
                      {d.extras.length ? d.extras.map((a) => `${Math.round(a.duration_min)} min`).join(", ") : "–"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
