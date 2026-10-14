"use client";
// The fields of the "New game" form. The solo difficulty only exists for a game of one player, and rated games need 2 to 4 players,
// so those two fields follow the choice of the number of players.
import { useState } from "react";

export function NewGameFields({
  clocks,
  isGuest,
}: {
  clocks: { key: string; label: string }[];
  isGuest: boolean;
}) {
  const [players, setPlayers] = useState(2);
  const solo = players === 1;
  return (
    <>
      <label>
        Players (1 is the solo game against the rival)
        <select name="players" value={players} onChange={(e) => setPlayers(Number(e.target.value))}>
          <option value="1">1 (solo)</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
        </select>
      </label>
      {solo ? (
        <label>
          Solo difficulty (gold stars)
          <select name="difficulty" defaultValue="3">
            {[1, 2, 3, 4, 5].map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <label>
        Clock
        <select name="clock" defaultValue="none">
          {clocks.map((c) => (
            <option key={c.key} value={c.key}>
              {c.label}
            </option>
          ))}
        </select>
      </label>
      {solo ? (
        <label className="row">
          <input type="checkbox" name="sandbox" /> Sandbox (practice: no rival, add any card, resources and turn the discs)
        </label>
      ) : null}
      {solo ? null : (
        <label className="row">
          <input type="checkbox" name="rated" disabled={isGuest} /> Rated (2 to 4 players, accounts only)
        </label>
      )}
      <label className="row">
        <input type="checkbox" name="promo" /> Include the two promo cards
      </label>
    </>
  );
}
