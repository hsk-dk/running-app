import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "../api";

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: 10,
  padding: 16,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "12px 16px",
  border: "1px solid #d1d5db",
  borderRadius: 8,
  background: "#ffffff",
  fontSize: 14,
  boxSizing: "border-box",
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
  padding: "8px 12px",
    borderRadius: 6,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#6b7280",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 500,
};

const compactButtonStyle: React.CSSProperties = {
  padding: "3px 7px",
  borderRadius: 6,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#6b7280",
  cursor: "pointer",
  fontSize: 11,
  fontWeight: 500,
  lineHeight: 1.1,
};

const dialogActionButtonStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: 6,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#6b7280",
  cursor: "pointer",
  fontSize: 12,
  fontWeight: 500,
  whiteSpace: "nowrap",
};

const dangerButtonStyle: React.CSSProperties = {
  ...dialogActionButtonStyle,
    color: "#b91c1c",
  border: "1px solid #fecaca",
  background: "#fff7f7",
};

const activeFilterButtonStyle: React.CSSProperties = {
  ...secondaryButtonStyle,
  background: "#eef2ff",
  border: "1px solid #c7d2fe",
  color: "#4338ca",
};

const modalBackdropStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.32)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 24,
  zIndex: 1000,
  boxSizing: "border-box",
};

const modalStyle: React.CSSProperties = {
  width: "min(860px, calc(100vw - 48px))",
  maxHeight: "calc(100vh - 48px)",
  overflowY: "auto",
  overflowX: "hidden",
  background: "#ffffff",
  borderRadius: 14,
  border: "1px solid #e5e7eb",
  boxShadow: "0 20px 50px rgba(0,0,0,0.25)",
  padding: 20,
  boxSizing: "border-box",
  };

const modalHeaderStyle: React.CSSProperties = {
  position: "sticky",
  top: -20,
  zIndex: 2,
  background: "#ffffff",
  paddingTop: 20,
  paddingBottom: 12,
  marginBottom: 16,
  borderBottom: "1px solid #e5e7eb",
};

function formatDate(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("da-DK");
}

