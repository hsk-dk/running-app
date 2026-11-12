import {
  AreaChart,
  Area,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const cardStyle: React.CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-large)",
  padding: 16,
};

function parseDateOnly(value?: string) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatDate(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("da-DK");
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
  if (status === "Grøn" || status === "gennemført") {
    return { bg: "#ecfdf5", border: "#bbf7d0", color: "#166534" };
  }
  if (status === "Gul" || status === "forkortet") {
    return { bg: "#fffbeb", border: "#fde68a", color: "#92400e" };
  }
  if (status === "Rød" || status === "sprunget over") {
    return { bg: "#fef2f2", border: "#fecaca", color: "#991b1b" };
  }
  if (status === "planlagt") {
    return { bg: "var(--color-surface-muted)", border: "#cbd5e1", color: "var(--color-text-muted)" };
  }
  if (status === "flyttet") {
    return { bg: "#eef2ff", border: "#c7d2fe", color: "#4338ca" };
  }
  if (status === "valgfri") {
    return { bg: "#faf5ff", border: "#e9d5ff", color: "#7c3aed" };
  }
  return { bg: "var(--color-surface-muted)", border: "#e2e8f0", color: "var(--color-text-muted)" };
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

function changeText(
  current: number | null | undefined,
  previous: number | null | undefined,
  unit: string,
  decimals = 0
) {
  if (current == null) return "Ingen data";
  if (previous == null) return `Denne måned: ${current.toFixed(decimals)} ${unit}`;
  const diff = current - previous;
  const sign = diff > 0 ? "+" : "";
  return `${sign}${diff.toFixed(decimals)} ${unit} vs. sidste måned`;
}

function hrChangeText(
  current: number | null | undefined,
  previous: number | null | undefined
) {
  if (current == null) return "Ingen pulsdata";
  if (previous == null) return "Ingen sammenligning endnu";
  const diff = current - previous;
  const sign = diff > 0 ? "+" : "";
  return `${sign}${diff.toFixed(1)} bpm vs. sidste måned`;
}

function SummaryCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string | number;
  subtitle: string;
}) {
  return (
    <div style={cardStyle}>
      <div
        style={{
          fontSize: 12,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: "var(--color-text-muted)",
          marginBottom: 6,
        }}
      >
        {title}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "var(--color-text)" }}>{value}</div>
      <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 4 }}>{subtitle}</div>
    </div>
  );
}

