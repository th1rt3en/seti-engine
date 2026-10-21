// Statistics of the games that were played to their end, averaged for each player of each game (the counters come from the engine: stats.py).
// The filter chooses which games count: the number of players, the expansion, rated or casual. Nothing is worked out here that is a rule.
// Drawn as tiles and charts (components/StatCharts.tsx), every block with its numbers as a table behind a button.
import {
  ActionIcon,
  CreditIcon,
  DataIcon,
  DeckCardIcon,
  DisplayCardIcon,
  EnergyIcon,
  MissionIcon,
  PublicityIcon,
  ScoreIcon,
  TraceIcon,
} from "@/components/Icons";
import { OrgName } from "@/components/OrgName";
import { BarList, Histogram, LineChart, Panel, Pills, StackBar, Tile, round } from "@/components/StatCharts";
import { getDb } from "@/lib/db";
import { ORG_NAMES } from "@/lib/moves";
import { statRows } from "@/lib/queries";
import { type Spread, aggregate, parseFilter, spreadOf } from "@/lib/stats";
import { TECH_INFO } from "@/lib/techs";
import type { ReactNode } from "react";
import assets from "../../generated/assets.json";

export const dynamic = "force-dynamic";
export const metadata = { title: "Statistics" };

const pct = (x: number): string => `${Math.round(x * 100)}%`;
const cap = (w: string): string => w.charAt(0).toUpperCase() + w.slice(1);
const signed = (x: number): string => `${x > 0 ? "+" : ""}${round(x)}`;
const SPECIES_NAMES: Record<string, string> = { oumuamua: "'Oumuamua" };
const BACKS = assets.alienBacks as Record<string, string>;
const TECH_CATEGORIES = ["probe", "telescope", "computer"];
const SECTOR_COLORS = ["red", "yellow", "blue", "black"];
const TRACE_COLORS = ["pink", "yellow", "blue"];
const INCOME_KINDS = ["credit", "energy", "card"];
// the colours of the things in the game (the same on every chart); `black` is a grey with a light edge, as it is dark on the dark page
const SECTOR_HEX: Record<string, string> = { red: "#d9503c", yellow: "#e0b000", blue: "#3b82d6", black: "#4a515c" };
const TRACE_HEX: Record<string, string> = { pink: "#d55181", yellow: "#c98500", blue: "#3987e5" };
const INCOME_HEX: Record<string, string> = { credit: "#c98500", energy: "#199e70", card: "#3987e5" };
const VIZ = ["var(--viz-1)", "var(--viz-2)", "var(--viz-3)", "var(--viz-4)", "var(--viz-5)"];

