import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Area } from "../lib/areas";
import { Camera, FlightArea, Indoor, Point, Segment, Town, Tour, arcPoint, arcPoints, buildTour, dwellMs, flightAreas, mercator, smooth, stateAt, startOfArrival, startOfHold, startOfIndoor } from "../lib/flight";
import { prefersReducedMotion } from "../lib/motion";
import { deliverImage } from "../lib/shareImage";
import { frameAt, partial, timeline } from "../lib/playback";
import { useWidth } from "../lib/useWidth";
import { parseDateKey } from "../lib/week";

type Land = { rings: Float64Array[]; boxes: [number, number, number, number][] };
/** `coast` is the detailed Danish coast; `coastBox` is the area it covers, in map units. */
type Assets = { land: Land; coast: Land | null; coastBox: [number, number, number, number] | null; towns: Town[] };

const DRAW_SHARE = 0.8; // routes are drawn during the first 80 % of a stay, then everything rests for a moment

function decodeLand(data: { scale: number; rings: number[][] }): Land {
  const rings: Float64Array[] = [];
  const boxes: [number, number, number, number][] = [];
  for (const flat of data.rings) {
    const pts = new Float64Array(flat.length);
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (let i = 0; i < flat.length; i += 2) {
      const [x, y] = mercator(flat[i] / data.scale, flat[i + 1] / data.scale);
      pts[i] = x;
      pts[i + 1] = y;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    rings.push(pts);
    boxes.push([minX, minY, maxX, maxY]);
  }
  return { rings, boxes };
}

function decodeCoast(data: { scale: number; bbox: number[]; rings: number[][] }): Pick<Assets, "coast" | "coastBox"> {
  const [lon0, lat0, lon1, lat1] = data.bbox;
  const [x0, y1] = mercator(lon0, lat0); // y grows southwards, so the south edge has the larger y
  const [x1, y0] = mercator(lon1, lat1);
  return { coast: decodeLand(data), coastBox: [x0, y0, x1, y1] };
}

const ramp = (v: number, a: number, b: number) => Math.min(1, Math.max(0, (v - a) / (b - a)));
const niceStep = (target: number) => {
  const mag = Math.pow(10, Math.floor(Math.log10(target)));
  return [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= target) ?? target;
};
const dateText = (d: string) => parseDateKey(d).toLocaleDateString("da-DK", { day: "numeric", month: "short", year: "numeric" });

type Frame = { W: number; H: number; cam: Camera; tour: Tour; areas: FlightArea[]; assets: Assets | null; ms: number; playbacks: ReturnType<typeof timeline>[]; indoor: Indoor | null };

const shortDate = (d: string | null) => (d ? parseDateKey(d).toLocaleDateString("da-DK", { day: "numeric", month: "short", year: "numeric" }) : "");
const km1 = (v: number) => v.toLocaleString("da-DK", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** A point on a running track (a stadium: two straights and two half circles), t from 0 to 1 once round. */
function trackPoint(cx: number, cy: number, w: number, h: number, t: number): Point {
  const r = h / 2;
  const L = w - h;
  const perim = 2 * L + 2 * Math.PI * r;
  let d = (((t % 1) + 1) % 1) * perim;
  if (d < L) return [cx - L / 2 + d, cy - r]; // top, left to right
  d -= L;
  if (d < Math.PI * r) {
    const a = -Math.PI / 2 + d / r; // right end, downwards
    return [cx + L / 2 + r * Math.cos(a), cy + r * Math.sin(a)];
  }
  d -= Math.PI * r;
  if (d < L) return [cx + L / 2 - d, cy + r]; // bottom, right to left
  d -= L;
  const a = Math.PI / 2 + d / r; // left end, upwards
  return [cx - L / 2 + r * Math.cos(a), cy + r * Math.sin(a)];
}

/** The treadmill stop: the map steps back, and a track fills up with one mark per run while the distance counts up. */
function drawTreadmill(ctx: CanvasRenderingContext2D, W: number, H: number, progress: number, indoor: Indoor) {
  const dim = Math.min(ramp(progress, 0, 0.14), 1 - ramp(progress, 0.9, 1));
  if (dim <= 0.01) return;
  ctx.fillStyle = `rgba(16,32,54,${0.86 * dim})`;
  ctx.fillRect(0, 0, W, H);
  const p = ramp(progress, 0.12, 0.88);
  const tw = Math.min(W * 0.68, 480);
  const th = Math.min(tw * 0.42, H * 0.5);
  const cx = W / 2;
  const cy = H * 0.46;
  const path = (inset: number) => {
    const r = th / 2 - inset;
    const L = tw - th;
    ctx.beginPath();
    ctx.moveTo(cx - L / 2, cy - r);
    ctx.lineTo(cx + L / 2, cy - r);
    ctx.arc(cx + L / 2, cy, r, -Math.PI / 2, Math.PI / 2);
    ctx.lineTo(cx - L / 2, cy + r);
    ctx.arc(cx - L / 2, cy, r, Math.PI / 2, (3 * Math.PI) / 2);
    ctx.closePath();
  };
  ctx.globalAlpha = dim;
  ctx.lineCap = "round";
  ctx.setLineDash([]);
  ctx.strokeStyle = "rgba(255,255,255,0.14)";
  ctx.lineWidth = 22;
  path(11);
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,0.32)";
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 6]);
  path(11);
  ctx.stroke();
  ctx.setLineDash([]);
  const n = Math.min(indoor.runs, 48);
  const lit = Math.floor(p * n + 1e-9);
  for (let i = 0; i < n; i++) {
    const [x, y] = trackPoint(cx, cy, tw - 22, th - 22, i / n);
    ctx.fillStyle = i < lit ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.2)";
    ctx.beginPath();
    ctx.arc(x, y, i < lit ? 3.6 : 2.4, 0, Math.PI * 2);
    ctx.fill();
  }
  const [dx, dy] = trackPoint(cx, cy, tw - 22, th - 22, p * Math.min(n, 12));
  ctx.fillStyle = "rgba(156,196,255,0.4)";
  ctx.beginPath();
  ctx.arc(dx, dy, 11, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.beginPath();
  ctx.arc(dx, dy, 4.5, 0, Math.PI * 2);
  ctx.fill();

  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "#fff";
  ctx.font = `700 ${Math.round(Math.min(40, th * 0.34))}px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`;
  ctx.fillText(`${Math.round(indoor.km * p).toLocaleString("da-DK")} km`, cx, cy + th * 0.06);
  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.font = `400 12px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`;
  ctx.fillText(`${Math.round(indoor.runs * p)} af ${indoor.runs} løb`, cx, cy + th * 0.06 + 20);
  const ls = ctx as any;
  if ("letterSpacing" in ls) ls.letterSpacing = "0.22em";
  ctx.fillStyle = "rgba(255,255,255,0.78)";
  ctx.font = `600 13px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`;
  ctx.fillText("LØBEBÅND OG INDENDØRS", cx, cy + th / 2 + 40);
  if ("letterSpacing" in ls) ls.letterSpacing = "0px";
  ctx.globalAlpha = 1;
}

