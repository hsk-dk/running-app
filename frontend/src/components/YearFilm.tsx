import { useEffect, useMemo, useState } from "react";
import { Area } from "../lib/areas";
import { FilmSummary, countUp, lineOpacity, statsMs } from "../lib/film";
import { Indoor } from "../lib/flight";
import { prefersReducedMotion, useClock } from "../lib/motion";
import FlightMap from "./FlightMap";

type Scene = "idle" | "title" | "flight" | "stats" | "end";
const TITLE_MS = 3200;

const stage: React.CSSProperties = {
  minHeight: 280,
  borderRadius: 12,
  background: "linear-gradient(135deg, #3A5F90, #22405f)",
  color: "#fff",
  display: "grid",
  alignContent: "center",
  justifyItems: "center",
  gap: 12,
  padding: 24,
  textAlign: "center",
};

function TitleScene({ title, summary, onDone, still }: { title: string; summary: FilmSummary; onDone: () => void; still: boolean }) {
  const [ms] = useClock(TITLE_MS, !still);
  useEffect(() => {
    if (!still && ms >= TITLE_MS) onDone();
  }, [ms, still, onDone]);
  const shown = still ? summary.km : countUp(ms, TITLE_MS - 600, summary.km);
  return (
    <div style={stage}>
      <p style={{ margin: 0, letterSpacing: "0.22em", fontSize: 13, textTransform: "uppercase", opacity: 0.8 }}>{title}</p>
      <p style={{ margin: 0, fontSize: 64, fontWeight: 700, lineHeight: 1 }} aria-label={`${Math.round(summary.km)} kilometer`}>
        {Math.round(shown).toLocaleString("da-DK")}
        <span style={{ fontSize: 24, fontWeight: 400, marginLeft: 8 }}>km</span>
      </p>
      <p style={{ margin: 0, opacity: 0.75 }}>{summary.runs} løb</p>
    </div>
  );
}

function StatsScene({ summary, onDone, still }: { summary: FilmSummary; onDone: () => void; still: boolean }) {
  const total = statsMs(summary);
  const [ms] = useClock(total, !still);
  useEffect(() => {
    if (!still && ms >= total) onDone();
  }, [ms, total, still, onDone]);
  return (
    <div style={stage}>
      {summary.lines.map((line, i) => (
        <p key={line} style={{ margin: 0, fontSize: i === 0 ? 26 : 20, fontWeight: i === 0 ? 700 : 400, opacity: still ? 1 : lineOpacity(i, ms), transform: `translateY(${still ? 0 : (1 - lineOpacity(i, ms)) * 10}px)` }}>
          {line}
        </p>
      ))}
    </div>
  );
}

/**
 * A short film of the year: the total counts up, the camera flies over the places (and the treadmill), and the highlights
 * come in one by one. Starts when asked, can be skipped, and is a still summary for people who want less motion.
 */
export default function YearFilm({ title, areas, indoor, summary }: { title: string; areas: Area[]; indoor: Indoor | null; summary: FilmSummary }) {
  const reduced = useMemo(() => prefersReducedMotion(), []);
  const [scene, setScene] = useState<Scene>("idle");
  const hasMap = areas.length > 0;
  const toFlight = () => setScene(hasMap ? "flight" : "stats");
  const next: Record<Scene, Scene> = { idle: "title", title: hasMap ? "flight" : "stats", flight: "stats", stats: "end", end: "end" };
  const advance = () => setScene((s) => next[s]);

  if (summary.runs === 0) return <p className="u-card__meta">Ingen løb at vise i den periode.</p>;

  if (reduced) {
    return (
      <div style={{ display: "grid", gap: 12 }}>
        <TitleScene title={title} summary={summary} onDone={() => undefined} still />
        <StatsScene summary={summary} onDone={() => undefined} still />
        <p className="u-card__meta">Bevægelse er slået fra, så filmen vises som et stillbillede.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 10 }}>
      {scene === "idle" && (
        <div style={stage}>
          <p style={{ margin: 0, letterSpacing: "0.22em", fontSize: 13, textTransform: "uppercase", opacity: 0.8 }}>{title}</p>
          <p style={{ margin: 0, fontSize: 22 }}>En kort film om dit løb</p>
          <button type="button" className="u-btn u-btn--primary" onClick={() => setScene("title")}>Afspil filmen</button>
        </div>
      )}
      {scene === "title" && <TitleScene title={title} summary={summary} onDone={toFlight} still={false} />}
      {scene === "flight" && <FlightMap areas={areas} indoor={indoor} speed={1.6} bare onDone={advance} />}
      {scene === "stats" && <StatsScene summary={summary} onDone={advance} still={false} />}
      {scene === "end" && (
        <div style={stage}>
          <p style={{ margin: 0, fontSize: 32, fontWeight: 700 }}>Flot løbet!</p>
          <p style={{ margin: 0, opacity: 0.8 }}>{title}: {Math.round(summary.km).toLocaleString("da-DK")} km</p>
          <button type="button" className="u-btn u-btn--primary" onClick={() => setScene("title")}>Se filmen igen</button>
        </div>
      )}
      {scene !== "idle" && scene !== "end" && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button type="button" className="u-btn u-btn--secondary" onClick={advance}>Spring over</button>
          <span className="u-card__meta" role="status">
            {scene === "title" ? "Året i tal" : scene === "flight" ? "Flyvetur" : "Højdepunkter"}
          </span>
        </div>
      )}
    </div>
  );
}
