"use client";
// The mission cards that a trigger can be covered on, shown in the context bar: the circles that may be covered are clickable on the card itself
// (the engine's `cover` moves say which), the circles that cannot are not. A card whose circles have no known place on the picture gets buttons.
import { cardImage } from "@/lib/cardImages";
import { MISSION_CIRCLES } from "@/lib/missionCircles";
import { cardName } from "@/lib/moves";
import type { CSSProperties } from "react";

export type CoverChoice = { card: string; circle: number };

export function MissionCover({
  options,
  picked,
  onPick,
}: {
  /** The circles that can be covered now. */
  options: CoverChoice[];
  picked: CoverChoice | null;
  onPick: (c: CoverChoice) => void;
}) {
  const cards = [...new Set(options.map((o) => o.card))];
  return (
    <span className="coverbar">
      {cards.map((card) => {
        const places = MISSION_CIRCLES[card];
        const mine = options.filter((o) => o.card === card);
        const src = cardImage(card);
        return (
          <span key={card} className="covercard">
            {src && places ? (
              <span className="coverpic">
                <img src={src} alt={cardName(card)} />
                {mine.map((o) => {
                  const at = places[o.circle];
                  if (!at) return null;
                  const on = picked?.card === card && picked.circle === o.circle;
                  return (
                    <button
                      key={o.circle}
                      type="button"
                      className={on ? "coverspot on" : "coverspot"}
                      style={{ left: `${at.x * 100}%`, "--y": at.y } as CSSProperties}
                      aria-pressed={on}
                      aria-label={`Cover circle ${o.circle + 1} of ${cardName(card)}`}
                      onClick={() => onPick(o)}
                    />
                  );
                })}
              </span>
            ) : (
              mine.map((o) => (
                <button key={o.circle} type="button" className="secondary small" onClick={() => onPick(o)}>
                  Cover circle {o.circle + 1} of {cardName(card)}
                </button>
              ))
            )}
          </span>
        );
      })}
    </span>
  );
}
