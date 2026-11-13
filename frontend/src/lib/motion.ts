import { useCallback, useEffect, useRef, useState } from "react";

/** True when the person has asked for less motion. Animations then show their finished picture instead. */
export const prefersReducedMotion = (): boolean =>
  typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * A clock that counts milliseconds from 0 up to `totalMs` while `running`, then stops there.
 * `restart` sets it back to 0 and starts again.
 */
export function useClock(totalMs: number, running: boolean): [number, () => void] {
  const [ms, setMs] = useState(0);
  const base = useRef({ at: 0, from: 0 });
  const [round, setRound] = useState(0);

  useEffect(() => {
    if (!running || totalMs <= 0) return;
    let frame = 0;
    base.current = { at: performance.now(), from: ms };
    const tick = (now: number) => {
      const next = Math.min(totalMs, base.current.from + (now - base.current.at));
      setMs(next);
      if (next < totalMs) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // `ms` is read once when (re)starting; the loop itself keeps its own base
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, totalMs, round]);

  const restart = useCallback(() => {
    setMs(0);
    base.current = { at: performance.now(), from: 0 };
    setRound((r) => r + 1);
  }, []);

  return [ms, restart];
}
