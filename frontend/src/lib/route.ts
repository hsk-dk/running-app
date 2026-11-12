/** Decoding and projecting a Google-encoded polyline (precision 5) for the route poster. */

export type LatLng = [number, number];

export function decodePolyline(encoded: string): LatLng[] {
  const points: LatLng[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;
  while (index < encoded.length) {
    for (const axis of [0, 1]) {
      let shift = 0;
      let result = 0;
      let byte: number;
      do {
        if (index >= encoded.length) return points; // truncated input: keep what was decoded
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20);
      const delta = result & 1 ? ~(result >> 1) : result >> 1;
      if (axis === 0) lat += delta;
      else lng += delta;
    }
    points.push([lat / 1e5, lng / 1e5]);
  }
  return points;
}

/** Fits the route into a width x height box with padding, keeping the true proportions. North is up. */
export function projectRoute(points: LatLng[], width: number, height: number, pad = 24): [number, number][] {
  if (points.length < 2) return [];
  const midLat = points.reduce((s, p) => s + p[0], 0) / points.length;
  const kx = Math.cos((midLat * Math.PI) / 180); // longitude shrinks towards the poles
  const xs = points.map((p) => p[1] * kx);
  const ys = points.map((p) => -p[0]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const spanX = maxX - minX || 1e-9;
  const spanY = maxY - minY || 1e-9;
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
  const offX = (width - spanX * scale) / 2;
  const offY = (height - spanY * scale) / 2;
  return points.map((_, i) => [offX + (xs[i] - minX) * scale, offY + (ys[i] - minY) * scale]);
}

export function toPath(points: [number, number][]): string {
  return points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
}
