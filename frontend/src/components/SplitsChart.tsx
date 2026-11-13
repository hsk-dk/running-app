import { useEffect, useState } from "react";
import { api } from "../api";
import { Split, barWidths, extremes, paceLabel } from "../lib/splits";

type Splits = { available: boolean; splits: Split[] };

/** Pace per kilometre as horizontal bars. Faster is longer; fastest and slowest are named in words, not just colour. */
export default function SplitsChart({
  activityId,
  load = (id: number) => api.getSplits(id),
}: {
  activityId: number;
  load?: (id: number) => Promise<Splits>;
}) {
  const [data, setData] = useState<Splits | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setFailed(false);
    load(activityId)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activityId]);

  if (failed) return <p className="u-card__meta">Kilometertiderne kunne ikke hentes.</p>;
  if (!data) return <p className="u-card__meta" role="status">Henter kilometertider…</p>;
  if (!data.available) return <p className="u-card__meta">Kilometertiderne kan ikke hentes fra Strava lige nu. Prøv igen senere.</p>;
  if (data.splits.length === 0) return <p className="u-card__meta">Der er ingen kilometertider for dette løb.</p>;

  const widths = barWidths(data.splits);
  const ex = extremes(data.splits);

  return (
    <section aria-labelledby="splits-title" style={{ display: "grid", gap: 8 }}>
      <h3 id="splits-title" className="u-h3">Kilometertider</h3>
      <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 6 }}>
        {data.splits.map((s, i) => {
          const tag = ex && i === ex.fastest ? "hurtigst" : ex && i === ex.slowest ? "langsomst" : null;
          return (
            <li
              key={s.km}
              style={{ display: "grid", gridTemplateColumns: "2.5rem minmax(0, 1fr) 4.5rem", alignItems: "center", gap: 8 }}
            >
              <span className="u-card__meta">{s.partial ? `${(s.distance_m / 1000).toLocaleString("da-DK", { maximumFractionDigits: 2 })}` : s.km}</span>
              <span style={{ display: "block", background: "var(--data-1, #446ea8)", height: 18, borderRadius: 4, width: `${widths[i]}%`, opacity: s.partial ? 0.55 : 1 }} aria-hidden="true" />
              <span style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                {paceLabel(s.pace_s_per_km)}
                {tag && <span className="u-card__meta" style={{ display: "block", fontSize: 12 }}>{tag}</span>}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="u-card__meta">Min/km. Længere streg er hurtigere. Sidste række er den ufuldstændige rest.</p>
    </section>
  );
}
