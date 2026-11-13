import { useState } from "react";
import YearPage from "./YearPage";
import ActivitiesPage from "./ActivitiesPage";

type Tab = "overview" | "runs";

/** The year at a glance, with the full list of runs one tab away (keeps the main navigation at five items). */
export default function YearSection(props: {
  activities: any[];
  plannedRuns: any[];
  loading: boolean;
  onRunAction: (action: "ingest" | "plan") => void;
  error: string | null;
}) {
  const [tab, setTab] = useState<Tab>("overview");
  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Oversigt" },
    { key: "runs", label: "Alle løb" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 20 }}>
      <nav aria-label="År">
        <ul className="u-tabs">
          {tabs.map((t) => (
            <li key={t.key}>
              <button type="button" className="u-tab" aria-current={tab === t.key ? "page" : undefined} onClick={() => setTab(t.key)}>
                {t.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      {tab === "overview" ? <YearPage activities={props.activities} /> : <ActivitiesPage {...props} />}
    </div>
  );
}