/** Draws one frame. Pure drawing: everything it needs is in `f`. */
function draw(ctx: CanvasRenderingContext2D, f: Frame) {
  const { W, H, tour, areas, assets, ms } = f;
  const st = stateAt(tour, ms);
  const cam = st.camera;
  const s = W / cam.w;
  const px = (x: number, y: number): Point => [(x - cam.x) * s + W / 2, (y - cam.y) * s + H / 2];

  // sea
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, "#3A5F90");
  bg.addColorStop(1, "#22405f");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // a faint grid, finer the closer you are
  const step = niceStep(cam.w / 7);
  ctx.strokeStyle = "rgba(255,255,255,0.055)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  const x0 = Math.floor((cam.x - cam.w / 2) / step) * step;
  for (let x = x0; x <= cam.x + cam.w / 2; x += step) {
    const sx = px(x, 0)[0];
    ctx.moveTo(sx, 0);
    ctx.lineTo(sx, H);
  }
  const hh = (cam.w * H) / W;
  const y0 = Math.floor((cam.y - hh / 2) / step) * step;
  for (let y = y0; y <= cam.y + hh / 2; y += step) {
    const sy = px(0, y)[1];
    ctx.moveTo(0, sy);
    ctx.lineTo(W, sy);
  }
  ctx.stroke();

  // land. The coarse European outline, and over Denmark a detailed coast that takes over once the view is inside its area.
  // The two cross-fade, because the detailed one is cut off at the edge of its area.
  const minX = cam.x - cam.w / 2, maxX = cam.x + cam.w / 2, minY = cam.y - hh / 2, maxY = cam.y + hh / 2;
  let fine = 0;
  if (assets?.coast && assets.coastBox) {
    const [bx0, by0, bx1, by1] = assets.coastBox;
    const margin = Math.min(minX - bx0, bx1 - maxX, minY - by0, by1 - maxY);
    fine = smooth(ramp(margin, 0, 0.25));
  }
  const paintLand = (land: Land, alpha: number) => {
    if (alpha < 0.01) return;
    ctx.fillStyle = `rgba(255,255,255,${0.11 * alpha})`;
    ctx.strokeStyle = `rgba(255,255,255,${0.3 * alpha})`;
    ctx.lineWidth = 1;
    ctx.lineJoin = "round";
    land.rings.forEach((ring, i) => {
      const b = land.boxes[i];
      if (b[2] < minX || b[0] > maxX || b[3] < minY || b[1] > maxY) return;
      ctx.beginPath();
      for (let k = 0; k < ring.length; k += 2) {
        const sx = (ring[k] - cam.x) * s + W / 2;
        const sy = (ring[k + 1] - cam.y) * s + H / 2;
        if (k === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    });
  };
  if (assets) {
    // coarse land is a stand-in at close range, so it fades out when zoomed in, unless the detailed coast covers that place
    paintLand(assets.land, smooth(ramp(cam.w, 0.18, 1.3)) * (1 - fine));
    if (assets.coast) paintLand(assets.coast, fine * smooth(ramp(cam.w, 0.01, 0.08)));
  }

  // lines between places, dotted, drawn while flying
  const full = Math.min(areas.length - 1, Math.floor(Math.min(st.linesDrawn, areas.length)));
  ctx.lineCap = "round";
  ctx.setLineDash([1, 7]);
  ctx.strokeStyle = "rgba(255,255,255,0.6)";
  ctx.lineWidth = 2;
  const line = (a: Point, b: Point, upTo: number) => {
    const pts = arcPoints(a, b, upTo);
    ctx.beginPath();
    pts.forEach(([x, y], i) => {
      const [sx, sy] = px(x, y);
      if (i === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    });
    ctx.stroke();
  };
  for (let k = 0; k < full; k++) line(areas[k].center, areas[k + 1].center, 1);
  const partialLine = st.linesDrawn - Math.floor(st.linesDrawn);
  if (Number.isFinite(st.linesDrawn) && st.segment.kind === "fly" && st.segment.fromArea !== null && st.segment.toArea !== null && partialLine > 0.001) {
    line(areas[st.segment.fromArea].center, areas[st.segment.toArea].center, partialLine);
  }
  ctx.setLineDash([]);

  // routes
  const dwell = st.segment.kind === "dwell" ? st.segment : null;
  const reachedCount = Math.min(areas.length, Number.isFinite(st.reached) ? st.reached : areas.length);
  const trace = (pts: Point[], upTo?: Point[]) => {
    ctx.beginPath();
    (upTo ?? pts).forEach(([x, y], i) => {
      const [sx, sy] = px(x, y);
      if (i === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    });
    ctx.stroke();
  };
  const near = ramp(1.2 - cam.w, 0, 1.1); // 0 far away, 1 close: routes are thin threads from afar and bright when close
  ctx.lineJoin = "round";
  for (let i = 0; i < reachedCount; i++) {
    const done = areas[i].routes;
    ctx.strokeStyle = `rgba(255,255,255,${0.22 + 0.5 * near})`;
    ctx.lineWidth = 1 + near * 1.4;
    for (const r of done) trace(r.points);
  }
  if (dwell) {
    const area = areas[dwell.area];
    const total = Math.max(1, dwell.endMs - dwell.startMs);
    const drawMs = total * DRAW_SHARE;
    const frame = frameAt(f.playbacks[dwell.area], Math.min(drawMs, st.progress * total) * (f.playbacks[dwell.area].totalMs / drawMs));
    const byId = new Map(area.routes.map((r) => [r.id, r]));
    ctx.strokeStyle = "rgba(255,255,255,0.82)";
    ctx.lineWidth = 2.2;
    for (const id of frame.doneIds) trace(byId.get(id)!.points);
    const cur = frame.currentId !== null ? byId.get(frame.currentId) : null;
    if (cur) {
      const pts = partial(cur.points, frame.fraction);
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 3.2;
      trace(pts);
      const [hx, hy] = px(pts[pts.length - 1][0], pts[pts.length - 1][1]);
      ctx.fillStyle = "rgba(156,196,255,0.35)";
      ctx.beginPath();
      ctx.arc(hx, hy, 11, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#ffffff";
      ctx.beginPath();
      ctx.arc(hx, hy, 4.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // pins: where you have run, visible from afar
  const far = ramp(cam.w, 0.05, 0.4);
  if (far > 0.01) {
    for (let i = 0; i < reachedCount; i++) {
      const [sx, sy] = px(areas[i].center[0], areas[i].center[1]);
      ctx.fillStyle = `rgba(156,196,255,${0.3 * far})`;
      ctx.beginPath();
      ctx.arc(sx, sy, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = `rgba(255,255,255,${0.95 * far})`;
      ctx.beginPath();
      ctx.arc(sx, sy, 3.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // the little aeroplane-dot on the line while flying between places
  if (st.segment.kind === "fly" && st.segment.fromArea !== null && st.segment.toArea !== null) {
    const p = arcPoint(areas[st.segment.fromArea].center, areas[st.segment.toArea].center, smooth(st.progress));
    const [sx, sy] = px(p[0], p[1]);
    ctx.fillStyle = "rgba(156,196,255,0.4)";
    ctx.beginPath();
    ctx.arc(sx, sy, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.beginPath();
    ctx.arc(sx, sy, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  // names: quiet. One small label while you are somewhere; tiny ones next to the pins when zoomed out.
  const ls = (ctx as any);
  const spaced = (px_: number, weight = 600) => {
    ctx.font = `${weight} ${px_}px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`;
    if ("letterSpacing" in ls) ls.letterSpacing = px_ >= 12 ? "0.22em" : "0.14em";
  };
  const pad = Math.max(16, W * 0.03);
  if (dwell) {
    const a = areas[dwell.area];
    const alpha = Math.min(ramp(st.progress, 0.04, 0.2), 1 - ramp(st.progress, 0.9, 1));
    if (alpha > 0.01) {
      const base = H - pad;
      ctx.textBaseline = "alphabetic";
      ctx.textAlign = "left";
      ctx.fillStyle = `rgba(255,255,255,${0.78 * alpha})`;
      spaced(13);
      ctx.fillText(a.name.toUpperCase(), pad + 34, base - 56);
      ctx.fillRect(pad, base - 60, 24, 1);
      spaced(11, 400);
      ctx.fillStyle = `rgba(255,255,255,${0.55 * alpha})`;
      ctx.fillText(`${a.routes.length} løb · ${Math.round(a.km)} km`.toUpperCase(), pad + 34, base - 36);
      ctx.fillText(`FØRST ${shortDate(a.firstDate)} · LÆNGST ${km1(a.longest.km)} KM`.toUpperCase(), pad + 34, base - 18);
      const now = (() => {
        const total = Math.max(1, dwell.endMs - dwell.startMs);
        const fr = frameAt(f.playbacks[dwell.area], Math.min(total * DRAW_SHARE, st.progress * total) * (f.playbacks[dwell.area].totalMs / (total * DRAW_SHARE)));
        return fr.currentId !== null ? a.routes.find((r) => r.id === fr.currentId) ?? null : null;
      })();
      if (now) {
        ctx.fillStyle = `rgba(255,255,255,${0.85 * alpha})`;
        ctx.fillText(`${shortDate(now.date)} · ${km1(now.km)} km`.toUpperCase(), pad + 34, base);
      }
    }
  } else if (far > 0.4 && cam.w > 0.25) {
    spaced(11, 500);
    ctx.textAlign = "left";
    ctx.fillStyle = `rgba(255,255,255,${0.7 * far})`;
    for (let i = 0; i < reachedCount; i++) {
      const [sx, sy] = px(areas[i].center[0], areas[i].center[1]);
      ctx.fillText(areas[i].name.toUpperCase(), sx + 14, sy + 4);
    }
  }
  if ("letterSpacing" in ls) ls.letterSpacing = "0px";
  if (st.segment.kind === "indoor" && f.indoor) drawTreadmill(ctx, W, H, st.progress, f.indoor);
}

const jumpMs = (tour: Tour, i: number) => startOfArrival(tour, i);

/** A stylised map. The camera flies between the places you have run: out, across, in, with a dotted line behind it. */
export default function FlightMap({
  areas,
  indoor = null,
  speed = 1,
  autoplay = true,
  bare = false,
  onDone,
}: {
  areas: Area[];
  /** Runs without a route: they get a treadmill stop at the end. */
  indoor?: Indoor | null;
  speed?: number;
  autoplay?: boolean;
  /** No controls, no slider and no notes: for the year film, which has its own. */
  bare?: boolean;
  onDone?: () => void;
}) {
  const [box, W] = useWidth<HTMLDivElement>();
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const [assets, setAssets] = useState<Assets | null>(null);
  const reduced = useMemo(() => prefersReducedMotion(), []);
  const [playing, setPlaying] = useState(autoplay && !reduced);
  const done = useRef(onDone);
  done.current = onDone;
  const [uiMs, setUiMs] = useState(0);
  const [saved, setSaved] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([import("../assets/europe-land.json"), import("../assets/europe-towns.json"), import("../assets/denmark-coast.json").catch(() => null)])
      .then(([land, towns, coast]) => {
        if (cancelled) return;
        const detail = coast ? decodeCoast((coast as any).default) : { coast: null, coastBox: null };
        setAssets({ land: decodeLand((land as any).default), ...detail, towns: (towns as any).default });
      })
      .catch(() => !cancelled && setAssets({ land: { rings: [], boxes: [] }, coast: null, coastBox: null, towns: [] })); // no coast, but the flight still works
    return () => {
      cancelled = true;
    };
  }, []);

  const narrow = W < 520;
  const H = Math.round(Math.min(560, Math.max(280, W * (narrow ? 0.95 : 0.58))));
  const fa = useMemo(() => (assets ? flightAreas(areas, W / H, assets.towns) : []), [areas, assets, W, H]);
  const tour = useMemo(() => (fa.length ? buildTour(fa, W / H, { indoor, speed }) : null), [fa, W, H, indoor, speed]);
  const playbacks = useMemo(
    () => fa.map((a) => timeline(a.routes.map((r) => ({ id: r.id, date: r.date, distance_km: r.km, route: "" })), dwellMs(a) * DRAW_SHARE)),
    [fa],
  );

  const msRef = useRef(0);
  const playingRef = useRef(playing);
  playingRef.current = playing;
  const last = useRef(0);
  const raf = useRef(0);
  const dirty = useRef(true);

  const paint = useCallback(() => {
    const el = canvas.current;
    if (!el || !tour) return;
    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    if (el.width !== Math.round(W * dpr) || el.height !== Math.round(H * dpr)) {
      el.width = Math.round(W * dpr);
      el.height = Math.round(H * dpr);
    }
    const ctx = el.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw(ctx, { W, H, cam: tour.overview, tour, areas: fa, assets, ms: msRef.current, playbacks, indoor });
  }, [W, H, tour, fa, assets, playbacks, indoor]);

  // the loop: runs while playing, and once more whenever something changed while paused
  useEffect(() => {
    if (!tour) return;
    if (reduced && msRef.current === 0) msRef.current = startOfHold(tour);
    const tick = (now: number) => {
      if (playingRef.current) {
        const dt = last.current ? now - last.current : 0;
        msRef.current = Math.min(tour.totalMs, msRef.current + dt);
        dirty.current = true;
        if (msRef.current >= tour.totalMs) {
          setPlaying(false);
          done.current?.();
        }
      }
      last.current = now;
      if (dirty.current) {
        dirty.current = false;
        paint();
        setUiMs((prev) => (Math.abs(prev - msRef.current) > 120 || msRef.current >= tour.totalMs ? msRef.current : prev));
      }
      raf.current = requestAnimationFrame(tick);
    };
    last.current = 0;
    dirty.current = true;
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [tour, paint, reduced]);

  const seek = (ms: number) => {
    msRef.current = ms;
    dirty.current = true;
    setUiMs(ms);
  };
  const restart = () => {
    seek(0);
    setPlaying(true);
  };
  const flyTo = (i: number) => {
    if (!tour) return;
    if (reduced) {
      const seg = tour.segments.find((s): s is Extract<Segment, { kind: "dwell" }> => s.kind === "dwell" && s.area === i);
      seek(seg ? seg.startMs + (seg.endMs - seg.startMs) * 0.85 : 0); // a still picture of the place, routes and name in place
      setPlaying(false);
    } else {
      seek(jumpMs(tour, i));
      setPlaying(true);
    }
  };

  /** Saves what is on the map right now. Opt-in, because the picture shows places. */
  const saveFrame = async () => {
    const el = canvas.current;
    if (!el) return;
    paint();
    setSaved("");
    const blob: Blob | null = await new Promise((resolve) => el.toBlob(resolve, "image/png"));
    if (!blob) {
      setSaved("Billedet kunne ikke laves.");
      return;
    }
    try {
      const how = await deliverImage(blob, "min-flyvetur.png", "Min flyvetur");
      setSaved(how === "shared" ? "Delt." : how === "downloaded" ? "Billedet er gemt som en fil." : "");
    } catch (e: any) {
      setSaved(e?.message || "Billedet kunne ikke gemmes.");
    }
  };

  const flyToIndoor = () => {
    if (!tour) return;
    const at = startOfIndoor(tour);
    if (at === null) return;
    const seg = tour.segments.find((x) => x.kind === "indoor")!;
    seek(reduced ? seg.startMs + (seg.endMs - seg.startMs) * 0.85 : at);
    setPlaying(!reduced);
  };

  const st = tour ? stateAt(tour, uiMs) : null;
  const here = st && st.segment.kind === "dwell" ? fa[st.segment.area] : null;
  const finished = tour ? uiMs >= tour.totalMs : false;
  const totalKm = fa.reduce((s, a) => s + a.km, 0);
  const totalRuns = fa.reduce((s, a) => s + a.routes.length, 0);

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div ref={box}>
        <canvas
          ref={canvas}
          role="img"
          aria-label={`Animeret kort, der flyver mellem de ${fa.length} steder, du har løbet: ${fa.map((a) => a.name).join(", ")}.${indoor ? ` Til sidst vises ${indoor.runs} løb indendørs.` : ""}`}
          style={{ display: "block", width: "100%", height: H, borderRadius: 12, background: "#22405f" }}
        />
      </div>

      {tour && !bare && (
        <>
          <p className="u-card__meta" role="status" aria-live="polite">
            {here
              ? `${here.name} · ${here.routes.length} løb · ${Math.round(here.km)} km`
              : st && st.segment.kind === "indoor" && indoor
                ? `Løbebånd og indendørs · ${indoor.runs} løb · ${Math.round(indoor.km)} km`
                : finished || (st && st.segment.kind === "hold")
                ? `${fa.length} ${fa.length === 1 ? "sted" : "steder"} · ${totalRuns} løb · ${Math.round(totalKm)} km${indoor ? ` · og ${indoor.runs} indendørs` : ""}`
                : st && st.segment.kind === "fly"
                  ? "Flyver videre…"
                  : ""}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            {finished ? (
              <button type="button" className="u-btn u-btn--primary" onClick={restart}>Flyv igen</button>
            ) : (
              <button type="button" className="u-btn u-btn--secondary" onClick={() => setPlaying((p) => !p)}>{playing ? "Pause" : "Fortsæt"}</button>
            )}
            {(fa.length > 1 || indoor) && (
              <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span className="u-card__meta">Fly til</span>
                <select
                  value=""
                  onChange={(e) => (e.target.value === "indoor" ? flyToIndoor() : e.target.value !== "" && flyTo(Number(e.target.value)))}
                  style={{ minHeight: 44, padding: "0 10px", border: "1px solid #cbd3dd", borderRadius: 8, font: "inherit", background: "var(--color-surface)" }}
                >
                  <option value="">Vælg sted</option>
                  {fa.map((a, i) => (
                    <option key={a.key} value={i}>{a.name}</option>
                  ))}
                  {indoor && <option value="indoor">Løbebånd og indendørs</option>}
                </select>
              </label>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" className="u-btn u-btn--secondary" onClick={saveFrame}>Gem kortet som billede</button>
            <span className="u-card__meta" role="status">{saved || "Billedet viser kortet med stednavne, som det ser ud lige nu."}</span>
          </div>
          <label className="u-card__meta" style={{ display: "grid", gap: 2 }}>
            Tid i flyveturen
            <input
              type="range"
              min={0}
              max={Math.round(tour.totalMs)}
              step={50}
              value={Math.round(uiMs)}
              onChange={(e) => {
                setPlaying(false);
                seek(Number(e.target.value));
              }}
              style={{ width: "100%", minHeight: 44, accentColor: "#446EA8" }}
            />
          </label>
          <p className="u-card__meta">
            {reduced
              ? "Bevægelse er slået fra: kortet viser alle dine steder. Vælg et sted for at se det."
              : "Kortet tegnes lokalt og dine positioner forlader ikke browseren. Kyster: Natural Earth. Byer: GeoNames (CC BY 4.0). Stednavne er fra dine løbs navne."}
            {fa.some((a) => a.firstDate) && ` Første løb: ${dateText(fa.map((a) => a.firstDate).filter(Boolean).sort()[0] as string)}.`}
          </p>
        </>
      )}
      {!tour && <p className="u-card__meta" role="status">Henter kortet…</p>}
    </div>
  );
}
