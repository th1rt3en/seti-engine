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

export function SandboxPanel({ marker, send, handCards }: { marker: Marker; send: Send; handCards: string[] }) {
  const [query, setQuery] = useState("");
  const [amount, setAmount] = useState(1);
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const matches = marker.cards.filter((id) => {
    const text = `${id} ${cardName(id)}`.toLowerCase();
    return words.every((w) => text.includes(w));
  });
  return (
    <details className="sandbox">
      <summary>Sandbox (practice game: nothing here counts as a rule)</summary>
      <div className="sandboxbody">
        <section aria-label="Add a card to your hand">
          <h4>Add a card to your hand</h4>
          <input
            type="search"
            placeholder="Search by name or number, for example “rover” or “ET.31”"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search cards"
          />
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
              ? `${matches.length} cards match: type more to narrow them down. `
              : `${matches.length} cards match. `}
            Alien cards appear when their species is face up.
          </p>
        </section>
        <section aria-label="Resources">
          <h4>Resources</h4>
          <label className="row">
            Amount{" "}
            <input
              type="number"
              min={1}
              max={50}
              value={amount}
              onChange={(e) => setAmount(Math.min(50, Math.max(1, Number(e.target.value) || 1)))}
            />
          </label>
          <div className="moves">
            {marker.resources.map((r) => (
              <span key={r} className="sandboxres">
                <button type="button" onClick={() => send({ type: "sandbox_resource", resource: r, n: amount })}>
                  + {amount} {RESOURCE_LABELS[r] ?? r}
                </button>
                <button
                  type="button"
                  aria-label={`Remove ${amount} ${RESOURCE_LABELS[r] ?? r}`}
                  onClick={() => send({ type: "sandbox_resource", resource: r, n: -amount })}
                >
                  −
                </button>
              </span>
            ))}
          </div>
        </section>
        <section aria-label="Rotate a disc">
          <h4>Rotate a disc (one step, no rewards)</h4>
          <div className="moves">
            {marker.discs.map((d) => (
              <span key={d} className="sandboxres">
                <button type="button" onClick={() => send({ type: "sandbox_rotate", disc: d, step: -1 })}>
                  ⟲ Disc {d}
                </button>
                <button type="button" onClick={() => send({ type: "sandbox_rotate", disc: d, step: 1 })}>
                  ⟳ Disc {d}
                </button>
              </span>
            ))}
          </div>
        </section>
      </div>
    </details>
  );
}
