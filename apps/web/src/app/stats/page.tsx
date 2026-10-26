import { AlienStatsSection } from "@/components/AlienStats";
import { CardStats } from "@/components/CardStats";
// Statistics of the games that were played to their end, averaged for each player of each game (the counters come from the engine: stats.py).
// The filter chooses which games count: the number of players, the expansion, rated or friendly. Nothing is worked out here that is a rule.
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
import { MultiChoice } from "@/components/MultiChoice";
import { OrgName } from "@/components/OrgName";
import { ResourcePies } from "@/components/ResourcePies";
import { BarList, Histogram, LineChart, Panel, Pills, Tile, WithSpread, round } from "@/components/StatCharts";
import { getDb } from "@/lib/db";
import { ORG_NAMES } from "@/lib/moves";
import { SPECIES_KEYS, type Spread, parseFilter, spreadOf } from "@/lib/stats";
import { cachedStats } from "@/lib/statsCache";
import { TECH_INFO } from "@/lib/techs";
import type { ReactNode } from "react";
import assets from "../../generated/assets.json";
import expansionAssets from "../../generated/expansion-assets.json";

export const dynamic = "force-dynamic";
export const metadata = { title: "Statistics" };

const pct = (x: number): string => `${Math.round(x * 100)}%`;
const cap = (w: string): string => w.charAt(0).toUpperCase() + w.slice(1);
const signed = (x: number): string => `${x > 0 ? "+" : ""}${round(x)}`;
const SPECIES_NAMES: Record<string, string> = { oumuamua: "'Oumuamua" };
/** The picture of a species board (the five of the base game, and the expansion's), shown small as the icon of the species. */
const BOARDS = { ...(assets.species as Record<string, string>) };
for (const [key, src] of Object.entries(expansionAssets as Record<string, string>)) {
  if (key.startsWith("boards/") && !key.includes("-")) BOARDS[key.slice(7)] ??= src;
}
const TECH_CATEGORIES = ["probe", "telescope", "computer"];
/** The color of each type of tech, as on the tiles: probe orange, telescope pink, computer blue. */
const TECH_COLOR: Record<string, string> = {
  probe: "var(--tech-probe)",
  telescope: "var(--tech-telescope)",
  computer: "var(--tech-computer)",
};
const techKind = (tech: string): string => tech.split("-")[0] ?? "";
const TECH_FRONTS = assets.techFronts as Record<string, string>;
const GOLD = assets.gold as Record<string, { src: string; per?: string }>;
const SECTOR_COLORS = ["red", "yellow", "blue", "black"];
const TRACE_COLORS = ["pink", "yellow", "blue"];
const INCOME_KINDS = ["credit", "energy", "card"];
// the colours of the things in the game (the same on every chart); `black` is a grey with a light edge, as it is dark on the dark page
const SECTOR_HEX: Record<string, string> = { red: "#d9503c", yellow: "#e0b000", blue: "#3b82d6", black: "#4a515c" };
const TRACE_HEX: Record<string, string> = { pink: "#d55181", yellow: "#c98500", blue: "#3987e5" };
const INCOME_HEX: Record<string, string> = { credit: "#c98500", energy: "#199e70", card: "#3987e5" };
const VIZ = ["var(--viz-1)", "var(--viz-2)", "var(--viz-3)", "var(--viz-4)", "var(--viz-5)"];

