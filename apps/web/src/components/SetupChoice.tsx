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
  need,
  quickOffered = [],
  onSelect,
  onConfirm,
}: {
  kind: "org" | "quick";
  offers: string[];
  /** The cards that are picked now. */
  selected: string[];
  /** How many cards must be picked (the organization: 1; the quick start cards: 2). */
  need: number;
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
      // biome-ignore lint/a11y/useSemanticElements: a bar, not a section of the page
      <div className="setupaside" role="region" aria-label="The choice is put aside">
        <span>{org ? "Choosing your organization" : `Choosing ${need} quick start cards`}</span>
        <button type="button" className="primary" onClick={() => setAside(false)}>
          Back to the choice
        </button>
      </div>
    );
  }
  return (
    <div
      className="setupchoice"
      // biome-ignore lint/a11y/useSemanticElements: a layer over the board that the page controls itself, not a native <dialog>
      role="dialog"
      aria-modal="true"
      aria-label={org ? "Choose your organization" : "Choose a quick start card"}
    >
      <div className="setupinner">
        <h2>{org ? "Choose your organization" : `Choose ${need} quick start cards`}</h2>
        <p className="muted">
          {org
            ? "Your organization decides your powers, your starting resources and your income for the game."
            : "Each quick start card puts markers on the board at no reward now and gives its bonus at the start. Keep two: pick both, then confirm."}
        </p>
        <div className={org ? "setupcards orgs" : "setupcards quick"}>
          {offers.map((id) => {
            const info = org ? ORGS[id] : undefined;
            return (
              <button
                key={id}
                type="button"
                className={selected.includes(id) ? "setupcard chosen" : "setupcard"}
                aria-pressed={selected.includes(id)}
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
        {org && quickOffered.length > 0 && quickOffered.length <= 3 ? (
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
          <button type="button" className="primary big" disabled={selected.length !== need} onClick={onConfirm}>
            {org ? "Take this organization" : `Keep these ${need} cards (${selected.length} of ${need} picked)`}
          </button>
        </div>
      </div>
    </div>
  );
}

/** The cards that a player tucks for income at the start (EXP-ORG-07, EXP-ORG-14): one at a time, each at once, independent of the others. A tuck that
 * draws a card cannot be taken back, and the drawn card may be tucked next; the player locks in after the last tuck, and can unlock to take back the tucks
 * that only gave resources and tuck other cards. What each player tucks is shown to the others when all have locked in. */
export function SetupTucks({
  hand,
  tucked,
  need,
  picked,
  drawing,
  onPick,
  onTuck,
  onUntuck,
  onLock,
  clock,
  status,
}: {
  /** The cards of the hand that can be tucked now. */
  hand: string[];
  /** The cards tucked so far, and whether each can be taken back. */
  tucked: { card: string; undoable: boolean }[];
  /** How many cards the player tucks in all. */
  need: number;
  picked: string | null;
  /** The picked card gives a card: the tuck draws one and cannot be taken back. */
  drawing: boolean;
  onPick: (id: string) => void;
  onTuck: () => void;
  onUntuck: (card: string) => void;
  /** Present when every tuck is made. */
  onLock?: () => void;
  clock: string | null;
  status: string;
}) {
  const [aside, setAside] = useState(false);
  if (aside) {
    return (
      // biome-ignore lint/a11y/useSemanticElements: a bar, not a section of the page
      <div className="setupaside" role="region" aria-label="The choice is put aside">
        <span>
          Tucking cards for income{clock ? ` · ${clock}` : ""} · {status}
        </span>
        <button type="button" className="primary" onClick={() => setAside(false)}>
          Back to the tucks
        </button>
      </div>
    );
  }
  return (
    <div
      className="setupchoice"
      // biome-ignore lint/a11y/useSemanticElements: a layer over the board that the page controls itself, not a native <dialog>
      role="dialog"
      aria-modal="true"
      aria-label="Tuck cards for income"
    >
      <div className="setupinner">
        <h2>
          Tuck {need === 1 ? "a card" : `${need} cards`} for income ({tucked.length} of {need} done)
        </h2>
        <p className="muted">
          You tuck one card at a time and its income comes at once, so a card that gives a card lets you tuck the new card next. Everybody
          tucks on their own and at the same time; nobody sees the others' cards until all of you have locked in.{" "}
          {clock ? <b>Your clock: {clock}. </b> : null}
          {status}
        </p>
        {tucked.length > 0 ? (
          <>
            <h3>Tucked</h3>
            <div className="setupcards tucks">
              {tucked.map((t, k) => (
                <div key={`${t.card}-${k}`} className="setupcard">
                  <img src={cardImage(t.card)} alt={`Tucked card ${t.card}`} />
                  {t.undoable ? (
                    <button type="button" className="secondary small" onClick={() => onUntuck(t.card)}>
                      Take back
                    </button>
                  ) : (
                    <span className="muted small">drew a card: final</span>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : null}
        {hand.length > 0 ? (
          <>
            <h3>Your hand</h3>
            <div className="setupcards tucks">
              {hand.map((id) => (
                <button
                  key={id}
                  type="button"
                  className={picked === id ? "setupcard chosen" : "setupcard"}
                  aria-pressed={picked === id}
                  onClick={() => onPick(id)}
                >
                  <img src={cardImage(id)} alt={`Card ${id}`} />
                </button>
              ))}
            </div>
          </>
        ) : null}
        <div className="setupbar">
          <button type="button" className="secondary big" onClick={() => setAside(true)} title="Hide the choice to look at the board">
            View the board
          </button>
          {hand.length > 0 ? (
            <button type="button" className="primary big" disabled={picked === null} onClick={onTuck}>
              {picked === null ? "Pick a card to tuck" : drawing ? "Tuck it (it draws a card: final)" : "Tuck it"}
            </button>
          ) : null}
          {onLock ? (
            <button type="button" className="primary big" onClick={onLock}>
              Lock in my tucks
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** The setup of a game in which everybody chooses at the same time (EXP-ORG-14): the organizations and the quick start cards on one screen, a choice that
 * can be changed until the player locks it in, and who has locked in already. Nothing that anybody chose is shown to the others before all have locked in. */
export function SetupBoth({
  orgs,
  quick,
  pickedOrg,
  pickedQuick,
  need,
  onPickOrg,
  onPickQuick,
  onLock,
  clock,
  status,
}: {
  orgs: string[];
  quick: string[];
  pickedOrg: string | null;
  pickedQuick: string[];
  /** How many quick start cards are kept. */
  need: number;
  onPickOrg: (id: string) => void;
  onPickQuick: (id: string) => void;
  onLock: () => void;
  /** The time left of the player's clock, when the game has one. */
  clock: string | null;
  /** Who has locked in and who is still choosing. */
  status: string;
}) {
  const [aside, setAside] = useState(false);
  const ready = pickedOrg !== null && pickedQuick.length === need;
  if (aside) {
    return (
      // biome-ignore lint/a11y/useSemanticElements: a bar, not a section of the page
      <div className="setupaside" role="region" aria-label="The choice is put aside">
        <span>
          Choosing your organization and quick start cards{clock ? ` · ${clock}` : ""} · {status}
        </span>
        <button type="button" className="primary" onClick={() => setAside(false)}>
          Back to the choice
        </button>
      </div>
    );
  }
  return (
    <div
      className="setupchoice"
      // biome-ignore lint/a11y/useSemanticElements: a layer over the board that the page controls itself, not a native <dialog>
      role="dialog"
      aria-modal="true"
      aria-label="Choose your organization and your quick start cards"
    >
      <div className="setupinner">
        <h2>Choose your organization and your quick start cards</h2>
        <p className="muted">
          Everybody chooses at the same time, and nobody sees what the others chose until all of you have locked in. You can change your
          mind until you lock in. {clock ? <b>Your clock: {clock}. </b> : null}
          {status}
        </p>
        <h3>1. Your organization</h3>
        <div className="setupcards orgs">
          {orgs.map((id) => {
            const info = ORGS[id];
            return (
              <button
                key={id}
                type="button"
                className={pickedOrg === id ? "setupcard chosen" : "setupcard"}
                aria-pressed={pickedOrg === id}
                onClick={() => onPickOrg(id)}
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
        <h3>
          2. Your quick start cards ({pickedQuick.length} of {need} picked)
        </h3>
        <div className="setupcards quick">
          {quick.map((id) => (
            <button
              key={id}
              type="button"
              className={pickedQuick.includes(id) ? "setupcard chosen" : "setupcard"}
              aria-pressed={pickedQuick.includes(id)}
              onClick={() => onPickQuick(id)}
            >
              <img src={cardImage(id)} alt={`Quick start card ${id}`} />
            </button>
          ))}
        </div>
        <div className="setupbar">
          <button type="button" className="secondary big" onClick={() => setAside(true)} title="Hide the choice to look at the board">
            View the board
          </button>
          <button type="button" className="primary big" disabled={!ready} onClick={onLock}>
            Lock in my choices
          </button>
        </div>
      </div>
    </div>
  );
}
