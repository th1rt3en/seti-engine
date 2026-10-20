// The rows of the statistics of one game, as the game over panel shows them: a label and a value worked out from the counters of one player
// (the engine's stats.py). It only reads the counters; it adds no rule.
import { TECH_INFO } from "./techs";

export type Counters = Record<string, number>;
export interface StatLine {
  label: string;
  value: (c: Counters) => string;
}
export interface StatGroup {
  title: string;
  lines: StatLine[];
}

const n = (c: Counters, k: string): number => c[k] ?? 0;
const num =
  (k: string) =>
  (c: Counters): string =>
    String(n(c, k));
const cap = (w: string): string => w.charAt(0).toUpperCase() + w.slice(1);
const keysOf = (counters: Counters[]): string[] => [...new Set(counters.flatMap((c) => Object.keys(c)))];

export function statGroups(counters: Counters[]): StatGroup[] {
  const keys = keysOf(counters);
  const rounds = [...new Set(keys.filter((k) => k.startsWith("incomerate.r")).map((k) => Number(k.split(".")[1]?.slice(1))))].sort(
    (a, b) => a - b,
  );
  const gold = keys
    .filter((k) => k.startsWith("gold.") && k.endsWith(".times"))
    .map((k) => k.slice(5, -6))
    .sort();
  const techs = keys.filter((k) => k.startsWith("tech.")).sort();
  const planets = (c: Counters): number =>
    Object.keys(c)
      .filter((k) => k.startsWith("publicity.visit.") && !["comet", "asteroid", "asteroids"].includes(k.slice(16)))
      .reduce((a, k) => a + n(c, k), 0);
  const groups: StatGroup[] = [
    {
      title: "Actions",
      lines: [
        ["Launch", "launch"],
        ["Scan", "scan"],
        ["Analyze", "analyze"],
        ["Research", "research"],
        ["Orbit", "orbit"],
        ["Land", "land"],
        ["Play a card", "play_card"],
        ["Pass", "pass"],
      ].map(([label, k]) => ({ label: label as string, value: num(`action.${k}`) })),
    },
    {
      title: "Probes, planets and cards",
      lines: [
        { label: "Probes launched", value: num("probes.launched") },
        { label: "Orbiters", value: num("orbiters") },
        { label: "Landers", value: num("landers") },
        { label: "Cards drawn", value: num("cards.drawn") },
        { label: "Cards played", value: num("cards.played") },
        { label: "Missions played", value: num("missions.played") },
        { label: "Missions completed", value: num("missions.completed") },
        { label: "End-of-game cards played", value: num("endcards.played") },
        { label: "Points from them", value: num("endcards.points") },
      ],
    },
    { title: "Life traces", lines: ["pink", "yellow", "blue"].map((k) => ({ label: cap(k), value: num(`trace.${k}`) })) },
    {
      title: "Cards tucked for income",
      lines: ["credit", "energy", "card", "publicity", "data"].map((k) => ({ label: cap(k), value: num(`tucked.${k}`) })),
    },
    {
      title: "Income at the end of each round (credit / energy / card)",
      lines: rounds.map((r) => ({
        label: `Round ${r}`,
        value: (c: Counters) =>
          `${n(c, `incomerate.r${r}.credit`)} / ${n(c, `incomerate.r${r}.energy`)} / ${n(c, `incomerate.r${r}.card`)}`,
      })),
    },
    {
      title: "Publicity gained",
      lines: [
        { label: "From comets", value: num("publicity.visit.comet") },
        { label: "From asteroids", value: (c) => String(n(c, "publicity.visit.asteroid") + n(c, "publicity.visit.asteroids")) },
        { label: "From planets", value: (c) => String(planets(c)) },
        { label: "From completing a sector", value: num("publicity.sector") },
      ],
    },
    {
      title: "Data",
      lines: [
        { label: "Gained", value: num("data.gained") },
        { label: "Placed in the computer", value: num("data.computer") },
        { label: "Used in other ways", value: (c) => String(Math.max(0, n(c, "data.lost") - n(c, "data.computer"))) },
      ],
    },
    {
      title: "Sectors won and signals marked",
      lines: ["red", "yellow", "blue", "black"].flatMap((k) => [
        { label: `${cap(k)} sectors won`, value: num(`sectorwin.${k}`) },
        { label: `${cap(k)} signals`, value: num(`signal.${k}`) },
      ]),
    },
    {
      title: "Tech researched",
      lines: [
        ...["probe", "telescope", "computer"].map((k) => ({ label: cap(k), value: num(`techcat.${k}`) })),
        ...techs.map((k) => ({ label: TECH_INFO[k.slice(5)]?.name ?? k.slice(5), value: num(k) })),
      ],
    },
    { title: "Gold scoring tiles (points)", lines: gold.map((g) => ({ label: g, value: num(`gold.${g}.points`) })) },
  ];
  return groups.filter((g) => g.lines.length > 0);
}
