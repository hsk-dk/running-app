import { useEffect, useState } from "react";
import { api } from "../api";
import { useMe } from "../lib/meContext";
import { Stars, countsNote, milestoneText, paceText, rewardText, starSlots, starsNote } from "../lib/rewards";

/** This week's stars and the family's reward. A star is for effort (an active day, a challenge day), never for speed or distance. */
export default function StarsCard({ onLoaded }: { onLoaded?: (s: Stars) => void }) {
  const { isChild } = useMe();
  const [data, setData] = useState<Stars | null>(null);
  useEffect(() => {
    api.getStars().then((s: Stars) => {
      setData(s);
      onLoaded?.(s);
    }).catch(() => setData(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  if (!data) return null;
  const slots = starSlots(data.week);
  const r = data.reward;

  return (
    <section className="u-card" aria-labelledby="stars-title" style={{ display: "grid", gap: 10 }}>
      <h2 id="stars-title" className="u-h2">Stjerner</h2>
      <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }} role="img" aria-label={`${slots.filled} af ${data.week.cap} stjerner denne uge${slots.extra ? `, og ${slots.extra} ekstra` : ""}`}>
        {Array.from({ length: slots.filled }).map((_, i) => <span key={`f${i}`} aria-hidden style={{ fontSize: 30 }}>⭐</span>)}
        {Array.from({ length: slots.empty }).map((_, i) => (
          <span key={`e${i}`} aria-hidden style={{ width: 28, height: 28, borderRadius: 14, border: "2px dashed var(--color-border-control)", display: "inline-block" }} />
        ))}
        {slots.extra > 0 && <span className="u-chip u-chip--good">+{slots.extra} bonus</span>}
      </div>
      <p className="u-card__meta" style={{ margin: 0, ...(slots.filled >= data.week.cap ? { fontWeight: 700, color: "var(--color-text)" } : {}) }}>{starsNote(slots.filled + slots.extra, data.week.cap, isChild)}</p>
      {r && (
        <div style={{ display: "grid", gap: 6, borderTop: "1px solid var(--color-border)", paddingTop: 10 }}>
          <p style={{ margin: 0, fontWeight: 600 }}>{r.name}</p>
          <div role="progressbar" aria-valuenow={Math.min(r.stars, r.cost)} aria-valuemin={0} aria-valuemax={r.cost} aria-label={`${r.stars} af ${r.cost} stjerner til ${r.name}`} style={{ height: 16, borderRadius: 8, background: "var(--data-muted)", overflow: "hidden" }}>
            <div style={{ width: `${Math.min(100, Math.round((r.stars / r.cost) * 100))}%`, height: "100%", background: "var(--data-1)" }} />
          </div>
          <p className="u-card__meta" style={{ margin: 0 }}>{rewardText(r)} {milestoneText(r.stars, r.cost)}</p>
          {paceText(r) && <p className="u-card__meta" style={{ margin: 0 }}>{paceText(r)}</p>}
          <p className="u-card__meta" style={{ margin: 0 }}>{countsNote(r.counts)}</p>
        </div>
      )}
    </section>
  );
}
