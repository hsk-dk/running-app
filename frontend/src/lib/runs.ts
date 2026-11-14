/** A run shorter than this is a warm-up or a stopped recording, not a run: it is left out of records, streaks and the film. */
export const MIN_RUN_KM = 1;

export const isRun = (r: { distance_km: number }): boolean => r.distance_km >= MIN_RUN_KM;
