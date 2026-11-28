import LoadCard from "../components/LoadCard";
import { useEffect, useState } from "react";
import MilestoneCard from "../components/MilestoneCard";
import RaceCard from "../components/RaceCard";
import PaceLandscape from "../components/PaceLandscape";
import RoutesCard from "../components/RoutesCard";
import TrophyShelf from "../components/TrophyShelf";
import YearRing from "../components/YearRing";
import { api } from "../api";
import FirstsCard from "../components/FirstsCard";
import BadgeShelf from "../components/BadgeShelf";
import JourneyCard from "../components/JourneyCard";
import { journey } from "../lib/journey";
import { useMe } from "../lib/meContext";
import { useMemo } from "react";
import { Other } from "../lib/other";
import { Activity, PlannedRun } from "../lib/week";

/** The pictures. Quick things first (badges, records, the next race, load, build-up, the year), the big map and the pace landscape last. */
export default function ExplorePage({ activities, plannedRuns }: { activities: Activity[]; plannedRuns: PlannedRun[] }) {
  const [others, setOthers] = useState<Other[]>([]);
  useEffect(() => {
    api.getOther().then(setOthers).catch(() => setOthers([])); // other training is a bonus: everything works without it
  }, []);
  const { isChild } = useMe();
  const beginner = useMemo(() => journey(activities, new Date())?.beginner ?? false, [activities]);
  // someone new to running meets their own start first; the records wait until there is something to beat
  const start = (
    <>
      <JourneyCard activities={activities} />
      <FirstsCard />
    </>
  );
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <p className="now__eyebrow">Udforsk</p>
        <h1 className="u-h1">Din træning i billeder</h1>
      </section>
      <BadgeShelf />
      {(beginner || isChild) && start}
      {!beginner && !isChild && <TrophyShelf activities={activities} />}
      {!isChild && <RaceCard activities={activities} plannedRuns={plannedRuns} />}
      {!isChild && <LoadCard activities={activities} others={others} />}
      {!beginner && !isChild && start}
      <YearRing activities={activities} others={others} />
      {!isChild && <MilestoneCard activities={activities} />}
      {/* the big pictures last: the map is a block that would push everything else out of sight */}
      {!isChild && <RoutesCard others={others} />}
      {!isChild && <PaceLandscape />}
    </div>
  );
}
