"use client";
// The mission cards that a trigger can be covered on, shown in the context bar: the circles that may be covered are clickable on the card itself
// (the engine's `cover` moves say which), the circles that cannot are not. A card whose circles have no known place on the picture gets buttons.
import { cardImage } from "@/lib/cardImages";
import { MISSION_CIRCLES } from "@/lib/missionCircles";
import { cardName } from "@/lib/moves";
import type { CSSProperties } from "react";
import { CoverMarker } from "./CoverMarker";
import type { PieceColor } from "./Pieces";

export type CoverChoice = { card: string; circle: number };

export function MissionCover({
  options,
  used,
  color,
  picked,
  onPick,
}: {
  /** The circles that can be covered now. */
  options: CoverChoice[];
  /** For each mission card, which of its circles are already covered. */
  used: Record<string, boolean[]>;
  /** The colour of the player's markers, which lie on the circles that are covered. */
  color: PieceColor;
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
                {places.map((at, i) => {
                  if (mine.some((o) => o.circle === i)) return null;
                  if (used[card]?.[i] === true)
                    return (
                      <CoverMarker key={`covered-${at.x}`} x={at.x} y={at.y} color={color} title={`Circle ${i + 1} is already covered`} />
                    );
                  return (
                    <span
                      key={`blocked-${at.x}`}
                      className="coverblocked"
                      style={{ left: `${at.x * 100}%`, "--y": at.y } as CSSProperties}
                      title={`Circle ${i + 1} is not triggered by this`}
                    >
                      ×
                    </span>
                  );
                })}
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
