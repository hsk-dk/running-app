import { useMemo, useState } from "react";
import { contactSheet } from "../lib/contact";
import { paceLabel } from "../lib/profile";
import { PosterRoute } from "../lib/poster";
import { parseDateKey } from "../lib/week";

const TW = 160;
const TH = 120;

const dateLabel = (d: string | null) => (d ? parseDateKey(d).toLocaleDateString("da-DK", { day: "numeric", month: "short", year: "2-digit" }) : "–");

/** Every route in a tile of its own, each drawing itself. Tap a tile to watch it again. */
export default function ContactSheet({ routes, replayKey }: { routes: PosterRoute[]; replayKey: number }) {
  const tiles = useMemo(() => contactSheet(routes, TW, TH, 14), [routes]);
  const [again, setAgain] = useState<Record<number, number>>({});

  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 12 }}>
      {tiles.map((t, i) => (
        <li key={t.id}>
          <button
            type="button"
            onClick={() => setAgain((a) => ({ ...a, [t.id]: (a[t.id] ?? 0) + 1 }))}
            aria-label={`Rute ${dateLabel(t.date)}, ${t.km.toLocaleString("da-DK", { maximumFractionDigits: 1 })} kilometer. Tryk for at se den tegnes igen.`}
            style={{ display: "block", width: "100%", padding: 0, border: 0, background: "transparent", cursor: "pointer", textAlign: "left", minHeight: 44 }}
          >
            <svg viewBox={`0 0 ${TW} ${TH}`} role="img" aria-hidden="true" style={{ display: "block", width: "100%", height: "auto", borderRadius: 10, background: "linear-gradient(135deg, #3A5F90, #25405f)" }}>
              <g key={`${replayKey}-${again[t.id] ?? 0}`} style={{ ["--delay" as any]: `${Math.min(i, 24) * 90}ms` }}>
                <path className="route-draw route-glow" d={t.d} pathLength={1} fill="none" stroke="#9cc4ff" strokeOpacity={0.35} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" />
                <path className="route-draw" d={t.d} pathLength={1} fill="none" stroke="#ffffff" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
                <circle className="route-dot" cx={t.start[0]} cy={t.start[1]} r={3.2} fill="#ffffff" />
                <circle className="route-dot" cx={t.end[0]} cy={t.end[1]} r={3.2} fill="#25405f" stroke="#ffffff" strokeWidth={1.6} />
              </g>
            </svg>
            <span style={{ display: "block", marginTop: 6, fontSize: 13, lineHeight: 1.3 }}>
              <b>{dateLabel(t.date)}</b> · {t.km.toLocaleString("da-DK", { maximumFractionDigits: 1 })} km
              {t.pace ? <span className="u-card__meta"> · {paceLabel(t.pace)} /km</span> : null}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
