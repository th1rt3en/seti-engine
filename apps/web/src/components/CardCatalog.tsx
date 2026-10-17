"use client";
// The list of all the cards with filters. The cards come from generated/card-catalog.json (tools/web/sync_data.py), which is made from the
// engine's own card data: the page works out nothing about the rules, it only filters what the engine's data says.
import { useMemo, useState } from "react";
import catalog from "../generated/card-catalog.json";
import { CardImage } from "./CardImage";

interface Entry {
  id: string;
  name: string;
  deck: string;
  species: string | null;
  income: string | null;
  sector: string | null;
  cost: number;
  free: string[];
  type: string;
  tags: string[];
  known: boolean;
}
const CARDS = catalog as Entry[];

const ANY = "";
const SPECIES_NAMES: Record<string, string> = {
  anomalies: "Anomalies",
  centaurians: "Centaurians",
  exertians: "Exertians",
  mascamites: "Mascamites",
  oumuamua: "'Oumuamua",
  amoeba: "Amoeba",
  arkhos: "Arkhos",
  glyphids: "Glyphids",
};
const FREE_NAMES: Record<string, string> = {
  publicity: "Publicity",
  move: "Movement",
  data: "Data",
  score: "Score",
  explore_minor: "Explore",
  glyph: "Glyph",
};
const INCOME_NAMES: Record<string, string> = { energy: "Energy", credit: "Credit", card: "Card", data: "Data", publicity: "Publicity" };
const SECTOR_NAMES: Record<string, string> = { blue: "Blue", red: "Red", yellow: "Yellow", black: "Black" };
const TYPE_NAMES: Record<string, string> = {
  quick: "Quick mission",
  mission: "Full mission",
  end: "End-of-game scoring",
  none: "None",
};
const EFFECTS: [string, string][] = [
  ["launch", "Launch"],
  ["land", "Land"],
  ["scan", "Scan"],
  ["trace", "Mark a trace"],
  ["tech", "Any tech"],
  ["tech_orange", "Orange tech"],
  ["tech_pink", "Pink tech"],
  ["tech_blue", "Blue tech"],
  ["move", "Move"],
  ["signal", "Mark a signal"],
];

const unique = (list: (string | null | undefined)[]): string[] => [...new Set(list.filter((x): x is string => typeof x === "string"))];

function Select({
  label,
  value,
  onChange,
  options,
}: { label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <label className="catfilter">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value={ANY}>Any</option>
        {options.map(([v, text]) => (
          <option key={v} value={v}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

export function CardCatalog() {
  const [name, setName] = useState("");
  const [species, setSpecies] = useState(ANY);
  const [free, setFree] = useState(ANY);
  const [income, setIncome] = useState(ANY);
  const [sector, setSector] = useState(ANY);
  const [type, setType] = useState(ANY);
  const [effects, setEffects] = useState<string[]>([]);

  const options = useMemo(() => {
    const pick = (names: Record<string, string>, values: string[]): [string, string][] =>
      Object.keys(names)
        .filter((k) => values.includes(k))
        .map((k) => [k, names[k] ?? k]);
    return {
      species: [["none", "None (main deck)"], ...pick(SPECIES_NAMES, unique(CARDS.map((c) => c.species)))] as [string, string][],
      free: pick(FREE_NAMES, unique(CARDS.flatMap((c) => c.free))),
      income: pick(INCOME_NAMES, unique(CARDS.map((c) => c.income))),
      sector: pick(SECTOR_NAMES, unique(CARDS.map((c) => c.sector))),
    };
  }, []);

  const words = name.toLowerCase().split(/\s+/).filter(Boolean);
  const shown = CARDS.filter(
    (c) =>
      words.every((w) => `${c.id} ${c.name}`.toLowerCase().includes(w)) &&
      (species === ANY || (species === "none" ? c.species === null : c.species === species)) &&
      (free === ANY || c.free.includes(free)) &&
      (income === ANY || c.income === income) &&
      (sector === ANY || c.sector === sector) &&
      (type === ANY || c.type === type) &&
      effects.every((e) => c.tags.includes(e)),
  );
  const toggle = (e: string) => setEffects((old) => (old.includes(e) ? old.filter((x) => x !== e) : [...old, e]));
  const clear = () => {
    setName("");
    setSpecies(ANY);
    setFree(ANY);
    setIncome(ANY);
    setSector(ANY);
    setType(ANY);
    setEffects([]);
  };
  const unknown = CARDS.filter((c) => !c.known).length;

  return (
    <div className="catalog">
      <div className="catfilters">
        <label className="catfilter catname">
          <span>Name or number</span>
          <input type="search" value={name} onChange={(e) => setName(e.target.value)} placeholder="for example rover or ET.31" />
        </label>
        <Select label="Alien species" value={species} onChange={setSpecies} options={options.species} />
        <Select label="Free corner action" value={free} onChange={setFree} options={options.free} />
        <Select label="Income" value={income} onChange={setIncome} options={options.income} />
        <Select label="Sector" value={sector} onChange={setSector} options={options.sector} />
        <Select label="Card type" value={type} onChange={setType} options={Object.entries(TYPE_NAMES)} />
      </div>
      <details className="catadvanced">
        <summary>Advanced filters: what the card effect does</summary>
        <div className="cateffects">
          {EFFECTS.map(([key, label]) => (
            <label key={key}>
              <input type="checkbox" checked={effects.includes(key)} onChange={() => toggle(key)} /> {label}
            </label>
          ))}
        </div>
        <p className="muted small">
          A card must do everything that is ticked. Only the effect of the card when played counts, not its mission or end-of-game scoring.
          {unknown > 0 ? ` The effect of ${unknown} alien cards is not entered yet, so they never match here.` : ""}
        </p>
      </details>
      <p className="catcount">
        <b>{shown.length}</b> of {CARDS.length} cards{" "}
        <button type="button" className="secondary small" onClick={clear}>
          Clear the filters
        </button>
      </p>
      <ul className="catgrid">
        {shown.map((c) => (
          <li key={c.id}>
            <CardImage id={c.id} width={170} title={c.name} />
            <span className="catname-text">
              <b>{c.name}</b> <span className="muted small">{c.id}</span>
            </span>
          </li>
        ))}
      </ul>
      {shown.length === 0 ? <p>No card matches these filters.</p> : null}
    </div>
  );
}
