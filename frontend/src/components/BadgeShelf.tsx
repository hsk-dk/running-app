import { useEffect, useState } from "react";
import { api } from "../api";
import { GROUP_LABEL, GROUP_ORDER, Shelf, compactShelf } from "../lib/rewards";
import { parseDateKey } from "../lib/week";

const dateText = (d: string) => parseDateKey(d).toLocaleDateString("da-DK", { day: "numeric", month: "short", year: "numeric" });

/** Badges you have collected (in colour) and the next ones ahead (grey). Every badge is about you and your own start. */
export default function BadgeShelf({ title = "Mine mærker" }: { title?: string }) {
  const [shelf, setShelf] = useState<Shelf | null>(null);
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    api.getBadges().then(setShelf).catch(() => setShelf(null)); // a bonus: everything else works without it
  }, []);
  if (!shelf) return null;

  const view = compactShelf(shelf, expanded);
  const tile = (b: { key: string; icon: string; title: string }, earned: boolean, note: string, isNew = false) => (
    <li
      key={b.key}
      style={{ display: "grid", justifyItems: "center", gap: 4, textAlign: "center", padding: 10, borderRadius: 12, border: "1px solid var(--color-border)", background: earned ? "var(--color-surface)" : "transparent", opacity: earned ? 1 : 0.55 }}
    >
      <span aria-hidden style={{ fontSize: 34, filter: earned ? "none" : "grayscale(1)" }}>{b.icon}</span>
      <span style={{ fontWeight: 700, fontSize: 14 }}>{b.title}</span>
      <span className="u-card__meta" style={{ fontSize: 12 }}>{note}</span>
      {isNew && <span className="u-chip u-chip--good">Nyt</span>}
    </li>
  );
  const grid: React.CSSProperties = { listStyle: "none", margin: 0, padding: 0, display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(7.5rem, 1fr))", gap: 10 };

  return (
    <section className="u-card" aria-labelledby="badges-title" style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <h2 id="badges-title" className="u-h2">{title}</h2>
        <span className="u-card__meta">{shelf.earned.length} af {shelf.total}</span>
      </div>
      {shelf.earned.length === 0 && <p className="u-card__meta" style={{ margin: 0 }}>Her samler du mærker. Det første kommer, når du har løbet dit første løb eller fået din første stjerne.</p>}

      {!expanded ? (
        <>
          <ul style={grid}>
            {view.earned.map((b) => tile(b, true, dateText(b.date), b.is_new))}
            {view.ahead.map((b) => tile(b, false, b.hint))}
          </ul>
        </>
      ) : (
        GROUP_ORDER.map((g) => {
          const earned = view.earned.filter((b) => b.group === g);
          const ahead = view.ahead.filter((b) => b.group === g);
          if (earned.length + ahead.length === 0) return null;
          return (
            <div key={g} style={{ display: "grid", gap: 8 }}>
              <h3 className="u-h3" style={{ margin: 0 }}>{GROUP_LABEL[g]}</h3>
              <ul style={grid}>
                {earned.map((b) => tile(b, true, dateText(b.date), b.is_new))}
                {ahead.map((b) => tile(b, false, b.hint))}
              </ul>
            </div>
          );
        })
      )}

      {(view.foldedEarned > 0 || expanded) && (
        <button type="button" className="u-btn u-btn--secondary" style={{ justifySelf: "start" }} aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Vis færre" : "Vis alle mærker"}
        </button>
      )}
      {!expanded && view.foldedEarned === 0 && shelf.ahead.length > view.ahead.length && (
        <button type="button" className="u-btn u-btn--secondary" style={{ justifySelf: "start" }} onClick={() => setExpanded(true)}>Se alle mærker</button>
      )}
    </section>
  );
}
