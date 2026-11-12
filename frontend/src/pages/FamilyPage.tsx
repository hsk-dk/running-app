import { useEffect, useState } from "react";
import { api } from "../api";
import ActivityDetail from "../components/ActivityDetail";
import { levelLabel } from "../lib/sharing";

type Run = { id: number; date: string | null; name: string | null; distance_km: number; duration_min: number };
type Member = {
  user_id: number;
  name: string;
  is_me: boolean;
  level: string;
  shared: boolean;
  strava_connected: boolean;
  week: { done: number; total: number; open: number } | null;
  month_km: number | null;
  month_runs: number | null;
  streak_weeks: number | null;
  recent_runs: Run[] | null;
};
type Family = { members: Member[]; total_km_this_month: number; sharing_enabled: boolean };

const km = (v: number, d = 1) => v.toLocaleString("da-DK", { minimumFractionDigits: d, maximumFractionDigits: d });

function MemberCard({ m, onOpen }: { m: Member; onOpen: (m: Member, id: number) => void }) {
  const id = `member-${m.user_id}`;
  return (
    <section className="u-card" aria-labelledby={id} style={{ display: "grid", gap: 12, alignContent: "start" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <h2 id={id} className="u-h2">{m.is_me ? `${m.name} (dig)` : m.name}</h2>
        <span className="u-chip">{levelLabel(m.level)}</span>
      </div>

      {!m.shared && (
        <p className="u-card__meta">
          {m.is_me ? "Du deler ikke dine løb med familien." : `${m.name} deler ikke sine løb.`}
        </p>
      )}
      {m.shared && !m.strava_connected && <p className="u-card__meta">Strava er ikke forbundet endnu.</p>}

      {m.shared && m.week && (
        <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(7rem, 1fr))", gap: 12, margin: 0 }}>
          <div>
            <dt className="u-card__meta">Ugen</dt>
            <dd style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{m.week.total === 0 ? "Ingen plan" : `${m.week.done} af ${m.week.total}`}</dd>
          </div>
          <div>
            <dt className="u-card__meta">Denne måned</dt>
            <dd style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{km(m.month_km ?? 0)} km</dd>
          </div>
          <div>
            <dt className="u-card__meta">Uger i træk</dt>
            <dd style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{m.streak_weeks ?? 0}</dd>
          </div>
        </dl>
      )}

      {m.recent_runs && m.recent_runs.length > 0 && (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
          {m.recent_runs.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                className="u-btn u-btn--secondary"
                style={{ width: "100%", justifyContent: "space-between", textAlign: "left" }}
                onClick={() => onOpen(m, r.id)}
              >
                <span>
                  {r.date ? new Date(r.date).toLocaleDateString("da-DK", { day: "numeric", month: "short" }) : "–"} · {r.name || "Løb"}
                </span>
                <span>{km(r.distance_km)} km</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Everyone's training side by side. No rankings: just who has been out, and how much together. */
export default function FamilyPage() {
  const [family, setFamily] = useState<Family | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<{ member: Member; id: number } | null>(null);

  useEffect(() => {
    api.getFamily().then(setFamily).catch((e: any) => setError(e.message || "Kunne ikke hente familien"));
  }, []);

  if (error) {
    return (
      <div className="u-notice u-notice--error" role="alert">
        <b className="u-notice__level">Fejl</b>
        <span>{error}</span>
      </div>
    );
  }
  if (!family) return <p className="u-card__meta" role="status">Henter familien…</p>;

  if (open) {
    const load = open.member.is_me
      ? (id: number) => api.getActivity(id)
      : (id: number) => api.getFamilyActivity(open.member.user_id, id);
    return (
      <div style={{ display: "grid", gap: 16 }}>
        <p className="u-card__meta">{open.member.is_me ? "Dit løb" : `${open.member.name}s løb`}</p>
        <ActivityDetail activityId={open.id} onClose={() => setOpen(null)} load={load} />
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <p className="now__eyebrow">Familie</p>
        <h1 className="u-h1">{km(family.total_km_this_month, 0)} km sammen denne måned</h1>
      </section>

      {!family.sharing_enabled && (
        <div className="u-notice u-notice--warning" role="status">
          <b className="u-notice__level">Slået fra</b>
          <span>Deling mellem familiemedlemmer er slået fra på serveren. Alle ser kun deres egne løb.</span>
        </div>
      )}

      <div className="u-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 18rem), 1fr))" }}>
        {family.members.map((m) => (
          <MemberCard key={m.user_id} m={m} onOpen={(member, id) => setOpen({ member, id })} />
        ))}
      </div>
    </div>
  );
}
