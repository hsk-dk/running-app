import BadgeShelf from "./BadgeShelf";
import CelebrationBanner from "./CelebrationBanner";
import ChallengeCard from "./ChallengeCard";
import StarsCard from "./StarsCard";

/** A child's first page: today's challenge, this week's stars and the badges. No plans, no pace, nothing for adults. */
export default function ChildHome({ error }: { error: string | null }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gap: 24 }}>
      <section>
        <p className="now__eyebrow">Hej</p>
        <h1 className="u-h1">Din dag</h1>
      </section>
      {error && (
        <div className="u-notice u-notice--error" role="alert">
          <b className="u-notice__level">Fejl</b>
          <span>{error}</span>
        </div>
      )}
      <CelebrationBanner />
      <ChallengeCard />
      <StarsCard />
      <BadgeShelf />
    </div>
  );
}
