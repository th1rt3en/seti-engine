// The statistics of the alien species: what each of them gave and did, averaged over the players of the games where it was discovered. The numbers
// are counters of the engine (stats.py: `alien.<species>.<part>.<resource>`, `mascamites.delivered` ...); nothing here is a rule.
import { RESOURCE_COLORS, RESOURCE_NAMES } from "@/lib/resources";
import type { AlienStats } from "@/lib/stats";
import type { ReactNode } from "react";
import { PieChart } from "./PieChart";
import { KindIcon, Rewards } from "./Reward";
import { BarList, Panel, Tile, WithSpread, round } from "./StatCharts";

/** What a gain on the Centaurian board is, hex by hex (docs data alien-boards.json, `message_rewards`). */
const CENTAURIAN_REWARDS: { t: string; n: number }[][] = [
  [{ t: "trace", n: 1 }],
  [
    { t: "alien_card", n: 1 },
    { t: "energy", n: 1 },
  ],
  [{ t: "publicity", n: 3 }],
  [{ t: "vp", n: 8 }],
];
const RESOURCES = ["vp", "credit", "energy", "card", "publicity", "data", "move"];
const COLORS = ["pink", "yellow", "blue"];
const COLOR_HEX: Record<string, string> = { pink: "#d55181", yellow: "#c98500", blue: "#3987e5" };
const cap = (w: string): string => w.charAt(0).toUpperCase() + w.slice(1);
const pct = (x: number): string => `${Math.round(x * 100)}%`;

