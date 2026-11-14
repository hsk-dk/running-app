import LoadCard from "../components/LoadCard";
import { useEffect, useState } from "react";
import MilestoneCard from "../components/MilestoneCard";
import RaceCard from "../components/RaceCard";
import PaceLandscape from "../components/PaceLandscape";
import RoutesCard from "../components/RoutesCard";
import TrophyShelf from "../components/TrophyShelf";
import YearRing from "../components/YearRing";
import { api } from "../api";
import { Other } from "../lib/other";
import { Activity, PlannedRun } from "../lib/week";

/** The pictures: your routes, your year, the next race and the total. */
export default function ExplorePage({ activities, plannedRuns }: { activities: Activity[]; plannedRuns: PlannedRun[] }) {
  const [others, setOthers] = useState<Other[]>([]);
  useEffect(() => {
    api.getOther().then(setOthers).catch(() => setOthers([])); // other training is a bonus: everything works without it
  }, []);
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <p className="now__eyebrow">Udforsk</p>
        <h1 className="u-h1">Din træning i billeder</h1>
      </section>
      <RaceCard activities={activities} plannedRuns={plannedRuns} />
      <RoutesCard others={others} />
      <PaceLandscape />
      <LoadCard activities={activities} others={others} />
      <TrophyShelf activities={activities} />
      <YearRing activities={activities} others={others} />
      <MilestoneCard activities={activities} />
    </div>
  );
}
