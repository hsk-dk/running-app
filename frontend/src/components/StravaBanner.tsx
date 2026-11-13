import { useState } from "react";
import { api } from "../api";

export type StravaNotice = "connected" | "denied" | null;

type Me = { strava: { connected: boolean; configured: boolean } };

/** Asks the person to connect their own Strava, and says what happened when they come back from Strava. */
export default function StravaBanner({ me, notice, onDismiss }: { me: Me; notice: StravaNotice; onDismiss: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const { url } = await api.stravaConnect();
      window.location.href = url;
    } catch (e: any) {
      setError(e.message || "Kunne ikke starte forbindelsen til Strava");
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 12, marginBottom: 20 }}>
      {notice === "connected" && (
        <div className="u-notice" role="status">
          <b className="u-notice__level">Forbundet</b>
          <span>Strava er forbundet. Dine løb hentes nu, og de dukker op om lidt.</span>
          <button type="button" className="u-btn u-btn--secondary" onClick={onDismiss}>Luk</button>
        </div>
      )}
      {notice === "denied" && (
        <div className="u-notice u-notice--warning" role="status">
          <b className="u-notice__level">Afvist</b>
          <span>Strava blev ikke forbundet. Du kan prøve igen, når du vil.</span>
          <button type="button" className="u-btn u-btn--secondary" onClick={onDismiss}>Luk</button>
        </div>
      )}
      {!me.strava.connected && (
        <section className="u-card" aria-labelledby="connect-title" style={{ display: "grid", gap: 8 }}>
          <h2 id="connect-title" className="u-h2">Forbind din Strava</h2>
          <p className="u-card__meta">
            Appen henter dine løb fra din egen Strava-konto. Du kan altid frakoble igen under Mere → Mig.
          </p>
          {!me.strava.configured && (
            <div className="u-notice u-notice--warning" role="status">
              <b className="u-notice__level">Ikke sat op</b>
              <span>Strava er ikke sat op på serveren endnu. Bed administratoren om at sætte Strava-nøglerne.</span>
            </div>
          )}
          {error && (
            <div className="u-notice u-notice--error" role="alert">
              <b className="u-notice__level">Fejl</b>
              <span>{error}</span>
            </div>
          )}
          <div>
            <button type="button" className="u-btn u-btn--primary" onClick={connect} disabled={busy || !me.strava.configured}>
              {busy ? "Sender dig til Strava…" : "Forbind Strava"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
