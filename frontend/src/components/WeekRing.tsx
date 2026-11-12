import { DayState, weekdayName } from "../lib/week";

const LETTERS = ["M", "T", "O", "T", "F", "L", "S"];

const KIND_TEXT: Record<string, string> = {
  done: "løbet",
  shortened: "forkortet løb",
  skipped: "sprunget over",
  planned: "planlagt",
  rest: "hviledag",
};

/** One segment per day of the week: filled = run, dotted = planned, thin = rest. Colour is never the only signal. */
export default function WeekRing({
  days,
  done,
  total,
  weekNumber,
}: {
  days: DayState[];
  done: number;
  total: number;
  weekNumber: number;
}) {
  const cx = 120;
  const cy = 120;
  const R = 86;
  const gap = 7;
  const label = `Uge ${weekNumber}: ${done} af ${total} planlagte løb gennemført. ` +
    days.map((d) => `${weekdayName(d.weekday)} ${KIND_TEXT[d.kind]}${d.isToday ? " (i dag)" : ""}`).join(", ") + ".";

  const segments = days.map((d, i) => {
    const a0 = ((-90 + (i * 360) / 7 + gap / 2) * Math.PI) / 180;
    const a1 = ((-90 + ((i + 1) * 360) / 7 - gap / 2) * Math.PI) / 180;
    const x0 = cx + R * Math.cos(a0);
    const y0 = cy + R * Math.sin(a0);
    const x1 = cx + R * Math.cos(a1);
    const y1 = cy + R * Math.sin(a1);
    const path = `M${x0} ${y0} A${R} ${R} 0 0 1 ${x1} ${y1}`;
    const am = (a0 + a1) / 2;
    const lx = cx + (R + 24) * Math.cos(am);
    const ly = cy + (R + 24) * Math.sin(am);
    return { d, i, path, lx, ly };
  });

  return (
    <svg viewBox="0 0 240 240" role="img" aria-label={label} style={{ width: "100%", maxWidth: 240, height: "auto" }}>
      {segments.map(({ d, i, path, lx, ly }) => (
        <g key={d.date}>
          {d.kind === "done" && (
            <path d={path} fill="none" stroke="var(--data-1)" strokeWidth={18} strokeLinecap="round" />
          )}
          {d.kind === "shortened" && (
            <path d={path} fill="none" stroke="var(--data-1)" strokeWidth={10} strokeLinecap="round" />
          )}
          {d.kind === "planned" && (
            <path
              d={path}
              fill="none"
              stroke="var(--color-text-muted)"
              strokeWidth={3}
              strokeDasharray="2 7"
              strokeLinecap="round"
            />
          )}
          {d.kind === "skipped" && (
            <path d={path} fill="none" stroke="var(--text-bad)" strokeWidth={4} strokeLinecap="butt" />
          )}
          {d.kind === "rest" && (
            <path d={path} fill="none" stroke="var(--color-border-control)" strokeWidth={3} strokeLinecap="round" />
          )}
          {d.extras.length > 0 && <circle cx={cx + (R - 20) * Math.cos(((-90 + ((i + 0.5) * 360) / 7) * Math.PI) / 180)} cy={cy + (R - 20) * Math.sin(((-90 + ((i + 0.5) * 360) / 7) * Math.PI) / 180)} r={3.5} fill="var(--data-1)" opacity={0.55} />}
          <text
            x={lx}
            y={ly + 4}
            textAnchor="middle"
            fontSize={11}
            fill={d.isToday ? "var(--color-text)" : "var(--color-text-muted)"}
            fontWeight={d.isToday ? 800 : 500}
          >
            {LETTERS[i]}
          </text>
          {d.isToday && <circle cx={lx} cy={ly + 14} r={2.6} fill="var(--data-1)" />}
        </g>
      ))}
      <text
        x={cx}
        y={cy + 12}
        textAnchor="middle"
        fontSize={46}
        fontWeight={800}
        fill="var(--color-text)"
        style={{ letterSpacing: "-0.03em" }}
      >
        {done}/{total}
      </text>
      <text x={cx} y={cy + 34} textAnchor="middle" fontSize={11} fill="var(--color-text-muted)">
        løb i uge {weekNumber}
      </text>
    </svg>
  );
}
