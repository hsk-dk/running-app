import { useMemo } from "react";
import { journey } from "../lib/journey";
import { useWidth } from "../lib/useWidth";
import { Activity, parseDateKey } from "../lib/week";

const H = 150;
const PAD = { l: 30, r: 6, t: 20, b: 24 };
const monthName = (key: string) => parseDateKey(`${key}-01`).toLocaleDateString("da-DK", { month: "short" });
const n0 = (v: number) => v.toLocaleString("da-DK", { maximumFractionDigits: 0 });

/** Your own road from the first run to today: how long you have been going, and how your longest run grew month by month. */
export default function JourneyCard({ activities, today = new Date() }: { activities: Activity[]; today?: Date }) {
  const j = useMemo(() => journey(activities, today), [activities, today]);
  const [box, W] = useWidth<HTMLDivElement>();
  if (!j) return null;

  const top = Math.max(5, Math.ceil(Math.max(...j.months.map((m) => m.longest)) / 5) * 5);
  const inner = W - PAD.l - PAD.r;
  const step = inner / j.months.length;
  const bw = Math.max(10, Math.min(40, step * 0.62));
  const y = (km: number) => PAD.t + (1 - km / top) * (H - PAD.t - PAD.b);
  const label = `Dit længste løb måned for måned: ${j.months.map((m) => `${monthName(m.key)} ${m.longest > 0 ? `${n0(m.longest)} km` : "ingen løb"}`).join(", ")}`;

  return (
    <section className="u-card" aria-labelledby="journey-title" style={{ display: "grid", gap: 10 }}>
      <h2 id="journey-title" className="u-h2">Din opbygning</h2>
      <p style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>{j.headline}</p>
      {j.note && <p className="u-card__meta" style={{ margin: 0 }}>{j.note}</p>}
      {j.months.length > 1 && (
        <div ref={box}>
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} style={{ display: "block", width: "100%", height: "auto" }}>
            {[0, top / 2, top].map((v) => (
              <g key={v}>
                <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="var(--color-border-control)" strokeWidth={0.6} />
                <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end" fontSize={11} fill="var(--color-text-muted)">{n0(v)}</text>
              </g>
            ))}
            <text x={PAD.l} y={12} fontSize={11} fill="var(--color-text-muted)">Længste løb i kilometer, måned for måned</text>
            {j.months.map((m, i) => {
              const x = PAD.l + i * step + (step - bw) / 2;
              const h = Math.max(m.longest > 0 ? 3 : 0, H - PAD.b - y(m.longest));
              const last = i === j.months.length - 1;
              return (
                <g key={m.key}>
                  <title>{m.runs > 0 ? `${monthName(m.key)}: ${m.runs} løb, længste ${m.longest.toLocaleString("da-DK", { maximumFractionDigits: 1 })} km` : `${monthName(m.key)}: ingen løb, og det er helt i orden`}</title>
                  <rect x={x} y={H - PAD.b - h} width={bw} height={h} rx={4} fill={last ? "var(--data-1)" : "var(--data-muted)"} />
                  {m.longest > 0 && step >= 34 && <text x={x + bw / 2} y={H - PAD.b - h - 5} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--color-text)">{n0(m.longest)}</text>}
                  {(j.months.length <= 8 || i % 2 === (j.months.length - 1) % 2) && (
                    <text x={x + bw / 2} y={H - PAD.b + 16} textAnchor="middle" fontSize={11} fill="var(--color-text-muted)">{monthName(m.key)}</text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      )}
      <p className="u-card__meta" style={{ margin: 0 }}>
        {j.runs} {j.runs === 1 ? "løb" : "løb"} og {n0(j.km)} km siden {parseDateKey(j.firstDate).toLocaleDateString("da-DK", { day: "numeric", month: "long", year: "numeric" })}.
      </p>
    </section>
  );
}
