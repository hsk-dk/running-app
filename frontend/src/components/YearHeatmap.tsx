import { useMemo, useState } from "react";
import { DayCell, levelFn } from "../lib/year";

const CELL = 12;
const GAP = 3;
const LEFT = 30;
const TOP = 22;
const MONTHS = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];
const LEVEL_PCT = [0, 28, 50, 75, 100];

/** A year as weeks in columns and weekdays in rows. Darker means a longer run. */
export default function YearHeatmap({ days, label }: { days: DayCell[]; label: string }) {
  const [metric, setMetric] = useState<"km" | "min">("km");
  const level = useMemo(() => levelFn(days.map((d) => d[metric])), [days, metric]);
  const cols = days.length ? days[days.length - 1].weekIndex + 1 : 0;
  const width = LEFT + cols * (CELL + GAP);

  const monthLabels: { x: number; text: string }[] = [];
  let lastMonth = -1;
  for (const d of days) {
    const month = Number(d.date.slice(5, 7)) - 1;
    if (d.weekday === 0 && month !== lastMonth && Number(d.date.slice(8, 10)) <= 7) {
      lastMonth = month;
      monthLabels.push({ x: LEFT + d.weekIndex * (CELL + GAP), text: MONTHS[month] });
    }
  }

  const fill = (lvl: number) => (lvl === 0 ? "var(--data-muted)" : `color-mix(in srgb, var(--data-1) ${LEVEL_PCT[lvl]}%, var(--data-muted))`);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
        <p className="u-card__meta" style={{ margin: 0 }}>Hver firkant er en dag. Mørkere er længere.</p>
        <div role="group" aria-label="Vælg mål" style={{ display: "flex", gap: 8 }}>
          <button type="button" className="u-btn u-btn--secondary" aria-pressed={metric === "km"} onClick={() => setMetric("km")}>Kilometer</button>
          <button type="button" className="u-btn u-btn--secondary" aria-pressed={metric === "min"} onClick={() => setMetric("min")}>Minutter</button>
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${width} ${TOP + 7 * (CELL + GAP) + 28}`} role="img" aria-label={label} style={{ display: "block", width: "100%", minWidth: 720, height: "auto" }}>
          {monthLabels.map((m) => (
            <text key={m.x} x={m.x} y={14} fontSize={11} fill="var(--color-text-muted)">{m.text}</text>
          ))}
          {["man", "ons", "fre"].map((t, i) => (
            <text key={t} x={0} y={TOP + i * 2 * (CELL + GAP) + 10} fontSize={11} fill="var(--color-text-muted)">{t}</text>
          ))}
          {days.map((d) => (
            <rect key={d.date} x={LEFT + d.weekIndex * (CELL + GAP)} y={TOP + d.weekday * (CELL + GAP)} width={CELL} height={CELL} rx={3} fill={fill(level(d[metric]))}>
              <title>
                {new Date(d.date).toLocaleDateString("da-DK", { weekday: "long", day: "numeric", month: "long" })}
                {d.runs ? `: ${d.km.toLocaleString("da-DK", { maximumFractionDigits: 1 })} km, ${d.min} min` : ": hviledag"}
              </title>
            </rect>
          ))}
          <g transform={`translate(${width - 190}, ${TOP + 7 * (CELL + GAP) + 6})`}>
            <text x={0} y={10} fontSize={11} fill="var(--color-text-muted)">Mindre</text>
            {[0, 1, 2, 3, 4].map((l) => (
              <rect key={l} x={48 + l * 17} y={0} width={12} height={12} rx={3} fill={fill(l)} />
            ))}
            <text x={138} y={10} fontSize={11} fill="var(--color-text-muted)">Mere</text>
          </g>
        </svg>
      </div>
    </div>
  );
}
