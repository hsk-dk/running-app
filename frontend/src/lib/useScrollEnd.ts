import { useEffect, useRef } from "react";

/** For a chart that scrolls sideways on a small screen: start at the right-hand end, where the newest data is. */
export function useScrollEnd<T extends HTMLElement>(deps: unknown[] = []) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (el && el.scrollWidth > el.clientWidth) el.scrollLeft = el.scrollWidth;
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  return ref;
}

/** A round number to end an axis on: 4 or fewer steps of 5, 10, 20, 50, 100... */
export function niceMax(value: number, minimum = 20): { max: number; step: number } {
  const target = Math.max(value, minimum);
  const step = [5, 10, 20, 25, 50, 100, 200, 500, 1000].find((s) => Math.ceil(target / s) <= 4) ?? 1000;
  return { max: Math.ceil(target / step) * step, step };
}
