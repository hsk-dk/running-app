import { useEffect, useState } from "react";
import { api } from "../api";
import { FIRSTS_SHOWN, pickFirsts } from "../lib/firsts";
import { parseDateKey } from "../lib/week";

type First = { key: string; label: string; date: string; is_new: boolean };
type NextUp = { key: string; label: string; current: number; target: number; unit: string };

const dateText = (d: string) => parseDateKey(d).toLocaleDateString("da-DK", { day: "numeric", month: "short", year: "numeric" });
const num = (v: number) => v.toLocaleString("da-DK", { maximumFractionDigits: 1 });

/** The things you have done for the first time, and what is next. Only ever about you. */
export default function FirstsCard() {
  const [data, setData] = useState<{ achieved: First[]; next: NextUp[] } | null>(null);
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    api.getFirsts().then(setData).catch(() => setData(null)); // a bonus: the page works without it
  }, []);
  if (!data || data.achieved.length === 0) return null;

  const newestFirst = [...data.achieved].reverse();
  const { shown, hidden } = pickFirsts(newestFirst, expanded);
  const many = newestFirst.length > FIRSTS_SHOWN + 1; // a long history: what is next matters more than what was
  const nextUp = data.next.length > 0 && (
    <div style={{ display: "grid", gap: 10, ...(many ? {} : { borderTop: "1px solid var(--color-border)", paddingTop: 12 }) }}>
      <p className="u-card__meta" style={{ margin: 0 }}>Det næste</p>
      {data.next.map((n) => {
        const pct = Math.min(100, Math.round((n.current / n.target) * 100));
        return (
          <div key={n.key} style={{ display: "grid", gap: 4 }}>
            <span style={{ fontWeight: 600 }}>{n.label}</span>
            <div role="progressbar" aria-valuenow={Math.min(n.current, n.target)} aria-valuemin={0} aria-valuemax={n.target} aria-label={`${n.label}: ${num(n.current)} af ${num(n.target)} ${n.unit}`} style={{ height: 10, borderRadius: 5, background: "var(--data-muted)", overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: "var(--data-1)" }} />
            </div>
            <span className="u-card__meta">{num(n.current)} af {num(n.target)} {n.unit}</span>
          </div>
        );
      })}
    </div>
  );

  return (
    <section className="u-card" aria-labelledby="firsts-title" style={{ display: "grid", gap: 12 }}>
      <h2 id="firsts-title" className="u-h2">Dine første gange</h2>
      {many && nextUp}
      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
        {shown.map((a) => (
          <li key={a.key} style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
            <span aria-hidden style={{ color: "var(--data-1)", fontWeight: 700 }}>✓</span>
            <span style={{ fontWeight: 600 }}>{a.label}</span>
            <span className="u-card__meta">{dateText(a.date)}</span>
            {a.is_new && <span className="u-chip u-chip--good">Ny</span>}
          </li>
        ))}
      </ul>
      {(hidden > 0 || expanded) && newestFirst.length > FIRSTS_SHOWN + 1 && (
        <button type="button" className="u-btn u-btn--secondary" style={{ justifySelf: "start" }} aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Vis færre" : `Vis alle ${newestFirst.length}`}
        </button>
      )}
      {!many && nextUp}
    </section>
  );
}
