import { useEffect, useState } from "react";
import { api } from "../api";
import ActivityDetail from "../components/ActivityDetail";
import { Guardian, guardianNote, weekText } from "../lib/family";
import { useMe } from "../lib/meContext";
import FamilySettings from "../components/FamilySettings";
import { levelLabel } from "../lib/sharing";

type Run = { id: number; date: string | null; name: string | null; distance_km: number; duration_min: number };
type Member = {
  user_id: number;
  name: string;
  is_me: boolean;
  level: string;
  shared: boolean;
  week: { done: number; total: number; open: number } | null;
  month_km: number | null;
  month_runs: number | null;
  streak_weeks: number | null;
  recent_runs: Run[] | null;
  new_milestones: { key: string; label: string; date: string }[] | null;
  is_child: boolean;
  guardian: Guardian | null;
};
type Goal = { target_km: number | null; km: number; month: string };
type Family = { members: Member[]; total_km_this_month: number; sharing_enabled: boolean; goal: Goal };

/** Monday of this week as YYYY-MM-DD, local time. */
function weekStartKey(now = new Date()): string {
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

const km = (v: number, d = 1) => v.toLocaleString("da-DK", { minimumFractionDigits: d, maximumFractionDigits: d });

const minutes = (v: number) => (v < 60 ? `${v} min` : `${Math.floor(v / 60)} t${v % 60 ? ` ${v % 60} min` : ""}`);
const todayKey = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

/** What a parent sees about a child: how often and for how long. Never how far, how fast, or where. */
function GuardianSummary({ g }: { g: Guardian }) {
  return (
    <>
      <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(7rem, 1fr))", gap: 12, margin: 0 }}>
        <div>
          <dt className="u-card__meta">Denne uge</dt>
          <dd style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{g.runs_week} {g.runs_week === 1 ? "gang" : "gange"}</dd>
          <dd className="u-card__meta" style={{ margin: 0 }}>{minutes(g.minutes_week)}</dd>
        </div>
        <div>
          <dt className="u-card__meta">Denne måned</dt>
          <dd style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{g.runs_month} {g.runs_month === 1 ? "gang" : "gange"}</dd>
          <dd className="u-card__meta" style={{ margin: 0 }}>{minutes(g.minutes_month)}</dd>
        </div>
        <div>
          <dt className="u-card__meta">Uger i gang</dt>
          <dd style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{g.streak_weeks}</dd>
        </div>
      </dl>
      <p className="u-card__meta" style={{ margin: 0 }}>{guardianNote(g, todayKey())}</p>
    </>
  );
}

function MemberCard({ m, onOpen }: { m: Member; onOpen: (m: Member, id: number) => void }) {
  const id = `member-${m.user_id}`;
  return (
    <section className="u-card" aria-labelledby={id} style={{ display: "grid", gap: 12, alignContent: "start" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <h2 id={id} className="u-h2">{m.is_me ? `${m.name} (dig)` : m.name}</h2>
        <span className="u-chip">{levelLabel(m.level)}</span>
      </div>

      {m.guardian && <GuardianSummary g={m.guardian} />}

      {m.shared && !m.guardian && m.level === "milestones" && (
        <p className="u-card__meta">{m.new_milestones && m.new_milestones.length > 0 ? "Har nået noget nyt, se øverst." : `${m.name} er med i familien.`}</p>
      )}

      {!m.shared && (
        <p className="u-card__meta">
          {m.is_me ? "Du deler ikke dine løb med familien." : `${m.name} holder sine løb for sig selv. Det er helt i orden.`}
        </p>
      )}

      {m.shared && m.week && (
        <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(7rem, 1fr))", gap: 12, margin: 0 }}>
          <div>
            <dt className="u-card__meta">Ugen</dt>
            <dd style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{weekText(m.week, m.recent_runs ? m.recent_runs.filter((r) => r.date && r.date >= weekStartKey()).length : 0)}</dd>
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
  const { isAdmin } = useMe();

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
    const loadSplits = open.member.is_me
      ? (id: number) => api.getSplits(id)
      : (id: number) => api.getFamilySplits(open.member.user_id, id);
    const loadProfile = open.member.is_me
      ? (id: number) => api.getProfile(id)
      : (id: number) => api.getFamilyProfile(open.member.user_id, id);
    return (
      <div style={{ display: "grid", gap: 16 }}>
        <p className="u-card__meta">{open.member.is_me ? "Dit løb" : `${open.member.name}s løb`}</p>
        <ActivityDetail activityId={open.id} onClose={() => setOpen(null)} load={load} loadSplits={loadSplits} loadProfile={loadProfile} />
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <p className="now__eyebrow">Familie</p>
        <h1 className="u-h1">{km(family.total_km_this_month, 0)} km sammen denne måned</h1>
      </section>

      {family.goal.target_km !== null && family.goal.target_km > 0 && (
        <section className="u-card" aria-labelledby="goal-title" style={{ display: "grid", gap: 8 }}>
          <h2 id="goal-title" className="u-h2">Fælles mål</h2>
          <div role="progressbar" aria-valuenow={Math.min(family.goal.km, family.goal.target_km)} aria-valuemin={0} aria-valuemax={family.goal.target_km} aria-label={`Fælles mål: ${km(family.goal.km, 0)} af ${km(family.goal.target_km, 0)} kilometer`} style={{ height: 18, borderRadius: 9, background: "var(--data-muted)", overflow: "hidden" }}>
            <div style={{ width: `${Math.min(100, Math.round((family.goal.km / family.goal.target_km) * 100))}%`, height: "100%", background: "var(--data-1)" }} />
          </div>
          <p style={{ margin: 0, fontWeight: 600 }}>
            {km(family.goal.km, 0)} af {km(family.goal.target_km, 0)} km
            {family.goal.km >= family.goal.target_km ? ": målet er nået!" : ""}
          </p>
          <p className="u-card__meta" style={{ margin: 0 }}>Alle, der deler med familien, løber sammen. Ingen kan se, hvem der har løbet hvor meget.</p>
        </section>
      )}

      {(() => {
        const items = family.members
          .flatMap((m) => (m.new_milestones ?? []).map((x) => ({ ...x, name: m.is_me ? "Du" : m.name })))
          .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : a.label < b.label ? -1 : 1));
        if (items.length === 0) return null;
        return (
          <section className="u-card" aria-labelledby="news-title" style={{ display: "grid", gap: 10 }}>
            <h2 id="news-title" className="u-h2">Nyt i familien</h2>
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
              {items.map((x) => (
                <li key={`${x.name}-${x.key}`} style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
                  <span aria-hidden>🎉</span>
                  <span style={{ fontWeight: 600 }}>{x.name}:</span>
                  <span>{x.label.charAt(0).toLowerCase() + x.label.slice(1)}</span>
                  <span className="u-card__meta">{new Date(x.date).toLocaleDateString("da-DK", { day: "numeric", month: "short" })}</span>
                </li>
              ))}
            </ul>
            <p className="u-card__meta" style={{ margin: 0 }}>Kun milepæle, ingen kilometer og ingen rangliste.</p>
          </section>
        );
      })()}

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
      {isAdmin && <FamilySettings goal={family.goal} onChanged={() => api.getFamily().then(setFamily)} />}
    </div>
  );
}
