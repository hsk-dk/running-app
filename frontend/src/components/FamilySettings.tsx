import { useEffect, useState } from "react";
import { api } from "../api";

type Person = { id: number; name: string; username: string; role: string; is_child: boolean };
type Goal = { target_km: number | null; km: number; month: string };

/** For the parents: who is a child, and the family's monthly goal. */
export default function FamilySettings({ goal, onChanged }: { goal: Goal; onChanged: () => void }) {
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
      <p className="u-card__meta" role="status" style={{ margin: 0 }}>{message}</p>
    </section>
  );
}
