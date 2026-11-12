/** Maps a status word to a chip variant from useful-design (D20). The word itself carries the meaning. */
export type ChipVariant = "good" | "warn" | "bad" | "neutral" | "info" | "optional";

const VARIANTS: Record<string, ChipVariant> = {
  // plan and run status
  "gennemført": "good",
  "forkortet": "warn",
  "sprunget over": "bad",
  "flyttet": "info",
  "planlagt": "neutral",
  // week score
  "grøn": "good",
  "gul": "warn",
  "rød": "bad",
  // activities
  "matchet": "good",
  "ikke planlagt": "info",
  "afbrudt": "bad",
  // other
  "afventer": "info",
  "valgfri": "optional",
  "manuel": "neutral",
};

export function statusVariant(value: string): ChipVariant {
  return VARIANTS[value.trim().toLowerCase()] ?? "neutral";
}

export const chipClass = (variant: ChipVariant) => (variant === "neutral" ? "u-chip" : `u-chip u-chip--${variant}`);