export default function OverviewPage({
  summary,
  monthlyVolume,
  weeklyConsistency,
  plannedRuns,
  error,
}: {
  summary: any;
  monthlyVolume: any[];
  weeklyConsistency: any[];
  plannedRuns: any[];
  loading: boolean;
  onRunAction: (action: "ingest" | "plan") => void;
  error: string | null;
}) {
  const currentWeekKey = getCurrentIsoWeekKey();

  const currentWeekRuns = plannedRuns.filter(
    (p: any) => getIsoWeekKey(p.planned_date) === currentWeekKey
  );

  const currentWeekMandatory = currentWeekRuns.filter((p: any) => !p.optional);

  const currentWeekRelevant = currentWeekMandatory.filter((p: any) => {
    if (p.status !== "planlagt") return true;
    return !isAwaiting(p.planned_date, 1);
  });

  const currentWeekCompleted = currentWeekRelevant.filter(
    (p: any) => p.status === "gennemført"
  ).length;

  const currentWeekShortened = currentWeekRelevant.filter(
    (p: any) => p.status === "forkortet"
  ).length;

  const currentWeekAwaiting = currentWeekMandatory.filter(
    (p: any) => p.status === "planlagt" && isAwaiting(p.planned_date, 1)
  ).length;

  let currentWeekScore = "Grøn";
  if (currentWeekRelevant.length > 0) {
    if (currentWeekCompleted === currentWeekRelevant.length) currentWeekScore = "Grøn";
    else if (currentWeekCompleted + currentWeekShortened > 0) currentWeekScore = "Gul";
    else currentWeekScore = "Rød";
  }

  const nextPlanned = [...plannedRuns]
    .filter((p: any) => p.status === "planlagt")
    .sort((a: any, b: any) => String(a.planned_date).localeCompare(String(b.planned_date)))[0];

  const latestMatched = [...plannedRuns]
    .filter((p: any) => p.matched_activity_name)
    .sort((a: any, b: any) => String(b.planned_date).localeCompare(String(a.planned_date)))[0];

  const upcomingRuns = [...plannedRuns]
    .filter((p: any) => p.status === "planlagt")
    .sort((a: any, b: any) => String(a.planned_date).localeCompare(String(b.planned_date)))
    .slice(0, 3);

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <section>
        <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)" }}>Overblik</div>
        <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
          Hurtig status på løb, plan og konsistens.
        </div>
      </section>

      {error && (
        <section
          style={{
            ...cardStyle,
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
          }}
        >
          {error}
        </section>
      )}

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 16,
        }}
      >
        <SummaryCard
          title="Løb denne måned"
          value={summary?.runs_this_month ?? 0}
          subtitle={changeText(summary?.runs_this_month, summary?.runs_prev_month, "løb", 0)}
        />
        <SummaryCard
          title="Km denne måned"
          value={summary?.km_this_month ?? 0}
          subtitle={changeText(summary?.km_this_month, summary?.km_prev_month, "km", 1)}
        />
        <SummaryCard
          title="Gns. puls denne måned"
          value={summary?.avg_hr_this_month ?? "-"}
          subtitle={hrChangeText(summary?.avg_hr_this_month, summary?.avg_hr_prev_month)}
        />
        <SummaryCard
          title="Planopfyldelse denne uge"
          value={`${summary?.adherence_pct_current_week ?? 0}%`}
          subtitle={`${summary?.current_week_completed ?? 0}/${summary?.current_week_relevant ?? 0} relevante obligatoriske pas`}
        />
      </section>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(280px, 360px) minmax(280px, 360px) minmax(0, 1fr)",
          gap: 16,
        }}
      >
        <div style={cardStyle}>
          <div style={{ marginBottom: 8, fontWeight: 600, color: "var(--color-text)" }}>Denne uge</div>

          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
            <StatusBadge value={currentWeekScore} />
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{currentWeekKey}</span>
          </div>

          <div style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)", marginBottom: 4 }}>
            {currentWeekCompleted}/{currentWeekRelevant.length}
          </div>

          <div style={{ fontSize: 14, color: "var(--color-text-muted)", marginBottom: 10 }}>
            aktuelle obligatoriske pas gennemført
          </div>

          <div style={{ display: "grid", gap: 6, fontSize: 13, color: "var(--color-text-muted)" }}>
            <div>Forkortede pas: {currentWeekShortened}</div>
            <div>Afventende obligatoriske pas: {currentWeekAwaiting}</div>
            <div>Valgfrie pas denne uge: {currentWeekRuns.filter((p: any) => p.optional).length}</div>
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ marginBottom: 8, fontWeight: 600, color: "var(--color-text)" }}>
            Næste planlagte træning
          </div>

          {nextPlanned ? (
            <div style={{ display: "grid", gap: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: "var(--color-text)" }}>
                {nextPlanned.display_target}
              </div>
              <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
                {formatDate(nextPlanned.planned_date)} · {nextPlanned.session_type}
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <StatusBadge value={nextPlanned.status} />
                {nextPlanned.optional ? <StatusBadge value="valgfri" /> : null}
              </div>
              {nextPlanned.notes ? (
                <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{nextPlanned.notes}</div>
              ) : null}
            </div>
          ) : (
            <div style={{ color: "var(--color-text-muted)" }}>Ingen planlagte træninger.</div>
          )}
        </div>

        <div style={cardStyle}>
          <div style={{ marginBottom: 8, fontWeight: 600, color: "var(--color-text)" }}>
            Kommende plan
          </div>

          {upcomingRuns.length === 0 ? (
            <div style={{ color: "var(--color-text-muted)" }}>Ingen kommende træninger.</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {upcomingRuns.map((run: any) => (
                <div
                  key={run.id}
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    justifyContent: "space-between",
                    gap: 12,
                    paddingBottom: 8,
                    borderBottom: "1px solid var(--color-surface-muted)",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: "var(--color-text)" }}>
                      {formatDate(run.planned_date)}
                    </div>
                    <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                      {run.session_type} · {run.display_target}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <StatusBadge value={run.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 2fr) minmax(320px, 1fr)",
          gap: 16,
        }}
      >
        <div style={cardStyle}>
          <div style={{ marginBottom: 12, fontWeight: 600, color: "var(--color-text)" }}>
            Månedlig distance
          </div>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <AreaChart data={monthlyVolume}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="km"
                  stroke="var(--data-1)"
                  fill="var(--data-fill)"
                  fillOpacity={0.22}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ marginBottom: 12, fontWeight: 600, color: "var(--color-text)" }}>
            Seneste planmatch
          </div>

          {latestMatched ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "var(--color-text)" }}>
                  {latestMatched.matched_activity_name}
                </div>
                <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
                  {formatDate(latestMatched.planned_date)} · {latestMatched.session_type}
                </div>
              </div>

              <div style={{ display: "grid", gap: 6, fontSize: 14 }}>
                <div>
                  <strong>Mål:</strong> {latestMatched.display_target}
                </div>
                <div>
                  <strong>Faktisk:</strong> {latestMatched.display_actual}
                </div>
              </div>

              <div>
                <StatusBadge value={latestMatched.status} />
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--color-text-muted)" }}>Ingen match endnu.</div>
          )}
        </div>
      </section>

      <section
        style={{
          ...cardStyle,
          display: "grid",
          gap: 8,
        }}
      >
        <div style={{ fontWeight: 600, color: "var(--color-text)" }}>Ugekonsistens</div>

        {weeklyConsistency.length === 0 ? (
          <div style={{ color: "var(--color-text-muted)", fontSize: 14 }}>
            Ingen planlagte træninger endnu.
          </div>
        ) : (
          weeklyConsistency.slice(-4).map((week: any) => (
            <div
              key={week.week}
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                alignItems: "center",
                padding: 12,
                borderRadius: 8,
                background: "var(--color-surface-muted)",
                border: "1px solid var(--color-border)",
              }}
            >
              <div>
                <div style={{ fontWeight: 600 }}>{week.week}</div>
                <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                  {week.completed}/{week.relevant_runs} relevante obligatoriske pas
                </div>
              </div>
              <StatusBadge value={week.score} />
            </div>
          ))
        )}
      </section>
    </div>
  );
}
