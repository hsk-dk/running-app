import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { PosterRoute, buildPoster } from "../lib/poster";
import { addDays, dateKey } from "../lib/week";

const W = 640;
const H = 480;

/** Every route laid over every other: the paths run most often glow brightest. */
export default function RoutesPoster({ today = new Date() }: { today?: Date }) {
  const [routes, setRoutes] = useState<PosterRoute[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<"all" | "year">("all");

  useEffect(() => {
    api.getRoutes().then(setRoutes).catch((e: any) => setError(e.message || "Kunne ikke hente ruterne"));
  }, []);

  const shown = useMemo(() => {
    if (!routes) return [];
    if (range === "all") return routes;
    const since = dateKey(addDays(today, -365));
    return routes.filter((r) => r.date && r.date >= since);
  }, [routes, range, today]);
  const poster = useMemo(() => buildPoster(shown, W, H, 24), [shown]);

  return (
    <section className="u-card" aria-labelledby="poster-title" style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 id="poster-title" className="u-h2">Dine ruter</h2>
        <div role="group" aria-label="Periode" style={{ display: "flex", gap: 8 }}>
          {([["all", "Alle"], ["year", "Seneste år"]] as const).map(([key, label]) => (
            <button key={key} type="button" className={`u-btn ${range === key ? "u-btn--primary" : "u-btn--secondary"}`} aria-pressed={range === key} onClick={() => setRange(key)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="u-card__meta" role="alert">{error}</p>}
      {!routes && !error && <p className="u-card__meta" role="status">Henter ruterne…</p>}
      {routes && poster.used === 0 && (
        <p className="u-card__meta">
          Ingen ruter at vise{routes.length === 0 ? ". Løb på løbebånd har ingen GPS-rute. Udendørsløb får deres rute fra Garmin." : " i den periode."}
        </p>
      )}

      {poster.used > 0 && (
        <>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            role="img"
            aria-label={`${poster.used} løbeture lagt oven i hinanden på ét kort. De steder du løber oftest, er lysest.`}
            style={{ display: "block", width: "100%", height: "auto", borderRadius: 12 }}
          >
            <defs>
              <linearGradient id="poster-bg" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#3A5F90" />
                <stop offset="1" stopColor="#25405f" />
              </linearGradient>
              <filter id="poster-glow" x="-5%" y="-5%" width="110%" height="110%">
                <feGaussianBlur stdDeviation="3" />
              </filter>
            </defs>
            <rect width={W} height={H} fill="url(#poster-bg)" />
            <g filter="url(#poster-glow)" stroke="#9cc4ff" strokeOpacity={0.16} strokeWidth={5} fill="none" strokeLinecap="round" strokeLinejoin="round">
              {poster.paths.map((d, i) => <path key={i} d={d} />)}
            </g>
            <g stroke="#ffffff" strokeOpacity={0.3} strokeWidth={1.3} fill="none" strokeLinecap="round" strokeLinejoin="round">
              {poster.paths.map((d, i) => <path key={i} d={d} />)}
            </g>
          </svg>
          <p className="u-card__meta">
            {poster.used} løb · {poster.totalKm.toLocaleString("da-DK", { maximumFractionDigits: 0 })} km
            {poster.outside > 0 && ` · ${poster.outside} løb for langt væk er ikke med`}
            . Lysere stier er dem, du løber oftest.
          </p>
        </>
      )}
    </section>
  );
}
