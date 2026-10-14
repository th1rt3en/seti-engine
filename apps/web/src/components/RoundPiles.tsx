// The piles of end-of-round cards, one for each round, below the board. Their cards are face down (nobody sees them until they are taken), so
// each pile shows the back of the main deck and how many cards are left in it.
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";

export function RoundPiles({ view }: { view: View }) {
  const s = view.state;
  if (s.end_of_round_stacks.length === 0) return null;
  // The moon token lies on the pile of the round in which the next first pass will rotate the solar system (PASS-03): this round's pile until
  // somebody has passed, then the next round's. After the last pile it is gone.
  const moonOn = s.phase === "finished" ? -1 : s.first_pass_done ? s.round : s.round - 1;
  return (
    <section className="roundpiles" aria-label="Draw piles for the coming rounds">
      {s.end_of_round_stacks.map((pile, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: the index is the round
        <figure key={i} className={pile.length === 0 ? "pile empty" : "pile"}>
          <div className="pilecards">
            <img src={assets.cardBack} alt="" width={300} height={418} loading="lazy" decoding="async" />
            {i === moonOn ? (
              <img
                className="pilemoon"
                src={assets.moon}
                alt="Moon token"
                title="The first player to pass in this round turns the solar system, and the moon moves on"
                width={80}
                height={80}
              />
            ) : null}
            <span className="count" title={`${pile.length} cards left`}>
              {pile.length}
            </span>
          </div>
          <figcaption className={s.round === i + 1 ? "small current" : "small muted"}>Round {i + 1}</figcaption>
        </figure>
      ))}
    </section>
  );
}
