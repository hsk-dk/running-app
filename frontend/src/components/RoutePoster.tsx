import { useMemo } from "react";
import { decodePolyline, projectRoute, toPath } from "../lib/route";

const W = 360;
const H = 300;

/** A run drawn as a line over faint contour rings. Falls back to a short note when there is no route. */
export default function RoutePoster({ route, name }: { route: string | null; name: string }) {
  const path = useMemo(() => {
    if (!route) return null;
    const projected = projectRoute(decodePolyline(route), W, H, 28);
    return projected.length < 2 ? null : { d: toPath(projected), start: projected[0], end: projected[projected.length - 1] };
  }, [route]);

  if (!path) {
    return (
      <div className="u-empty" style={{ minHeight: H, display: "grid", placeContent: "center" }}>
        <p className="u-empty__title">Ingen rute</p>
        <p>Dette løb har ingen GPS-rute, fx fordi det er løbet på løbebånd.</p>
      </div>
    );
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Rute for ${name}`} style={{ display: "block", width: "100%", height: "auto" }}>
      {[0.3, 0.5, 0.7, 0.9].map((f) => (
        <ellipse key={f} cx={W * 0.46} cy={H * 0.52} rx={W * f * 0.55} ry={H * f * 0.5} fill="none" stroke="var(--color-border)" strokeWidth={1.2} />
      ))}
      <path d={path.d} fill="none" stroke="var(--data-1)" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={path.start[0]} cy={path.start[1]} r={6} fill="var(--color-text)" />
      <circle cx={path.end[0]} cy={path.end[1]} r={6} fill="var(--color-surface)" stroke="var(--data-1)" strokeWidth={3} />
      <text x={12} y={H - 10} fontSize={11} fill="var(--color-text-muted)">● start  ○ slut</text>
    </svg>
  );
}
