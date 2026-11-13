import { useEffect, useState } from "react";
import { api } from "../api";
import SplitsChart from "./SplitsChart";
import RoutePoster from "./RoutePoster";

type Detail = {
  id: number;
  date: string | null;
  name: string | null;
  distance_km: number;
  duration_min: number;
  avg_hr: number | null;
  max_hr: number | null;
  elevation_gain_m: number | null;
  avg_pace_s_per_km: number | null;
  start_time_local: string | null;
  route: string | null;
};

const num = (v: number, d = 1) => v.toLocaleString("da-DK", { minimumFractionDigits: d, maximumFractionDigits: d });
function pace(s: number | null) {
  if (!s) return "–";
  const m = Math.floor(s / 60);
  return `${m}:${String(Math.round(s % 60)).padStart(2, "0")} /km`;
}
function duration(min: number) {
  const total = Math.round(min);
  const h = Math.floor(total / 60);
  return h > 0 ? `${h}:${String(total % 60).padStart(2, "0")} t` : `${total} min`;
}

/** One run as a story: the route first, then the three numbers that matter. */
export default function ActivityDetail({
  activityId,
  onClose,
  load = (id: number) => api.getActivity(id),
  loadSplits,
}: {
  activityId: number;
  onClose: () => void;
  /** Fetches the run; family members' runs come from a different endpoint. */
  load?: (id: number) => Promise<any>;
  /** Fetches the kilometre splits; family members' runs use a different endpoint. */
  loadSplits?: (id: number) => Promise<any>;
}) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    setError(null);
    load(activityId)
      .then((d: Detail) => !cancelled && setDetail(d))
      .catch((e: any) => !cancelled && setError(e.message || "Kunne ikke hente løbet"));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activityId]);

  return (
    <section className="u-card" aria-labelledby="detail-title" style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 id="detail-title" className="u-h2">
            {detail?.name ?? "Løb"}
          </h2>
          {detail?.date && (
            <p className="u-card__meta">
              {new Date(detail.date).toLocaleDateString("da-DK", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
            </p>
          )}
        </div>
        <button type="button" className="u-btn u-btn--secondary" onClick={onClose}>
          Luk
        </button>
      </div>

      {error && (
        <div className="u-notice u-notice--error" role="alert">
          <b className="u-notice__level">Fejl</b>
          <span>{error}</span>
        </div>
      )}

      {!detail && !error && (
        <div aria-busy="true" className="u-stack">
          <div className="u-skeleton" style={{ width: "40%" }} />
          <div className="u-skeleton" style={{ width: "90%", height: 160 }} />
        </div>
      )}

      {detail && (
        <div className="detail">
          <div className="detail__route">
            <RoutePoster route={detail.route} name={detail.name ?? "løbet"} />
          </div>
          <div className="detail__facts">
            <div className="u-tile"><span className="u-tile__label">Distance</span><span className="u-tile__value">{num(detail.distance_km, 2)} km</span></div>
            <div className="u-tile"><span className="u-tile__label">Tid</span><span className="u-tile__value">{duration(detail.duration_min)}</span></div>
            <div className="u-tile"><span className="u-tile__label">Tempo</span><span className="u-tile__value">{pace(detail.avg_pace_s_per_km)}</span></div>
            {"avg_hr" in detail && <div className="u-tile"><span className="u-tile__label">Puls (gns / max)</span><span className="u-tile__value">{detail.avg_hr ? num(detail.avg_hr, 0) : "–"}{detail.max_hr ? ` / ${num(detail.max_hr, 0)}` : ""}</span></div>}
            <div className="u-tile"><span className="u-tile__label">Stigning</span><span className="u-tile__value">{detail.elevation_gain_m != null ? `${num(detail.elevation_gain_m, 0)} m` : "–"}</span></div>
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <SplitsChart activityId={activityId} load={loadSplits} />
          </div>
        </div>
      )}
    </section>
  );
}
