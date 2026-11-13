import { useState } from "react";
import { api } from "../api";
import { SHARING_LEVELS, SharingLevel } from "../lib/sharing";
import { tokenNotice } from "../lib/token";

type Me = {
  display_name: string;
  username: string;
  role: string;
  sharing_level: SharingLevel;
  family_sharing_enabled: boolean;
  strava: { connected: boolean; configured: boolean; athlete_id: string | null };
  smashrun: { connected: boolean; configured: boolean; mode?: string | null; expires_at?: string | null; expired?: boolean };
  runna: { connected: boolean; last_sync_at: string | null; last_error: string | null };
};

/** Your own settings: who sees your runs, and which Strava the app reads. */
export default function MePage({ me, onChanged }: { me: Me; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [token, setToken] = useState("");
  const [runnaUrl, setRunnaUrl] = useState("");

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
            <p className="u-card__meta">
              Forbundet{me.smashrun.mode === "token" ? " med et personligt token" : ""}. Dine løb hentes herfra.
              {me.smashrun.mode === "token" &&
                (me.smashrun.expires_at
                  ? ` Tokenet gælder til ${me.smashrun.expires_at}.`
                  : " Smashrun oplyser ikke, hvornår tokenet udløber. Virker synkroniseringen en dag ikke, så indsæt et nyt.")}
            </p>
            {tokenNotice(me.smashrun) && (
              <div className={`u-notice u-notice--${tokenNotice(me.smashrun)!.level}`} role="status">
                <b className="u-notice__level">{me.smashrun.expired ? "Udløbet" : "Snart"}</b>
                <span>{tokenNotice(me.smashrun)!.text}</span>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" className="u-btn u-btn--secondary" disabled={busy} onClick={() => run(() => api.smashrunDisconnect())}>
                Frakobl Smashrun
              </button>
            </div>
          </>
        ) : (
          <p className="u-card__meta">Ikke forbundet.</p>
        )}

        {(!me.smashrun.connected || me.smashrun.mode === "token") && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!token.trim()) return;
              run(async () => {
                await api.smashrunToken(token);
                setToken("");
              });
            }}
            style={{ display: "grid", gap: 8 }}
          >
            <label htmlFor="smashrun-token" className="u-card__meta">
              {me.smashrun.connected ? "Indsæt et nyt personligt token" : "Personligt token"}
            </label>
            <input
              id="smashrun-token"
              type="password"
              autoComplete="off"
              spellCheck={false}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              style={{ minHeight: 44, padding: "0 12px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", width: "100%", boxSizing: "border-box" }}
            />
            <details>
              <summary className="u-card__meta" style={{ cursor: "pointer", minHeight: 44, display: "flex", alignItems: "center" }}>Sådan får du tokenet</summary>
              <ol className="u-card__meta" style={{ margin: "4px 0 0", paddingLeft: 20, display: "grid", gap: 4 }}>
                <li>Åbn <a href="https://api.smashrun.com/v1/documentation" target="_blank" rel="noreferrer">Smashruns dokumentation</a> og klik på API Explorer.</li>
                <li>Skriv <b>client</b> i feltet og tryk Connect. Log ind hos Smashrun.</li>
                <li>Kopiér access token og indsæt det her.</li>
              </ol>
              <p className="u-card__meta" style={{ marginTop: 8 }}>
                Tokenet virker i ca. 12 uger. Du kan bede Smashrun (api@smashrun.com) om at forlænge det, eller bruge en app-nøgle, som fornyer sig selv.
              </p>
            </details>
            <div>
              <button type="submit" className="u-btn u-btn--primary" disabled={busy || !token.trim()}>
                Gem token
              </button>
            </div>
          </form>
        )}

        {me.smashrun.configured && !me.smashrun.connected && (
          <div>
            <button type="button" className="u-btn u-btn--secondary" disabled={busy} onClick={() => connect("smashrun")}>
              Forbind via Smashrun i stedet
            </button>
          </div>
        )}
      </section>

      <section className="u-card" aria-labelledby="runna-title" style={{ display: "grid", gap: 12 }}>
        <h2 id="runna-title" className="u-h2">Runna-plan</h2>
        {me.runna.connected ? (
          <>
            <p className="u-card__meta">
              Forbundet. Din plan hentes fra Runna, og dine løb får Runnas navne.
              {me.runna.last_sync_at && ` Sidst hentet ${new Date(me.runna.last_sync_at).toLocaleString("da-DK", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}.`}
            </p>
            {me.runna.last_error && (
              <div className="u-notice u-notice--error" role="alert">
                <b className="u-notice__level">Fejl</b>
                <span>{me.runna.last_error}</span>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" className="u-btn u-btn--secondary" disabled={busy} onClick={() => run(() => api.runnaSync())}>
                Hent planen nu
              </button>
              <button type="button" className="u-btn u-btn--secondary" disabled={busy} onClick={() => run(() => api.runnaDisconnect())}>
                Frakobl Runna
              </button>
            </div>
          </>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!runnaUrl.trim()) return;
              run(async () => {
                await api.runnaConnect(runnaUrl);
                setRunnaUrl("");
              });
            }}
            style={{ display: "grid", gap: 8 }}
          >
            <p className="u-card__meta">Ikke forbundet. Indsæt dit Runna-kalenderlink for at hente din plan.</p>
            <label htmlFor="runna-link" className="u-card__meta">Runna-kalenderlink</label>
            <input
              id="runna-link"
              type="password"
              autoComplete="off"
              spellCheck={false}
              placeholder="https://cal.runna.com/…"
              value={runnaUrl}
              onChange={(e) => setRunnaUrl(e.target.value)}
              style={{ minHeight: 44, padding: "0 12px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", width: "100%", boxSizing: "border-box" }}
            />
            <details>
              <summary className="u-card__meta" style={{ cursor: "pointer", minHeight: 44, display: "flex", alignItems: "center" }}>Sådan finder du linket</summary>
              <p className="u-card__meta" style={{ marginTop: 4 }}>
                Åbn Runna-appen, gå til <b>Connected Apps &amp; Devices</b> og vælg kalender. Kopiér iCalendar-linket (det begynder med cal.runna.com).
                Dine planlagte løb hentes herfra; løb, du selv har oprettet, bliver ikke overskrevet.
              </p>
            </details>
            <div>
              <button type="submit" className="u-btn u-btn--primary" disabled={busy || !runnaUrl.trim()}>
                Gem link
              </button>
            </div>
          </form>
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