function parseDateOnly(value?: string) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function daysBetween(a?: string, b?: string) {
  const da = parseDateOnly(a);
  const db = parseDateOnly(b);
  if (!da || !db) return Number.MAX_SAFE_INTEGER;
  const ms = Math.abs(da.getTime() - db.getTime());
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

function getActivityComparableValue(activity: any, targetType: "time" | "distance") {
    if (targetType === "distance") return Number(activity.distance_km ?? 0);
  return Number(activity.duration_min ?? 0);
}

function getIsoWeekKey(value?: string) {
  const d = parseDateOnly(value);
  if (!d) return "";
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNum = Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(weekNum).padStart(2, "0")}`;
}

function getCurrentIsoWeekKey() {
  return getIsoWeekKey(new Date().toISOString());
}

function isAwaiting(plannedDate?: string, toleranceDays = 1) {
  const d = parseDateOnly(plannedDate);
  if (!d) return false;
  const deadline = new Date(d);
  deadline.setDate(deadline.getDate() + toleranceDays);
  return new Date() <= deadline;
}

function metricTone(status: string) {
  if (status === "gennemført" || status === "Grøn") {
    return { bg: "#ecfdf5", border: "#bbf7d0", color: "#166534" };
  }
  if (status === "forkortet" || status === "Gul") {
    return { bg: "#fffbeb", border: "#fde68a", color: "#92400e" };
  }
  if (status === "sprunget over" || status === "Rød") {
        return { bg: "#fef2f2", border: "#fecaca", color: "#991b1b" };
  }
  if (status === "planlagt") {
    return { bg: "#f8fafc", border: "#cbd5e1", color: "#475569" };
  }
  if (status === "flyttet") {
    return { bg: "#eef2ff", border: "#c7d2fe", color: "#4338ca" };
  }
  return { bg: "#f8fafc", border: "#e2e8f0", color: "#475569" };
}

function StatusBadge({ value }: { value: string }) {
  const tone = metricTone(value);
  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        background: tone.bg,
        border: `1px solid ${tone.border}`,
        color: tone.color,
        whiteSpace: "nowrap",
      }}
    >
      {value}
    </span>
  );
}

function OverrideBadge() {
  return (
    <span
          style={{
        display: "inline-block",
        padding: "3px 8px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        background: "#f8fafc",
        border: "1px solid #cbd5e1",
        color: "#475569",
        whiteSpace: "nowrap",
      }}
    >
      Manuel
    </span>
  );
}

function OptionalBadge() {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 8px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        background: "#faf5ff",
        border: "1px solid #e9d5ff",
        color: "#7c3aed",
        whiteSpace: "nowrap",
      }}
    >
      Valgfri
    </span>
  );
  }

function AwaitingBadge() {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 8px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        background: "#eff6ff",
        border: "1px solid #bfdbfe",
        color: "#1d4ed8",
        whiteSpace: "nowrap",
      }}
    >
      Afventer
    </span>
  );
}

type FilterKey =
  | "alle"
  | "planlagt"
  | "gennemført"
  | "forkortet"
  | "sprunget over"
  | "flyttet";

function Modal({
  children,
  onClose,
  closeDisabled = false,
}: {
    children: React.ReactNode;
  onClose: () => void;
  closeDisabled?: boolean;
}) {
  return createPortal(
    <div
      style={modalBackdropStyle}
      onClick={() => {
        if (!closeDisabled) onClose();
      }}
    >
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>,
    document.body
  );
}

export default function PlanPage({
  plannedRuns,
  activities,
  onAddPlannedRun,
  onPlanningChanged,
}: {
  plannedRuns: any[];
  activities: any[];
  onAddPlannedRun: (payload: {
    planned_date: string;
    session_type: string;
    target_type: "time" | "distance";
    target_value: number;
    optional?: boolean;
    notes?: string;
  }) => Promise<void>;
    onPlanningChanged: () => Promise<void>;
  loading: boolean;
  onRunAction: (action: "ingest" | "metrics" | "plan") => void;
  error: string | null;
}) {
  const [form, setForm] = useState({
    planned_date: "",
    session_type: "easy",
    target_type: "time" as "time" | "distance",
    target_value: 30,
    optional: false,
    notes: "",
  });

  const [filter, setFilter] = useState<FilterKey>("alle");
  const [rowLoadingId, setRowLoadingId] = useState<number | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [editing, setEditing] = useState<any | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [showAllCandidates, setShowAllCandidates] = useState(false);

  useEffect(() => {
    const modalOpen = createOpen || !!editing;
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;

    if (modalOpen) {
      document.body.style.overflow = "hidden";
      document.documentElement.style.overflow = "hidden";
    }

    return () => {
      document.body.style.overflow = previousBodyOverflow;
           document.documentElement.style.overflow = previousHtmlOverflow;
    };
  }, [createOpen, editing]);

  const filteredRuns = useMemo(() => {
    if (filter === "alle") return plannedRuns;
    return plannedRuns.filter((p) => p.status === filter);
  }, [plannedRuns, filter]);

  const currentWeek = useMemo(() => {
    const weekKey = getCurrentIsoWeekKey();
    const runs = plannedRuns.filter((p) => getIsoWeekKey(p.planned_date) === weekKey);
    const mandatory = runs.filter((p) => !p.optional);
    const relevantNow = mandatory.filter((p) => {
      if (p.status !== "planlagt") return true;
      return !isAwaiting(p.planned_date, 1);
    });
    const completed = relevantNow.filter((p) => p.status === "gennemført").length;
    const shortened = relevantNow.filter((p) => p.status === "forkortet").length;

    let score = "Grøn";
    if (relevantNow.length > 0) {
      if (completed === relevantNow.length) score = "Grøn";
      else if (completed + shortened > 0) score = "Gul";
      else score = "Rød";
    }

    return {
      weekKey,
      total: runs.length,
      mandatory: mandatory.length,
      relevantNow: relevantNow.length,
      completed,
      shortened,
      awaiting: mandatory.filter(
                (p) => p.status === "planlagt" && isAwaiting(p.planned_date, 1)
      ).length,
      score,
    };
  }, [plannedRuns]);

  const candidateGroups = useMemo(() => {
    if (!editing) {
      return { near: [], other: [] as any[] };
    }

    const targetType = (editing.target_type ?? "time") as "time" | "distance";
    const targetValue = Number(editing.target_value ?? 0);

    const baseCandidates = activities
      .filter((a) => {
        if (a.is_aborted) return false;
        if (!a.is_extra && a.matched_planned_run_id !== editing.id) return false;
        return true;
      })
      .map((a) => {
        const dayDiff = daysBetween(editing.planned_date, a.date);
        const comparableValue = getActivityComparableValue(a, targetType);
        const valueDiff = Math.abs(comparableValue - targetValue);

        return {
          ...a,
          dayDiff,
          valueDiff,
        };
      })
      .sort((a, b) => {
        if (a.dayDiff !== b.dayDiff) return a.dayDiff - b.dayDiff;
        return a.valueDiff - b.valueDiff;
      });
    
    const near = baseCandidates.filter((a) => a.dayDiff <= 3);
    const other = baseCandidates.filter((a) => a.dayDiff > 3);

    return { near, other };
  }, [activities, editing]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);
    setCreating(true);
    try {
      await onAddPlannedRun(form);
      await onPlanningChanged();
      setForm({
        planned_date: "",
        session_type: "easy",
        target_type: "time",
        target_value: 30,
        optional: false,
        notes: "",
      });
      setCreateOpen(false);
    } catch (e: any) {
      setLocalError(e.message || "Kunne ikke oprette træning");
    } finally {
      setCreating(false);
    }
  }

  async function handleMarkSkipped(id: number) {
    setRowLoadingId(id);
    setLocalError(null);
    try {
      await api.markPlannedRunSkipped(id);
           await onPlanningChanged();
      setEditing(null);
    } catch (e: any) {
      setLocalError(e.message || "Kunne ikke markere som sprunget over");
    } finally {
      setRowLoadingId(null);
    }
  }

  async function handleMarkRescheduled(id: number) {
    setRowLoadingId(id);
    setLocalError(null);
    try {
      await api.markPlannedRunRescheduled(id);
      await onPlanningChanged();
      setEditing(null);
    } catch (e: any) {
      setLocalError(e.message || "Kunne ikke markere som flyttet");
    } finally {
      setRowLoadingId(null);
    }
  }

  async function handleClearMatch(id: number) {
    setRowLoadingId(id);
    setLocalError(null);
    try {
      await api.clearPlannedRunMatch(id);
      await onPlanningChanged();
      setEditing(null);
    } catch (e: any) {
      setLocalError(e.message || "Kunne ikke fjerne match");
    } finally {
      setRowLoadingId(null);
    }
     }

  async function handleDelete(id: number) {
    if (!window.confirm("Er du sikker på, at du vil slette træningen?")) return;
    setRowLoadingId(id);
    setLocalError(null);
    try {
      await api.deletePlannedRun(id);
      await onPlanningChanged();
      setEditing(null);
    } catch (e: any) {
      setLocalError(e.message || "Kunne ikke slette træning");
    } finally {
      setRowLoadingId(null);
    }
  }

  async function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;

    setSavingEdit(true);
    setLocalError(null);
    try {
      await api.updatePlannedRun(editing.id, {
        planned_date: editing.planned_date,
        session_type: editing.session_type,
        target_type: editing.target_type,
        target_value: Number(editing.target_value),
        optional: editing.optional,
        notes: editing.notes,
      });
      await onPlanningChanged();
      setEditing(null);
    } catch (e: any) {
          setLocalError(e.message || "Kunne ikke gemme ændringer");
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleMatchActivity(activityId: number) {
    if (!editing) return;
    setSavingEdit(true);
    setLocalError(null);
    try {
      await api.matchActivityToPlannedRun(editing.id, activityId);
      await onPlanningChanged();
      setEditing(null);
    } catch (e: any) {
      setLocalError(e.message || "Kunne ikke vælge match");
    } finally {
      setSavingEdit(false);
    }
  }

  function openEdit(run: any) {
    setShowAllCandidates(false);
    setEditing({ ...run });
  }

  const filters: FilterKey[] = [
    "alle",
    "planlagt",
    "gennemført",
    "forkortet",
    "sprunget over",
    "flyttet",
  ];

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
          <div style={{ fontSize: 18, fontWeight: 700, color: "#243140" }}>Plan</div>
          <div style={{ fontSize: 14, color: "#425061" }}>
            Planevaluering og overstyring af planlagte træninger.
          </div>
        </div>

        <button
          type="button"
          style={primaryButtonStyle}
          onClick={() => setCreateOpen(true)}
        >
          Tilføj træning
        </button>
      </section>

      {localError && (
        <section
          style={{
            ...cardStyle,
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
          }}
               >
          {localError}
        </section>
      )}

      <section
        style={{
          ...cardStyle,
          display: "grid",
          gridTemplateColumns: "minmax(220px, 280px) 1fr",
          gap: 16,
          alignItems: "start",
        }}
      >
        <div>
          <div style={{ fontWeight: 600, color: "#374151", marginBottom: 8 }}>
            Denne uge
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <StatusBadge value={currentWeek.score} />
            <span style={{ fontSize: 13, color: "#64748b" }}>{currentWeek.weekKey}</span>
          </div>
        </div>

        <div style={{ display: "grid", gap: 6 }}>
          <div style={{ fontSize: 14, color: "#243140" }}>
            {currentWeek.completed}/{currentWeek.relevantNow} aktuelle obligatoriske pas gennemført
          </div>
          <div style={{ fontSize: 13, color: "#64748b" }}>
            {currentWeek.awaiting} obligatoriske pas afventer stadig og tæller ikke negativt endnu.
          </div>
          <div style={{ fontSize: 13, color: "#64748b" }}>
            Valgfrie træninger vises i planen, men påvirker ikke ugefarven negativt.
          </div>
        </div>
        </section>

      <section>
        <div style={cardStyle}>
          <div
            style={{
              marginBottom: 12,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <div style={{ fontWeight: 600, color: "#374151" }}>Planevaluering</div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {filters.map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  style={filter === f ? activeFilterButtonStyle : secondaryButtonStyle}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid #e5e7eb" }}>
                                Dato
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid #e5e7eb" }}>
                    Type
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid #e5e7eb" }}>
                    Mål
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid #e5e7eb" }}>
                    Faktisk
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid #e5e7eb" }}>
                    Match
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid #e5e7eb" }}>
                    Status
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid #e5e7eb" }}>
                    Handling
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredRuns.map((p) => {
                  const isBusy = rowLoadingId === p.id;
                  const awaiting = p.status === "planlagt" && isAwaiting(p.planned_date, 1);

                  return (
                    <tr key={p.id}>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid #f1f5f9" }}>
                        {formatDate(p.planned_date)}
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid #f1f5f9" }}>
                        {p.session_type}
                      </td>
                                      <td style={{ padding: "6px 8px", borderBottom: "1px solid #f1f5f9" }}>
                        {p.display_target}
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid #f1f5f9" }}>
                        {p.display_actual}
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid #f1f5f9" }}>
                        {p.matched_activity_name ?? "-"}
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid #f1f5f9" }}>
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            alignItems: "center",
                            flexWrap: "wrap",
                          }}
                        >
                          <StatusBadge value={p.status} />
                          {awaiting ? <AwaitingBadge /> : null}
                          {p.optional ? <OptionalBadge /> : null}
                          {p.manual_override ? <OverrideBadge /> : null}
                        </div>
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid #f1f5f9" }}>
                        <button
                          type="button"
                          style={compactButtonStyle}
                          disabled={isBusy}
                          onClick={() => openEdit(p)}
                        >
                          {isBusy ? "..." : "Rediger"}
                        </button>
                      </td>
                    </tr>
                             );
                })}

                {filteredRuns.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      style={{
                        padding: "18px 8px",
                        color: "#64748b",
                        textAlign: "center",
                        borderBottom: "1px solid #f1f5f9",
                      }}
                    >
                      Ingen træninger matcher det valgte filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {createOpen && (
        <Modal onClose={() => setCreateOpen(false)} closeDisabled={creating}>
          <div
            style={{
              ...modalHeaderStyle,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
            }}
          >
                 <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#243140" }}>
                Tilføj træning
              </div>
              <div style={{ fontSize: 14, color: "#64748b" }}>
                Opret en ny planlagt træning.
              </div>
            </div>

            <button
              type="button"
              style={{ ...secondaryButtonStyle, flexShrink: 0 }}
              onClick={() => setCreateOpen(false)}
              disabled={creating}
            >
              Luk
            </button>
          </div>

          <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12 }}>
            <input
              style={inputStyle}
              type="date"
              value={form.planned_date}
              onChange={(e) => setForm({ ...form, planned_date: e.target.value })}
              required
            />

            <select
              style={inputStyle}
              value={form.session_type}
              onChange={(e) => setForm({ ...form, session_type: e.target.value })}
            >
              <option value="easy">Easy</option>
              <option value="long">Lang tur</option>
                  <option value="intervals">Intervaller</option>
            </select>

            <select
              style={inputStyle}
              value={form.target_type}
              onChange={(e) =>
                setForm({
                  ...form,
                  target_type: e.target.value as "time" | "distance",
                  target_value: e.target.value === "distance" ? 5 : 30,
                })
              }
            >
              <option value="time">Tid</option>
              <option value="distance">Afstand</option>
            </select>

            <input
              style={inputStyle}
              type="number"
              step={form.target_type === "distance" ? "0.1" : "1"}
              min={0}
              value={form.target_value}
              onChange={(e) =>
                setForm({
                  ...form,
                  target_value: Number(e.target.value),
                })
              }
              required
            />

            <label
              style={{
                         display: "flex",
                gap: 8,
                alignItems: "center",
                color: "#4b5563",
                fontSize: 14,
              }}
            >
              <input
                type="checkbox"
                checked={form.optional}
                onChange={(e) => setForm({ ...form, optional: e.target.checked })}
              />
              Valgfri træning
            </label>

            <input
              style={inputStyle}
              type="text"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Noter"
            />

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="submit" style={primaryButtonStyle} disabled={creating}>
                {creating ? "Opretter..." : "Tilføj træning"}
              </button>

              <button
                type="button"
                style={secondaryButtonStyle}
                onClick={() => setCreateOpen(false)}
                disabled={creating}
              >
                Annullér
                    </button>
            </div>
          </form>
        </Modal>
      )}

      {editing && (
        <Modal onClose={() => setEditing(null)} closeDisabled={savingEdit}>
          <div
            style={{
              ...modalHeaderStyle,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#243140" }}>
                Rediger træning
              </div>
              <div style={{ fontSize: 14, color: "#64748b" }}>
                {formatDate(editing.planned_date)} · {editing.session_type}
              </div>
            </div>

            <button
              type="button"
              style={{ ...secondaryButtonStyle, flexShrink: 0 }}
              onClick={() => setEditing(null)}
              disabled={savingEdit}
            >
              Luk
            </button>
          </div>
          
          <div style={{ display: "grid", gap: 18 }}>
            <form onSubmit={handleSaveEdit} style={{ display: "grid", gap: 12 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: 12,
                }}
              >
                <input
                  style={inputStyle}
                  type="date"
                  value={editing.planned_date}
                  onChange={(e) =>
                    setEditing({ ...editing, planned_date: e.target.value })
                  }
                  required
                />

                <select
                  style={inputStyle}
                  value={editing.session_type}
                  onChange={(e) =>
                    setEditing({ ...editing, session_type: e.target.value })
                  }
                >
                  <option value="easy">Easy</option>
                  <option value="long">Lang tur</option>
                  <option value="intervals">Intervaller</option>
                </select>

                <select
                  style={inputStyle}
                  value={editing.target_type}
                         onChange={(e) =>
                    setEditing({ ...editing, target_type: e.target.value })
                  }
                >
                  <option value="time">Tid</option>
                  <option value="distance">Afstand</option>
                </select>

                <input
                  style={inputStyle}
                  type="number"
                  step={editing.target_type === "distance" ? "0.1" : "1"}
                  min={0}
                  value={editing.target_value}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      target_value: Number(e.target.value),
                    })
                  }
                  required
                />
              </div>

              <label
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                  color: "#4b5563",
                  fontSize: 14,
                }}
              >
                <input
                  type="checkbox"
                              checked={editing.optional}
                  onChange={(e) =>
                    setEditing({ ...editing, optional: e.target.checked })
                  }
                />
                Valgfri træning
              </label>

              <input
                style={inputStyle}
                type="text"
                value={editing.notes ?? ""}
                onChange={(e) => setEditing({ ...editing, notes: e.target.value })}
                placeholder="Noter"
              />

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  <button
                    type="submit"
                    style={primaryButtonStyle}
                    disabled={savingEdit}
                  >
                    {savingEdit ? "Gemmer..." : "Gem ændringer"}
                  </button>

                  <button
                         type="button"
                    style={dialogActionButtonStyle}
                    onClick={() => handleMarkSkipped(editing.id)}
                    disabled={savingEdit}
                  >
                    Sprunget over
                  </button>

                  <button
                    type="button"
                    style={dialogActionButtonStyle}
                    onClick={() => handleMarkRescheduled(editing.id)}
                    disabled={savingEdit}
                  >
                    Flyttet
                  </button>

                  <button
                    type="button"
                    style={dialogActionButtonStyle}
                    onClick={() => handleClearMatch(editing.id)}
                    disabled={savingEdit}
                  >
                    Fjern match
                  </button>
                </div>

                <div>
                  <button
                    type="button"
                    style={dangerButtonStyle}
                    onClick={() => handleDelete(editing.id)}
                    disabled={savingEdit}
                  >
                    Slet
                        </button>
                </div>
              </div>
            </form>

            {(editing.matched_activity_name || editing.match_reason) && (
              <div
                style={{
                  borderTop: "1px solid #e5e7eb",
                  paddingTop: 16,
                  display: "grid",
                  gap: 8,
                }}
              >
                <div style={{ fontWeight: 600, color: "#374151" }}>Nuværende match</div>

                {editing.matched_activity_name ? (
                  <div
                    style={{
                      padding: "10px 12px",
                      border: "1px solid #e5e7eb",
                      borderRadius: 8,
                      background: "#f8fafc",
                      display: "grid",
                      gap: 4,
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#243140" }}>
                      {editing.matched_activity_name}
                    </div>

                    <div style={{ fontSize: 13, color: "#64748b" }}>
                      {editing.matched_activity_date
                        ? `${formatDate(editing.matched_activity_date)}`
                        : "Dato ukendt"}
                        {" · "}
                      {editing.display_actual || "-"}
                    </div>

                    {editing.match_reason ? (
                      <div style={{ fontSize: 13, color: "#475569" }}>
                        <strong>Begrundelse:</strong> {editing.match_reason}
                      </div>
                    ) : null}

                    {editing.match_score !== null &&
                    editing.match_score !== undefined ? (
                      <div style={{ fontSize: 12, color: "#64748b" }}>
                        Match-score: {editing.match_score}
                      </div>
                    ) : null}
                  </div>
                ) : editing.match_reason ? (
                  <div
                    style={{
                      padding: "10px 12px",
                      border: "1px solid #e5e7eb",
                      borderRadius: 8,
                      background: "#f8fafc",
                      fontSize: 13,
                      color: "#475569",
                    }}
                  >
                    <strong>Begrundelse:</strong> {editing.match_reason}
                  </div>
                ) : null}
              </div>
            )}

            <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: 16 }}>
               <div style={{ fontWeight: 600, color: "#374151", marginBottom: 6 }}>
                Vælg match
              </div>
              <div style={{ fontSize: 13, color: "#64748b", marginBottom: 10 }}>
                Kandidater sorteres efter nærhed til planlagt dato og derefter nærhed til målet.
              </div>

              {candidateGroups.near.length > 0 && (
                <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
                    Tæt på planen
                  </div>

                  {candidateGroups.near.map((a) => (
                    <div
                      key={a.id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: 12,
                        padding: 10,
                        borderRadius: 8,
                        border: "1px solid #e5e7eb",
                        background: "#f8fafc",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: "#243140" }}>{a.name}</div>
                        <div style={{ fontSize: 13, color: "#64748b" }}>
                          {formatDate(a.date)} · {a.distance_km} km · {a.duration_min} min ·{" "}
                          {a.dayDiff} dag(e) fra planen
                        </div>
                      </div>
                      <button
                        type="button"
                        style={compactButtonStyle}
                        onClick={() => handleMatchActivity(a.id)}
                        disabled={savingEdit}
                      >
                        Vælg
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {candidateGroups.other.length > 0 && (
                <div style={{ display: "grid", gap: 8 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                    }}
                  >
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
                      Andre kandidater
                    </div>

                    <button
                      type="button"
                      style={compactButtonStyle}
                      onClick={() => setShowAllCandidates((v) => !v)}
                    >
                      {showAllCandidates ? "Skjul" : "Vis flere"}
                    </button>
                  </div>
                  
                  {showAllCandidates &&
                    candidateGroups.other.map((a) => (
                      <div
                        key={a.id}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 12,
                          padding: 10,
                          borderRadius: 8,
                          border: "1px solid #e5e7eb",
                          background: "#f8fafc",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, color: "#243140" }}>{a.name}</div>
                          <div style={{ fontSize: 13, color: "#64748b" }}>
                            {formatDate(a.date)} · {a.distance_km} km · {a.duration_min} min ·{" "}
                            {a.dayDiff} dag(e) fra planen
                          </div>
                        </div>

                        <button
                          type="button"
                          style={compactButtonStyle}
                          onClick={() => handleMatchActivity(a.id)}
                          disabled={savingEdit}
                        >
                          Vælg
                        </button>
                      </div>
                    ))}
                </div>
            )}

              {candidateGroups.near.length === 0 && candidateGroups.other.length === 0 && (
                <div style={{ color: "#64748b", fontSize: 14 }}>
                  Ingen relevante løb at matche med.
                </div>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
