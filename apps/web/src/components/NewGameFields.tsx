"use client";
// The fields of the "New game" form. The solo difficulty only exists for a game of one player, and rated games need 2 to 4 players,
// so those two fields follow the choice of the number of players.
import { useState } from "react";

export function NewGameFields({
  clocks,
  isGuest,
}: {
  clocks: { key: string; label: string; mode: "realtime" | "turnbased" | "both" }[];
  isGuest: boolean;
}) {
  const [players, setPlayers] = useState(2);
  // real-time or turn-based play (D34): each has three speeds and the choice of no time control
  const [mode, setMode] = useState<"realtime" | "turnbased">("realtime");
  const solo = players === 1;
  // the sandbox can choose its two face-down alien species (SANDBOX-06)
  const [sandbox, setSandbox] = useState(false);
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  // the Space Agencies expansion (D35): the organization module also works in the solo game; the neutral pieces are for 1 to 2 players
  const [expansion, setExpansion] = useState(false);
  const [organizations, setOrganizations] = useState(true); // the intended way to play the expansion: organizations, 4 rounds
  const orgsAllowed = true; // EXP-SOLO-01: the solo game against the rival can use them too
  const orgsOn = expansion && organizations && orgsAllowed;
  const SPECIES = [
    "anomalies",
    "centaurians",
    "exertians",
    "mascamites",
    "oumuamua",
    ...(expansion ? ["arkhos", "glyphids", "amoeba"] : []), // the species of the expansion, when it is in the game (SANDBOX-06)
  ];
  const speciesSelect = (name: string, label: string, value: string, onChange: (v: string) => void, taken: string) => (
    <label>
      {label}
      <select name={name} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Random</option>
        {SPECIES.filter((sp) => sp !== taken).map((sp) => (
          <option key={sp} value={sp}>
            {sp.charAt(0).toUpperCase() + sp.slice(1)}
          </option>
        ))}
      </select>
    </label>
  );
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
      <fieldset className="modeswitch">
        <legend>Table</legend>
        <label className="row">
          <input type="radio" name="mode" value="realtime" checked={mode === "realtime"} onChange={() => setMode("realtime")} /> Real time
        </label>
        <label className="row">
          <input type="radio" name="mode" value="turnbased" checked={mode === "turnbased"} onChange={() => setMode("turnbased")} /> Turn
          based (days per game)
        </label>
      </fieldset>
      <label>
        Time control
        <select name="clock" key={mode} defaultValue="none">
          {clocks
            .filter((c) => c.mode === "both" || c.mode === mode)
            .map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
        </select>
      </label>
      {solo ? (
        <label className="row">
          <input type="checkbox" name="sandbox" checked={sandbox} onChange={(e) => setSandbox(e.target.checked)} /> Sandbox (practice: no
          rival, add any card, resources and turn the discs)
        </label>
      ) : null}
      {solo && sandbox ? (
        <>
          {speciesSelect("species1", "Face-down alien species, left", first, setFirst, second)}
          {speciesSelect("species2", "Face-down alien species, right", second, setSecond, first)}
        </>
      ) : null}
      {solo ? null : (
        <label className="row">
          <input type="checkbox" name="rated" disabled={isGuest} /> Rated (2 to 4 players, accounts only)
        </label>
      )}
      <label className="row">
        <input type="checkbox" name="promo" /> Include the two promo cards (set 1)
      </label>
      <label className="row">
        <input type="checkbox" name="promo2" /> Include the promo cards of set 2 (Space Agencies, DLR)
      </label>
      <fieldset className="expansion">
        <legend>Space Agencies expansion</legend>
        <label className="row">
          <input
            type="checkbox"
            name="expansion"
            checked={expansion}
            onChange={(e) => {
              setExpansion(e.target.checked);
              if (!e.target.checked) {
                // the species of the expansion can no longer be chosen
                const base = (v: string) => (["arkhos", "glyphids", "amoeba"].includes(v) ? "" : v);
                setFirst(base(first));
                setSecond(base(second));
              }
            }}
          />{" "}
          Include the Space Agencies expansion
        </label>
        {expansion ? (
          <>
            <label className="row">
              <input
                type="checkbox"
                name="organizations"
                checked={organizations && orgsAllowed}
                disabled={!orgsAllowed}
                onChange={(e) => setOrganizations(e.target.checked)}
              />{" "}
              Organizations and quick start cards (4 rounds)
            </label>
            {orgsOn ? (
              <>
                <label className="row">
                  <input type="checkbox" name="beginner" /> First game: organizations 1 to 4 and two quick start cards
                </label>
                {players <= 2 ? (
                  <label className="row">
                    <input type="checkbox" name="neutral" /> Neutral quick start pieces (1 to 2 players)
                  </label>
                ) : null}
              </>
            ) : null}
            <p className="small muted">
              Adds the 42 new cards, signal tokens, the three new alien species (Arkhos, Glyphids, Amoeba) and the organization module.
              Organizations and 4 rounds are the intended way to play it; untick them to play the base game's setup with the expansion's
              cards and species.
            </p>
          </>
        ) : null}
      </fieldset>
    </>
  );
}
