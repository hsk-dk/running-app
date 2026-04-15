import { useMemo, useState } from "react";

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: 10,
  padding: 16,
};

const filterButtonStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 6,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#6b7280",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 500,
};

const activeFilterButtonStyle: React.CSSProperties = {
  ...filterButtonStyle,
  background: "#eef2ff",
  border: "1px solid #c7d2fe",
  color: "#4338ca",
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

function statusTone(status: string) {
  if (status === "Matchet") {
    return { bg: "#ecfdf5", border: "#bbf7d0", color: "#166534" };
  }
  if (status === "Ikke planlagt") {
    return { bg: "#eff6ff", border: "#bfdbfe", color: "#1d4ed8" };
  }
  if (status === "Afbrudt") {
    return { bg: "#fef2f2", border: "#fecaca", color: "#991b1b" };
  }
  if (status === "Manuel") {
    return { bg: "#f8fafc", border: "#cbd5e1", color: "#475569" };
  }
  return { bg: "#f8fafc", border: "#e2e8f0", color: "#475569" };
}

function StatusBadge({ value }: { value: string }) {
  const tone = statusTone(value);
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

type FilterKey = "alle" | "matchede" | "ikke-planlagte" | "afbrudte" | "denne-uge";

export default function ActivitiesPage({
  activities,
  plannedRuns,
}: {
  activities: any[];
  plannedRuns: any[];
  loading: boolean;
  onRunAction: (action: "ingest" | "metrics" | "plan") => void;
  error: string | null;
}) {
  const [filter, setFilter] = useState<FilterKey>("alle");

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
    <div style={{ display: "grid", gap: 24 }}>
      <section>
        <div style={{ fontSize: 18, fontWeight: 700, color: "#243140" }}>Løb</div>
        <div style={{ fontSize: 14, color: "#425061" }}>
          Oversigt over synkroniserede aktiviteter og deres relation til planen.
        </div>
      </section>

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
          <div style={{ fontWeight: 600, color: "#374151" }}>Aktiviteter</div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {filters.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFilter(f.key)}
                style={filter === f.key ? activeFilterButtonStyle : filterButtonStyle}
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
            color: "#64748b",
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
              <tr style={{ textAlign: "left", color: "#6b7280" }}>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  Dato
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  Navn
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  Km
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  Min
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  Puls
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  Plan
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  Uge
                </th>
                <th style={{ padding: "10px 8px", borderBottom: "1px solid #e5e7eb" }}>
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredActivities.map((a) => (
                <tr key={a.id}>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid #f1f5f9" }}>
                    {formatDate(a.date)}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid #f1f5f9" }}>
                    {a.name}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid #f1f5f9" }}>
                    {a.distance_km}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid #f1f5f9" }}>
                    {a.duration_min}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid #f1f5f9" }}>
                    {a.avg_hr ?? "-"}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid #f1f5f9" }}>
                    {a.matchedPlan ? (
                      <div style={{ display: "grid", gap: 2 }}>
                        <span style={{ color: "#243140", fontWeight: 600 }}>
                          {a.matchedPlan.session_type}
                        </span>
                        <span style={{ fontSize: 12, color: "#64748b" }}>
                          {formatDate(a.matchedPlan.planned_date)}
                        </span>
                      </div>
                    ) : (
                      <span style={{ color: "#94a3b8" }}>-</span>
                    )}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid #f1f5f9" }}>
                    {a.weekKey || "-"}
                  </td>
                  <td style={{ padding: "10px 8px", borderBottom: "1px solid #f1f5f9" }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                      <StatusBadge value={a.derivedStatus} />
                      {a.matchedPlan?.manual_override ? <StatusBadge value="Manuel" /> : null}
                    </div>
                  </td>
                </tr>
              ))}

              {filteredActivities.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    style={{
                      padding: "18px 8px",
                      color: "#64748b",
                      textAlign: "center",
                      borderBottom: "1px solid #f1f5f9",
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
