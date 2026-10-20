// Statistics of the games that were played to their end, averaged for each player of each game (the counters come from the engine: stats.py).
// The filter chooses which games count: the number of players, the expansion, rated or casual. Nothing is worked out here that is a rule.
import { getDb } from "@/lib/db";
import { ORG_NAMES } from "@/lib/moves";
import { statRows } from "@/lib/queries";
import { aggregate, parseFilter } from "@/lib/stats";
import { TECH_INFO } from "@/lib/techs";
import type { ReactNode } from "react";

export const dynamic = "force-dynamic";
export const metadata = { title: "Statistics" };

const one = (x: number): string => (Math.round(x * 10) / 10).toString();
const pct = (x: number): string => `${Math.round(x * 100)}%`;
const cap = (w: string): string => w.charAt(0).toUpperCase() + w.slice(1);
const signed = (x: number): string => `${x > 0 ? "+" : ""}${one(x)}`;
const SPECIES_NAMES: Record<string, string> = { oumuamua: "'Oumuamua" };
const TECH_CATEGORIES = ["probe", "telescope", "computer"];
const SECTOR_COLORS = ["red", "yellow", "blue", "black"];
const TRACE_COLORS = ["pink", "yellow", "blue"];
const INCOME_KINDS = ["credit", "energy", "card"];

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

export default async function StatsPage({
  searchParams,
}: { searchParams: Promise<{ players?: string; expansion?: string; rated?: string }> }) {
  const sp = await searchParams;
  const filter = parseFilter(sp);
  const s = aggregate(await statRows(getDb(), filter), filter);
  const m = (k: string): number => s.mean[k] ?? 0;
  const per = (label: string, keys: string[]): ReactNode[] => [label, ...keys.map((k) => one(m(k)))];
  return (
    <>
      <h1>Statistics</h1>
      <p className="muted">
        Averages for each player of the games that were played to their end. A game that was cancelled, resigned or lost on time is not
        counted.
      </p>
      <form method="get" action="/stats" className="card" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "end" }}>
        <label>
          Players
          <select name="players" defaultValue={filter.players === null ? "" : String(filter.players)}>
            <option value="">any number</option>
            <option value="1">solo</option>
            <option value="2">2 players</option>
            <option value="3">3 players</option>
            <option value="4">4 players</option>
          </select>
        </label>
        <label>
          Space Agencies expansion
          <select name="expansion" defaultValue={filter.expansion === null ? "" : filter.expansion ? "yes" : "no"}>
            <option value="">with or without</option>
            <option value="yes">with</option>
            <option value="no">without</option>
          </select>
        </label>
        <label>
          Rated
          <select name="rated" defaultValue={filter.rated === null ? "" : filter.rated ? "yes" : "no"}>
            <option value="">rated or casual</option>
            <option value="yes">rated</option>
            <option value="no">casual</option>
          </select>
        </label>
        <button type="submit" className="primary">
          Show
        </button>
      </form>
      <p>
        <b>{s.games}</b> game{s.games === 1 ? "" : "s"} · <b>{s.rows}</b> player{s.rows === 1 ? "" : "s"} counted
      </p>
      {s.rows === 0 ? (
        <p>No finished game matches this filter yet.</p>
      ) : (
        <>
          <h2>Organizations</h2>
          {s.orgs.length === 0 ? (
            <p className="muted">No game with organizations matches.</p>
          ) : (
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
          )}

          <h2>Alien species</h2>
          <p className="muted small">The average final score of the players of the games that have the species, discovered or not.</p>
          <Table
            head={["Species", "Games", "Average final score"]}
            rows={s.species.map((x) => [SPECIES_NAMES[x.species] ?? cap(x.species), x.games, one(x.avgScore)])}
          />

          <h2>Actions per game</h2>
          <Table
            head={["Launch", "Scan", "Analyze", "Research", "Orbit", "Land", "Play a card", "Pass"]}
            rows={[["launch", "scan", "analyze", "research", "orbit", "land", "play_card", "pass"].map((a) => one(m(`action.${a}`)))]}
          />

          <h2>Probes, planets and cards</h2>
          <Table
            head={["Probes launched", "Orbiters", "Landers", "Cards drawn", "Cards played", "Missions played", "Missions completed"]}
            rows={[
              [
                one(m("probes.launched")),
                one(m("orbiters")),
                one(m("landers")),
                one(m("cards.drawn")),
                one(m("cards.played")),
                one(m("missions.played")),
                one(m("missions.completed")),
              ],
            ]}
          />

          <h2>Life traces</h2>
          <Table head={TRACE_COLORS.map(cap)} rows={[TRACE_COLORS.map((c) => one(m(`trace.${c}`)))]} />

          <h2>Cards tucked for income</h2>
          <Table
            head={INCOME_KINDS.concat(["publicity", "data"]).map(cap)}
            rows={[INCOME_KINDS.concat(["publicity", "data"]).map((k) => one(m(`tucked.${k}`)))]}
          />

          <h2>Income at the end of each round</h2>
          <p className="muted small">What the player's income was in that round. The expansion has no round 1.</p>
          <Table
            head={["Round", ...INCOME_KINDS.map(cap)]}
            rows={s.rounds.map((r) => [r, ...INCOME_KINDS.map((k) => one(m(`incomerate.r${r}.${k}`)))])}
          />

          <h2>End-of-game scoring</h2>
          <Table head={["End-of-game cards played", "Points from them"]} rows={[[one(m("endcards.played")), one(m("endcards.points"))]]} />
          {s.gold.length > 0 ? (
            <Table
              head={["Gold scoring tile (face)", "Times scored", "Average points each time"]}
              rows={s.gold.map((g) => [g.face, g.times, one(g.avgPoints)])}
            />
          ) : null}

          <h2>Publicity gained</h2>
          <Table
            head={["From comets", "From asteroids", "From planets", "From completing a sector"]}
            rows={[
              [
                one(m("publicity.visit.comet")),
                one(m("publicity.visit.asteroid") + m("publicity.visit.asteroids")),
                one(
                  Object.keys(s.mean)
                    .filter(
                      (k) =>
                        k.startsWith("publicity.visit.") &&
                        !["comet", "asteroid", "asteroids"].includes(k.slice("publicity.visit.".length)),
                    )
                    .reduce((a, k) => a + (s.mean[k] ?? 0), 0),
                ),
                one(m("publicity.sector")),
              ],
            ]}
          />

          <h2>Data</h2>
          <Table
            head={["Gained", "Placed in the computer", "Used in other ways"]}
            rows={[[one(m("data.gained")), one(m("data.computer")), one(Math.max(0, m("data.lost") - m("data.computer")))]]}
          />

          <h2>Sectors and signals</h2>
          <Table
            head={["Color", "Sectors won", "Signals marked"]}
            rows={SECTOR_COLORS.map((c) => [cap(c), one(m(`sectorwin.${c}`)), one(m(`signal.${c}`))])}
          />

          <h2>Tech</h2>
          <Table head={["Category", "Researched per game"]} rows={TECH_CATEGORIES.map((c) => [cap(c), one(m(`techcat.${c}`))])} />
          <Table
            head={["Tech", "Researched in"]}
            rows={s.techs.map((t) => [TECH_INFO[t.tech]?.name ?? t.tech, `${pct(t.share)} of the games of a player`])}
          />
        </>
      )}
    </>
  );
}
