import { ChipVariant, chipClass, statusLabel, statusVariant } from "../lib/status";

/** A status or category as a tinted chip. The variant follows the word unless one is given. */
export default function StatusBadge({ value, variant }: { value: string; variant?: ChipVariant }) {
  return <span className={chipClass(variant ?? statusVariant(value))}>{statusLabel(value)}</span>;
}
