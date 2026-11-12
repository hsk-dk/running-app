const cardStyle: React.CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-large)",
  padding: 16,
};

const primaryButtonStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: 6,
  border: "1px solid transparent",
  background: "var(--color-action-strong)",
  color: "var(--color-on-action)",
  boxShadow: "var(--shadow-small)",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 500,
};

const secondaryButtonStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: 6,
  border: "1px solid var(--color-border-control)",
  background: "var(--color-surface)",
  color: "var(--color-text-muted)",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 500,
};

function formatDateTime(value?: unknown) {
  if (value === null || value === undefined || value === "") return "-";

  if (typeof value === "number") {
    const ms = value < 10_000_000_000 ? value * 1000 : value;
    const d = new Date(ms);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleString("da-DK", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    }
  }

  if (typeof value === "string") {
    const d = new Date(value);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleString("da-DK", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    }
    return value;
  }

  return String(value);
}

function safeText(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function AdminPage({
  adminStatus,
  loading,
  onRunAction,
}: {
  adminStatus: any;
  loading: boolean;
  onRunAction: (action: "ingest" | "plan") => void;
  error: string | null;
}) {
  const lastSync = adminStatus?.last_sync_at?.value;
  const lastWebhook = adminStatus?.last_webhook_at?.value;
  const webhookCount = adminStatus?.webhook_event_count ?? 0;
  const lastIngest = adminStatus?.last_ingest_result?.value;
  const lastError = adminStatus?.last_error?.value;
  const lastWebhookMeta = adminStatus?.last_webhook;

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
          <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)" }}>Admin</div>
          <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
            Drift, sync og teknisk status.
          </div>
        </div>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            style={primaryButtonStyle}
            onClick={() => onRunAction("ingest")}
            disabled={loading}
          >
            Synkronisér
          </button>
          <button
            style={secondaryButtonStyle}
            onClick={() => onRunAction("plan")}
            disabled={loading}
          >
            Evaluer plan
          </button>
        </div>
      </section>

      <section style={cardStyle}>
        <div style={{ display: "grid", gap: 14, fontSize: 14 }}>
          <div>
            <strong>Sidste sync:</strong> {formatDateTime(lastSync)}
          </div>

          <div>
            <strong>Sidste webhook:</strong> {formatDateTime(lastWebhook)}
          </div>

          <div>
            <strong>Webhook-events:</strong> {webhookCount}
          </div>

          <div>
            <strong>Seneste webhook-metadata:</strong>
            <pre
              style={{
                marginTop: 6,
                padding: 12,
                background: "var(--color-surface-muted)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                fontSize: 12,
                color: "var(--color-text-muted)",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
              }}
            >
              {safeText(lastWebhookMeta)}
            </pre>
          </div>

          <div>
            <strong>Seneste ingest:</strong>
            <pre
              style={{
                marginTop: 6,
                padding: 12,
                background: "var(--color-surface-muted)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                fontSize: 12,
                color: "var(--color-text-muted)",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
              }}
            >
              {safeText(lastIngest)}
            </pre>
          </div>

          <div>
            <strong>Seneste fejl:</strong>
            <pre
              style={{
                marginTop: 6,
                padding: 12,
                background: "#fff7ed",
                border: "1px solid #fed7aa",
                borderRadius: 8,
                fontSize: 12,
                color: lastError ? "#9a3412" : "var(--color-text-muted)",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
              }}
            >
              {safeText(lastError)}
            </pre>
          </div>
        </div>
      </section>
    </div>
  );
}
