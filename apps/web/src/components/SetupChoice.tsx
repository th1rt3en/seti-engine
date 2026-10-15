"use client";
// The first choice of a game with the organization module: the organizations and then the quick start cards that were dealt to the player (EXP-ORG-04).
// It takes over the whole screen, on a phone too: the organization boards keep their rectangular shape, and the player clicks one and confirms.
import { cardImage } from "@/lib/cardImages";
import { ORG_NAMES } from "@/lib/moves";
import { useState } from "react";
import organizations from "../generated/organizations.json";

const ORGS = organizations as unknown as Record<string, { name: string; abilities: Record<string, string> }>;

export function SetupChoice({
  kind,
  offers,
  selected,
  kept,
  quickOffered = [],
  onSelect,
  onConfirm,
}: {
  kind: "org" | "quick";
  offers: string[];
  selected: string | null;
  /** How many quick start cards the player has kept already (they keep 2). */
  kept: number;
  /** The quick start cards that were dealt to the player: shown under the organizations, so that the choice can take them into account. */
  quickOffered?: string[];
  onSelect: (id: string) => void;
  onConfirm: () => void;
}) {
  const org = kind === "org";
  // the player can put the choice aside to look at the board (the neutral cards, the objectives, the planets) and bring it back
  const [aside, setAside] = useState(false);
  if (aside) {
    return (
      <div className="setupaside" role="region" aria-label="The choice is put aside">
        <span>{org ? "Choosing your organization" : `Choosing quick start card ${kept + 1} of 2`}</span>
        <button type="button" className="primary" onClick={() => setAside(false)}>
          Back to the choice
        </button>
      </div>
    );
  }
  return (
    <div
      className="setupchoice"
      role="dialog"
      aria-modal="true"
      aria-label={org ? "Choose your organization" : "Choose a quick start card"}
    >
      <div className="setupinner">
        <h2>{org ? "Choose your organization" : `Choose quick start card ${kept + 1} of 2`}</h2>
        <p className="muted">
          {org
            ? "Your organization decides your powers, your starting resources and your income for the game."
            : "Each quick start card puts markers on the board at no reward now and gives its bonus at the start. Keep two of the three."}
        </p>
        <div className={org ? "setupcards orgs" : "setupcards quick"}>
          {offers.map((id) => {
            const info = org ? ORGS[id] : undefined;
            return (
              <button
                key={id}
                type="button"
                className={selected === id ? "setupcard chosen" : "setupcard"}
                aria-pressed={selected === id}
                onClick={() => onSelect(id)}
              >
                <img src={cardImage(id)} alt={ORG_NAMES[id] ?? id} />
                {info ? (
                  <span className="setuptext">
                    <b>{info.name}</b>
                    <span className="muted small">{info.abilities.passive ?? info.abilities.mainAction ?? ""}</span>
                    {info.abilities.freeAction ? <span className="muted small">Free action: {info.abilities.freeAction}</span> : null}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
        {org && quickOffered.length > 0 ? (
          <section className="setupquick" aria-label="Your quick start cards">
            <h3>Your quick start cards</h3>
            <p className="muted small">You will keep two of these three after choosing your organization.</p>
            <div className="setupcards quick small">
              {quickOffered.map((id) => (
                <img key={id} src={cardImage(id)} alt={`Quick start card ${id}`} />
              ))}
            </div>
          </section>
        ) : null}
        <div className="setupbar">
          <button type="button" className="secondary big" onClick={() => setAside(true)} title="Hide the choice to look at the board">
            View the board
          </button>
          <button type="button" className="primary big" disabled={selected === null} onClick={onConfirm}>
            {org ? "Take this organization" : "Keep this card"}
          </button>
        </div>
      </div>
    </div>
  );
}
