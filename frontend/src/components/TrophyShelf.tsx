import { useMemo } from "react";
import { newRecords, records } from "../lib/records";
import { Activity } from "../lib/week";

/** Your personal bests in one place, with a mark on those set this week. */
export default function TrophyShelf({ activities, today = new Date() }: { activities: Activity[]; today?: Date }) {
  const { list, fresh } = useMemo(() => ({ list: records(activities), fresh: new Set(newRecords(activities, today).map((r) => r.key)) }), [activities, today]);
  if (list.length === 0) return null;
  return (
    <section className="u-card" aria-labelledby="trophy-title" style={{ display: "grid", gap: 12 }}>
      <h2 id="trophy-title" className="u-h2">Dine rekorder</h2>
      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 12rem), 1fr))", gap: 12 }}>
        {list.map((r) => (
          <li key={r.key} style={{ border: "1px solid var(--color-border)", borderRadius: 12, padding: 12, display: "grid", gap: 4, background: "var(--color-surface)" }}>
            <span className="u-card__meta">{r.label}</span>
            <span style={{ fontSize: 24, fontWeight: 700 }}>{r.value}</span>
            <span className="u-card__meta">{r.detail}</span>
            {fresh.has(r.key) && <span className="u-chip u-chip--good" style={{ justifySelf: "start" }}>Ny denne uge</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}
