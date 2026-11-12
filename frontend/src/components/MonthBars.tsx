import { MonthTotal } from "../lib/year";

const MONTHS = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];
const W = 860;
const B = 160;
const H = 130;

/** Kilometres per month. The newest (possibly unfinished) month is in full colour. */
export default function MonthBars({ months }: { months: MonthTotal[] }) {
  const mx = Math.max(100, Math.ceil(Math.max(...months.map((m) => m.km), 0) / 100) * 100);
  const left = 40;
  const step = (W - left - 10) / Math.max(months.length, 1);
  const bw = Math.min(38, step * 0.7);
  const ticks = [0, mx / 4, mx / 2, (mx * 3) / 4, mx];
  const label = `Kilometer pr. måned: ${months.map((m) => `${MONTHS[Number(m.key.slice(5)) - 1]} ${Math.round(m.km)}`).join(", ")}`;

  return (
    <div style={{ overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} 190`} role="img" aria-label={label} style={{ display: "block", width: "100%", minWidth: 600, height: "auto" }}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={left} y1={B - (v / mx) * H} x2={W - 10} y2={B - (v / mx) * H} stroke="var(--color-border-control)" strokeWidth={0.6} />
            <text x={left - 6} y={B - (v / mx) * H + 4} textAnchor="end" fontSize={11} fill="var(--color-text-muted)">{Math.round(v)}</text>
          </g>
        ))}
        <text x={left} y={12} fontSize={11} fill="var(--color-text-muted)">Kilometer pr. måned</text>
        {months.map((m, i) => {
          const x = left + i * step + (step - bw) / 2;
          const h = (m.km / mx) * H;
          const last = i === months.length - 1;
          const month = Number(m.key.slice(5)) - 1;
          const yearMark = i === 0 || month === 0 ? ` '${m.key.slice(2, 4)}` : "";
          return (
            <g key={m.key}>
              <rect x={x} y={B - h} width={bw} height={h} rx={4} fill={last ? "var(--data-1)" : "var(--data-muted)"} />
              <text x={x + bw / 2} y={B - h - 6} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--color-text)">{Math.round(m.km)}</text>
              <text x={x + bw / 2} y={B + 16} textAnchor="middle" fontSize={11} fill="var(--color-text-muted)">{MONTHS[month] + yearMark}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
