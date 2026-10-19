"use client";
// The fields of the "New game" form, in four steps: who plays (players and, for a solo game, the difficulty), the clock, the options, and the Space
// Agencies expansion. Choices with a few answers are segmented buttons, yes-or-no choices are switches. The solo difficulty only exists for a game of one
// player, and rated games need 2 to 4 players, so those two fields follow the choice of the number of players. The names of the fields are those that the
// server action reads (`createGameAction`): players, difficulty, mode, clock, sandbox, species1, species2, rated, promo, promo2, expansion,
// organizations, beginner, neutral.
import { type ReactNode, useState } from "react";

interface Choice {
  value: string;
  label: string;
  sub?: string;
  disabled?: boolean;
}

/** Radio buttons that look like one segmented control. */
function Segmented({
  name,
  value,
  choices,
  onChange,
  label,
  columns,
}: { name: string; value: string; choices: Choice[]; onChange: (v: string) => void; label: string; columns?: 2 }) {
  return (
    <div className={columns === 2 ? "seg cols2" : "seg"} role="radiogroup" aria-label={label}>
      {choices.map((c) => (
        <label key={c.value} className={`segopt${value === c.value ? " on" : ""}${c.disabled ? " off" : ""}`}>
          <input
            type="radio"
            name={name}
            value={c.value}
            checked={value === c.value}
            disabled={c.disabled}
            onChange={() => onChange(c.value)}
          />
          <span className="segmain">{c.label}</span>
          {c.sub ? <small>{c.sub}</small> : null}
        </label>
      ))}
    </div>
  );
}

/** A yes-or-no choice: its name and what it means on the left, the switch on the right. */
function Option({
  name,
  title,
  hint,
  checked,
  onChange,
  disabled,
}: { name: string; title: string; hint?: ReactNode; checked?: boolean; onChange?: (on: boolean) => void; disabled?: boolean }) {
  const controlled = checked !== undefined;
  return (
    <label className={`optrow${disabled ? " off" : ""}`}>
      <span className="opttext">
        <b>{title}</b>
        {hint ? <small>{hint}</small> : null}
      </span>
      <input
        type="checkbox"
        className="switch"
        name={name}
        disabled={disabled}
        {...(controlled
          ? {
              role: "switch",
              "aria-checked": checked,
              checked,
              onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange?.(e.target.checked),
            }
          : {})}
      />
    </label>
  );
}

