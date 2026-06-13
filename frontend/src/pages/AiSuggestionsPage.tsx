import { useState } from "react";
import { api } from "../api";

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: 10,
  padding: 16,
};

const primaryButtonStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: 6,
  border: "1px solid transparent",
  background: "linear-gradient(to bottom right, #9dc0ff, #446ea8)",
  color: "white",
  boxShadow: "0 6px 16px rgba(0,0,0,0.18)",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 500,
};

const secondaryButtonStyle: React.CSSProperties = {
  padding: "8px 16px",
  borderRadius: 6,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#374151",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 500,
};

const SESSION_TYPE_LABELS: Record<string, string> = {
  easy: "Let løb",
  tempo: "Tempo",
  long: "Langtur",
  intervals: "Intervaller",
  recovery: "Restitution",
};

function formatDate(isoDate: string) {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString("da-DK", {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });
}

function sessionLabel(type: string) {
  return SESSION_TYPE_LABELS[type] ?? type;
}

function targetLabel(type: string, value: number | null | undefined) {
  if (value == null) return "-";
  return type === "distance" ? `${value} km` : `${value} min`;
}

interface Suggestion {
  planned_date: string;
  session_type: string;
  target_type: string;
  target_value: number | null;
  mandatory: boolean;
  notes: string | null;
}

interface AiResult {
  available: boolean;
  error: string | null;
  model?: string;
  next_week_start?: string;
  summary?: string | null;
  suggestions: Suggestion[];
}

