import { useEffect, useState } from "react";
import { api } from "../api";
import { useMe } from "../lib/meContext";
import { Seen, Shelf, Stars, whatsNew } from "../lib/rewards";

/** "⭐ Du fik 2 nye stjerner" and "🎉 Nyt mærke": what has happened since the last time you looked, said once and then put away. */
export default function CelebrationBanner() {
  const { id } = useMe();
  const [news, setNews] = useState<{ stars: number; badges: string[]; titles: string[] } | null>(null);
  const [now, setNow] = useState<Seen | null>(null);

  useEffect(() => {
    if (id === null) return;
    let live = true;
    Promise.all([api.getStars(), api.getBadges()])
      .then(([s, b]: [Stars, Shelf]) => {
        if (!live) return;
        const current: Seen = { stars: s.total, badges: b.earned.map((x) => x.key) };
        const key = `traening.seen.${id}`;
        let seen: Seen | null = null;
        try {
          seen = JSON.parse(window.localStorage.getItem(key) || "null");
        } catch {
          seen = null;
        }
        const diff = whatsNew(seen, current);
        setNow(current);
        if (diff.stars > 0 || diff.badges.length > 0) {
          setNews({ ...diff, titles: b.earned.filter((x) => diff.badges.includes(x.key)).map((x) => `${x.icon} ${x.title}`) });
        } else {
          window.localStorage.setItem(key, JSON.stringify(current)); // first time, or nothing new: remember where we are
        }
      })
      .catch(() => undefined); // a bonus: the page works without it
    return () => {
      live = false;
    };
  }, [id]);

  if (!news || !now) return null;
  const close = () => {
    try {
      window.localStorage.setItem(`traening.seen.${id}`, JSON.stringify(now));
    } catch {
      // private browsing: the news will simply show again next time
    }
    setNews(null);
  };

  return (
    <div className="u-notice u-notice--success" role="status" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", justifyContent: "space-between" }}>
      <span>
        {news.stars > 0 && <b>⭐ {news.stars === 1 ? "Du fik en ny stjerne!" : `Du fik ${news.stars} nye stjerner!`} </b>}
        {news.titles.length > 0 && <b>🎉 {news.titles.length === 1 ? "Nyt mærke: " : "Nye mærker: "}{news.titles.join(", ")}</b>}
      </span>
      <button type="button" className="u-btn u-btn--secondary" onClick={close}>Fedt!</button>
    </div>
  );
}