export function NewGameFields({
  clocks,
  isGuest,
}: {
  clocks: { key: string; label: string; mode: "realtime" | "turnbased" | "both" }[];
  isGuest: boolean;
}) {
  const [players, setPlayers] = useState("2");
  const [difficulty, setDifficulty] = useState("3");
  // real-time or turn-based play (D34): each has three speeds and the choice of no time control
  const [mode, setMode] = useState<"realtime" | "turnbased">("realtime");
  const [clock, setClock] = useState("none");
  const n = Number(players);
  const solo = n === 1;
  // the sandbox can choose its two face-down alien species (SANDBOX-06)
  const [sandbox, setSandbox] = useState(false);
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  // the Space Agencies expansion (D35): the organization module also works in the solo game; the neutral pieces are for 1 to 2 players
  const [expansion, setExpansion] = useState(false);
  const [organizations, setOrganizations] = useState(true); // the intended way to play the expansion: organizations, 4 rounds
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
  const speeds = clocks.filter((c) => c.mode === "both" || c.mode === mode);
  const speedChoices: Choice[] = speeds.map((c) => {
    // "Fast: 5 min, +1 min 30 s per turn" is shown as a name and the times under it
    const [name, rest] = c.label.includes(": ") ? c.label.split(": ") : [c.label, ""];
    return { value: c.key, label: name ?? c.label, sub: rest || undefined };
  });
  const chosen = speeds.find((c) => c.key === clock) ?? speeds[0];
  const summary = `${solo ? "Solo against the rival" : `${n} players`} · ${mode === "realtime" ? "real time" : "turn-based"} · ${
    chosen?.key === "none" || !chosen ? "no clock" : (chosen.label.split(": ")[0] ?? "").toLowerCase()
  }${expansion ? " · Space Agencies" : ""}`;
  return (
    <>
      <section className="formsec" aria-labelledby="ng-players">
        <h3 id="ng-players">
          <span className="stepno">1</span> Who plays
        </h3>
        <Segmented
          name="players"
          label="Number of players"
          value={players}
          onChange={setPlayers}
          choices={[
            { value: "1", label: "Solo", sub: "against the rival" },
            { value: "2", label: "2" },
            { value: "3", label: "3" },
            { value: "4", label: "4" },
          ]}
        />
        {solo ? (
          <>
            <p className="formlabel">Rival difficulty (gold stars)</p>
            <Segmented
              name="difficulty"
              label="Solo difficulty"
              value={difficulty}
              onChange={setDifficulty}
              choices={[1, 2, 3, 4, 5].map((d) => ({ value: String(d), label: String(d) }))}
            />
          </>
        ) : null}
      </section>

      <section className="formsec" aria-labelledby="ng-time">
        <h3 id="ng-time">
          <span className="stepno">2</span> Time
        </h3>
        <Segmented
          name="mode"
          label="Real time or turn-based"
          value={mode}
          onChange={(v) => {
            setMode(v as "realtime" | "turnbased");
            setClock("none");
          }}
          choices={[
            { value: "realtime", label: "Real time", sub: "minutes" },
            { value: "turnbased", label: "Turn-based", sub: "days" },
          ]}
        />
        <Segmented
          name="clock"
          label="Time control"
          value={chosen?.key ?? "none"}
          onChange={setClock}
          choices={speedChoices}
          columns={speedChoices.length > 3 ? 2 : undefined}
        />
      </section>

      <section className="formsec" aria-labelledby="ng-options">
        <h3 id="ng-options">
          <span className="stepno">3</span> Options
        </h3>
        {solo ? (
          <>
            <Option
              name="sandbox"
              title="Sandbox"
              hint="Practice: no rival; add any card or resource and turn the discs."
              checked={sandbox}
              onChange={setSandbox}
            />
            {sandbox ? (
              <div className="optsub">
                {speciesSelect("species1", "Face-down alien species, left", first, setFirst, second)}
                {speciesSelect("species2", "Face-down alien species, right", second, setSecond, first)}
              </div>
            ) : null}
          </>
        ) : (
          <Option
            name="rated"
            title="Rated"
            hint={isGuest ? "Needs an account: create one first." : "Counts for the rating. 2 to 4 players, accounts only."}
            disabled={isGuest}
          />
        )}
        <Option name="promo" title="Promo cards, set 1" hint="Adds the two promo cards to the deck." />
        <Option name="promo2" title="Promo cards, set 2" hint="Adds Space Agencies and DLR to the deck." />
      </section>

      <section className="formsec expansion" aria-labelledby="ng-exp">
        <h3 id="ng-exp">
          <span className="stepno">4</span> Space Agencies expansion
        </h3>
        <Option
          name="expansion"
          title="Play with the expansion"
          hint="42 new cards, signal tokens and three new alien species: Arkhos, Glyphids and Amoeba."
          checked={expansion}
          onChange={(on) => {
            setExpansion(on);
            if (!on) {
              // the species of the expansion can no longer be chosen
              const base = (v: string) => (["arkhos", "glyphids", "amoeba"].includes(v) ? "" : v);
              setFirst(base(first));
              setSecond(base(second));
            }
          }}
        />
        {expansion ? (
          <div className="optsub">
            <Option
              name="organizations"
              title="Organizations and quick start cards"
              hint="The intended way to play it: 4 rounds. Switch off to play the base game's setup with the new cards and species."
              checked={organizations}
              onChange={setOrganizations}
            />
            {organizations ? (
              <>
                <Option name="beginner" title="First game" hint="Organizations 1 to 4 and two quick start cards." />
                {n <= 2 ? <Option name="neutral" title="Neutral quick start pieces" hint="For 1 to 2 players." /> : null}
              </>
            ) : null}
          </div>
        ) : null}
      </section>

      <p className="formsummary" aria-live="polite">
        {summary}
      </p>
    </>
  );
}