export default function AiSuggestionsPage({
  onPlanningChanged,
}: {
  onPlanningChanged: () => void;
}) {
  const [result, setResult] = useState<AiResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [addedIds, setAddedIds] = useState<Set<number>>(new Set());
  const [addingId, setAddingId] = useState<number | null>(null);
  const [addAllLoading, setAddAllLoading] = useState(false);

  async function handleGenerate() {
    setLoading(true);
    setLocalError(null);
    setResult(null);
    setAddedIds(new Set());
    try {
      const data = await api.getAiSuggestions();
      setResult(data);
    } catch (e: any) {
      setLocalError(e.message || "Kunne ikke hente forslag");
    } finally {
      setLoading(false);
    }
  }

  async function handleAddOne(suggestion: Suggestion, index: number) {
    setAddingId(index);
    try {
      await api.addPlannedRun({
        planned_date: suggestion.planned_date,
        session_type: suggestion.session_type,
        target_type: suggestion.target_type as "time" | "distance",
        target_value: suggestion.target_value ?? 0,
        optional: !suggestion.mandatory,
        notes: suggestion.notes ?? undefined,
      });
      setAddedIds((prev) => new Set([...prev, index]));
      onPlanningChanged();
    } catch (e: any) {
      setLocalError(e.message || "Kunne ikke tilføje træning");
    } finally {
      setAddingId(null);
    }
  }

  async function handleAddAll() {
    if (!result) return;
    setAddAllLoading(true);
    setLocalError(null);
    const unadded = result.suggestions.filter((_, i) => !addedIds.has(i));
    const newAdded = new Set(addedIds);
    for (let i = 0; i < result.suggestions.length; i++) {
      if (addedIds.has(i)) continue;
      try {
        await api.addPlannedRun({
          planned_date: result.suggestions[i].planned_date,
          session_type: result.suggestions[i].session_type,
          target_type: result.suggestions[i].target_type as "time" | "distance",
          target_value: result.suggestions[i].target_value ?? 0,
          optional: !result.suggestions[i].mandatory,
          notes: result.suggestions[i].notes ?? undefined,
        });
        newAdded.add(i);
      } catch {
        // continue
      }
    }
    setAddedIds(newAdded);
    if (unadded.length > 0) onPlanningChanged();
    setAddAllLoading(false);
  }

  const allAdded =
    result !== null &&
    result.suggestions.length > 0 &&
    result.suggestions.every((_, i) => addedIds.has(i));

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <section
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#243140" }}>
            AI Træningsforslag
          </div>
          <div style={{ fontSize: 14, color: "#425061" }}>
            Generér næste uges træningsplan baseret på din Strava-historik via
            lokal AI (Ollama) eller cloud LLM.
          </div>
        </div>

        <button
          style={primaryButtonStyle}
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? "Analyserer…" : "Generér forslag"}
        </button>
      </section>

      {localError && (
        <section
          style={{
            ...cardStyle,
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
            fontSize: 14,
          }}
        >
          {localError}
        </section>
      )}

      {loading && (
        <section style={{ ...cardStyle, color: "#64748b", fontSize: 14 }}>
          AI analyserer din træningshistorik og genererer forslag… Dette kan
          tage op til et minut.
        </section>
      )}

      {result && !result.available && (
        <section
          style={{
            ...cardStyle,
            border: "1px solid #fed7aa",
            background: "#fff7ed",
          }}
        >
          <div
            style={{ fontWeight: 600, color: "#92400e", marginBottom: 6 }}
          >
            AI-tjeneste ikke tilgængelig
          </div>
          <div style={{ fontSize: 14, color: "#78350f" }}>
            {result.error ||
              "Sørg for at Ollama kører lokalt. Se env.example for konfiguration."}
          </div>
          <div style={{ fontSize: 13, color: "#92400e", marginTop: 10 }}>
            <strong>Trin for at aktivere AI:</strong>
            <ol style={{ margin: "6px 0 0 18px", lineHeight: 1.8 }}>
              <li>
                Installér{" "}
                <a
                  href="https://ollama.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "#1d4ed8" }}
                >
                  Ollama
                </a>
              </li>
              <li>
                Kør modellen:{" "}
                <code
                  style={{
                    background: "#fde68a",
                    padding: "1px 6px",
                    borderRadius: 4,
                  }}
                >
                  ollama run llama3
                </code>
              </li>
              <li>
                Sæt{" "}
                <code
                  style={{
                    background: "#fde68a",
                    padding: "1px 6px",
                    borderRadius: 4,
                  }}
                >
                  OLLAMA_URL
                </code>{" "}
                i .env (standard: http://localhost:11434)
              </li>
            </ol>
          </div>
        </section>
      )}

      {result && result.available && (
        <>
          {result.summary && (
            <section style={cardStyle}>
              <div
                style={{ fontWeight: 600, color: "#374151", marginBottom: 8 }}
              >
                Coaching-kommentar
              </div>
              <div style={{ fontSize: 14, color: "#374151", lineHeight: 1.7 }}>
                {result.summary}
              </div>
              {result.model && (
                <div
                  style={{
                    fontSize: 12,
                    color: "#94a3b8",
                    marginTop: 8,
                  }}
                >
                  Genereret af {result.model}
                  {result.next_week_start
                    ? ` · Uge starter ${result.next_week_start}`
                    : ""}
                </div>
              )}
            </section>
          )}

          {result.suggestions.length > 0 && (
            <section style={{ display: "grid", gap: 16 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <div
                  style={{ fontWeight: 600, color: "#374151", fontSize: 15 }}
                >
                  Foreslåede træninger ({result.suggestions.length})
                </div>
                {!allAdded && (
                  <button
                    style={secondaryButtonStyle}
                    onClick={handleAddAll}
                    disabled={addAllLoading || allAdded}
                  >
                    {addAllLoading ? "Tilføjer…" : "Tilføj alle til plan"}
                  </button>
                )}
              </div>

              {result.suggestions.map((s, i) => {
                const added = addedIds.has(i);
                return (
                  <div
                    key={i}
                    style={{
                      ...cardStyle,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: 16,
                      flexWrap: "wrap",
                      opacity: added ? 0.6 : 1,
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 200 }}>
                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          alignItems: "center",
                          marginBottom: 6,
                          flexWrap: "wrap",
                        }}
                      >
                        <span
                          style={{
                            fontWeight: 700,
                            color: "#243140",
                            fontSize: 15,
                          }}
                        >
                          {formatDate(s.planned_date)}
                        </span>
                        <span
                          style={{
                            background: "#eff6ff",
                            border: "1px solid #bfdbfe",
                            color: "#1e40af",
                            borderRadius: 6,
                            padding: "2px 8px",
                            fontSize: 12,
                            fontWeight: 600,
                          }}
                        >
                          {sessionLabel(s.session_type)}
                        </span>
                        {!s.mandatory && (
                          <span
                            style={{
                              background: "#faf5ff",
                              border: "1px solid #e9d5ff",
                              color: "#7c3aed",
                              borderRadius: 6,
                              padding: "2px 8px",
                              fontSize: 12,
                              fontWeight: 600,
                            }}
                          >
                            valgfri
                          </span>
                        )}
                        {added && (
                          <span
                            style={{
                              background: "#ecfdf5",
                              border: "1px solid #bbf7d0",
                              color: "#166534",
                              borderRadius: 6,
                              padding: "2px 8px",
                              fontSize: 12,
                              fontWeight: 600,
                            }}
                          >
                            ✓ Tilføjet
                          </span>
                        )}
                      </div>

                      <div style={{ fontSize: 14, color: "#374151" }}>
                        <strong>Mål:</strong>{" "}
                        {targetLabel(s.target_type, s.target_value)}
                      </div>

                      {s.notes && (
                        <div
                          style={{
                            fontSize: 13,
                            color: "#64748b",
                            marginTop: 4,
                            fontStyle: "italic",
                          }}
                        >
                          {s.notes}
                        </div>
                      )}
                    </div>

                    {!added && (
                      <button
                        style={{
                          ...secondaryButtonStyle,
                          alignSelf: "center",
                          whiteSpace: "nowrap",
                        }}
                        onClick={() => handleAddOne(s, i)}
                        disabled={addingId === i}
                      >
                        {addingId === i ? "Tilføjer…" : "Tilføj til plan"}
                      </button>
                    )}
                  </div>
                );
              })}
            </section>
          )}

          {result.suggestions.length === 0 && (
            <section style={{ ...cardStyle, color: "#64748b", fontSize: 14 }}>
              AI returnerede ingen forslag. Prøv at synkronisere Strava-data
              og prøv igen.
            </section>
          )}
        </>
      )}

      {!result && !loading && (
        <section style={{ ...cardStyle, color: "#64748b", fontSize: 14 }}>
          Klik <strong>Generér forslag</strong> for at lade AI analysere din
          træningshistorik og foreslå næste uges plan.
          <br />
          <br />
          <em>
            Kræver enten en lokal Ollama-instans eller en konfigureret cloud
            LLM (se env.example).
          </em>
        </section>
      )}
    </div>
  );
}
