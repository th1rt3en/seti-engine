"use client";
// The sandbox of a practice game (D33): search any card and put it in the hand, add resources, turn the discs. The engine says what is possible
// (the `sandbox` entry of the legal moves) and checks every action; nothing here is a rule.
import { cardName } from "@/lib/moves";
import { useState } from "react";

type Marker = { type: "sandbox"; resources: string[]; discs: number[]; cards: string[] };
type Send = (action: Record<string, unknown>) => void;

const RESOURCE_LABELS: Record<string, string> = {
  credit: "Credits",
  energy: "Energy",
  data: "Data",
  publicity: "Publicity",
  exofossil: "Exofossils",
};
const MAX_SHOWN = 24;
const MIN_CHARS = 2; // no card is listed before the search has this many characters
const MAX_AMOUNT = 50;

/** A curved arrow turning counter-clockwise (`dir` -1) or clockwise (1), for the buttons that turn a disc. */
function TurnIcon({ dir }: { dir: 1 | -1 }) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={dir === -1 ? { transform: "scaleX(-1)" } : undefined}
    >
      <path d="M20 12a8 8 0 1 1-2.6-5.9" />
      <path d="M20 3.5v4.6h-4.6" />
    </svg>
  );
}

export function SandboxPanel({ marker, send, handCards }: { marker: Marker; send: Send; handCards: string[] }) {
  const [query, setQuery] = useState("");
  const [resource, setResource] = useState(marker.resources[0] ?? "credit");
  const [amount, setAmount] = useState(1);
  const typed = query.trim();
  const words = typed.toLowerCase().split(/\s+/).filter(Boolean);
  const matches =
    typed.length < MIN_CHARS
      ? []
      : marker.cards.filter((id) => {
          const text = `${id} ${cardName(id)}`.toLowerCase();
          return words.every((w) => text.includes(w));
        });
  // the amount goes from -50 to 50 and is never 0: a negative amount takes resources away
  const step = (by: number) =>
    setAmount((old) => {
      const next = old + by;
      return next === 0 ? (by > 0 ? 1 : -1) : Math.min(MAX_AMOUNT, Math.max(-MAX_AMOUNT, next));
    });
  return (
    <details className="sandbox">
      <summary>Sandbox (practice game: nothing here counts as a rule)</summary>
      <div className="sandboxbody">
        <section aria-label="Add a card to your hand">
          <h4>Add a card to your hand</h4>
          <input
            type="search"
            placeholder="Type at least 2 characters: a name or a number, for example “rover” or “ET.31”"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search cards"
          />
          {typed.length >= MIN_CHARS ? (
            <>
              <ul className="sandboxcards">
                {matches.slice(0, MAX_SHOWN).map((id) => (
                  <li key={id}>
                    <button type="button" onClick={() => send({ type: "sandbox_add_card", card: id })}>
                      + {cardName(id)}
                      {handCards.includes(id) ? " (in hand)" : ""}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="muted small">
                {matches.length > MAX_SHOWN
                  ? `${matches.length} cards match: type more to narrow them down.`
                  : `${matches.length} cards match.`}{" "}
                Alien cards appear when their species is face up.
              </p>
            </>
          ) : null}
        </section>
        <section aria-label="Resources">
          <h4>Resources</h4>
          <div className="sandboxform">
            <select value={resource} onChange={(e) => setResource(e.target.value)} aria-label="Resource">
              {marker.resources.map((r) => (
                <option key={r} value={r}>
                  {RESOURCE_LABELS[r] ?? r}
                </option>
              ))}
            </select>
            <button type="button" className="secondary" aria-label="One less" onClick={() => step(-1)}>
              −
            </button>
            <output className="sandboxamount" aria-label="Amount">
              {amount > 0 ? `+${amount}` : amount}
            </output>
            <button type="button" className="secondary" aria-label="One more" onClick={() => step(1)}>
              +
            </button>
            <button type="button" className="primary" onClick={() => send({ type: "sandbox_resource", resource, n: amount })}>
              Confirm
            </button>
          </div>
        </section>
        <section aria-label="Rotate a disc">
          <h4>Rotate a disc (one step, no rewards)</h4>
          <div className="moves">
            {marker.discs.map((d) => (
              <span key={d} className="sandboxres">
                <button
                  type="button"
                  title={`Turn disc ${d} counter-clockwise`}
                  onClick={() => send({ type: "sandbox_rotate", disc: d, step: -1 })}
                >
                  <TurnIcon dir={-1} /> Disc {d}
                </button>
                <button type="button" title={`Turn disc ${d} clockwise`} onClick={() => send({ type: "sandbox_rotate", disc: d, step: 1 })}>
                  Disc {d} <TurnIcon dir={1} />
                </button>
              </span>
            ))}
          </div>
        </section>
      </div>
    </details>
  );
}
