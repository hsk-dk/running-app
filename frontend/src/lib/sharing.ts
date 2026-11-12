/** What each sharing level means, in words a family member can decide on. Matches the server's levels. */
export type SharingLevel = "private" | "overview" | "all";

export const SHARING_LEVELS: { key: SharingLevel; label: string; summary: string }[] = [
  { key: "private", label: "Privat", summary: "Ingen andre ser noget af dine løb. Du er stadig med i familien, men uden tal." },
  {
    key: "overview",
    label: "Overblik",
    summary: "Familien ser dit navn, ugens løb, kilometer denne måned og uger i træk. Ingen ruter, tider eller puls.",
  },
  {
    key: "all",
    label: "Det hele",
    summary: "Familien ser også dine seneste løb med distance og tid og kan åbne dem med ruten. Pulsen deles ikke.",
  },
];

export const levelLabel = (level: string) => SHARING_LEVELS.find((l) => l.key === level)?.label ?? level;
