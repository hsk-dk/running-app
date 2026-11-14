import { useEffect, useState } from "react";
import { api } from "../api";
import { Challenge, WEEKDAY_NAMES, WEEKDAY_SHORT, dayMessage, planText, unitText } from "../lib/challenge";

const field: React.CSSProperties = { minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", background: "var(--color-surface)" };

function WeekDots({ c }: { c: Challenge }) {
  return (
    <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", gap: 8 }} aria-label="Ugen">
      {c.week.map((d, i) => {
        const done = d.status === "done";
        const partial = d.status === "partial";
        const today = d.status === "today";
        const rest = d.status === "rest" || d.status === "before";
        return (
          <li key={d.date} style={{ display: "grid", justifyItems: "center", gap: 2 }}>
            <span
              role="img"
              aria-label={`${WEEKDAY_NAMES[i]}: ${done ? "klaret" : partial ? "i gang" : rest ? "fri" : today ? "i dag" : d.status === "future" ? "kommer" : "ingen"}`}
              style={{
                width: 26,
                height: 26,
                borderRadius: 13,
                display: "grid",
                placeItems: "center",
                fontSize: 13,
                fontWeight: 700,
                color: done ? "#fff" : "var(--color-text-muted)",
                background: done ? "var(--data-1)" : partial ? "color-mix(in srgb, var(--data-1) 35%, white)" : "transparent",
                border: today ? "2px solid var(--data-1)" : rest ? "1.5px dashed var(--color-border-control)" : done || partial ? "none" : "1.5px solid var(--color-border-control)",
              }}
            >
              {done ? "✓" : ""}
            </span>
            <span className="u-card__meta" style={{ fontSize: 11 }}>{WEEKDAY_SHORT[i]}</span>
          </li>
        );
      })}
    </ol>
  );
}

function One({ c, onChanged, onEdit }: { c: Challenge; onChanged: (c: Challenge) => void; onEdit: () => void }) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const u = unitText(c.unit);

  async function save(count: number) {
    setBusy(true);
    setError("");
    try {
      onChanged(await api.logChallenge(c.id, count));
      setValue("");
    } catch (e: any) {
      setError(e?.message || "Det kunne ikke gemmes.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 10, padding: 14, border: "1px solid var(--color-border)", borderRadius: 12, background: "var(--color-surface)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap", alignItems: "baseline" }}>
        <h3 className="u-h3" style={{ margin: 0 }}>{c.name}</h3>
        <span className="u-card__meta">{c.planned_week > 0 ? `${c.done_week} af ${c.planned_week} ${c.planned_week === 1 ? "dag" : "dage"} i denne uge` : ""}</span>
      </div>

      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        {c.today_target !== null ? (
          <>
            <span style={{ fontSize: 44, fontWeight: 700, lineHeight: 1 }}>{c.today_target}</span>
            <span style={{ fontSize: 18 }}>{u} i dag</span>
          </>
        ) : null}
        <span className="u-card__meta" role="status">{dayMessage(c)}</span>
      </div>

      <WeekDots c={c} />

      {c.today_target !== null && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {!c.today_done && (
            <button type="button" className="u-btn u-btn--primary" disabled={busy} onClick={() => save(c.today_target!)}>
              Jeg klarede {c.today_target}
            </button>
          )}
          <form
            style={{ display: "flex", gap: 8 }}
            onSubmit={(e) => {
              e.preventDefault();
              const n = Math.round(Number(value.replace(",", ".")));
              if (Number.isFinite(n) && n >= 0 && n <= 100000) save(n);
              else setError("Skriv et helt tal.");
            }}
          >
            <label className="u-card__meta" style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span>{c.today_done ? "Ret tallet" : "Eller skriv selv"}</span>
              <input inputMode="numeric" aria-label={`Antal ${c.unit} i dag`} value={value} onChange={(e) => setValue(e.target.value)} style={{ ...field, width: 90 }} />
            </label>
            <button type="submit" className="u-btn u-btn--secondary" disabled={busy || value === ""}>Gem</button>
          </form>
        </div>
      )}
      {error && <p className="u-card__meta" role="alert" style={{ margin: 0 }}>{error}</p>}

      <p className="u-card__meta" style={{ margin: 0 }}>
        {planText(c.plan, c.unit)}
        {c.best_day > 0 ? ` Din bedste dag: ${c.best_day} ${u}` : ""}
        {c.streak_days > 1 ? ` · ${c.streak_days} dage i træk` : ""}
      </p>
      <div>
        <button type="button" className="u-btn u-btn--secondary" onClick={onEdit}>Ret planen</button>
      </div>
    </div>
  );
}

type Draft = { id: number | null; name: string; unit: string; start_value: string; step: string; step_every_days: string; cap: string; rest: number[] };
const blank = (): Draft => ({ id: null, name: "Armbøjninger", unit: "stk", start_value: "5", step: "1", step_every_days: "7", cap: "", rest: [] });

function Form({ draft, setDraft, onDone, onCancel }: { draft: Draft; setDraft: (d: Draft) => void; onDone: () => void; onCancel: () => void }) {
  const [error, setError] = useState("");
  const set = (patch: Partial<Draft>) => setDraft({ ...draft, ...patch });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body = {
      name: draft.name.trim(),
      unit: draft.unit,
      start_value: Number(draft.start_value),
      step: Number(draft.step),
      step_every_days: Number(draft.step_every_days),
      cap: draft.cap.trim() === "" ? null : Number(draft.cap),
      rest_weekdays: draft.rest,
    };
    if (!body.name || !(body.start_value >= 1) || !(body.step >= 0) || !(body.step_every_days >= 1)) {
      setError("Giv udfordringen et navn og et startmål på mindst 1.");
      return;
    }
    try {
      if (draft.id === null) await api.createChallenge(body);
      else await api.updateChallenge(draft.id, body);
      onDone();
    } catch (err: any) {
      setError(err?.message || "Det kunne ikke gemmes.");
    }
  }

  return (
    <form onSubmit={submit} style={{ display: "grid", gap: 12, padding: 14, border: "1px solid var(--color-border)", borderRadius: 12, background: "var(--color-surface)" }}>
      <h3 className="u-h3" style={{ margin: 0 }}>{draft.id === null ? "Ny daglig udfordring" : "Ret planen"}</h3>
      <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
        Hvad vil du blive bedre til?
        <input value={draft.name} maxLength={40} onChange={(e) => set({ name: e.target.value })} style={field} />
      </label>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
          Måles i
          <select value={draft.unit} onChange={(e) => set({ unit: e.target.value })} style={field}>
            <option value="stk">stk. (fx armbøjninger)</option>
            <option value="sek">sekunder (fx planke)</option>
            <option value="min">minutter</option>
          </select>
        </label>
        <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
          Start med
          <input inputMode="numeric" value={draft.start_value} onChange={(e) => set({ start_value: e.target.value })} style={{ ...field, width: 90 }} />
        </label>
        <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
          Lægges oven i
          <input inputMode="numeric" value={draft.step} onChange={(e) => set({ step: e.target.value })} style={{ ...field, width: 90 }} />
        </label>
        <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
          Hver … dage
          <input inputMode="numeric" value={draft.step_every_days} onChange={(e) => set({ step_every_days: e.target.value })} style={{ ...field, width: 90 }} />
        </label>
        <label className="u-card__meta" style={{ display: "grid", gap: 4 }}>
          Stop ved (valgfrit)
          <input inputMode="numeric" value={draft.cap} onChange={(e) => set({ cap: e.target.value })} style={{ ...field, width: 110 }} />
        </label>
      </div>
      <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="u-card__meta">Fridage</legend>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {WEEKDAY_NAMES.map((n, i) => {
            const on = draft.rest.includes(i);
            return (
              <button key={n} type="button" className={`u-btn ${on ? "u-btn--primary" : "u-btn--secondary"}`} aria-pressed={on} onClick={() => set({ rest: on ? draft.rest.filter((x) => x !== i) : [...draft.rest, i] })}>
                {n.slice(0, 3)}
              </button>
            );
          })}
        </div>
      </fieldset>
      {error && <p className="u-card__meta" role="alert" style={{ margin: 0 }}>{error}</p>}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="submit" className="u-btn u-btn--primary">Gem</button>
        <button type="button" className="u-btn u-btn--secondary" onClick={onCancel}>Annuller</button>
        {draft.id !== null && (
          <button
            type="button"
            className="u-btn u-btn--secondary"
            onClick={async () => {
              if (window.confirm("Vil du lægge udfordringen væk? Dine tal bliver gemt, men den vises ikke mere.")) {
                await api.deleteChallenge(draft.id!);
                onDone();
              }
            }}
          >
            Læg væk
          </button>
        )}
      </div>
    </form>
  );
}

