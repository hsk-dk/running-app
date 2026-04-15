const API_BASE = import.meta.env.VITE_API_BASE || "/api";

async function getJson(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, init);

  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) {
        message = `${message} - ${data.detail}`;
      }
    } catch {
      // ignore non-json error bodies
    }
    throw new Error(message);
  }

  return res.json();
}

export const api = {
  // Metrics
  getSummary: () => getJson("/metrics/summary"),
  getMonthlyVolume: () => getJson("/metrics/monthly-volume"),

  // Activities
  getActivities: () => getJson("/activities"),

  // Planning
  getPlannedRuns: () => getJson("/planning"),
  getWeeklyConsistency: () => getJson("/planning/weekly-consistency"),
  evaluatePlanning: () => getJson("/planning/evaluate", { method: "POST" }),

  addPlannedRun: (payload: {
    planned_date: string;
    session_type: string;
    target_type: "time" | "distance";
    target_value: number;
    optional?: boolean;
    notes?: string;
  }) =>
    getJson("/planning", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  markPlannedRunSkipped: (plannedRunId: number) =>
    getJson(`/planning/${plannedRunId}/mark-skipped`, {
      method: "POST",
    }),

  markPlannedRunRescheduled: (plannedRunId: number) =>
    getJson(`/planning/${plannedRunId}/mark-rescheduled`, {
      method: "POST",
    }),

  clearPlannedRunMatch: (plannedRunId: number) =>
    getJson(`/planning/${plannedRunId}/clear-match`, {
      method: "POST",
    }),

  matchActivityToPlannedRun: (plannedRunId: number, activityId: number) =>
    getJson(`/planning/${plannedRunId}/match-activity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activity_id: activityId }),
    }),

  // Admin / drift
  getAdminStatus: () => getJson("/admin/status"),
  runIngest: () => getJson("/admin/ingest", { method: "POST" }),
  runMetrics: () => getJson("/admin/rebuild-metrics", { method: "POST" }),
  runPlanEval: () => getJson("/admin/recalculate-plan", { method: "POST" }),

  // AI suggestions
  getAiSuggestions: () => getJson("/ai/suggestions"),

updatePlannedRun: (id: number, payload: any) =>
  getJson(`/planning/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),

deletePlannedRun: (id: number) =>
  getJson(`/planning/${id}`, {
    method: "DELETE",
  }),
};
