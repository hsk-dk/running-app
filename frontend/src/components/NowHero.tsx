import { useMemo } from "react";
import Sparkline from "./Sparkline";
import WeekRing from "./WeekRing";
import {
  Activity,
  PlannedRun,
  dayLabel,
  insights,
  isoWeekNumber,
  nextRun,
  summarizeWeek,
  weekDays,
  weekHeadline,
  weekStartOf,
} from "../lib/week";

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const fmtKm = (v: number) => v.toLocaleString("da-DK", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** The first screen: one sentence about the week, the week as a ring, the next run, and the month. */
export default function NowHero({
  summary,
  plannedRuns,
  activities,
  monthlyVolume,
  today = new Date(),
}: {
  summary: any;
  plannedRuns: PlannedRun[];
  activities: Activity[];
  monthlyVolume: { month: string; km: number }[];
  today?: Date;
}) {
  const view = useMemo(() => {
    const start = weekStartOf(today);
    const days = weekDays(plannedRuns, activities, start, today);
    const week = summarizeWeek(days);
    const next = nextRun(plannedRuns, today);
    return { days, week, next, headline: weekHeadline(week, next, today), weekNumber: isoWeekNumber(today) };
  }, [plannedRuns, activities, today]);

  const notes = insights(summary);
  const kmNow = Number(summary?.km_this_month ?? 0);
  const kmPrev = Number(summary?.km_prev_month ?? 0);
  const series = monthlyVolume.slice(-12).map((m) => Number(m.km) || 0);
  const monthName = cap(today.toLocaleDateString("da-DK", { month: "long" }));
  const dateLine = `${cap(today.toLocaleDateString("da-DK", { weekday: "long", day: "numeric", month: "long" }))} · uge ${view.weekNumber}`;

  return (
    <section className="now" aria-labelledby="now-title">
      <div className="now__lead">
        <p className="now__eyebrow">{dateLine}</p>
        <h1 id="now-title" className="u-h1">
          {view.headline}
        </h1>
        {notes.length > 0 && (
          <div className="now__notes">
            {notes.map((n) => (
              <p key={n}>{n}</p>
            ))}
          </div>
        )}
      </div>

      <div className="now__ring">
        <WeekRing days={view.days} done={view.week.done} total={view.week.total} weekNumber={view.weekNumber} />
      </div>

      <div className="now__side">
        <div className="u-tile">
          <span className="u-tile__label">Næste løb</span>
          {view.next ? (
            <>
              <span className="u-tile__value" style={{ fontSize: "var(--text-lg)" }}>
                {cap(dayLabel(view.next.planned_date, today))} · {view.next.display_target}
              </span>
              <span className="u-card__meta">{view.next.session_type}{view.next.optional ? " · valgfri" : ""}</span>
            </>
          ) : (
            <span className="u-card__meta">Ingen planlagte løb.</span>
          )}
        </div>

        <div className="u-tile">
          <span className="u-tile__label">{monthName}</span>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 12, flexWrap: "wrap" }}>
            <div>
              <span className="u-tile__value" style={{ fontSize: "var(--text-xl)" }}>{fmtKm(kmNow)} km</span>
              {kmPrev > 0 && <div className="u-card__meta">Hele sidste måned: {fmtKm(kmPrev)} km</div>}
            </div>
            {series.length > 1 && (
              <Sparkline
                values={series}
                label={`Kilometer pr. måned de seneste ${series.length} måneder, fra ${fmtKm(series[0])} til ${fmtKm(series[series.length - 1])} km`}
              />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
