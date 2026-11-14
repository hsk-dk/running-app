import { sessionTypeOptions } from "../lib/sessionTypes";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "../api";
import StatusBadge from "../components/StatusBadge";
import WeekPlanChart from "../components/WeekPlanChart";

const cardStyle: React.CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-large)",
  padding: 16,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "12px 16px",
  border: "1px solid var(--color-border-control)",
  borderRadius: 8,
  background: "var(--color-surface)",
  fontSize: 14,
  boxSizing: "border-box",
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
  background: "var(--color-surface)",
  borderRadius: 14,
  border: "1px solid var(--color-border)",
  boxShadow: "0 20px 50px rgba(0,0,0,0.25)",
  padding: 20,
  boxSizing: "border-box",
  };

const modalHeaderStyle: React.CSSProperties = {
  position: "sticky",
  top: -20,
  zIndex: 2,
  background: "var(--color-surface)",
  paddingTop: 20,
  paddingBottom: 12,
  marginBottom: 16,
  borderBottom: "1px solid var(--color-border)",
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
  label,
}: {
  children: React.ReactNode;
  onClose: () => void;
  closeDisabled?: boolean;
  label: string;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  // Move keyboard focus into the dialog and give it back when the dialog closes.
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    return () => previous?.focus?.();
  }, []);

  // Escape closes the dialog unless it is busy saving.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !closeDisabled) onCloseRef.current();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [closeDisabled]);

  return createPortal(
    <div
      style={modalBackdropStyle}
      onClick={() => {
        if (!closeDisabled) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        style={{ ...modalStyle, outline: "none" }}
        onClick={(e) => e.stopPropagation()}
      >
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
  onRunAction: (action: "ingest" | "plan") => void;
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
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
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
          <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)" }}>Plan</div>
          <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
            Planevaluering og overstyring af planlagte træninger.
          </div>
        </div>

        <button
          type="button"
          className="u-btn u-btn--primary"
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

      <WeekPlanChart
        plannedRuns={plannedRuns}
        activities={activities}
        badge={<StatusBadge value={currentWeek.score} />}
      />
      <p className="u-card__meta" style={{ marginTop: -8 }}>
        {currentWeek.awaiting} vigtige løb venter stadig og tæller ikke negativt endnu. Valgfrie
        træninger vises i planen, men påvirker ikke ugefarven negativt.
      </p>

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
            <div style={{ fontWeight: 600, color: "var(--color-text)" }}>Planevaluering</div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {filters.map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  className="u-btn u-btn--secondary"
                  aria-pressed={filter === f}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "var(--color-text-muted)" }}>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid var(--color-border)" }}>
                                Dato
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid var(--color-border)" }}>
                    Type
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid var(--color-border)" }}>
                    Mål
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid var(--color-border)" }}>
                    Faktisk
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid var(--color-border)" }}>
                    Match
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid var(--color-border)" }}>
                    Status
                  </th>
                  <th style={{ padding: "9px 8px", borderBottom: "1px solid var(--color-border)" }}>
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
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                        {formatDate(p.planned_date)}
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                        {p.session_type}
                      </td>
                                      <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                        {p.display_target}
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                        {p.display_actual}
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                        {p.matched_activity_name ?? "-"}
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            alignItems: "center",
                            flexWrap: "wrap",
                          }}
                        >
                          <StatusBadge value={p.status} />
                          {awaiting ? <StatusBadge value="Afventer" variant="info" /> : null}
                          {p.optional ? <StatusBadge value="Valgfri" variant="optional" /> : null}
                          {p.manual_override ? <StatusBadge value="Manuel" /> : null}
                        </div>
                      </td>
                      <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                        <button
                          type="button"
                          className="u-btn u-btn--secondary"
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
                        color: "var(--color-text-muted)",
                        textAlign: "center",
                        borderBottom: "1px solid var(--color-surface-muted)",
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
        <Modal label="Tilføj træning" onClose={() => setCreateOpen(false)} closeDisabled={creating}>
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
              <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)" }}>
                Tilføj træning
              </div>
              <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
                Opret en ny planlagt træning.
              </div>
            </div>

            <button
              type="button"
              className="u-btn u-btn--secondary" style={{ flexShrink: 0 }}
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
              {sessionTypeOptions(form.session_type).map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
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
                color: "var(--color-text-muted)",
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
              <button type="submit" className="u-btn u-btn--primary" disabled={creating}>
                {creating ? "Opretter..." : "Tilføj træning"}
              </button>

              <button
                type="button"
                className="u-btn u-btn--secondary"
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
        <Modal label="Rediger træning" onClose={() => setEditing(null)} closeDisabled={savingEdit}>
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
              <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)" }}>
                Rediger træning
              </div>
              <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
                {formatDate(editing.planned_date)} · {editing.session_type}
              </div>
            </div>

            <button
              type="button"
              className="u-btn u-btn--secondary" style={{ flexShrink: 0 }}
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
                  {sessionTypeOptions(editing.session_type).map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
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
                  color: "var(--color-text-muted)",
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
                    className="u-btn u-btn--primary"
                    disabled={savingEdit}
                  >
                    {savingEdit ? "Gemmer..." : "Gem ændringer"}
                  </button>

                  <button
                         type="button"
                    className="u-btn u-btn--secondary"
                    onClick={() => handleMarkSkipped(editing.id)}
                    disabled={savingEdit}
                  >
                    Sprunget over
                  </button>

                  <button
                    type="button"
                    className="u-btn u-btn--secondary"
                    onClick={() => handleMarkRescheduled(editing.id)}
                    disabled={savingEdit}
                  >
                    Flyttet
                  </button>

                  <button
                    type="button"
                    className="u-btn u-btn--secondary"
                    onClick={() => handleClearMatch(editing.id)}
                    disabled={savingEdit}
                  >
                    Fjern match
                  </button>
                </div>

                <div>
                  <button
                    type="button"
                    className="u-btn u-btn--danger"
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
                  borderTop: "1px solid var(--color-border)",
                  paddingTop: 16,
                  display: "grid",
                  gap: 8,
                }}
              >
                <div style={{ fontWeight: 600, color: "var(--color-text)" }}>Nuværende match</div>

                {editing.matched_activity_name ? (
                  <div
                    style={{
                      padding: "10px 12px",
                      border: "1px solid var(--color-border)",
                      borderRadius: 8,
                      background: "var(--color-surface-muted)",
                      display: "grid",
                      gap: 4,
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "var(--color-text)" }}>
                      {editing.matched_activity_name}
                    </div>

                    <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                      {editing.matched_activity_date
                        ? `${formatDate(editing.matched_activity_date)}`
                        : "Dato ukendt"}
                        {" · "}
                      {editing.display_actual || "-"}
                    </div>

                    {editing.match_reason ? (
                      <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                        <strong>Begrundelse:</strong> {editing.match_reason}
                      </div>
                    ) : null}

                    {editing.match_score !== null &&
                    editing.match_score !== undefined ? (
                      <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                        Match-score: {editing.match_score}
                      </div>
                    ) : null}
                  </div>
                ) : editing.match_reason ? (
                  <div
                    style={{
                      padding: "10px 12px",
                      border: "1px solid var(--color-border)",
                      borderRadius: 8,
                      background: "var(--color-surface-muted)",
                      fontSize: 13,
                      color: "var(--color-text-muted)",
                    }}
                  >
                    <strong>Begrundelse:</strong> {editing.match_reason}
                  </div>
                ) : null}
              </div>
            )}

            <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: 16 }}>
               <div style={{ fontWeight: 600, color: "var(--color-text)", marginBottom: 6 }}>
                Vælg match
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 10 }}>
                Kandidater sorteres efter nærhed til planlagt dato og derefter nærhed til målet.
              </div>

              {candidateGroups.near.length > 0 && (
                <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text)" }}>
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
                        border: "1px solid var(--color-border)",
                        background: "var(--color-surface-muted)",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: "var(--color-text)" }}>{a.name}</div>
                        <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                          {formatDate(a.date)} · {a.distance_km} km · {a.duration_min} min ·{" "}
                          {a.dayDiff} dag(e) fra planen
                        </div>
                      </div>
                      <button
                        type="button"
                        className="u-btn u-btn--secondary"
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
                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text)" }}>
                      Andre kandidater
                    </div>

                    <button
                      type="button"
                      className="u-btn u-btn--secondary"
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
                          border: "1px solid var(--color-border)",
                          background: "var(--color-surface-muted)",
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, color: "var(--color-text)" }}>{a.name}</div>
                          <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                            {formatDate(a.date)} · {a.distance_km} km · {a.duration_min} min ·{" "}
                            {a.dayDiff} dag(e) fra planen
                          </div>
                        </div>

                        <button
                          type="button"
                          className="u-btn u-btn--secondary"
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
                <div style={{ color: "var(--color-text-muted)", fontSize: 14 }}>
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
