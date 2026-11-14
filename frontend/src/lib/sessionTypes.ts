/** The kinds of run a plan can hold. Imports (Runna) and AI suggestions use all of them, so the editor must offer all of them. */
export const SESSION_TYPES: { value: string; label: string }[] = [
  { value: "easy", label: "Let løb" },
  { value: "long", label: "Langtur" },
  { value: "tempo", label: "Tempo" },
  { value: "intervals", label: "Intervaller" },
  { value: "recovery", label: "Restitution" },
  { value: "race", label: "Løb" },
];

/** What a plan's session type is called on screen. Unknown types are shown as they are. */
export function sessionLabel(value: string | null | undefined): string {
  if (!value) return "";
  return SESSION_TYPES.find((t) => t.value === value)?.label ?? value;
}

/** The options for a select, plus the current value when it is not one we know (so saving never changes it silently). */
export function sessionTypeOptions(current?: string): { value: string; label: string }[] {
  if (current && !SESSION_TYPES.some((t) => t.value === current)) return [...SESSION_TYPES, { value: current, label: current }];
  return SESSION_TYPES;
}
