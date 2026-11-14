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

/** What a status chip says. The week colours become words everyone understands. */
const LABELS: Record<string, string> = { "grøn": "På sporet", "gul": "Lidt bagud", "rød": "Bagud" };
export const statusLabel = (value: string) => LABELS[value.trim().toLowerCase()] ?? (value ? value.charAt(0).toUpperCase() + value.slice(1) : value);

export function statusVariant(value: string): ChipVariant {
  return VARIANTS[value.trim().toLowerCase()] ?? "neutral";
}

export const chipClass = (variant: ChipVariant) => (variant === "neutral" ? "u-chip" : `u-chip u-chip--${variant}`);
