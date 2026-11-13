import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { clusterRoutes } from "../lib/areas";
import { PosterRoute } from "../lib/poster";
import { addDays, dateKey } from "../lib/week";
import AreaPosters from "./AreaPosters";
import ContactSheet from "./ContactSheet";
import YearPlayback from "./YearPlayback";

type View = "contact" | "areas" | "play";
const VIEWS: { key: View; label: string }[] = [
  { key: "contact", label: "Kontaktark" },
  { key: "areas", label: "Områder" },
  { key: "play", label: "Afspil" },
];

/** Your routes, three ways: a sheet with every run on its own tile, one map per place, and a playback in date order. */
export default function RoutesCard({ today = new Date() }: { today?: Date }) {
  const [routes, setRoutes] = useState<PosterRoute[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("contact");
  const [range, setRange] = useState<"all" | "year">("all");
  const [replayKey, setReplayKey] = useState(0);
  const [areaKey, setAreaKey] = useState<string | null>(null);

  useEffect(() => {
    api.getRoutes().then(setRoutes).catch((e: any) => setError(e.message || "Kunne ikke hente ruterne"));
  }, []);

  const shown = useMemo(() => {
    if (!routes) return [];
    if (range === "all") return routes;
    const since = dateKey(addDays(today, -365));
    return routes.filter((r) => r.date && r.date >= since);
  }, [routes, range, today]);
  const areas = useMemo(() => clusterRoutes(shown), [shown]);
  const area = areas.find((a) => a.key === areaKey) ?? areas[0] ?? null;
  const totalKm = shown.reduce((s, r) => s + r.distance_km, 0);

  function open(next: View) {
    setView(next);
    if (next === "contact") setReplayKey((k) => k + 1); // draw them again
  }

  return (
    <section className="u-card" aria-labelledby="routes-title" style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 id="routes-title" className="u-h2">Dine ruter</h2>
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

      {routes && shown.length === 0 && (
        <p className="u-card__meta">
          Ingen ruter at vise{routes.length === 0 ? ". Løb på løbebånd har ingen GPS-rute. Udendørsløb får deres rute fra Garmin." : " i den periode."}
        </p>
      )}

      {shown.length > 0 && (
        <>
          <div role="group" aria-label="Visning" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {VIEWS.map((v) => (
              <button key={v.key} type="button" className={`u-btn ${view === v.key ? "u-btn--primary" : "u-btn--secondary"}`} aria-pressed={view === v.key} onClick={() => open(v.key)}>
                {v.label}
              </button>
            ))}
            {view === "contact" && (
              <button type="button" className="u-btn u-btn--secondary" onClick={() => setReplayKey((k) => k + 1)}>Tegn alle igen</button>
            )}
          </div>

          {view === "play" && areas.length > 1 && (
            <label className="u-card__meta" style={{ display: "grid", gap: 4, maxWidth: 320 }}>
              Område
              <select value={area?.key ?? ""} onChange={(e) => setAreaKey(e.target.value)} style={{ minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", background: "var(--color-surface)" }}>
                {areas.map((a) => <option key={a.key} value={a.key}>{a.name} ({a.routes.length} løb)</option>)}
              </select>
            </label>
          )}

          {view === "contact" && <ContactSheet routes={shown} replayKey={replayKey} />}
          {view === "areas" && <AreaPosters areas={areas} onPlay={(key) => { setAreaKey(key); setView("play"); }} />}
          {view === "play" && area && <YearPlayback area={area} />}

          <p className="u-card__meta">
            {shown.length} løb med GPS · {totalKm.toLocaleString("da-DK", { maximumFractionDigits: 0 })} km i {areas.length} {areas.length === 1 ? "område" : "områder"}.
            Løb på løbebånd har ingen rute og vises nedenfor som tempo.
          </p>
        </>
      )}
    </section>
  );
}
