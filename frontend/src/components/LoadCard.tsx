import { useMemo } from "react";
import { LoadLevel, loadOver } from "../lib/load";
import { useWidth } from "../lib/useWidth";
import { Activity, parseDateKey } from "../lib/week";

const LEVEL_CHIP: Record<LoadLevel, { text: string; cls: string } | null> = {
  rest: { text: "Hvile", cls: "u-chip u-chip--info" },
  steady: { text: "Stabilt", cls: "u-chip u-chip--good" },
  build: { text: "Opbygning", cls: "u-chip u-chip--info" },
  jump: { text: "Stor stigning", cls: "u-chip u-chip--warn" },
  unknown: null,
};

const H = 180;
const PAD = { l: 34, r: 8, t: 22, b: 28 };
const fmt = (v: number) => Math.round(v).toLocaleString("da-DK");
const weekNo = (start: string) => {
  const d = parseDateKey(start);
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - dayNum);
  const ys = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  return Math.ceil(((t.getTime() - ys.getTime()) / 86400000 + 1) / 7);
};

/** Twelve weeks of kilometres, the usual level as a band, and a plain reading of whether you are ramping up too fast. */
export default function LoadCard({ activities, today = new Date() }: { activities: Activity[]; today?: Date }) {
  const load = useMemo(() => loadOver(activities, today), [activities, today]);
  const [box, W] = useWidth<HTMLDivElement>();
  if (load.weeks.every((w) => w.runs === 0)) return null;

  const chip = LEVEL_CHIP[load.level];
  const max = Math.max(10, ...load.weeks.map((w) => w.km), load.baseline ?? 0);
  const top = Math.ceil(max / 10) * 10;
  const inner = W - PAD.l - PAD.r;
  const step = inner / load.weeks.length;
  const bw = Math.max(8, Math.min(34, step * 0.66));
  const y = (km: number) => PAD.t + (1 - km / top) * (H - PAD.t - PAD.b);
  const labelEvery = W < 480 ? 2 : 1;
  const label = `Kilometer pr. uge de seneste 12 uger: ${load.weeks.map((w) => `uge ${weekNo(w.start)} ${fmt(w.km)}`).join(", ")}`;

  return (
    <section className="u-card" aria-labelledby="load-title" style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <h2 id="load-title" className="u-h2">Belastning</h2>
        {chip && <span className={chip.cls}>{chip.text}</span>}
      </div>
      <p style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>{load.headline}</p>

      <div ref={box}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} style={{ display: "block", width: "100%", height: "auto" }}>
          {[0, top / 2, top].map((v) => (
            <g key={v}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="var(--color-border-control)" strokeWidth={0.6} />
              <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end" fontSize={11} fill="var(--color-text-muted)">{fmt(v)}</text>
            </g>
          ))}
          {load.baseline !== null && (
            <g>
              <rect x={PAD.l} y={y(load.baseline * 1.1)} width={inner} height={Math.max(2, y(load.baseline * 0.8) - y(load.baseline * 1.1))} fill="var(--data-1)" opacity={0.1} />
              <line x1={PAD.l} x2={W - PAD.r} y1={y(load.baseline)} y2={y(load.baseline)} stroke="var(--data-1)" strokeWidth={1} strokeDasharray="4 4" />
              <text x={W - PAD.r} y={y(load.baseline * 1.1) - 4} textAnchor="end" fontSize={11} fill="var(--color-text-muted)">dit gennemsnit ±</text>
            </g>
          )}
          {load.weeks.map((w, i) => {
            const x = PAD.l + i * step + (step - bw) / 2;
            const h = Math.max(w.km > 0 ? 2 : 0, H - PAD.b - y(w.km));
            return (
              <g key={w.start}>
                <title>{`Uge ${weekNo(w.start)}: ${fmt(w.km)} km i ${w.runs} løb${w.current ? " (ugen er ikke slut)" : ""}`}</title>
                {w.current ? (
                  <rect x={x} y={H - PAD.b - h} width={bw} height={h} rx={4} fill="none" stroke="var(--data-1)" strokeWidth={1.5} strokeDasharray="4 3" />
                ) : (
                  <rect x={x} y={H - PAD.b - h} width={bw} height={h} rx={4} fill={i === load.weeks.length - 2 ? "var(--data-1)" : "var(--data-muted)"} />
                )}
                {(load.weeks.length - 1 - i) % labelEvery === 0 && (
                  <text x={x + bw / 2} y={H - PAD.b + 16} textAnchor="middle" fontSize={11} fill="var(--color-text-muted)">{weekNo(w.start)}</text>
                )}
              </g>
            );
          })}
          <text x={PAD.l} y={12} fontSize={11} fill="var(--color-text-muted)">Kilometer pr. uge (uge nr.). Stiplet søjle: ugen er ikke slut.</text>
        </svg>
      </div>

      {load.notes.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 4 }}>
          {load.notes.map((n) => (
            <li key={n} className="u-card__meta">{n}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
