import { ReactNode, useState } from "react";

type Tab = "admin" | "ai";

/** Drift and the AI suggestions live together here so the main navigation stays at five items. */
export default function MorePage({ admin, ai }: { admin: ReactNode; ai: ReactNode }) {
  const [tab, setTab] = useState<Tab>("admin");
  const tabs: { key: Tab; label: string }[] = [
    { key: "admin", label: "Admin" },
    { key: "ai", label: "AI Forslag" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 20 }}>
      <nav aria-label="Mere">
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
      {tab === "admin" ? admin : ai}
    </div>
  );
}
