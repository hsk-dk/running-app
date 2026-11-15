import { useEffect, useState } from "react";
import { api } from "../api";
import { COUNTS_LABEL, INTERVAL_WEEKS, Reward, intervalNote, perWeekText, suggestCost } from "../lib/rewards";

type Person = { id: number; name: string; username: string; role: string; is_child: boolean };
type Goal = { target_km: number | null; km: number; month: string };

/** For the parents: who is a child, and the family's monthly goal. */
export default function FamilySettings({ goal, reward, pace, onChanged }: { goal: Goal; reward: Reward | null; pace: { people: number; per_week: number; estimated: boolean } | null; onChanged: () => void }) {
  const [rewardName, setRewardName] = useState(reward?.name ?? "");
  const [rewardCost, setRewardCost] = useState(reward ? String(reward.cost) : "");
  const [bonusNote, setBonusNote] = useState("");
  const [every, setEvery] = useState(3);
  const [counts, setCounts] = useState<"children" | "all">(reward?.counts ?? "children");
  const [people, setPeople] = useState<Person[] | null>(null);
  const [target, setTarget] = useState(goal.target_km ? String(goal.target_km) : "");
  const [message, setMessage] = useState("");
  const [meId, setMeId] = useState<number | null>(null);

  useEffect(() => {
    api.getPeople().then(setPeople).catch(() => setPeople(null));
    api.getMe().then((m: any) => setMeId(m.id)).catch(() => undefined);
  }, []);

  async function toggle(p: Person) {
    setMessage("");
    try {
      await api.setChild(p.id, !p.is_child);
      setPeople((list) => (list ?? []).map((x) => (x.id === p.id ? { ...x, is_child: !p.is_child } : x)));
      onChanged();
    } catch (e: any) {
      setMessage(e?.message || "Kunne ikke gemme.");
    }
  }

  async function saveReward(e: React.FormEvent) {
    e.preventDefault();
    const cost = Math.round(Number(rewardCost));
    if (!rewardName.trim() || !(cost >= 1 && cost <= 1000)) {
      setMessage("Skriv et navn og et antal stjerner mellem 1 og 1000.");
      return;
    }
    await run(() => api.setReward(rewardName.trim(), cost, counts), "Belønningen er gemt.");
  }

  async function run(action: () => Promise<unknown>, done: string) {
    setMessage("");
    try {
      await action();
      setMessage(done);
      onChanged();
    } catch (e: any) {
      setMessage(e?.message || "Det kunne ikke gemmes.");
    }
  }

  async function saveGoal(value: number | null) {
    setMessage("");
    try {
      await api.setFamilyGoal(value);
      setMessage(value === null ? "Målet er fjernet." : "Målet er gemt.");
      onChanged();
    } catch (e: any) {
      setMessage(e?.message || "Kunne ikke gemme målet.");
    }
  }

  return (
    <section className="u-card" aria-labelledby="family-settings-title" style={{ display: "grid", gap: 14 }}>
      <h2 id="family-settings-title" className="u-h2">Indstillinger for forældre</h2>

      <div style={{ display: "grid", gap: 8 }}>
        <p className="u-card__meta" style={{ margin: 0 }}>
          Et barn ser en enklere app uden tempo, puls, rekorder, ruter og belastning. Andre i familien ser kun barnets milepæle. Du ser, hvor ofte og hvor længe, men aldrig kilometer, tempo, puls eller steder.
        </p>
        {people === null && <p className="u-card__meta" role="status">Henter…</p>}
        {people && (
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 6 }}>
            {people.map((p) => (
              <li key={p.id}>
                <label style={{ display: "flex", gap: 10, alignItems: "center", minHeight: 44 }}>
                  <input type="checkbox" checked={p.is_child} disabled={p.id === meId} onChange={() => toggle(p)} style={{ width: 22, height: 22 }} />
                  <span>{p.name}{p.id === meId ? " (dig)" : ""} er et barn</span>
                </label>
              </li>
            ))}
          </ul>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          const v = Number(target.replace(",", "."));
          if (Number.isFinite(v) && v >= 1 && v <= 5000) saveGoal(v);
          else setMessage("Skriv et mål mellem 1 og 5000 kilometer.");
        }}
        style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}
      >
        <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
          Fælles mål pr. måned (km)
          <input
            inputMode="decimal"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            style={{ minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", width: 140 }}
          />
        </label>
        <button type="submit" className="u-btn u-btn--primary">Gem målet</button>
        {goal.target_km !== null && (
          <button type="button" className="u-btn u-btn--secondary" onClick={() => { setTarget(""); saveGoal(null); }}>Fjern målet</button>
        )}
      </form>
      <form onSubmit={saveReward} style={{ display: "grid", gap: 10, borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
        <p className="u-card__meta" style={{ margin: 0 }}>
          Fælles belønning: familien sparer stjerner sammen, fx til en biograftur. En stjerne er for en aktiv dag (mindst 15 minutter) og en klaret udfordringsdag, højst 5 om ugen pr. person, og aldrig for tempo eller kilometer. Alle, der deler, og alle børn tæller med.
        </p>
        <fieldset style={{ border: 0, padding: 0, margin: 0, display: "grid", gap: 4 }}>
          <legend className="u-card__meta">Hvem fylder bjælken?</legend>
          {(["children", "all"] as const).map((c) => (
            <label key={c} style={{ display: "flex", gap: 10, alignItems: "center", minHeight: 44 }}>
              <input type="radio" name="reward-counts" checked={counts === c} onChange={() => setCounts(c)} style={{ width: 22, height: 22 }} />
              <span>{COUNTS_LABEL[c]}{c === "children" ? " (anbefalet)" : ""}</span>
            </label>
          ))}
          <span className="u-card__meta">Med "kun børnene" kan en voksen, der løber ofte, ikke fylde bjælken alene. Er der ingen børn, tæller alle, der deler.</span>
        </fieldset>
        {pace && pace.per_week > 0 ? (
          <div style={{ display: "grid", gap: 6 }}>
            <p className="u-card__meta" style={{ margin: 0 }}>
              {pace.estimated
                ? `Der er endnu ikke nok at måle på. Jeg gætter på omkring ${perWeekText(pace.per_week)} stjerner om ugen for jer (${pace.people} personer, 3 hver).`
                : `I har fået omkring ${perWeekText(pace.per_week)} stjerner om ugen de seneste fire uger (${pace.people} personer).`}
            </p>
            <label className="u-card__meta" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              Hvor tit vil I have en belønning?
              <select value={every} onChange={(e) => setEvery(Number(e.target.value))} style={{ minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", background: "var(--color-surface)" }}>
                {INTERVAL_WEEKS.map((w) => <option key={w} value={w}>{w === 1 ? "hver uge" : `hver ${w}. uge`}</option>)}
              </select>
              <button type="button" className="u-btn u-btn--secondary" onClick={() => setRewardCost(String(suggestCost(pace.per_week, every)))}>
                Foreslå {suggestCost(pace.per_week, every)} stjerner
              </button>
            </label>
            <p className="u-card__meta" style={{ margin: 0 }}>{intervalNote(every)}</p>
          </div>
        ) : null}
        <div style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}>
          <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
            Hvad sparer vi til?
            <input value={rewardName} maxLength={40} onChange={(e) => setRewardName(e.target.value)} placeholder="Biograftur" style={{ minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", width: 200 }} />
          </label>
          <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
            Stjerner
            <input inputMode="numeric" value={rewardCost} onChange={(e) => setRewardCost(e.target.value)} style={{ minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", width: 100 }} />
          </label>
          <button type="submit" className="u-btn u-btn--primary">{reward ? "Gem ændringen" : "Start belønningen"}</button>
        </div>
        {reward && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span className="u-card__meta">{reward.stars} af {reward.cost} stjerner.</span>
            {reward.reached && <button type="button" className="u-btn u-btn--primary" onClick={() => run(() => api.redeemReward(), "Belønningen er givet. Den næste starter i morgen, og det, der var til overs, er med.")}>Giv belønningen</button>}
            <button type="button" className="u-btn u-btn--secondary" onClick={() => { if (window.confirm("Vil du fjerne belønningen? Stjernerne er stadig gemt.")) run(() => api.clearReward(), "Belønningen er fjernet."); }}>Fjern belønningen</button>
          </div>
        )}
      </form>

      {people && people.length > 0 && (
        <div style={{ display: "grid", gap: 8, borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
          <p className="u-card__meta" style={{ margin: 0 }}>Bonusstjerne: for indsats, der ikke kan måles, fx at blive ved, selv om det var hårdt. Højst 3 om dagen til samme person.</p>
          <label className="u-card__meta" style={{ display: "grid", gap: 4, maxWidth: 360 }}>
            Hvorfor? (valgfrit)
            <input value={bonusNote} maxLength={80} onChange={(e) => setBonusNote(e.target.value)} style={{ minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit" }} />
          </label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {people.map((p) => (
              <button key={p.id} type="button" className="u-btn u-btn--secondary" onClick={() => run(() => api.giveBonus(p.id, bonusNote), `${p.name} fik en bonusstjerne.`).then(() => setBonusNote(""))}>
                ⭐ Giv {p.name} en stjerne
              </button>
            ))}
          </div>
        </div>
      )}

      <p className="u-card__meta" role="status" style={{ margin: 0 }}>{message}</p>
    </section>
  );
}
