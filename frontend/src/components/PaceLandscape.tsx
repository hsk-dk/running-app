import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { LandscapeRun, landscapeHeight, ridges, shortName, speedCap } from "../lib/landscape";
import { paceLabel } from "../lib/profile";
import { useWidth } from "../lib/useWidth";
import { parseDateKey } from "../lib/week";

const COUNT = 16;
const dateText = (d: string | null) => (d ? parseDateKey(d).toLocaleDateString("da-DK", { day: "numeric", month: "short" }) : "");

/** The pace of your latest runs as a mountain range, oldest on top. Intervals are waves; an easy run is a plateau. */
export default function PaceLandscape() {
  const [runs, setRuns] = useState<LandscapeRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const [box, W] = useWidth<HTMLDivElement>();
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);

  const load = useCallback(() => api.getProfiles(COUNT).then(setRuns).catch((e: any) => setError(e.message || "Kunne ikke hente løbene")), []);
  useEffect(() => {
    load();
  }, [load]);

  async function readMore() {
    setBusy(true);
    setProgress("Læser urets filer…");
    try {
      let total = 0;
      for (let round = 0; round < 12; round++) {
        const r = await api.garminReadDetails(25);
        total += r.read;
        setProgress(r.remaining > 0 ? `Læst ${total}, ${r.remaining} tilbage…` : `Læst ${total}. Alle løb er læst.`);
        if (r.remaining === 0 || r.read === 0) break;
      }
      await load();
    } catch (e: any) {
      setProgress(e.message || "Kunne ikke læse fra Garmin");
    } finally {
      setBusy(false);
    }
  }

  const narrow = W < 520;
  const left = narrow ? 0 : 176;
  const rowH = narrow ? 30 : 36;
  const data = useMemo(() => (runs ? ridges(runs, W, rowH, left, 0) : []), [runs, W, rowH, left]);
  const cap = useMemo(() => (runs ? speedCap(runs) : 4), [runs]);
  const height = landscapeHeight(data.length, rowH, 0);
  const chosen = data.find((r) => r.id === picked) ?? data[data.length - 1] ?? null;
  const chosenRun = chosen ? runs?.find((r) => r.id === chosen.id) : null;

  return (
    <section className="u-card" aria-labelledby="land-title" style={{ display: "grid", gap: 12 }}>
      <div>
        <h2 id="land-title" className="u-h2">Dine løb som bjergkæde</h2>
        <p className="u-card__meta">Hvert bjerg er ét løb, ældste øverst. Højden er tempoet: et interval bliver en bølge, et roligt løb en slette. Tryk på et bjerg for at se løbet.</p>
      </div>

      {error && <p className="u-card__meta" role="alert">{error}</p>}
      {!runs && !error && <p className="u-card__meta" role="status">Henter løbene…</p>}

      {runs && runs.length < 3 && (
        <p className="u-card__meta">
          Der er kun {runs.length} løb med detaljer. Appen læser urets fil for et løb, første gang du åbner det. Læs de seneste ind på én gang:
        </p>
      )}

      {runs && runs.length >= 3 && (
        <>
          <div ref={box}>
            <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label={`Tempo for dine ${data.length} seneste løb som en bjergkæde`} style={{ display: "block", width: "100%", height: "auto" }}>
              {data.map((r, i) => {
                const strength = Math.min(1, Math.max(0, (r.peakSpeed - 2) / Math.max(1, cap - 2)));
                const on = chosen?.id === r.id;
                return (
                  <g
                    key={r.id}
                    tabIndex={0}
                    role="button"
                    aria-label={`${dateText(r.date)}, ${r.name}, ${r.km.toLocaleString("da-DK", { maximumFractionDigits: 1 })} kilometer`}
                    onClick={() => setPicked(r.id)}
                    onFocus={() => setPicked(r.id)}
                    onMouseEnter={() => setPicked(r.id)}
                    style={{ cursor: "pointer", outline: "none" }}
                  >
                    <g className="ridge-grow" style={{ ["--delay" as any]: `${i * 70}ms`, transformOrigin: `0px ${r.base}px` }}>
                      <path d={r.fill} fill="var(--color-surface)" />
                      <path d={r.fill} fill="var(--data-1)" fillOpacity={0.14 + 0.5 * strength} />
                      <path d={r.line} fill="none" stroke="var(--data-1)" strokeWidth={on ? 3 : 1.8} strokeLinejoin="round" strokeLinecap="round" />
                    </g>
                    <line x1={left} x2={W} y1={r.base} y2={r.base} stroke="var(--color-border)" />
                    {(!narrow || on || i === 0 || i === data.length - 1) && (
                      <text
                        x={narrow ? 4 : left - 10}
                        y={narrow ? r.base - 4 : r.base - 2}
                        textAnchor={narrow ? "start" : "end"}
                        fontSize={12}
                        fontWeight={on ? 700 : 400}
                        fill="var(--color-text)"
                        stroke="var(--color-surface)"
                        strokeWidth={narrow ? 3 : 0}
                        paintOrder="stroke"
                      >
                        {narrow ? `${dateText(r.date)} · ${shortName(r.name, 22)}` : `${dateText(r.date)}  ${shortName(r.name, 18)}`}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>
          {chosen && chosenRun && (
            <p className="u-card__meta" role="status" aria-live="polite">
              <b>{dateText(chosen.date)}</b> · {chosenRun.name ?? "Løb"} · {chosen.km.toLocaleString("da-DK", { maximumFractionDigits: 1 })} km
              {chosen.paceSec ? ` · ${paceLabel(chosen.paceSec)} /km i snit` : ""}
              {chosen.peakSpeed > 0 ? ` · hurtigst ${paceLabel(1000 / chosen.peakSpeed)} /km` : ""}
              {chosenRun.avg_hr ? ` · puls ${chosenRun.avg_hr}` : ""}
            </p>
          )}
        </>
      )}

      {runs && (
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button type="button" className="u-btn u-btn--secondary" disabled={busy} onClick={readMore}>
            {busy ? "Læser…" : "Læs flere løb ind fra Garmin"}
          </button>
          {progress && <span className="u-card__meta" role="status">{progress}</span>}
        </div>
      )}
    </section>
  );
}
