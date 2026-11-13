import { useEffect, useMemo, useState } from "react";
import { Area } from "../lib/areas";
import { prefersReducedMotion, useClock } from "../lib/motion";
import { frameAt, head, partial, timeline } from "../lib/playback";
import { layoutPoster } from "../lib/poster";
import { parseDateKey } from "../lib/week";

const W = 640;
const H = 420;
const toPath = (pts: [number, number][]) => pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");

/** Your runs in one place, played back in date order: each is drawn along its route and stays behind as a glowing trail. */
export default function YearPlayback({ area }: { area: Area }) {
  const layout = useMemo(() => layoutPoster(area.routes, W, H, 28), [area]);
  const tl = useMemo(() => timeline(layout.placed.map((p) => p.route), 16000), [layout]);
  const reduced = useMemo(() => prefersReducedMotion(), []);
  const [playing, setPlaying] = useState(!reduced);
  const [ms, restart] = useClock(tl.totalMs, playing);

  // a different area starts from the beginning
  useEffect(() => {
    restart();
    setPlaying(!reduced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area.key]);

  const byId = useMemo(() => new Map(layout.placed.map((p) => [p.route.id, p])), [layout]);
  const finished = reduced ? tl.totalMs : ms;
  const frame = frameAt(tl, finished);
  const allDone = finished >= tl.totalMs;
  const current = frame.currentId !== null ? byId.get(frame.currentId) : null;
  const partialPts = current ? partial(current.points, frame.fraction) : null;
  const dot = current ? head(current.points, frame.fraction) : null;
  const shownKm = Math.round(
    (allDone ? layout.placed : frame.doneIds.map((id) => byId.get(id)!).filter(Boolean)).reduce((s, p) => s + p.route.distance_km, 0),
  );

  const donePaths = useMemo(() => frame.doneIds.map((id) => toPath(byId.get(id)!.points)), [frame.doneIds.length, byId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (layout.placed.length === 0) return <p className="u-card__meta">Ingen ruter i dette område.</p>;

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Afspilning af ${layout.placed.length} løb i ${area.name} i datoorden`} style={{ display: "block", width: "100%", height: "auto", borderRadius: 12 }}>
        <defs>
          <linearGradient id="pb-bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#3A5F90" />
            <stop offset="1" stopColor="#25405f" />
          </linearGradient>
          <filter id="pb-glow" x="-5%" y="-5%" width="110%" height="110%">
            <feGaussianBlur stdDeviation="3" />
          </filter>
        </defs>
        <rect width={W} height={H} fill="url(#pb-bg)" />
        <g filter="url(#pb-glow)" stroke="#9cc4ff" strokeOpacity={0.14} strokeWidth={5} fill="none" strokeLinecap="round" strokeLinejoin="round">
          {donePaths.map((d, i) => <path key={i} d={d} />)}
        </g>
        <g stroke="#ffffff" strokeOpacity={0.3} strokeWidth={1.4} fill="none" strokeLinecap="round" strokeLinejoin="round">
          {donePaths.map((d, i) => <path key={i} d={d} />)}
        </g>
        {partialPts && partialPts.length > 1 && (
          <path d={toPath(partialPts)} fill="none" stroke="#ffffff" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
        )}
        {dot && (
          <>
            <circle cx={dot[0]} cy={dot[1]} r={9} fill="#9cc4ff" fillOpacity={0.35} />
            <circle cx={dot[0]} cy={dot[1]} r={4.5} fill="#ffffff" />
          </>
        )}
        <text x={20} y={H - 22} fontSize={30} fontWeight={700} fill="#ffffff" fillOpacity={0.92}>
          {frame.date ? parseDateKey(frame.date).toLocaleDateString("da-DK", { day: "numeric", month: "long", year: "numeric" }) : ""}
        </text>
        <text x={W - 20} y={H - 22} fontSize={16} textAnchor="end" fill="#ffffff" fillOpacity={0.8}>
          {allDone ? layout.placed.length : frame.doneIds.length + (current ? 1 : 0)} løb · {shownKm.toLocaleString("da-DK")} km
        </text>
      </svg>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        {allDone ? (
          <button type="button" className="u-btn u-btn--primary" onClick={() => { restart(); setPlaying(true); }}>Afspil igen</button>
        ) : (
          <button type="button" className="u-btn u-btn--secondary" onClick={() => setPlaying((p) => !p)}>{playing ? "Pause" : "Fortsæt"}</button>
        )}
        <span className="u-card__meta">
          {reduced ? "Bevægelse er slået fra, så hele året vises på én gang." : `${area.name}: løbene tegnes i datoorden, og de gamle stier bliver liggende.`}
        </span>
      </div>
    </div>
  );
}