function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="tablewrap">
      <table>
        <thead>
          <tr>
            {head.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells) => (
            <tr key={String(cells[0])}>
              {cells.map((c, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: the cells of a row have no identity
                <td key={i}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const Blank = () => <span className="icon-blank" aria-hidden="true" />;

export default async function StatsPage({
  searchParams,
}: { searchParams: Promise<{ players?: string; expansion?: string; rated?: string }> }) {
  const sp = await searchParams;
  const filter = parseFilter(sp);
  const s = aggregate(await statRows(getDb(), filter), filter);
  const m = (k: string): number => s.mean[k] ?? 0;
  // how the players differ in a counter, and in a number that is worked out from several counters (a player without the counter counts as 0)
  const sd = (k: string): Spread | undefined => s.spread[k];
  const sdOf = (f: (c: Record<string, number>) => number): Spread => spreadOf(s.players.map((p) => f(p.counters)));
  const base: Record<string, string> = {};
  if (filter.players !== null) base.players = String(filter.players);
  if (filter.expansion !== null) base.expansion = filter.expansion ? "yes" : "no";
  if (filter.rated !== null) base.rated = filter.rated ? "yes" : "no";

  const actions: { key: string; label: string; icon: ReactNode }[] = [
    { key: "launch", label: "Launch", icon: <ActionIcon name="launch" size={26} /> },
    { key: "scan", label: "Scan", icon: <ActionIcon name="scan" size={26} /> },
    { key: "analyze", label: "Analyze", icon: <ActionIcon name="analyze" size={26} /> },
    { key: "research", label: "Research", icon: <ActionIcon name="research" size={26} /> },
    { key: "orbit", label: "Orbit", icon: <ActionIcon name="orbit" size={26} /> },
    { key: "land", label: "Land", icon: <ActionIcon name="land" size={26} /> },
    { key: "play_card", label: "Play a card", icon: <DisplayCardIcon size={24} /> },
    { key: "pass", label: "Pass", icon: <ActionIcon name="pass" size={26} /> },
  ];
  const planetKeys = Object.keys(s.mean).filter(
    (k) => k.startsWith("publicity.visit.") && !["comet", "asteroid", "asteroids"].includes(k.slice("publicity.visit.".length)),
  );
  const planetsPublicity = planetKeys.reduce((a, k) => a + (s.mean[k] ?? 0), 0);
  const publicity = [
    { key: "comet", label: "From comets", value: m("publicity.visit.comet"), color: VIZ[0] as string, spread: sd("publicity.visit.comet") },
    {
      key: "asteroid",
      label: "From asteroids",
      value: m("publicity.visit.asteroid") + m("publicity.visit.asteroids"),
      color: VIZ[1] as string,
      spread: sdOf((c) => (c["publicity.visit.asteroid"] ?? 0) + (c["publicity.visit.asteroids"] ?? 0)),
    },
    {
      key: "planet",
      label: "From planets",
      value: planetsPublicity,
      color: VIZ[2] as string,
      spread: sdOf((c) => planetKeys.reduce((a, k) => a + (c[k] ?? 0), 0)),
    },
    {
      key: "sector",
      label: "From completing a sector",
      value: m("publicity.sector"),
      color: VIZ[3] as string,
      spread: sd("publicity.sector"),
    },
  ];
  const dataRows = [
    { key: "gained", label: "Gained", value: m("data.gained"), spread: sd("data.gained") },
    { key: "computer", label: "Placed in the computer", value: m("data.computer"), spread: sd("data.computer") },
    {
      key: "other",
      label: "Used in other ways",
      value: Math.max(0, m("data.lost") - m("data.computer")),
      spread: sdOf((c) => Math.max(0, (c["data.lost"] ?? 0) - (c["data.computer"] ?? 0))),
    },
  ];
  const tuckKinds = [
    { key: "credit", label: "Credit", icon: <CreditIcon size={20} /> },
    { key: "energy", label: "Energy", icon: <EnergyIcon size={20} /> },
    { key: "card", label: "Card", icon: <DeckCardIcon size={20} /> },
    { key: "publicity", label: "Publicity", icon: <PublicityIcon size={20} /> },
    { key: "data", label: "Data", icon: <DataIcon size={20} /> },
  ];

  return (
    <div className="stats-page">
      <h1>Statistics</h1>
      <p className="muted">
        Averages for each player of the games that were played to their end. A game that was cancelled, resigned or lost on time is not
        counted.
      </p>
      <div className="card stat-filters">
        <div>
          <span className="stat-filter-name">Players</span>
          <Pills
            name="players"
            current={filter.players === null ? "" : String(filter.players)}
            base={base}
            choices={[
              { value: "", label: "Any" },
              { value: "1", label: "Solo" },
              { value: "2", label: "2" },
              { value: "3", label: "3" },
              { value: "4", label: "4" },
            ]}
          />
        </div>
        <div>
          <span className="stat-filter-name">Space Agencies expansion</span>
          <Pills
            name="expansion"
            current={filter.expansion === null ? "" : filter.expansion ? "yes" : "no"}
            base={base}
            choices={[
              { value: "", label: "Either" },
              { value: "yes", label: "With" },
              { value: "no", label: "Without" },
            ]}
          />
        </div>
        <div>
          <span className="stat-filter-name">Games</span>
          <Pills
            name="rated"
            current={filter.rated === null ? "" : filter.rated ? "yes" : "no"}
            base={base}
            choices={[
              { value: "", label: "Any" },
              { value: "yes", label: "Rated" },
              { value: "no", label: "Casual" },
            ]}
          />
        </div>
      </div>

      {s.rows === 0 ? (
        <p>No finished game matches this filter yet.</p>
      ) : (
        <>
          <div className="stat-tiles">
            <Tile label={s.games === 1 ? "Game" : "Games"} value={s.games} />
            <Tile label={s.rows === 1 ? "Player counted" : "Players counted"} value={s.rows} />
            <Tile icon={<ScoreIcon size={30} />} label="Average final score" value={round(s.avgScore)} spread={spreadOf(s.scores)} />
            <Tile icon={<ScoreIcon size={30} />} label="Best final score" value={s.bestScore} />
          </div>

          <div className="stat-grid">
            <Panel title="Final scores" icon={<ScoreIcon size={24} />} note="How many players ended in each band of 25 points." wide>
              <Histogram values={s.scores} label="Number of players by final score" />
            </Panel>

            <Panel
              title="Organizations"
              note="How often each was picked of the times it was offered, and how the players who picked it did."
              wide
              table={
                s.orgs.length === 0 ? undefined : (
                  <Table
                    head={["Organization", "Offered", "Picked", "Pick rate", "Win rate", "Elo change (rated)"]}
                    rows={s.orgs.map((o) => [
                      ORG_NAMES[o.org] ?? o.org,
                      o.offered,
                      o.picked,
                      pct(o.pickRate),
                      o.winRate === null ? "–" : pct(o.winRate),
                      o.eloDelta === null ? "–" : `${signed(o.eloDelta)} (${o.eloGames})`,
                    ])}
                  />
                )
              }
            >
              {s.orgs.length === 0 ? (
                <p className="muted">No game with organizations matches.</p>
              ) : (
                <BarList
                  label="Pick rate of each organization"
                  max={1}
                  rows={s.orgs.map((o) => ({
                    key: o.org,
                    label: <OrgName id={o.org} />,
                    value: o.pickRate,
                    text: (
                      <>
                        <b>{pct(o.pickRate)}</b> picked
                        <span className="muted small">
                          {" "}
                          · {o.picked} of {o.offered}
                          {o.winRate === null ? "" : ` · wins ${pct(o.winRate)}`}
                          {o.eloDelta === null ? "" : ` · Elo ${signed(o.eloDelta)}`}
                        </span>
                      </>
                    ),
                    title: `${ORG_NAMES[o.org] ?? o.org}: offered ${o.offered} times, picked ${o.picked}`,
                  }))}
                />
              )}
            </Panel>

            <Panel
              title="Alien species"
              note="The average final score of the players of the games that have the species, discovered or not."
              table={
                <Table
                  head={["Species", "Games", "Average final score"]}
                  rows={s.species.map((x) => [SPECIES_NAMES[x.species] ?? cap(x.species), x.games, round(x.avgScore)])}
                />
              }
            >
              <BarList
                label="Average final score by alien species"
                rows={s.species.map((x) => ({
                  key: x.species,
                  label: (
                    <span className="icon-label">
                      {BACKS[x.species] ? <img src={BACKS[x.species]} alt="" width={20} height={28} className="thumb" /> : <Blank />}
                      {SPECIES_NAMES[x.species] ?? cap(x.species)}
                    </span>
                  ),
                  value: x.avgScore,
                  spread: x.spread,
                  text: (
                    <>
                      <b>{round(x.avgScore)}</b>
                      <span className="muted small">
                        {" "}
                        · {x.games} game{x.games === 1 ? "" : "s"}
                      </span>
                    </>
                  ),
                }))}
              />
            </Panel>

            <Panel title="Actions per game" note="How many times a player took each main action, on average.">
              <BarList
                label="Main actions per game"
                rows={actions.map((a) => ({
                  key: a.key,
                  label: (
                    <span className="icon-label">
                      {a.icon}
                      {a.label}
                    </span>
                  ),
                  value: m(`action.${a.key}`),
                  spread: sd(`action.${a.key}`),
                  text: <b>{round(m(`action.${a.key}`))}</b>,
                }))}
              />
            </Panel>

            <Panel title="Probes, planets and cards" wide>
              <div className="stat-tiles small">
                <Tile
                  icon={<ActionIcon name="launch" size={28} />}
                  label="Probes launched"
                  value={round(m("probes.launched"))}
                  spread={sd("probes.launched")}
                />
                <Tile icon={<ActionIcon name="orbit" size={28} />} label="Orbiters" value={round(m("orbiters"))} spread={sd("orbiters")} />
                <Tile icon={<ActionIcon name="land" size={28} />} label="Landers" value={round(m("landers"))} spread={sd("landers")} />
                <Tile icon={<DisplayCardIcon size={26} />} label="Cards drawn" value={round(m("cards.drawn"))} spread={sd("cards.drawn")} />
                <Tile icon={<DeckCardIcon size={26} />} label="Cards played" value={round(m("cards.played"))} spread={sd("cards.played")} />
                <Tile
                  icon={<MissionIcon size={30} />}
                  label="Missions played"
                  value={round(m("missions.played"))}
                  spread={sd("missions.played")}
                />
                <Tile
                  icon={<MissionIcon done size={30} />}
                  label="Missions completed"
                  value={round(m("missions.completed"))}
                  spread={sd("missions.completed")}
                />
              </div>
            </Panel>

            <Panel title="Life traces" icon={<TraceIcon size={24} />} note="Traces marked per game, by color.">
              <BarList
                label="Life traces by color"
                rows={TRACE_COLORS.map((c) => ({
                  key: c,
                  label: (
                    <span className="icon-label">
                      <span className="dot" style={{ background: TRACE_HEX[c] }} />
                      {cap(c)}
                    </span>
                  ),
                  value: m(`trace.${c}`),
                  spread: sd(`trace.${c}`),
                  text: <b>{round(m(`trace.${c}`))}</b>,
                  color: TRACE_HEX[c],
                }))}
              />
            </Panel>

            <Panel
              title="Cards tucked for income"
              icon={<IncomeDot />}
              note="Which kind of income the tucked cards were tucked for, per game."
            >
              <BarList
                label="Cards tucked for income"
                rows={tuckKinds.map((k) => ({
                  key: k.key,
                  label: (
                    <span className="icon-label">
                      {k.icon}
                      {k.label}
                    </span>
                  ),
                  value: m(`tucked.${k.key}`),
                  spread: sd(`tucked.${k.key}`),
                  text: <b>{round(m(`tucked.${k.key}`))}</b>,
                }))}
              />
            </Panel>

            <Panel
              title="Income at the end of each round"
              note="What the player's income was in that round. The expansion has no round 1."
              wide
              table={
                <Table
                  head={["Round", ...INCOME_KINDS.map(cap)]}
                  rows={s.rounds.map((r) => [r, ...INCOME_KINDS.map((k) => round(m(`incomerate.r${r}.${k}`)))])}
                />
              }
            >
              <LineChart
                label="Income of each kind at the end of each round"
                xName="Round"
                xs={s.rounds.map(String)}
                series={INCOME_KINDS.map((k) => ({
                  key: k,
                  label: cap(k),
                  color: INCOME_HEX[k] as string,
                  icon: k === "credit" ? <CreditIcon size={18} /> : k === "energy" ? <EnergyIcon size={18} /> : <DeckCardIcon size={18} />,
                  values: s.rounds.map((r) => m(`incomerate.r${r}.${k}`)),
                  spreads: s.rounds.map((r) => sd(`incomerate.r${r}.${k}`) ?? { min: 0, max: 0, std: 0 }),
                }))}
              />
            </Panel>

            <Panel title="Publicity gained" icon={<PublicityIcon size={24} />} note="Where the publicity of a player came from, per game.">
              <StackBar label="Publicity gained by source" parts={publicity} />
            </Panel>

            <Panel title="Data" icon={<DataIcon size={24} />} note="Data per game: what came in, and where it went.">
              <BarList
                label="Data gained and what it was used for"
                rows={dataRows.map((r) => ({
                  key: r.key,
                  label: r.label,
                  value: r.value,
                  spread: r.spread,
                  text: <b>{round(r.value)}</b>,
                }))}
              />
            </Panel>

            <Panel title="Sectors and signals" note="Per game, by the color of the sector." wide>
              <div className="stat-two">
                <div>
                  <h3>Sectors won</h3>
                  <BarList
                    label="Sectors won by color"
                    rows={SECTOR_COLORS.map((c) => ({
                      key: c,
                      label: (
                        <span className="icon-label">
                          <span className="dot" style={{ background: SECTOR_HEX[c] }} />
                          {cap(c)}
                        </span>
                      ),
                      value: m(`sectorwin.${c}`),
                      spread: sd(`sectorwin.${c}`),
                      text: <b>{round(m(`sectorwin.${c}`))}</b>,
                      color: SECTOR_HEX[c],
                      outline: c === "black",
                    }))}
                  />
                </div>
                <div>
                  <h3>Signals marked</h3>
                  <BarList
                    label="Signals marked by color"
                    rows={SECTOR_COLORS.map((c) => ({
                      key: c,
                      label: (
                        <span className="icon-label">
                          <span className="dot" style={{ background: SECTOR_HEX[c] }} />
                          {cap(c)}
                        </span>
                      ),
                      value: m(`signal.${c}`),
                      spread: sd(`signal.${c}`),
                      text: <b>{round(m(`signal.${c}`))}</b>,
                      color: SECTOR_HEX[c],
                      outline: c === "black",
                    }))}
                  />
                </div>
              </div>
            </Panel>

            <Panel
              title="Tech"
              wide
              table={
                <Table
                  head={["Tech", "Researched in"]}
                  rows={s.techs.map((t) => [TECH_INFO[t.tech]?.name ?? t.tech, `${pct(t.share)} of the games of a player`])}
                />
              }
            >
              <div className="stat-two">
                <div>
                  <h3>Researched per game</h3>
                  <BarList
                    label="Techs researched per game by category"
                    rows={TECH_CATEGORIES.map((c, i) => ({
                      key: c,
                      label: cap(c),
                      value: m(`techcat.${c}`),
                      spread: sd(`techcat.${c}`),
                      text: <b>{round(m(`techcat.${c}`))}</b>,
                      color: VIZ[i % VIZ.length],
                    }))}
                  />
                </div>
                <div>
                  <h3>Share of the games of a player</h3>
                  <BarList
                    label="Share of the players who researched each tech"
                    max={1}
                    rows={s.techs.map((t) => ({
                      key: t.tech,
                      label: TECH_INFO[t.tech]?.name ?? t.tech,
                      value: t.share,
                      text: <b>{pct(t.share)}</b>,
                      title: TECH_INFO[t.tech]?.effect,
                    }))}
                  />
                </div>
              </div>
            </Panel>

            <Panel
              title="End-of-game scoring"
              wide
              table={
                s.gold.length === 0 ? undefined : (
                  <Table
                    head={["Gold scoring tile (face)", "Times scored", "Average points each time"]}
                    rows={s.gold.map((g) => [g.face, g.times, round(g.avgPoints)])}
                  />
                )
              }
            >
              <div className="stat-tiles small">
                <Tile
                  icon={<DeckCardIcon size={26} />}
                  label="End-of-game cards played"
                  value={round(m("endcards.played"))}
                  spread={sd("endcards.played")}
                />
                <Tile
                  icon={<ScoreIcon size={28} />}
                  label="Points from them"
                  value={round(m("endcards.points"))}
                  spread={sd("endcards.points")}
                />
              </div>
              {s.gold.length > 0 ? (
                <>
                  <h3>Gold scoring tiles</h3>
                  <BarList
                    label="Times each gold scoring tile was scored"
                    rows={s.gold.map((g) => ({
                      key: g.face,
                      label: g.face,
                      value: g.times,
                      text: (
                        <>
                          <b>{g.times}</b>
                          <span className="muted small"> times · {round(g.avgPoints)} points each</span>
                        </>
                      ),
                    }))}
                  />
                </>
              ) : null}
            </Panel>
          </div>
        </>
      )}
    </div>
  );
}

/** The mark of an income: the printed income icon. */
function IncomeDot() {
  const src = (assets.printedIcons as Record<string, string>).income;
  return src ? <img src={src} alt="" width={24} height={24} className="resicon" /> : null;
}
