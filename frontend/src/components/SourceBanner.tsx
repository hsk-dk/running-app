import { useState } from "react";
import { api } from "../api";
import { tokenNotice } from "../lib/token";

export type SourceNotice = { source: "strava" | "smashrun"; result: "connected" | "denied" } | null;

type Me = {
  strava: { connected: boolean; configured: boolean };
  smashrun: { connected: boolean; configured: boolean; mode?: string | null; expires_at?: string | null; expired?: boolean };
};

const NAMES = { strava: "Strava", smashrun: "Smashrun" } as const;

/** Asks the person to connect where their runs come from, and says what happened when they come back. */
export default function SourceBanner({ me, notice, onDismiss, onOpenMe }: { me: Me; notice: SourceNotice; onDismiss: () => void; onOpenMe: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasSource = me.smashrun.connected || me.strava.connected;
  const expiry = tokenNotice(me.smashrun);

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
      {expiry && (
        <div className={`u-notice u-notice--${expiry.level}`} role={expiry.level === "error" ? "alert" : "status"}>
          <b className="u-notice__level">{expiry.level === "error" ? "Udløbet" : "Snart"}</b>
          <span>{expiry.text}</span>
          <button type="button" className="u-btn u-btn--secondary" onClick={onOpenMe}>Åbn Mig</button>
        </div>
      )}
      {!hasSource && (
        <section className="u-card" aria-labelledby="connect-title" style={{ display: "grid", gap: 8 }}>
          <h2 id="connect-title" className="u-h2">Forbind dine løb</h2>
          <p className="u-card__meta">
            Appen henter dine løb fra Smashrun. Du kan altid frakoble igen under Mere → Mig.
          </p>

          {error && (
            <div className="u-notice u-notice--error" role="alert">
              <b className="u-notice__level">Fejl</b>
              <span>{error}</span>
            </div>
          )}
          <div>
            {me.smashrun.configured ? (
              <button type="button" className="u-btn u-btn--primary" onClick={connect} disabled={busy}>
                {busy ? "Sender dig til Smashrun…" : "Forbind Smashrun"}
              </button>
            ) : (
              <button type="button" className="u-btn u-btn--primary" onClick={onOpenMe}>
                Forbind Smashrun
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
