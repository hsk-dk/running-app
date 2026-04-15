const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: 10,
  padding: 16,
};

const primaryButtonStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: 6,
  border: "1px solid transparent",
  background: "linear-gradient(to bottom right, #9dc0ff, #446ea8)",
  color: "white",
  boxShadow: "0 6px 16px rgba(0,0,0,0.18)",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 500,
};

const secondaryButtonStyle: React.CSSProperties = {
  padding: "10px 20px",
  borderRadius: 6,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#6b7280",
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
  onRunAction: (action: "ingest" | "metrics" | "plan") => void;
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
          <div style={{ fontSize: 18, fontWeight: 700, color: "#243140" }}>Admin</div>
          <div style={{ fontSize: 14, color: "#425061" }}>
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
            onClick={() => onRunAction("metrics")}
            disabled={loading}
          >
            Genberegn statistik
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
                background: "#f8fafc",
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                fontSize: 12,
                color: "#475569",
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
                background: "#f8fafc",
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                fontSize: 12,
                color: "#475569",
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
                color: lastError ? "#9a3412" : "#64748b",
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
