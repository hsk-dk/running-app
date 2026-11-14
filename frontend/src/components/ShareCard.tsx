import { useEffect, useMemo, useRef, useState } from "react";
import { APP_NAME } from "../lib/brand";
import { otherDays } from "../lib/other";
import { FilmRun, ShareStat, shareStats, summarise } from "../lib/film";
import { MONTHS, buildRing, monthMarks } from "../lib/ring";
import { Delivery, deliverImage, fileSafe } from "../lib/shareImage";
import { DayCell } from "../lib/year";

const W = 1080;
const H = 1350;
const C = W / 2;
const CY = 650;
const INNER = 160;
const OUTER = 385;
const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

type Props = { title: string; runs: FilmRun[]; days: DayCell[]; others?: { date: string | null }[] };

const km0 = (v: number) => Math.round(v).toLocaleString("da-DK");

/** The picture: the ring of days, the total and three numbers. No places, no routes, no heart rate. */
export function drawShareCard(ctx: CanvasRenderingContext2D, title: string, totalKm: number, stats: ShareStat[], days: DayCell[], otherSet: Set<string> = new Set()) {
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, "#3A5F90");
  bg.addColorStop(1, "#22405f");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  const ls = ctx as any;
  const spaced = (v: string) => {
    if ("letterSpacing" in ls) ls.letterSpacing = v;
  };
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.font = `600 30px ${FONT}`;
  spaced("0.3em");
  ctx.fillText("DIT TRÆNINGSÅR", C, 110);
  ctx.font = `400 34px ${FONT}`;
  spaced("0.12em");
  ctx.fillStyle = "rgba(255,255,255,0.62)";
  ctx.fillText(title.toUpperCase(), C, 164);
  spaced("0px");

  const { spokes, capKm } = buildRing(days, C, INNER, OUTER, Math.max(days.length, 1));
  ctx.strokeStyle = "rgba(255,255,255,0.18)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(C, CY, INNER - 12, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineCap = "round";
  for (const s of spokes) {
    if (s.km <= 0) continue;
    const strength = Math.min(1, s.km / capKm);
    ctx.strokeStyle = `rgba(255,255,255,${0.35 + 0.6 * strength})`;
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(s.x0, s.y0 - (C - CY));
    ctx.lineTo(s.x1, s.y1 - (C - CY));
    ctx.stroke();
  }
  // days with other training (rowing, walks, rides) as small dots on the inner ring, so a winter of rowing is not a blank
  ctx.fillStyle = "rgba(255,255,255,0.55)";
  for (const s of spokes) {
    if (!otherSet.has(s.date)) continue;
    ctx.beginPath();
    ctx.arc(C + Math.sin(s.angle) * (INNER - 12), CY - Math.cos(s.angle) * (INNER - 12), 4.5, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = "rgba(255,255,255,0.55)";
  ctx.font = `500 26px ${FONT}`;
  for (const m of monthMarks(spokes)) {
    const r = OUTER + 44;
    ctx.fillText(MONTHS[m.month], C + Math.sin(m.angle) * r, CY - Math.cos(m.angle) * r + 9);
  }

  ctx.fillStyle = "#fff";
  ctx.font = `700 ${totalKm >= 1000 ? 88 : 108}px ${FONT}`;
  ctx.fillText(km0(totalKm), C, CY + 28);
  ctx.fillStyle = "rgba(255,255,255,0.75)";
  ctx.font = `400 40px ${FONT}`;
  ctx.fillText("kilometer", C, CY + 84);

  const colW = W / Math.max(stats.length, 1);
  stats.forEach((st, i) => {
    const x = colW * i + colW / 2;
    ctx.fillStyle = "#fff";
    ctx.font = `700 64px ${FONT}`;
    ctx.fillText(st.value, x, 1190);
    ctx.fillStyle = "rgba(255,255,255,0.68)";
    ctx.font = `400 30px ${FONT}`;
    ctx.fillText(st.label, x, 1236);
  });
  ctx.fillStyle = "rgba(255,255,255,0.4)";
  ctx.font = `500 26px ${FONT}`;
  spaced("0.3em");
  ctx.fillText(APP_NAME.toUpperCase(), C, 1312);
  spaced("0px");
}

/** A picture of your year to keep or share. It contains no places, no routes and no heart rate, and is made in the browser. */
export default function ShareCard({ title, runs, days, others = [] }: Props) {
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const [message, setMessage] = useState<string>("");
  const stats = useMemo(() => shareStats(runs), [runs]);
  const totalKm = useMemo(() => summarise(runs).km, [runs]);

  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext("2d");
    if (!el || !ctx || stats.length === 0) return;
    drawShareCard(ctx, title, totalKm, stats, days, otherDays(others));
  }, [title, totalKm, stats, days, others]);

  if (stats.length === 0) return null;

  async function share() {
    const el = canvas.current;
    if (!el) return;
    setMessage("");
    const blob: Blob | null = await new Promise((resolve) => el.toBlob(resolve, "image/png"));
    if (!blob) {
      setMessage("Billedet kunne ikke laves.");
      return;
    }
    try {
      const how: Delivery = await deliverImage(blob, `mit-traeningsaar-${fileSafe(title)}.png`, `Mit træningsår: ${title}`);
      setMessage(how === "shared" ? "Delt." : how === "downloaded" ? "Billedet er gemt som en fil." : "");
    } catch (e: any) {
      setMessage(e?.message || "Billedet kunne ikke gemmes.");
    }
  }

  return (
    <section style={{ display: "grid", gap: 10, justifyItems: "start" }} aria-label="Del dit år som billede">
      <canvas
        ref={canvas}
        width={W}
        height={H}
        role="img"
        aria-label={`Billede til deling: ${title}, ${km0(totalKm)} kilometer, ${stats.map((s) => `${s.value} ${s.label}`).join(", ")}.`}
        style={{ width: "min(100%, 320px)", height: "auto", borderRadius: 12 }}
      />
      <button type="button" className="u-btn u-btn--primary" onClick={share}>Del eller gem som billede</button>
      <p className="u-card__meta" role="status">
        {message || "Billedet viser kun tal og dine træningsdage. Ingen steder, ingen ruter og ingen puls."}
      </p>
    </section>
  );
}
