import { useEffect, useState } from "react";
import { api } from "./api";
import OverviewPage from "./pages/OverviewPage";
import PlanPage from "./pages/PlanPage";
import ActivitiesPage from "./pages/ActivitiesPage";
import AdminPage from "./pages/AdminPage";
import AiSuggestionsPage from "./pages/AiSuggestionsPage";

type PageKey = "overview" | "plan" | "activities" | "admin" | "ai";

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
      type="button"
      className="u-header__link"
      aria-current={active ? "page" : undefined}
      onClick={onClick}
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

  async function handleAction(action: "ingest" | "plan") {
    setLoading(true);
    setError(null);
    try {
      if (action === "ingest") await api.runIngest();
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
      case "ai":
        return (
          <AiSuggestionsPage
            onPlanningChanged={loadAll}
          />
        );
      default:
        return null;
    }
  }

  return (
    <>
      <a className="u-skip-link" href="#indhold">
        Spring til indhold
      </a>

      <header className="u-header">
        <div className="u-header__inner">
          <div className="u-header__brand">Running</div>

          <nav className="u-header__nav" aria-label="Hovednavigation">
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
            <NavItem
              active={page === "ai"}
              label="AI Forslag"
              onClick={() => setPage("ai")}
            />
          </nav>
        </div>
      </header>

      <main id="indhold" className="u-container app-main" tabIndex={-1}>
        <div className="u-panel" style={{ minHeight: 620 }}>
          {renderPage()}
        </div>

        <footer className="app-footer">
          Sidst synkroniseret: {formatDateTime(adminStatus?.last_sync_at?.value)}
        </footer>
      </main>
    </>
  );
}
