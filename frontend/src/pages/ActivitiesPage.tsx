import { sessionLabel } from "../lib/sessionTypes";
import { useMemo, useState } from "react";
import ActivityDetail from "../components/ActivityDetail";
import StatusBadge from "../components/StatusBadge";

const cardStyle: React.CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-large)",
  padding: 16,
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

type FilterKey = "alle" | "matchede" | "ikke-planlagte" | "afbrudte" | "denne-uge";

export default function ActivitiesPage({
  activities,
  plannedRuns,
}: {
  activities: any[];
  plannedRuns: any[];
  loading: boolean;
  onRunAction: (action: "ingest" | "plan") => void;
  error: string | null;
}) {
  const [filter, setFilter] = useState<FilterKey>("alle");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const plannedRunById = useMemo(() => {
    const map = new Map<number, any>();
    for (const run of plannedRuns ?? []) {
      if (run?.id != null) map.set(run.id, run);
    }
    return map;
  }, [plannedRuns]);

  const enrichedActivities = useMemo(() => {
    return activities.map((a) => {
      const matchedPlan =
        a.matched_planned_run_id != null
          ? plannedRunById.get(a.matched_planned_run_id) ?? null
          : null;

      const weekKey = getIsoWeekKey(a.date);

      return {
        ...a,
        matchedPlan,
        weekKey,
        derivedStatus: a.is_aborted
          ? "Afbrudt"
          : a.matched_planned_run_id
            ? "Matchet"
            : "Ikke planlagt",
      };
    });
  }, [activities, plannedRunById]);

  const filteredActivities = useMemo(() => {
    const currentWeek = getCurrentIsoWeekKey();

    switch (filter) {
      case "matchede":
        return enrichedActivities.filter((a) => !!a.matched_planned_run_id && !a.is_aborted);
      case "ikke-planlagte":
        return enrichedActivities.filter(
          (a) => !a.matched_planned_run_id && !a.is_aborted
        );
      case "afbrudte":
        return enrichedActivities.filter((a) => !!a.is_aborted);
      case "denne-uge":
        return enrichedActivities.filter((a) => a.weekKey === currentWeek);
      default:
        return enrichedActivities;
    }
  }, [enrichedActivities, filter]);

  const counts = useMemo(() => {
    return {
      total: enrichedActivities.length,
      matched: enrichedActivities.filter((a) => !!a.matched_planned_run_id && !a.is_aborted).length,
      unplanned: enrichedActivities.filter((a) => !a.matched_planned_run_id && !a.is_aborted).length,
      aborted: enrichedActivities.filter((a) => !!a.is_aborted).length,
    };
  }, [enrichedActivities]);

  const filters: { key: FilterKey; label: string }[] = [
    { key: "alle", label: "Alle" },
    { key: "matchede", label: "Matchede" },
    { key: "ikke-planlagte", label: "Ikke planlagte" },
    { key: "afbrudte", label: "Afbrudte" },
    { key: "denne-uge", label: "Denne uge" },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)" }}>Løb</div>
        <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
          Oversigt over synkroniserede aktiviteter og deres relation til planen.
        </div>
      </section>

      {selectedId !== null && (
        <ActivityDetail activityId={selectedId} onClose={() => setSelectedId(null)} />
      )}

      <section style={cardStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
            marginBottom: 12,
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--color-text)" }}>Aktiviteter</div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {filters.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                className="u-btn u-btn--secondary"
                aria-pressed={filter === f.key}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            marginBottom: 14,
            fontSize: 13,
            color: "var(--color-text-muted)",
          }}
        >
          <span>{counts.total} i alt</span>
          <span>{counts.matched} matchede</span>
          <span>{counts.unplanned} ikke planlagte</span>
          <span>{counts.aborted} afbrudte</span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--color-text-muted)" }}>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Dato
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Navn
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Km
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Min
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Puls
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Plan
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Uge
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Status
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  Rute
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredActivities.map((a) => (
                <tr key={a.id}>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    {formatDate(a.date)}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    {a.name}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    {a.distance_km}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    {a.duration_min}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    {a.avg_hr ?? "-"}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    {a.matchedPlan ? (
                      <div style={{ display: "grid", gap: 2 }}>
                        <span style={{ color: "var(--color-text)", fontWeight: 600 }}>
                          {sessionLabel(a.matchedPlan.session_type)}
                        </span>
                        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                          {formatDate(a.matchedPlan.planned_date)}
                        </span>
                      </div>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)" }}>-</span>
                    )}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    {a.weekKey || "-"}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                      <StatusBadge value={a.derivedStatus} />
                      {a.matchedPlan?.manual_override ? <StatusBadge value="Manuel" /> : null}
                    </div>
                  </td>
                  <td style={{ padding: "6px 8px", borderBottom: "1px solid var(--color-surface-muted)" }}>
                    <button
                      type="button"
                      className="u-btn u-btn--secondary"
                      aria-label={`Vis rute for ${a.name ?? "løb"} den ${formatDate(a.date)}`}
                      onClick={() => {
                        setSelectedId(a.id);
                        window.scrollTo({ top: 0, behavior: "smooth" });
                      }}
                    >
                      Vis
                    </button>
                  </td>
                </tr>
              ))}

              {filteredActivities.length === 0 && (
                <tr>
                  <td
                    colSpan={9}
                    style={{
                      padding: "18px 8px",
                      color: "var(--color-text-muted)",
                      textAlign: "center",
                      borderBottom: "1px solid var(--color-surface-muted)",
                    }}
                  >
                    Ingen aktiviteter matcher det valgte filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
