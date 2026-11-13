import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Lap, Profile, lapsToShow, paceFromSpeed, paceLabel, smooth, speeds, ticks } from "../lib/profile";
import { useWidth } from "../lib/useWidth";

type Answer = { available: boolean; source: boolean; profile: Profile | null; laps: Lap[] };

const H = 220;
const PAD = { l: 46, r: 46, t: 10, b: 30 };
const km = (m: number) => (m / 1000).toLocaleString("da-DK", { maximumFractionDigits: 1 });
const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;

/** Pace (solid) and heart rate (dashed) along the run, so intervals show up as waves. Laps are listed below. */
export default function ProfileChart({ activityId, load = (id: number) => api.getProfile(id) }: { activityId: number; load?: (id: number) => Promise<Answer> }) {
  const [data, setData] = useState<Answer | null>(null);
  const [failed, setFailed] = useState(false);
  const [box, W] = useWidth<HTMLDivElement>();

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setFailed(false);
    load(activityId)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activityId]);

  const chart = useMemo(() => {
    const p = data?.profile;
    if (!p || p.d.length < 2) return null;
    const pace = smooth(speeds(p), 5).map(paceFromSpeed);
    const shown = pace.filter((v): v is number => v !== null);
    if (shown.length < 2) return null;
    // Keep the scale on the interesting part: a stop or a very slow walk must not squash everything else.
    const sorted = [...shown].sort((a, b) => a - b);
    const lo = sorted[Math.floor(sorted.length * 0.02)];
    const hi = Math.min(sorted[Math.ceil(sorted.length * 0.98) - 1], lo * 2.5);
    const hrs = (p.hr ?? []).filter((v): v is number => v !== null);
    return { p, pace, lo, hi, hrLo: hrs.length ? Math.min(...hrs) : 0, hrHi: hrs.length ? Math.max(...hrs) : 0, hasHr: hrs.length > 1 };
  }, [data]);

  if (failed) return <p className="u-card__meta">Tempo og puls kunne ikke hentes.</p>;
  if (!data) return <p className="u-card__meta" role="status">Henter tempo og puls…</p>;
  if (!data.source) return null; // not a run from Garmin: there is nothing more to show
  if (!data.available) return <p className="u-card__meta">Garmin svarer ikke lige nu, så tempo og puls kan ikke vises. Prøv igen senere.</p>;
  if (!chart) return <p className="u-card__meta">Garmin har ingen detaljerede målinger for dette løb.</p>;

  const { p, pace, lo, hi, hrLo, hrHi, hasHr } = chart;
  const maxD = p.d[p.d.length - 1];
  const x = (d: number) => PAD.l + (d / maxD) * (W - PAD.l - PAD.r);
  // faster (smaller pace) is higher on the chart
  const yPace = (s: number) => PAD.t + ((Math.min(Math.max(s, lo), hi) - lo) / (hi - lo || 1)) * (H - PAD.t - PAD.b);
  const yHr = (v: number) => H - PAD.b - ((v - hrLo) / (hrHi - hrLo || 1)) * (H - PAD.t - PAD.b);

  const paceLine = pace.reduce<string>((d, v, i) => (v === null ? d : `${d}${d && pace[i - 1] !== null ? "L" : "M"}${x(p.d[i]).toFixed(1)} ${yPace(v).toFixed(1)} `), "");
  const hrLine = hasHr
    ? (p.hr as (number | null)[]).reduce<string>((d, v, i) => (v === null ? d : `${d}${d && (p.hr as (number | null)[])[i - 1] !== null ? "L" : "M"}${x(p.d[i]).toFixed(1)} ${yHr(v).toFixed(1)} `), "")
    : "";
  // Ticks on whole minutes (4:00, 6:00, ...), not on seconds, so they are round numbers a runner reads at a glance.
  const paceTicks = ticks(lo / 60, hi / 60, 3).map((m) => Math.round(m * 60)).filter((v) => v >= lo && v <= hi);
  const hrTicks = hasHr ? ticks(hrLo, hrHi, 3) : [];
  const distTicks = ticks(0, maxD / 1000, Math.max(2, Math.floor((W - PAD.l - PAD.r) / 70)));
  const laps = lapsToShow(data.laps);

  return (
    <section aria-labelledby="profile-title" style={{ display: "grid", gap: 8 }}>
      <h3 id="profile-title" className="u-h3">Tempo{hasHr ? " og puls" : ""}</h3>
      <div ref={box}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Tempo${hasHr ? " og puls" : ""} gennem løbet på ${km(maxD)} kilometer`} style={{ display: "block", width: "100%", height: "auto" }}>
          {paceTicks.map((v) => (
            <g key={`p${v}`}>
              <line x1={PAD.l} x2={W - PAD.r} y1={yPace(v)} y2={yPace(v)} stroke="var(--color-border)" />
              <text x={PAD.l - 6} y={yPace(v)} textAnchor="end" dominantBaseline="middle" fontSize={12} fill="var(--data-1)">{paceLabel(v)}</text>
            </g>
          ))}
          {hrTicks.map((v) => (
            <text key={`h${v}`} x={W - PAD.r + 6} y={yHr(v)} dominantBaseline="middle" fontSize={12} fill="var(--data-4)">{Math.round(v)}</text>
          ))}
          {distTicks.map((v) => (
            <text key={`d${v}`} x={x(v * 1000)} y={H - 8} textAnchor="middle" fontSize={12} fill="var(--color-text-muted)">{v.toLocaleString("da-DK")}</text>
          ))}
          {laps.map((l, i) => {
            const startD = l.start_s === null ? null : p.t.findIndex((t) => t >= (l.start_s as number));
            return startD !== null && startD > 0 ? <line key={i} x1={x(p.d[startD])} x2={x(p.d[startD])} y1={PAD.t} y2={H - PAD.b} stroke="var(--color-border)" strokeDasharray="3 4" /> : null;
          })}
          {hasHr && <path d={hrLine} fill="none" stroke="var(--data-4)" strokeWidth={2} strokeDasharray="6 4" strokeLinejoin="round" />}
          <path d={paceLine} fill="none" stroke="var(--data-1)" strokeWidth={3} strokeLinejoin="round" strokeLinecap="round" />
          <text x={W - PAD.r} y={H - 8} textAnchor="end" fontSize={11} fill="var(--color-text-muted)">km</text>
        </svg>
      </div>
      <p className="u-card__meta">
        <span style={{ color: "var(--data-1)", fontWeight: 600 }}>━ Tempo</span> (min/km, øverst er hurtigst)
        {hasHr && (
          <>
            {" · "}
            <span style={{ color: "var(--data-4)", fontWeight: 600 }}>╌ Puls</span> (slag/min)
          </>
        )}
        {laps.length > 0 && ". Stiplede lodrette streger er rundeskift."}
      </p>

      {laps.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table className="u-table" style={{ width: "100%", borderCollapse: "collapse" }}>
            <caption className="u-card__meta" style={{ textAlign: "left", padding: "4px 0" }}>Runder</caption>
            <thead>
              <tr>
                <th scope="col" style={{ textAlign: "left" }}>#</th>
                <th scope="col" style={{ textAlign: "right" }}>Tid</th>
                <th scope="col" style={{ textAlign: "right" }}>Distance</th>
                <th scope="col" style={{ textAlign: "right" }}>Tempo</th>
                {laps.some((l) => l.avg_hr !== null) && <th scope="col" style={{ textAlign: "right" }}>Puls</th>}
              </tr>
            </thead>
            <tbody>
              {laps.slice(0, 60).map((l, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td style={{ textAlign: "right" }}>{mmss(l.duration_s)}</td>
                  <td style={{ textAlign: "right" }}>{l.distance_m === null ? "–" : `${Math.round(l.distance_m)} m`}</td>
                  <td style={{ textAlign: "right" }}>{l.pace_s_per_km === null ? "–" : `${paceLabel(l.pace_s_per_km)} /km`}</td>
                  {laps.some((x) => x.avg_hr !== null) && <td style={{ textAlign: "right" }}>{l.avg_hr === null ? "–" : l.avg_hr}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
