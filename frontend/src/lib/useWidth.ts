import { useEffect, useState } from "react";

/**
 * The width of an element in pixels, kept up to date. Charts use it so their text stays a readable size on a phone.
 * Returns a callback ref, so it also works for an element that only appears later (for example after data has loaded).
 */
export function useWidth<T extends HTMLElement>(fallback = 640): [(el: T | null) => void, number] {
  const [el, setEl] = useState<T | null>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    if (!el) return;
    const read = () => setWidth(Math.round(el.clientWidth) || fallback);
    read();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(read);
    ro.observe(el);
    return () => ro.disconnect();
  }, [el, fallback]);
  return [setEl, width];
}

/** Keeps a label only if it is at least `gap` pixels from the previous kept one (so labels never overlap). */
export function thinLabels(xs: number[], gap: number): boolean[] {
  let last = -Infinity;
  return xs.map((x) => {
    if (x - last >= gap) {
      last = x;
      return true;
    }
    return false;
  });
}
