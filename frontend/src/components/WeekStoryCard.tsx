import { useMemo } from "react";
import { useMe } from "../lib/meContext";
import { newRecords, weekStory } from "../lib/records";
import { Activity } from "../lib/week";

/** What went well this week, and any record set in the last days. Renders nothing when there is nothing true to say. */
export default function WeekStoryCard({ activities, today = new Date() }: { activities: Activity[]; today?: Date }) {
  const { isChild } = useMe();
  const { story, fresh } = useMemo(() => ({ story: weekStory(activities, today), fresh: isChild ? [] : newRecords(activities, today) }), [activities, today, isChild]); // a child gets no records to beat
  if (!story && fresh.length === 0) return null;
  return (
    <section className="u-card" aria-labelledby="story-title" style={{ display: "grid", gap: 8 }}>
      <h2 id="story-title" className="u-h2">Ugens historie</h2>
      {story && <p style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>{story.headline}</p>}
      {story?.notes.map((n) => (
        <p key={n} style={{ margin: 0 }}>{n}</p>
      ))}
      {fresh.length > 0 && (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexWrap: "wrap", gap: 8 }}>
          {fresh.map((r) => (
            <li key={r.key} className="u-chip u-chip--good">Ny rekord · {r.label}: {r.value}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