/** Daily challenges: today's target, one tap to say you did it, and a calm week. Nothing here ever says you failed. */
export default function ChallengeCard() {
  const [list, setList] = useState<Challenge[] | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);

  const load = () => api.getChallenges().then(setList).catch(() => setList([])); // a bonus: everything else works without it
  useEffect(() => {
    load();
  }, []);

  if (list === null) return null;

  return (
    <section className="u-card" aria-labelledby="challenge-title" style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <h2 id="challenge-title" className="u-h2">{list.length === 1 ? "Dagens udfordring" : "Dagens udfordringer"}</h2>
        {draft === null && (
          <button type="button" className="u-btn u-btn--secondary" onClick={() => setDraft(blank())}>
            {list.length === 0 ? "Lav en daglig udfordring" : "Ny udfordring"}
          </button>
        )}
      </div>
      {list.length === 0 && draft === null && (
        <p className="u-card__meta" style={{ margin: 0 }}>Vil du blive bedre til noget, fx armbøjninger eller planke? Lav en lille plan, der vokser langsomt, og skriv hver dag, hvor mange du nåede.</p>
      )}
      {list.map((c) =>
        draft && draft.id === c.id ? null : (
          <One
            key={c.id}
            c={c}
            onChanged={(next) => setList((l) => (l ?? []).map((x) => (x.id === next.id ? next : x)))}
            onEdit={() =>
              setDraft({ id: c.id, name: c.name, unit: c.unit, start_value: String(c.plan.start_value), step: String(c.plan.step), step_every_days: String(c.plan.step_every_days), cap: c.plan.cap ? String(c.plan.cap) : "", rest: c.plan.rest_weekdays })
            }
          />
        ),
      )}
      {draft && (
        <Form
          draft={draft}
          setDraft={setDraft}
          onCancel={() => setDraft(null)}
          onDone={() => {
            setDraft(null);
            load();
          }}
        />
      )}
    </section>
  );
}
