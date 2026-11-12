import { rollingAverage } from "../lib/year";

const W = 860;
const L = 44;
const B = 250;
const T = 14;

/** Kilometres per week as faint bars and the four-week average as a line. */
export default function FormChart({ weeklyKm, firstWeekLabel }: { weeklyKm: number[]; firstWeekLabel: (i: number) => string }) {
  const n = weeklyKm.length;
  if (n < 2) return null;
  const avg = rollingAverage(weeklyKm, 4);
  const mx = Math.max(20, Math.ceil(Math.max(...weeklyKm) / 20) * 20);
  const H = B - T;
  const step = (W - L) / n;
  const pts = avg.map((a, i) => `${i === 0 ? "M" : "L"}${(L + i * step + step / 2).toFixed(1)} ${(B - (a / mx) * H).toFixed(1)}`).join(" ");
  const ticks = Array.from({ length: mx / 20 + 1 }, (_, i) => i * 20);
  const label = `Kilometer pr. uge de seneste ${n} uger med gennemsnit over fire uger. Gennemsnittet går fra ${Math.round(avg[3] ?? avg[0])} til ${Math.round(avg[n - 1])} km.`;

  return (
    <div style={{ overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} 285`} role="img" aria-label={label} style={{ display: "block", width: "100%", minWidth: 600, height: "auto" }}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={L} y1={B - (v / mx) * H} x2={W - 10} y2={B - (v / mx) * H} stroke="var(--color-border-control)" strokeWidth={0.6} />
            <text x={L - 8} y={B - (v / mx) * H + 4} textAnchor="end" fontSize={11} fill="var(--color-text-muted)">{v} km</text>
          </g>
        ))}
        {weeklyKm.map((v, i) => {
          const w = step * 0.64;
          const x = L + i * step + step * 0.18;
          const h = (v / mx) * H;
          return (
            <g key={i}>
              <rect x={x} y={B - h} width={w} height={h} rx={3} fill="var(--data-muted)" />
              {i % 4 === 0 && (
                <text x={x + w / 2} y={B + 18} textAnchor="middle" fontSize={11} fill="var(--color-text-muted)">{firstWeekLabel(i)}</text>
              )}
            </g>
          );
        })}
        <path d={pts} fill="none" stroke="var(--data-1)" strokeWidth={3.5} strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={L + (n - 1) * step + step / 2} cy={B - (avg[n - 1] / mx) * H} r={5} fill="var(--data-1)" />
        <text x={W - 10} y={282} textAnchor="end" fontSize={11} fill="var(--color-text-muted)">Linje: gennemsnit over fire uger · søjler: kilometer pr. uge</text>
      </svg>
    </div>
  );
}
