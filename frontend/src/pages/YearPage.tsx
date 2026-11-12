import FormChart from "../components/FormChart";
import MonthBars from "../components/MonthBars";
import YearHeatmap from "../components/YearHeatmap";
import { Activity, isoWeekNumber, parseDateKey } from "../lib/week";
import { baseChange, buildDays, completeWeeks, monthlyTotals, weeklyTotals, yearFacts } from "../lib/year";

const LIMIT = 500; // the app fetches at most this many runs; older ones are missing from the calendar
const MONTH_NAMES = ["januar", "februar", "marts", "april", "maj", "juni", "juli", "august", "september", "oktober", "november", "december"];

const km = (v: number, d = 1) => v.toLocaleString("da-DK", { minimumFractionDigits: d, maximumFractionDigits: d });

export default function YearPage({ activities, today = new Date() }: { activities: Activity[]; today?: Date }) {
  const days = buildDays(activities, today);
  const weeks = weeklyTotals(days);
  const facts = yearFacts(days, weeks, activities);
  const months = monthlyTotals(days);
  const last26 = completeWeeks(weeks, today).slice(-26);
  const base = baseChange(last26.map((w) => w.km));
  const incomplete = activities.length >= LIMIT;

  const headline =
    facts.runDays === 0
      ? "Ingen løb de seneste 12 måneder."
      : `${km(facts.totalKm, 0)} km på ${facts.runDays} dage de seneste 12 måneder.`;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <p className="now__eyebrow">År</p>
        <h1 className="u-h1">{headline}</h1>
      </section>

      {incomplete && (
        <div className="u-notice u-notice--warning" role="status">
          <b className="u-notice__level">Ufuldstændig</b>
          <span>Siden viser de seneste {LIMIT} løb. Ældre løb mangler i kalenderen.</span>
        </div>
      )}

      <section className="u-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 12rem), 1fr))" }}>
        <div className="u-tile">
          <span className="u-tile__label">Længste løb</span>
          <span className="u-tile__value">{facts.longestRun ? `${km(facts.longestRun.km)} km` : "–"}</span>
          {facts.longestRun && <span className="u-card__meta">{new Date(facts.longestRun.date).toLocaleDateString("da-DK", { day: "numeric", month: "long" })}</span>}
        </div>
        <div className="u-tile">
          <span className="u-tile__label">Travleste uge</span>
          <span className="u-tile__value">{facts.busiestWeek ? `${km(facts.busiestWeek.km)} km` : "–"}</span>
          {facts.busiestWeek && <span className="u-card__meta">uge {isoWeekNumber(parseDateKey(facts.busiestWeek.weekStart))}</span>}
        </div>
        <div className="u-tile">
          <span className="u-tile__label">Uger i træk med løb</span>
          <span className="u-tile__value">{facts.longestWeekStreak}</span>
          <span className="u-card__meta">længste stime</span>
        </div>
        <div className="u-tile">
          <span className="u-tile__label">Dage med løb</span>
          <span className="u-tile__value">{facts.runDays}</span>
          <span className="u-card__meta">af {days.length} dage</span>
        </div>
      </section>

      <section className="u-card" style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 12 }}>
        <h2 className="u-h2">Kalender</h2>
        <YearHeatmap
          days={days}
          label={`Kalender over de seneste 12 måneder: ${km(facts.totalKm, 0)} km på ${facts.runDays} løbedage. Se tabellen under måned for måned for tallene.`}
        />
      </section>

      <section className="u-card" style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 12 }}>
        <h2 className="u-h2">Måned for måned</h2>
        <MonthBars months={months} />
        <p className="u-card__meta">Den første og den seneste måned kan være ufuldstændige.</p>
        <details>
          <summary style={{ cursor: "pointer", color: "var(--color-action-strong)", fontSize: 14 }}>Vis som tabel</summary>
          <table style={{ width: "100%", maxWidth: 420, borderCollapse: "collapse", fontSize: 14, marginTop: 8 }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--color-text-muted)" }}>
                <th style={{ padding: "6px 8px" }}>Måned</th>
                <th style={{ padding: "6px 8px" }}>Kilometer</th>
              </tr>
            </thead>
            <tbody>
              {months.map((m) => (
                <tr key={m.key} style={{ borderTop: "1px solid var(--color-border)" }}>
                  <td style={{ padding: "6px 8px" }}>{MONTH_NAMES[Number(m.key.slice(5)) - 1]} {m.key.slice(0, 4)}</td>
                  <td style={{ padding: "6px 8px" }}>{km(m.km)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </section>

      {last26.length >= 8 && (
        <section className="u-card" style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 12 }}>
          <h2 className="u-h2">
            {base ? (
              <>
                Din base er <span style={{ color: "var(--data-1)" }}>{Math.abs(base.pct)} % {base.pct > 0 ? "højere" : "lavere"}</span> end for {base.weeks} uger siden.
              </>
            ) : (
              "Form"
            )}
          </h2>
          <FormChart weeklyKm={last26.map((w) => w.km)} firstWeekLabel={(i) => `u${isoWeekNumber(parseDateKey(last26[i].weekStart))}`} />
          <p className="u-card__meta">Kun afsluttede uger er med.</p>
        </section>
      )}
    </div>
  );
}
