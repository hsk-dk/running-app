import MilestoneCard from "../components/MilestoneCard";
import RaceCard from "../components/RaceCard";
import PaceLandscape from "../components/PaceLandscape";
import RoutesCard from "../components/RoutesCard";
import YearRing from "../components/YearRing";
import { Activity, PlannedRun } from "../lib/week";

/** The pictures: your routes, your year, the next race and the total. */
export default function ExplorePage({ activities, plannedRuns }: { activities: Activity[]; plannedRuns: PlannedRun[] }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <p className="now__eyebrow">Udforsk</p>
        <h1 className="u-h1">Din træning i billeder</h1>
      </section>
      <RaceCard activities={activities} plannedRuns={plannedRuns} />
      <RoutesCard />
      <PaceLandscape />
      <YearRing activities={activities} />
      <MilestoneCard activities={activities} />
    </div>
  );
}
