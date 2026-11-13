import { useState } from "react";
import { api } from "../api";

export type SourceNotice = { source: "strava" | "smashrun"; result: "connected" | "denied" } | null;

type Me = {
  strava: { connected: boolean; configured: boolean };
  smashrun: { connected: boolean; configured: boolean };
};

const NAMES = { strava: "Strava", smashrun: "Smashrun" } as const;

/** Asks the person to connect where their runs come from, and says what happened when they come back. */
export default function SourceBanner({ me, notice, onDismiss }: { me: Me; notice: SourceNotice; onDismiss: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasSource = me.smashrun.connected || me.strava.connected;

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const { url } = await api.smashrunConnect();
      window.location.href = url;
    } catch (e: any) {
      setError(e.message || "Kunne ikke starte forbindelsen til Smashrun");
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 12, marginBottom: 20 }}>
      {notice?.result === "connected" && (
        <div className="u-notice" role="status">
          <b className="u-notice__level">Forbundet</b>
          <span>{NAMES[notice.source]} er forbundet. Dine løb hentes nu, og de dukker op om lidt.</span>
          <button type="button" className="u-btn u-btn--secondary" onClick={onDismiss}>Luk</button>
        </div>
      )}
      {notice?.result === "denied" && (
        <div className="u-notice u-notice--warning" role="status">
          <b className="u-notice__level">Afvist</b>
          <span>{NAMES[notice.source]} blev ikke forbundet. Du kan prøve igen, når du vil.</span>
          <button type="button" className="u-btn u-btn--secondary" onClick={onDismiss}>Luk</button>
        </div>
      )}
      {!hasSource && (
        <section className="u-card" aria-labelledby="connect-title" style={{ display: "grid", gap: 8 }}>
          <h2 id="connect-title" className="u-h2">Forbind dine løb</h2>
          <p className="u-card__meta">
            Appen henter dine løb fra Smashrun. Du kan altid frakoble igen under Mere → Mig.
          </p>
          {!me.smashrun.configured && (
            <div className="u-notice u-notice--warning" role="status">
              <b className="u-notice__level">Ikke sat op</b>
              <span>Smashrun er ikke sat op på serveren endnu. Bed administratoren om at sætte Smashrun-nøglerne.</span>
            </div>
          )}
          {error && (
            <div className="u-notice u-notice--error" role="alert">
              <b className="u-notice__level">Fejl</b>
              <span>{error}</span>
            </div>
          )}
          <div>
            <button type="button" className="u-btn u-btn--primary" onClick={connect} disabled={busy || !me.smashrun.configured}>
              {busy ? "Sender dig til Smashrun…" : "Forbind Smashrun"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
