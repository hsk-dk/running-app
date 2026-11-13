import { useState } from "react";
import { api } from "../api";
import { SHARING_LEVELS, SharingLevel } from "../lib/sharing";

type Me = {
  display_name: string;
  username: string;
  role: string;
  sharing_level: SharingLevel;
  family_sharing_enabled: boolean;
  strava: { connected: boolean; configured: boolean; athlete_id: string | null };
  smashrun: { connected: boolean; configured: boolean };
};

/** Your own settings: who sees your runs, and which Strava the app reads. */
export default function MePage({ me, onChanged }: { me: Me; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (e: any) {
      setError(e.message || "Handlingen fejlede");
    } finally {
      setBusy(false);
    }
  }

  async function connect(source: "strava" | "smashrun" = "strava") {
    setBusy(true);
    setError(null);
    try {
      const { url } = await (source === "smashrun" ? api.smashrunConnect() : api.stravaConnect());
      window.location.href = url;
    } catch (e: any) {
      setError(e.message || "Kunne ikke starte forbindelsen");
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <p className="now__eyebrow">Mig</p>
        <h1 className="u-h1">{me.display_name}</h1>
        <p className="u-card__meta">
          {me.username} {me.role === "admin" && <span className="u-chip">Admin</span>}
        </p>
      </section>

      {error && (
        <div className="u-notice u-notice--error" role="alert">
          <b className="u-notice__level">Fejl</b>
          <span>{error}</span>
        </div>
      )}

      <section className="u-card" aria-labelledby="share-title" style={{ display: "grid", gap: 12 }}>
        <h2 id="share-title" className="u-h2">Hvem ser dine løb?</h2>
        {!me.family_sharing_enabled && (
          <div className="u-notice u-notice--warning" role="status">
            <b className="u-notice__level">Slået fra</b>
            <span>Deling er slået fra på serveren. Uanset valget ser ingen andre dine løb.</span>
          </div>
        )}
        <fieldset style={{ border: 0, margin: 0, padding: 0, display: "grid", gap: 8 }} disabled={busy}>
          <legend className="u-card__meta">Vælg hvor meget familien må se</legend>
          {SHARING_LEVELS.map((l) => (
            <label
              key={l.key}
              style={{ display: "grid", gridTemplateColumns: "auto minmax(0, 1fr)", gap: 12, alignItems: "start", minHeight: 44, padding: "8px 0" }}
            >
              <input
                type="radio"
                name="sharing"
                checked={me.sharing_level === l.key}
                onChange={() => run(() => api.updateMe({ sharing_level: l.key }))}
                style={{ width: 22, height: 22, marginTop: 2, accentColor: "#446EA8" }}
              />
              <span>
                <b>{l.label}</b>
                <br />
                <span className="u-card__meta">{l.summary}</span>
              </span>
            </label>
          ))}
        </fieldset>
      </section>

      <section className="u-card" aria-labelledby="smashrun-title" style={{ display: "grid", gap: 12 }}>
        <h2 id="smashrun-title" className="u-h2">Smashrun</h2>
        {me.smashrun.connected ? (
          <>
            <p className="u-card__meta">Forbundet. Dine løb hentes herfra.</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" className="u-btn u-btn--secondary" disabled={busy} onClick={() => run(() => api.smashrunDisconnect())}>
                Frakobl Smashrun
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="u-card__meta">Ikke forbundet. Forbind din Smashrun-konto for at se dine løb her.</p>
            {!me.smashrun.configured && (
              <div className="u-notice u-notice--warning" role="status">
                <b className="u-notice__level">Ikke sat op</b>
                <span>Smashrun er ikke sat op på serveren endnu.</span>
              </div>
            )}
            <div>
              <button type="button" className="u-btn u-btn--primary" disabled={busy || !me.smashrun.configured} onClick={() => connect("smashrun")}>
                Forbind Smashrun
              </button>
            </div>
          </>
        )}
      </section>

      <section className="u-card" aria-labelledby="strava-title" style={{ display: "grid", gap: 12 }}>
        <h2 id="strava-title" className="u-h2">Strava</h2>
        {me.strava.connected ? (
          <>
            <p className="u-card__meta">Forbundet{me.strava.athlete_id ? ` (atlet ${me.strava.athlete_id})` : ""}. Dine løb hentes automatisk.</p>
            {confirmDisconnect ? (
              <div style={{ display: "grid", gap: 8 }}>
                <p>Frakobl Strava? Appen holder op med at hente nye løb. Dine gemte løb bliver liggende.</p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button type="button" className="u-btn u-btn--primary" disabled={busy} onClick={() => run(async () => { await api.stravaDisconnect(); setConfirmDisconnect(false); })}>
                    Ja, frakobl
                  </button>
                  <button type="button" className="u-btn u-btn--secondary" onClick={() => setConfirmDisconnect(false)}>Annuller</button>
                </div>
              </div>
            ) : (
              <div>
                <button type="button" className="u-btn u-btn--secondary" onClick={() => setConfirmDisconnect(true)}>Frakobl Strava</button>
              </div>
            )}
          </>
        ) : (
          <>
            <p className="u-card__meta">Ikke forbundet. Stravas API kræver nu et Strava-abonnement, så Smashrun er den nemmeste kilde.</p>
            <div>
              <button type="button" className="u-btn u-btn--primary" disabled={busy || !me.strava.configured} onClick={() => connect("strava")}>
                Forbind Strava
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
