import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { clusterRoutes } from "../lib/areas";
import { PosterRoute } from "../lib/poster";
import { summarise } from "../lib/film";
import { Indoor } from "../lib/flight";
import { ALL, LAST_YEAR, defaultFilmPeriod, inPeriod, periodLabel, yearsOf } from "../lib/period";
import AreaPosters from "./AreaPosters";
import ContactSheet from "./ContactSheet";
import FlightMap from "./FlightMap";
import YearFilm from "./YearFilm";
import YearPlayback from "./YearPlayback";

type View = "flight" | "film" | "contact" | "areas" | "play";
const VIEWS: { key: View; label: string }[] = [
  { key: "flight", label: "Flyvetur" },
  { key: "film", label: "Årsfilm" },
  { key: "contact", label: "Kontaktark" },
  { key: "areas", label: "Områder" },
  { key: "play", label: "Afspil" },
];

/** Your routes: a flight over the places you have run, a sheet with every run on its own tile, one map per place, and a playback. */
export default function RoutesCard({ today = new Date() }: { today?: Date }) {
  const [routes, setRoutes] = useState<PosterRoute[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("flight");
  const [indoorRuns, setIndoorRuns] = useState<{ date: string | null; distance_km: number; duration_min: number }[]>([]);
  const [period, setPeriod] = useState<string>(ALL);
  const [pickedYet, setPickedYet] = useState(false);
  const [replayKey, setReplayKey] = useState(0);
  const [areaKey, setAreaKey] = useState<string | null>(null);

  useEffect(() => {
    api.getRoutes().then(setRoutes).catch((e: any) => setError(e.message || "Kunne ikke hente ruterne"));
    api.getIndoor().then(setIndoorRuns).catch(() => setIndoorRuns([])); // the treadmill stop is a bonus: the map works without it
  }, []);

  const years = useMemo(() => yearsOf([...(routes ?? []).map((r) => r.date), ...indoorRuns.map((r) => r.date)]), [routes, indoorRuns]);

  const shown = useMemo(() => (routes ?? []).filter((r) => inPeriod(r.date, period, today)), [routes, period, today]);
  const indoorShown = useMemo(() => indoorRuns.filter((r) => inPeriod(r.date, period, today)), [indoorRuns, period, today]);
  const indoor: Indoor | null = useMemo(
    () => (indoorShown.length ? { runs: indoorShown.length, km: indoorShown.reduce((s, r) => s + r.distance_km, 0), min: indoorShown.reduce((s, r) => s + r.duration_min, 0) } : null),
    [indoorShown],
  );
  const summary = useMemo(() => summarise([...shown, ...indoorShown]), [shown, indoorShown]);
  const areas = useMemo(() => clusterRoutes(shown), [shown]);
  const area = areas.find((a) => a.key === areaKey) ?? areas[0] ?? null;
  const totalKm = shown.reduce((s, r) => s + r.distance_km, 0);

  function open(next: View) {
    // the film is about one year: start it on the newest year that has enough runs, unless a period was picked already
    if (next === "film" && !pickedYet && period === ALL && routes) {
      setPeriod(defaultFilmPeriod([...routes.map((r) => r.date), ...indoorRuns.map((r) => r.date)]));
    }
    setView(next);
    if (next === "contact") setReplayKey((k) => k + 1); // draw them again
  }

  return (
    <section className="u-card" aria-labelledby="routes-title" style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 id="routes-title" className="u-h2">Dine ruter</h2>
        <label className="u-card__meta" style={{ display: "flex", gap: 8, alignItems: "center" }}>
          Periode
          <select
            value={period}
            onChange={(e) => {
              setPeriod(e.target.value);
              setPickedYet(true);
            }}
            style={{ minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", background: "var(--color-surface)" }}
          >
            <option value={ALL}>{periodLabel(ALL)}</option>
            <option value={LAST_YEAR}>{periodLabel(LAST_YEAR)}</option>
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="u-card__meta" role="alert">{error}</p>}
      {!routes && !error && <p className="u-card__meta" role="status">Henter ruterne…</p>}

      {routes && shown.length === 0 && !indoor && (
        <p className="u-card__meta">
          Ingen ruter at vise{routes.length === 0 ? ". Løb på løbebånd har ingen GPS-rute. Udendørsløb får deres rute fra Garmin." : " i den periode."}
        </p>
      )}

      {(shown.length > 0 || indoor) && (
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

          {view === "flight" && (shown.length > 0 ? <FlightMap areas={areas} indoor={indoor} /> : <p className="u-card__meta">Ingen af løbene i perioden har en GPS-rute, så der er ikke noget at flyve over. Se filmen i stedet.</p>)}
          {view === "film" && <YearFilm key={period} title={periodLabel(period)} areas={areas} indoor={indoor} summary={summary} />}
          {view === "contact" && <ContactSheet routes={shown} replayKey={replayKey} />}
          {view === "areas" && <AreaPosters areas={areas} onPlay={(key) => { setAreaKey(key); setView("play"); }} />}
          {view === "play" && area && <YearPlayback area={area} />}

          <p className="u-card__meta">
            {shown.length} løb med GPS · {totalKm.toLocaleString("da-DK", { maximumFractionDigits: 0 })} km i {areas.length} {areas.length === 1 ? "område" : "områder"}.
            {indoor
              ? ` Dertil ${indoor.runs} løb uden rute (løbebånd og indendørs), ${Math.round(indoor.km).toLocaleString("da-DK")} km. De har et stop i flyveturen og vises nedenfor som tempo.`
              : " Løb på løbebånd har ingen rute og vises nedenfor som tempo."}
          </p>
        </>
      )}
    </section>
  );
}