/** The resources that a part of a species' rules gave, per player: one row for each part, one column for each resource. */
function ResourceTable({
  a,
  species,
  parts,
  label,
}: { a: AlienStats; species: string; parts: { key: string; label: string }[]; label: string }) {
  return (
    <details className="stat-table">
      <summary>By part of its rules, as a table</summary>
      <div className="tablewrap">
        <table className="res-table" aria-label={label}>
          <thead>
            <tr>
              <th scope="col">{label}</th>
              {RESOURCES.map((res) => (
                <th key={res} scope="col">
                  <KindIcon kind={res} size={20} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {parts.map((part) => (
              <tr key={part.key}>
                <th scope="row">{part.label}</th>
                {RESOURCES.map((res) => {
                  const k = `alien.${species}.${part.key}.${res}`;
                  const v = a.mean[k] ?? 0;
                  return (
                    <td key={res} className={v > 0 ? undefined : "muted"}>
                      <WithSpread spread={a.spread[k]}>{round(v)}</WithSpread>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

/** What the species gave, by resource: the slices have the color of the resource (the parts of its rules are added up for each player). */
function ResourcePie({ a, species }: { a: AlienStats; species: string }) {
  const slices = RESOURCES.map((res) => ({
    key: res,
    name: RESOURCE_NAMES[res] ?? res,
    label: (
      <span className="icon-label">
        <KindIcon kind={res} size={18} />
        {RESOURCE_NAMES[res] ?? res}
      </span>
    ),
    value: a.mean[`alien.${species}.all.${res}`] ?? 0,
    spread: a.spread[`alien.${species}.all.${res}`],
    color: RESOURCE_COLORS[res] ?? "#8b949e",
  })).filter((x) => x.value > 0);
  if (slices.length === 0) return null;
  return (
    <>
      <h3>Resources it gave, per player</h3>
      <PieChart slices={slices} label={`Resources gained through ${species}, by resource`} />
    </>
  );
}

function Species({
  title,
  species,
  icon,
  alien,
  children,
}: { title: string; species: string; icon?: string; alien: Record<string, AlienStats>; children: (a: AlienStats) => ReactNode }) {
  const a = alien[species];
  return (
    <Panel
      title={title}
      icon={icon ? <img src={icon} alt="" width={22} height={40} className="mini-board" /> : undefined}
      note={
        a && a.rows > 0
          ? `Per player, over the ${a.rows} player${a.rows === 1 ? "" : "s"} of the games where the species was discovered. Resources are the points, credits, energy, cards, publicity, data and movement that it gave; signals, traces and exofossils are not counted there.`
          : "No game where the species was discovered yet."
      }
      wide
    >
      {a && a.rows > 0 ? children(a) : null}
      {a && a.rows > 0 ? <ResourcePie a={a} species={species} /> : null}
    </Panel>
  );
}

const tile = (a: AlienStats, key: string, label: string, note?: string) => (
  <Tile key={key} label={label} note={note} value={round(a.mean[key] ?? 0)} spread={a.spread[key]} />
);

export function AlienStatsSection({ alien, boards }: { alien: Record<string, AlienStats>; boards: Record<string, string> }) {
  const m = (a: AlienStats, k: string): number => a.mean[k] ?? 0;
  const rate = (a: AlienStats, done: string, played: string): string => (m(a, played) > 0 ? pct(m(a, done) / m(a, played)) : "-");
  return (
    <>
      <Species title="Mascamites" species="mascamites" icon={boards.mascamites} alien={alien}>
        {(a) => (
          <>
            <div className="stat-tiles small">
              {tile(a, "mascamites.mission.played", "Delivery missions played")}
              {tile(a, "mascamites.delivered", "Delivery missions completed")}
              <Tile label="Completion rate" value={rate(a, "mascamites.delivered", "mascamites.mission.played")} />
            </div>
            <ResourceTable a={a} species="mascamites" parts={[{ key: "sample", label: "From samples" }]} label="Gained" />
          </>
        )}
      </Species>

      <Species title="Anomalies" species="anomalies" icon={boards.anomalies} alien={alien}>
        {(a) => (
          <>
            <div className="stat-tiles small">{tile(a, "anomalies.won", "Anomaly tokens won")}</div>
            <ResourceTable a={a} species="anomalies" parts={[{ key: "token", label: "From anomaly tokens" }]} label="Gained" />
          </>
        )}
      </Species>

      <Species title={"'Oumuamua"} species="oumuamua" icon={boards.oumuamua} alien={alien}>
        {(a) => (
          <div className="stat-tiles small">
            {tile(a, "oumuamua.exofossil.gained", "Exofossils gained")}
            {tile(a, "oumuamua.exofossil.spent", "Exofossils spent")}
            {tile(a, "oumuamua.signals", "Signals marked on it")}
            {tile(a, "oumuamua.wins", "Times its tile was won", "the tile was completed with a signal of the player")}
            {tile(a, "oumuamua.orbiters", "Orbiters at the end")}
            {tile(a, "oumuamua.landers", "Landers at the end")}
          </div>
        )}
      </Species>

      <Species title="Centaurians" species="centaurians" icon={boards.centaurians} alien={alien}>
        {(a) => {
          const picks = CENTAURIAN_REWARDS.map((_, k) => m(a, `centaurians.pick.${k}`));
          const total = picks.reduce((x, y) => x + y, 0);
          return (
            <>
              <div className="stat-tiles small">
                {tile(a, "centaurians.cards.played", "Message cards played")}
                {tile(a, "centaurians.cards.completed", "Message cards completed")}
                <Tile label="Completion rate" value={rate(a, "centaurians.cards.completed", "centaurians.cards.played")} />
              </div>
              <h3>The rewards of the message milestones</h3>
              <BarList
                label="How often each reward of the Centaurian board was taken, and how early"
                max={1}
                rows={CENTAURIAN_REWARDS.map((r, k) => {
                  const taken = m(a, `centaurians.pick.${k}`);
                  const order = taken > 0 ? m(a, `centaurians.order.${k}`) / taken : 0;
                  return {
                    key: String(k),
                    label: <Rewards list={r} size={18} />,
                    value: total > 0 ? taken / total : 0,
                    spread: a.spread[`centaurians.pick.${k}`],
                    color: "var(--viz-1)",
                    text: (
                      <>
                        <b>{total > 0 ? pct(taken / total) : "-"}</b>
                        <span className="muted small">{order > 0 ? ` · position ${round(order)}` : ""}</span>
                      </>
                    ),
                    title:
                      "The share of the rewards that the players took. The lower the position, the sooner it was taken: 1 means it was taken first.",
                  };
                })}
              />
              <p className="muted small">
                The position is the place of the reward in the order in which the four were taken, by anyone: a reward at 1.5 is a first
                choice, one at 3.5 is left for last.
              </p>
              <ResourceTable
                a={a}
                species="centaurians"
                parts={[
                  { key: "milestone", label: "From the rewards" },
                  { key: "card", label: "From message cards" },
                ]}
                label="Gained"
              />
            </>
          );
        }}
      </Species>

      <Species title="Exertians" species="exertians" icon={boards.exertians} alien={alien}>
        {(a) => (
          <div className="stat-tiles small">
            {tile(a, "exertians.danger", "Danger at the end")}
            {tile(a, "exertians.played", "Cards played facedown")}
            {tile(a, "exertians.danger.cards", "Danger from the facedown cards")}
            {tile(a, "exertians.danger.board", "Danger from the board")}
            {tile(
              a,
              "exertians.loss",
              "Points lost to the highest danger",
              "a tenth of the total goes to the player(s) with the most danger",
            )}
          </div>
        )}
      </Species>

      <Species title="Arkhos" species="arkhos" icon={boards.arkhos} alien={alien}>
        {(a) => (
          <>
            <div className="stat-tiles small">
              {tile(a, "arkhos.explore.minor", "Minor explorations")}
              {tile(a, "arkhos.explore.major", "Major explorations")}
              {tile(a, "arkhos.breach", "Security cards breached")}
              {tile(a, "arkhos.security.played", "Security cards played")}
            </div>
            <ResourceTable
              a={a}
              species="arkhos"
              parts={[
                { key: "minor", label: "Minor exploration" },
                { key: "major", label: "Major exploration" },
              ]}
              label="Gained"
            />
          </>
        )}
      </Species>

      <Species title="Glyphids" species="glyphids" icon={boards.glyphids} alien={alien}>
        {(a) => {
          const sources = [
            { key: "board_top", label: "Upper wells of the glyphid board" },
            { key: "board_low", label: "Lower wells of the glyphid board" },
            { key: "planet", label: "Orbiting or landing at a planet" },
            { key: "tech", label: "Researching a tech" },
            { key: "sector", label: "Winning a sector" },
          ];
          const all = sources.reduce((n, x) => n + m(a, `glyphids.token.${x.key}`), 0);
          return (
            <>
              <div className="stat-tiles small">
                <Tile label="Tokens acquired" value={round(all)} />
                {tile(a, "glyphids.placed", "Tokens placed on the translation board")}
                {tile(a, "glyphids.leftover", "Tokens left at the end")}
                {tile(a, "glyphids.leftover.vp", "Points from the tokens left")}
              </div>
              <h3>Where the tokens came from</h3>
              <BarList
                label="Glyph tokens acquired per game, by source"
                rows={sources.map((x) => ({
                  key: x.key,
                  label: x.label,
                  value: m(a, `glyphids.token.${x.key}`),
                  spread: a.spread[`glyphids.token.${x.key}`],
                  color: "var(--viz-2)",
                  text: <b>{round(m(a, `glyphids.token.${x.key}`))}</b>,
                }))}
              />
              <ResourceTable
                a={a}
                species="glyphids"
                parts={[{ key: "translation", label: "From the translation board" }]}
                label="Gained"
              />
            </>
          );
        }}
      </Species>

      <Species title="Amoeba" species="amoeba" icon={boards.amoeba} alien={alien}>
        {(a) => (
          <>
            <h3>Organelle triggers</h3>
            <div className="tablewrap">
              <table className="res-table" aria-label="Organelle triggers per game by color">
                <thead>
                  <tr>
                    <th scope="col">Color</th>
                    <th scope="col">Single</th>
                    <th scope="col">Group</th>
                    <th scope="col">Tokens per group</th>
                  </tr>
                </thead>
                <tbody>
                  {COLORS.map((c) => {
                    const groups = m(a, `amoeba.group.${c}`);
                    return (
                      <tr key={c}>
                        <th scope="row">
                          <span className="vswatch" style={{ background: COLOR_HEX[c] }} /> {cap(c)}
                        </th>
                        <td>
                          <WithSpread spread={a.spread[`amoeba.single.${c}`]}>{round(m(a, `amoeba.single.${c}`))}</WithSpread>
                        </td>
                        <td>
                          <WithSpread spread={a.spread[`amoeba.group.${c}`]}>{round(groups)}</WithSpread>
                        </td>
                        <td>{groups > 0 ? round(m(a, `amoeba.group.${c}.tokens`) / groups) : "-"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <ResourceTable
              a={a}
              species="amoeba"
              parts={[
                { key: "single", label: "Single trigger" },
                { key: "group", label: "Group trigger" },
              ]}
              label="Gained"
            />
          </>
        )}
      </Species>
    </>
  );
}
