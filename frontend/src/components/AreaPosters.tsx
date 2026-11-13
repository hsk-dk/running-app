import { useMemo } from "react";
import { Area } from "../lib/areas";
import { buildPoster } from "../lib/poster";

const W = 320;
const H = 240;

function AreaPoster({ area, onPlay }: { area: Area; onPlay: (key: string) => void }) {
  const poster = useMemo(() => buildPoster(area.routes, W, H, 18), [area]);
  return (
    <section aria-labelledby={`${area.key}-title`} style={{ display: "grid", gap: 8 }}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${poster.used} løb i ${area.name}, lagt oven i hinanden. De stier, du løber oftest, er lysest.`} style={{ display: "block", width: "100%", height: "auto", borderRadius: 12 }}>
        <defs>
          <linearGradient id={`${area.key}-bg`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#3A5F90" />
            <stop offset="1" stopColor="#25405f" />
          </linearGradient>
          <filter id={`${area.key}-glow`} x="-5%" y="-5%" width="110%" height="110%">
            <feGaussianBlur stdDeviation="2.5" />
          </filter>
        </defs>
        <rect width={W} height={H} fill={`url(#${area.key}-bg)`} />
        <g filter={`url(#${area.key}-glow)`} stroke="#9cc4ff" strokeOpacity={0.2} strokeWidth={4.5} fill="none" strokeLinecap="round" strokeLinejoin="round">
          {poster.paths.map((d, i) => <path key={i} d={d} />)}
        </g>
        <g stroke="#ffffff" strokeOpacity={0.4} strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round">
          {poster.paths.map((d, i) => <path key={i} d={d} />)}
        </g>
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <div>
          <h3 id={`${area.key}-title`} className="u-h3">{area.name}</h3>
          <p className="u-card__meta">
            {poster.used} løb · {poster.totalKm.toLocaleString("da-DK", { maximumFractionDigits: 0 })} km
          </p>
        </div>
        <button type="button" className="u-btn u-btn--secondary" onClick={() => onPlay(area.key)}>Afspil</button>
      </div>
    </section>
  );
}

/** One map per place you run, so the paths you repeat glow even when you run in several towns. */
export default function AreaPosters({ areas, onPlay }: { areas: Area[]; onPlay: (key: string) => void }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 280px), 1fr))", gap: 20 }}>
      {areas.map((a) => (
        <AreaPoster key={a.key} area={a} onPlay={onPlay} />
      ))}
    </div>
  );
}
