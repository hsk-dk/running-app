import { useEffect, useState } from "react";
import { api } from "./api";
import OverviewPage from "./pages/OverviewPage";
import PlanPage from "./pages/PlanPage";
import ActivitiesPage from "./pages/ActivitiesPage";
import AdminPage from "./pages/AdminPage";

type PageKey = "overview" | "plan" | "activities" | "admin";

const shellStyle: React.CSSProperties = {
  minHeight: "100vh",
  fontFamily:
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Inter, sans-serif",
  lineHeight: 1.6,
  color: "#1f2937",
  background:
    "#C9CFD8 url(https://auth.useful.dk/media/public/background.jpg) center center / cover no-repeat fixed",
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: 0,
  background:
    "radial-gradient(120% 120% at 50% 30%, rgba(0,0,0,0.00) 0%, rgba(0,0,0,0.05) 55%, rgba(0,0,0,0.14) 100%), linear-gradient(to bottom, rgba(0,0,0,0.04), rgba(0,0,0,0.06))",
  pointerEvents: "none",
};

const topbarOuterStyle: React.CSSProperties = {
  position: "relative",
  zIndex: 2,
  background: "linear-gradient(to right, #5d8fd9, #6ea0eb)",
  borderBottom: "1px solid rgba(255,255,255,0.18)",
  boxShadow: "0 1px 0 rgba(255,255,255,0.06) inset",
};

const topbarInnerStyle: React.CSSProperties = {
  maxWidth: 1280,
  margin: "0 auto",
  padding: "14px 18px",
  display: "flex",
  alignItems: "center",
  gap: 28,
};

const brandStyle: React.CSSProperties = {
  color: "#ffffff",
  fontSize: 22,
  fontWeight: 800,
  letterSpacing: "-0.02em",
  userSelect: "none",
};

const navStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 24,
  flexWrap: "wrap",
};

const mainWrapperStyle: React.CSSProperties = {
  position: "relative",
  zIndex: 1,
  maxWidth: 940,
  margin: "24px auto 0",
  padding: "0 16px 32px",
};

const panelStyle: React.CSSProperties = {
  background: "rgba(255,255,255,0.86)",
  backdropFilter: "saturate(110%) blur(6px)",
  borderRadius: 14,
  padding: 20,
  boxShadow: "0 10px 30px rgba(0,0,0,0.20)",
  border: "1px solid rgba(36,49,64,0.10)",
  minHeight: 620,
};

const footerStyle: React.CSSProperties = {
  textAlign: "center",
  marginTop: 18,
  color: "#425061",
  fontSize: 12,
};

function formatDateTime(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("da-DK", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function NavItem({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        appearance: "none",
        background: "transparent",
        border: "none",
        color: "#ffffff",
        cursor: "pointer",
        fontSize: 14,
        fontWeight: active ? 700 : 500,
        padding: "8px 0",
        borderBottom: active ? "2px solid rgba(255,255,255,0.95)" : "2px solid transparent",
        opacity: active ? 1 : 0.88,
      }}
    >
      {label}
    </button>
  );
}

export default function App() {
  const [page, setPage] = useState<PageKey>("overview");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [summary, setSummary] = useState<any>(null);
  const [monthlyVolume, setMonthlyVolume] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);
  const [plannedRuns, setPlannedRuns] = useState<any[]>([]);
  const [weeklyConsistency, setWeeklyConsistency] = useState<any[]>([]);
  const [adminStatus, setAdminStatus] = useState<any>(null);

  async function loadAll() {
    try {
      setError(null);
      const [s, mv, a, p, wc, admin] = await Promise.all([
        api.getSummary(),
        api.getMonthlyVolume(),
        api.getActivities(),
        api.getPlannedRuns(),
        api.getWeeklyConsistency(),
        api.getAdminStatus(),
      ]);

      setSummary(s);
      setMonthlyVolume(mv);
      setActivities(a);
      setPlannedRuns(p);
      setWeeklyConsistency(wc);
      setAdminStatus(admin);
    } catch (e: any) {
      setError(e.message || "Ukendt fejl");
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleAction(action: "ingest" | "metrics" | "plan") {
    setLoading(true);
    setError(null);
    try {
      if (action === "ingest") await api.runIngest();
      if (action === "metrics") await api.runMetrics();
      if (action === "plan") await api.evaluatePlanning();
      await loadAll();
    } catch (e: any) {
      setError(e.message || "Handling fejlede");
    } finally {
      setLoading(false);
    }
  }

  async function handleAddPlannedRun(payload: {
    planned_date: string;
    session_type: string;
    target_type: "time" | "distance";
    target_value: number;
    optional?: boolean;
    notes?: string;
  }) {
    setError(null);
    try {
      await api.addPlannedRun(payload);
      await loadAll();
      setPage("plan");
    } catch (e: any) {
      setError(e.message || "Kunne ikke oprette træning");
    }
  }

  function renderPage() {
    const common = {
      loading,
      onRunAction: handleAction,
      error,
    };

    switch (page) {
      case "overview":
        return (
          <OverviewPage
            {...common}
            summary={summary}
            monthlyVolume={monthlyVolume}
            weeklyConsistency={weeklyConsistency}
            plannedRuns={plannedRuns}
          />
        );
      case "plan":
        return (
          <PlanPage
            {...common}
            plannedRuns={plannedRuns}
            activities={activities}
            onAddPlannedRun={handleAddPlannedRun}
            onPlanningChanged={loadAll}
          />
        );
      case "activities":
        return (
          <ActivitiesPage
            {...common}
            activities={activities}
            plannedRuns={plannedRuns}
          />
        );
      case "admin":
        return <AdminPage {...common} adminStatus={adminStatus} />;
      default:
        return null;
    }
  }

  return (
    <div style={shellStyle}>
      <div style={overlayStyle} />

      <div style={topbarOuterStyle}>
        <div style={topbarInnerStyle}>
          <div style={brandStyle}>Running</div>

          <nav style={navStyle}>
            <NavItem
              active={page === "overview"}
              label="Overblik"
              onClick={() => setPage("overview")}
            />
            <NavItem
              active={page === "plan"}
              label="Plan"
              onClick={() => setPage("plan")}
            />
            <NavItem
              active={page === "activities"}
              label="Løb"
              onClick={() => setPage("activities")}
            />
            <NavItem
              active={page === "admin"}
              label="Admin"
              onClick={() => setPage("admin")}
            />
          </nav>
        </div>
      </div>

      <div style={mainWrapperStyle}>
        <div style={panelStyle}>{renderPage()}</div>

        <footer style={footerStyle}>
          Sidst synkroniseret: {formatDateTime(adminStatus?.last_sync_at?.value)}
        </footer>
      </div>
    </div>
  );
}