/** One of the three bars of an organization: the name of the number, the bar, and the number. */
function OrgBar({ label, share, color, text }: { label: string; share: number; color: string; text: ReactNode }) {
  return (
    <span className="orgbar">
      <span className="orgbar-label muted small">{label}</span>
      <span className="bar-track">
        <span className="bar-fill" style={{ width: `${Math.max(share > 0 ? 1.5 : 0, Math.min(1, share) * 100)}%`, background: color }} />
      </span>
      <span className="orgbar-text">{text}</span>
    </span>
  );
}

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
}: {
  searchParams: Promise<{
    players?: string;
    expansion?: string;
    rated?: string;
    who?: string;
    species?: string;
    org?: string;
    osort?: string;
  }>;
}) {
  const sp = await searchParams;
  const filter = parseFilter(sp);
  const s = await cachedStats(getDb(), filter);
  const m = (k: string): number => s.mean[k] ?? 0;
  // how the players differ in a counter, and in a number that is worked out from several counters (a player without the counter counts as 0)
  const sd = (k: string): Spread | undefined => s.spread[k];
  // the counters that came with the newer statistics are worked out over the rows that have them (see FreshStats)
  const fm = (k: string): number => s.fresh.mean[k] ?? 0;
  const fsd = (k: string): Spread | undefined => s.fresh.spread[k];
  const sdOf = (f: (c: Record<string, number>) => number): Spread => spreadOf(s.players.map((p) => f(p.counters)));
  const base: Record<string, string> = {};
  if (filter.players !== null) base.players = String(filter.players);
  if (filter.expansion !== null) base.expansion = filter.expansion ? "yes" : "no";
  if (filter.rated !== null) base.rated = filter.rated ? "yes" : "no";
  if (filter.who !== "people") base.who = filter.who ?? "all"; // "people" is the default and is not written in the address
  if (filter.species.length > 0) base.species = filter.species.join(",");
  if (filter.org.length > 0) base.org = filter.org.join(",");
  // the other filters, for the choices of species and organizations (which change those two themselves)
  const withoutAdvanced = Object.fromEntries(Object.entries(base).filter(([k]) => k !== "species" && k !== "org"));

  // the organizations, in the order that was asked for (those that nobody picked last)
  const orgSort = sp.osort === "win" || sp.osort === "score" ? sp.osort : "pick";
  const orgKey = (o: (typeof s.orgs)[number]): number | null =>
    orgSort === "win" ? o.winRate : orgSort === "score" ? o.avgScore : o.pickRate;
  const orgsSorted = [...s.orgs].sort((a, b) => (orgKey(b) ?? -1) - (orgKey(a) ?? -1) || b.picked - a.picked);
  const bestScore = Math.max(0, ...s.orgs.map((o) => o.avgScore ?? 0));
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
  const sumOf = (keys: string[]) => ({
    value: keys.reduce((a, k) => a + m(k), 0),
    spread: sdOf((c) => keys.reduce((a, k) => a + (c[k] ?? 0), 0)),
  });
  const alienKeys = Object.keys(s.mean).filter((k) => k.startsWith("publicity.alien."));
  const publicity = [
    { key: "comet", label: "From comets", value: m("publicity.visit.comet"), spread: sd("publicity.visit.comet") },
    {
      key: "asteroid",
      label: "From asteroids",
      value: m("publicity.visit.asteroid") + m("publicity.visit.asteroids"),
      spread: sdOf((c) => (c["publicity.visit.asteroid"] ?? 0) + (c["publicity.visit.asteroids"] ?? 0)),
    },
    {
      key: "planet",
      label: "From planets",
      value: planetsPublicity,
      spread: sdOf((c) => planetKeys.reduce((a, k) => a + (c[k] ?? 0), 0)),
    },
    { key: "sector", label: "From completing a sector", value: m("publicity.sector"), spread: sd("publicity.sector") },
    { key: "card", label: "From playing cards", ...sumOf(["gain.card.publicity", "gain.mission.publicity"]) },
    { key: "corner", label: "From discarding a card for its free corner", ...sumOf(["gain.corner.publicity"]) },
    { key: "tech", label: "From technologies", ...sumOf(["gain.tech.publicity"]) },
    { key: "trace", label: "From marking alien traces", ...sumOf(["gain.trace.publicity"]) },
    { key: "alien", label: "From alien effects", ...sumOf(alienKeys) },
    {
      key: "other",
      label: "From the organization and income",
      ...sumOf(["gain.organization.publicity", "gain.quick_start.publicity", "gain.income.publicity"]),
    },
  ];
  const techsOf = (c: Record<string, number>): number => TECH_CATEGORIES.reduce((n, k) => n + (c[`techcat.${k}`] ?? 0), 0);
  const techTotal = TECH_CATEGORIES.reduce((n, k) => n + m(`techcat.${k}`), 0);
  const techManual = m("action.research");
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
              { value: "no", label: "Friendly" },
            ]}
          />
        </div>
        <div>
          <span className="stat-filter-name">Players</span>
          <Pills
            name="who"
            current={filter.who === "people" ? "" : (filter.who ?? "all")}
            base={base}
            choices={[
              { value: "", label: "People only" },
              { value: "ai", label: "AI only" },
              { value: "all", label: "Everyone" },
            ]}
          />
        </div>
      </div>

      <details className="card stat-advanced" open={filter.species.length > 0 || filter.org.length > 0}>
        <summary>Advanced filters</summary>
        <div className="stat-advanced-form">
          <MultiChoice
            name="species"
            label="Alien species in the game (any of them)"
            action="/stats"
            base={base}
            selected={filter.species}
            choices={SPECIES_KEYS.map((k) => ({ value: k, label: SPECIES_NAMES[k] ?? cap(k) }))}
          />
          <MultiChoice
            name="org"
            label="Organization the player picked (any of them)"
            action="/stats"
            base={base}
            selected={filter.org}
            choices={Object.entries(ORG_NAMES)
              .sort((a, b) => a[1].localeCompare(b[1]))
              .map(([id, name]) => ({ value: id, label: name }))}
          />
          {filter.species.length > 0 || filter.org.length > 0 ? (
            <a
              className="small"
              href={`/stats${Object.keys(withoutAdvanced).length > 0 ? `?${new URLSearchParams(withoutAdvanced).toString()}` : ""}`}
            >
              Clear these
            </a>
          ) : null}
        </div>
        <p className="muted small">
          The alien species keeps the games that have at least one of the chosen species, discovered or not, and counts every player of
          those games. The organization keeps only the players who picked one of the chosen ones, so the tables of organizations, species
          and techs then describe those players. Both go with the filters above.
        </p>
      </details>

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

            <h2 className="stat-section">Where the resources came from</h2>
            <ResourcePies gains={s.gains} />

            <h2 className="stat-section">The cards</h2>
            <Panel
              title="Cards played"
              note="Every card of the main deck and of the species that was played, with what happened to the players who played it."
              wide
            >
              <CardStats cards={s.cards} rows={s.cardRows} rounds={s.rounds} />
            </Panel>

            <h2 className="stat-section">Organizations and species</h2>
            <Panel
              title="Organizations"
              note="How often each was picked of the times it was offered, how often the players who picked it won, and their average final score."
              wide
              table={
                s.orgs.length === 0 ? undefined : (
                  <Table
                    head={["Organization", "Offered", "Picked", "Pick rate", "Win rate", "Average score", "Elo change (rated)"]}
                    rows={orgsSorted.map((o) => [
                      ORG_NAMES[o.org] ?? o.org,
                      o.offered,
                      o.picked,
                      pct(o.pickRate),
                      o.winRate === null ? "–" : pct(o.winRate),
                      o.avgScore === null ? "–" : round(o.avgScore),
                      o.eloDelta === null ? "–" : `${signed(o.eloDelta)} (${o.eloGames})`,
                    ])}
                  />
                )
              }
            >
              {s.orgs.length === 0 ? (
                <p className="muted">No game with organizations matches.</p>
              ) : (
                <>
                  <div className="stat-sort">
                    <span className="stat-filter-name">Sort by</span>
                    <Pills
                      name="osort"
                      current={orgSort === "pick" ? "" : orgSort}
                      base={base}
                      choices={[
                        { value: "", label: "Pick rate" },
                        { value: "win", label: "Win rate" },
                        { value: "score", label: "Average score" },
                      ]}
                    />
                  </div>
                  <ul className="orgbars" aria-label="The organizations: pick rate, win rate and average score">
                    {orgsSorted.map((o) => (
                      <li key={o.org} title={`${ORG_NAMES[o.org] ?? o.org}: offered ${o.offered} times, picked ${o.picked}`}>
                        <OrgName id={o.org} banner />
                        <OrgBar
                          label="Pick rate"
                          share={o.pickRate}
                          color={VIZ[0] as string}
                          text={
                            <>
                              <b>{pct(o.pickRate)}</b>
                              <span className="muted small">
                                {" "}
                                {o.picked} of {o.offered}
                              </span>
                            </>
                          }
                        />
                        <OrgBar
                          label="Win rate"
                          share={o.winRate ?? 0}
                          color={VIZ[1] as string}
                          text={
                            o.winRate === null ? (
                              <span className="muted small">not picked</span>
                            ) : (
                              <>
                                <b>{pct(o.winRate)}</b>
                                <span className="muted small"> of {o.picked}</span>
                              </>
                            )
                          }
                        />
                        <OrgBar
                          label="Average score"
                          share={o.avgScore === null || bestScore <= 0 ? 0 : o.avgScore / bestScore}
                          color={VIZ[2] as string}
                          text={
                            o.avgScore === null ? (
                              <span className="muted small">not picked</span>
                            ) : (
                              <WithSpread spread={o.scoreSpread}>
                                <b>{round(o.avgScore)}</b>
                              </WithSpread>
                            )
                          }
                        />
                        {o.eloDelta === null ? null : (
                          <span className="muted small orgelo">
                            Elo {signed(o.eloDelta)} ({o.eloGames})
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </>
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
                      {BOARDS[x.species] ? <img src={BOARDS[x.species]} alt="" width={22} height={40} className="mini-board" /> : <Blank />}
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
                  value={round(fm("probes.launched"))}
                  spread={fsd("probes.launched")}
                />
                <Tile
                  icon={<ActionIcon name="launch" size={28} />}
                  label="Probes from effects"
                  note="Launched without the launch action"
                  value={round(fm("probes.launched.other"))}
                  spread={fsd("probes.launched.other")}
                />
                <Tile
                  icon={<ActionIcon name="orbit" size={28} />}
                  label="Orbiters"
                  value={round(fm("orbiters"))}
                  spread={fsd("orbiters")}
                />
                <Tile
                  icon={<ActionIcon name="orbit" size={28} />}
                  label="Orbiters from effects"
                  note="Placed without the orbit action"
                  value={round(fm("orbits.other"))}
                  spread={fsd("orbits.other")}
                />
                <Tile icon={<ActionIcon name="land" size={28} />} label="Landers" value={round(fm("landers"))} spread={fsd("landers")} />
                <Tile
                  icon={<ActionIcon name="land" size={28} />}
                  label="Landers from effects"
                  note="Placed without the land action"
                  value={round(fm("lands.other"))}
                  spread={fsd("lands.other")}
                />
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
                <Tile
                  icon={<MissionIcon done size={30} />}
                  label="Mission completion rate"
                  note="Missions completed out of missions played"
                  value={m("missions.played") > 0 ? `${Math.round((m("missions.completed") / m("missions.played")) * 100)}%` : "–"}
                />
              </div>
              {s.fresh.rows < s.rows ? (
                <p className="muted small">
                  Probes launched, orbiters, landers and the "from effects" numbers are counted over the {s.fresh.rows} of {s.rows} players
                  whose games could be replayed with the current rules; the other games only have older figures.
                </p>
              ) : null}
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
                      color: TECH_COLOR[c],
                    }))}
                  />
                  <h3>How they were researched</h3>
                  <BarList
                    label="Techs researched per game: by the research action or in another way"
                    rows={[
                      {
                        key: "all",
                        label: "In all",
                        value: techTotal,
                        spread: sdOf(techsOf),
                        text: <b>{round(techTotal)}</b>,
                      },
                      {
                        key: "manual",
                        label: "Research action (6 publicity)",
                        value: techManual,
                        spread: sd("action.research"),
                        text: <b>{round(techManual)}</b>,
                      },
                      {
                        key: "other",
                        label: "Other ways (cards, rewards, bonuses)",
                        value: Math.max(0, techTotal - techManual),
                        spread: sdOf((c) => Math.max(0, techsOf(c) - (c["action.research"] ?? 0))),
                        text: <b>{round(Math.max(0, techTotal - techManual))}</b>,
                      },
                    ]}
                  />
                </div>
                <div>
                  <h3>Researched in x% of games</h3>
                  <BarList
                    label="Share of the players who researched each tech"
                    max={1}
                    rows={s.techs.map((t) => ({
                      key: t.tech,
                      label: (
                        <span className="icon-label">
                          {TECH_FRONTS[t.tech] ? (
                            <img
                              src={TECH_FRONTS[t.tech]}
                              alt={TECH_INFO[t.tech]?.name ?? t.tech}
                              width={28}
                              height={39}
                              className="mini-tech"
                            />
                          ) : (
                            (TECH_INFO[t.tech]?.name ?? t.tech)
                          )}
                        </span>
                      ),
                      color: TECH_COLOR[techKind(t.tech)],
                      value: t.share,
                      text: <b>{pct(t.share)}</b>,
                      title: TECH_INFO[t.tech] ? `${TECH_INFO[t.tech]?.name}: ${TECH_INFO[t.tech]?.effect}` : undefined,
                    }))}
                  />
                </div>
              </div>
            </Panel>

            <Panel
              title="What the techs did"
              wide
              note="What each tech gave on average for the rest of the game after it was researched."
              table={
                <Table
                  head={["Tech", "Researched", "What", "Average"]}
                  rows={s.techUse.flatMap((t) =>
                    t.metrics.map((m) => [TECH_INFO[t.tech]?.name ?? t.tech, t.players, m.label, round(m.mean)]),
                  )}
                />
              }
            >
              <div className="techuse">
                {s.techUse
                  .filter((t) => t.metrics.length > 0)
                  .map((t) => (
                    <div key={t.tech} className="techuse-card" style={{ borderLeftColor: TECH_COLOR[techKind(t.tech)] }}>
                      {TECH_FRONTS[t.tech] ? (
                        <img
                          src={TECH_FRONTS[t.tech]}
                          alt={TECH_INFO[t.tech]?.name ?? t.tech}
                          title={`${TECH_INFO[t.tech]?.name ?? t.tech}: ${TECH_INFO[t.tech]?.effect ?? ""}`}
                          width={28}
                          height={39}
                          className="mini-tech"
                        />
                      ) : null}
                      <div>
                        {t.players === 0 ? (
                          <span className="muted small">not researched in these games yet</span>
                        ) : (
                          <>
                            {t.metrics.map((m) => (
                              <div key={m.key} className="techuse-line">
                                <span>{m.label}:</span>{" "}
                                <b>
                                  <WithSpread spread={m.spread}>{round(m.mean)}</WithSpread>
                                </b>
                              </div>
                            ))}
                            <span className="muted small">
                              researched {t.players} time{t.players === 1 ? "" : "s"}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
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
                      label: (
                        <span className="icon-label">
                          {GOLD[g.face] ? (
                            <span
                              className="mini-gold"
                              style={{ backgroundImage: `url(${GOLD[g.face]?.src})` }}
                              role="img"
                              aria-label={g.face}
                            />
                          ) : (
                            g.face
                          )}
                        </span>
                      ),
                      color: "var(--gold)",
                      title: GOLD[g.face]?.per ? `${g.face}: ${GOLD[g.face]?.per}` : g.face,
                      value: g.times,
                      text: (
                        <>
                          <b>{g.times}</b>
                          <span className="muted small">
                            {" "}
                            times · <WithSpread spread={g.spread}>{round(g.avgPoints)}</WithSpread> points each
                          </span>
                        </>
                      ),
                    }))}
                  />
                </>
              ) : null}
            </Panel>

            <h2 className="stat-section">The alien species in detail</h2>
            <AlienStatsSection alien={s.alien} boards={BOARDS} />
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
