"use client";
// The statistics of the cards that were played (a card of the main deck or of a species): how many players played each, the final score of those players, how
// often they won, in which round the card was played and which organization the players had. The numbers are the counters `card.<id>.r<round>` of the
// engine (stats.py) with the final score, the win and the organization of the player's row; the page works out nothing about the rules.
import { ORG_NAMES } from "@/lib/moves";
import type { CardStat, Spread } from "@/lib/stats";
import { useMemo, useState } from "react";
import catalog from "../generated/card-catalog.json";
import { CardImage } from "./CardImage";

interface Entry {
  id: string;
  name: string;
  deck: string;
  species: string | null;
  type: string;
}
const CARDS = new Map((catalog as Entry[]).map((c) => [c.id, c]));
/** The printed name of the card (the catalog's; the card number is shown beside it). */
const cardName = (id: string): string => CARDS.get(id)?.name ?? id;

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

/** The group a card belongs to in the tabs: the base deck, the expansion's deck, the promo cards, or its species. */
function groupOf(id: string): string {
  const c = CARDS.get(id);
  if (!c) return "other";
  if (c.deck === "base") return "base";
  if (c.deck === "expansion") return "expansion";
  if (c.deck === "promo" || c.deck === "promo2") return "promo";
  return c.species ?? "other";
}

const TABS = [
  { id: "", label: "All" },
  { id: "base", label: "Main deck" },
  { id: "expansion", label: "Space Agencies deck" },
  { id: "promo", label: "Promo cards" },
  ...Object.entries(SPECIES_NAMES).map(([id, label]) => ({ id, label })),
];

type Sort = "plays" | "score" | "win" | "early" | "late" | "playrate" | "discardrate";
const SORTS: { id: Sort; label: string }[] = [
  { id: "plays", label: "Most played" },
  { id: "score", label: "Highest average score" },
  { id: "win", label: "Highest win rate" },
  { id: "playrate", label: "Highest play rate" },
  { id: "discardrate", label: "Highest discard rate" },
  { id: "early", label: "Played earliest" },
  { id: "late", label: "Played latest" },
];

const r1 = (x: number): string => (Math.round(x * 10) / 10).toString();
const pct = (x: number): string => `${Math.round(x * 100)}%`;
const spreadText = (s: Spread): string => `lowest ${r1(s.min)}, highest ${r1(s.max)}, std. deviation ${r1(s.std)}`;

export function CardStats({ cards, rows, rounds }: { cards: CardStat[]; rows: number; rounds: number[] }) {
  const [group, setGroup] = useState("");
  const [sort, setSort] = useState<Sort>("plays");
  const [min, setMin] = useState(1);
  const [q, setQ] = useState("");
  const shown = useMemo(() => {
    const key = (c: CardStat): number =>
      sort === "score"
        ? c.avgScore
        : sort === "win"
          ? c.winRate
          : sort === "playrate"
            ? (c.playRate ?? -1)
            : sort === "discardrate"
              ? (c.discardRate ?? -1)
              : sort === "early"
                ? -c.avgRound
                : sort === "late"
                  ? c.avgRound
                  : c.plays;
    return cards
      .filter((c) => (group === "" || groupOf(c.id) === group) && c.plays >= min)
      .filter((c) => q === "" || cardName(c.id).toLowerCase().includes(q.toLowerCase()) || c.id.toLowerCase().includes(q.toLowerCase()))
      .sort((a, b) => key(b) - key(a) || b.plays - a.plays);
  }, [cards, group, sort, min, q]);
  const roundList = rounds.length > 0 ? rounds : [1, 2, 3, 4, 5];
  return (
    <div className="cardstats">
      <p className="muted small">
        Over the {rows} player{rows === 1 ? "" : "s"} of the games whose statistics have the cards (the older games get them when their
        statistics are made again). A card counts for a player when it was played as a main action; the final score, the win and the
        organization are the player's own.
      </p>
      <div className="cs-controls">
        <nav className="fpills" aria-label="Cards of">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={group === t.id ? "fpill on" : "fpill"}
              aria-pressed={group === t.id}
              onClick={() => setGroup(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <label>
          <span className="stat-filter-name">Sort by</span>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
            {SORTS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="stat-filter-name">Played at least</span>
          <select value={min} onChange={(e) => setMin(Number(e.target.value))}>
            {[1, 3, 5, 10, 20, 50].map((n) => (
              <option key={n} value={n}>
                {n} time{n === 1 ? "" : "s"}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="stat-filter-name">Find a card</span>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name or number" />
        </label>
      </div>
      {shown.length === 0 ? (
        <p className="muted">No card matches.</p>
      ) : (
        <ul className="cs-list">
          {shown.slice(0, 120).map((c) => (
            <li key={c.id} className="cs-row">
              <div className="cs-card">
                <CardImage id={c.id} width={64} />
              </div>
              <div className="cs-body">
                <div className="cs-title">
                  <b>{cardName(c.id)}</b> <span className="muted small">{c.id}</span>
                </div>
                <dl className="cs-nums">
                  <div title={`${c.plays} plays by ${c.players} players`}>
                    <dt>Played</dt>
                    <dd>
                      <b>{c.plays}</b> <span className="muted small">time{c.plays === 1 ? "" : "s"}</span>
                    </dd>
                  </div>
                  <div
                    title={
                      c.held === 0
                        ? "Not counted in the games so far"
                        : `Played in ${Math.round((c.playRate ?? 0) * c.held)} of the ${c.held} games in which it was in a hand`
                    }
                  >
                    <dt>Play rate</dt>
                    <dd>
                      <b>{c.playRate === null ? "–" : pct(c.playRate)}</b>
                    </dd>
                  </div>
                  <div
                    title={
                      c.held === 0
                        ? "Not counted in the games so far"
                        : `Discarded for its free corner ${c.discards} times in the ${c.held} games in which it was in a hand`
                    }
                  >
                    <dt>Discard rate</dt>
                    <dd>
                      <b>{c.discardRate === null ? "–" : pct(c.discardRate)}</b>
                    </dd>
                  </div>
                  {CARDS.get(c.id)?.type === "mission" ? (
                    <div title="The share of its plays whose mission was completed (over the games that count it)">
                      <dt>Mission completed</dt>
                      <dd>
                        <b>{c.missionRate === null ? "–" : pct(c.missionRate)}</b>
                      </dd>
                    </div>
                  ) : null}
                  {CARDS.get(c.id)?.type === "end" ? (
                    <div title="The points its end-of-game scoring gave, on average, each time it was played">
                      <dt>Average end-of-game points</dt>
                      <dd>
                        <b>{c.endAvg === null ? "–" : r1(c.endAvg)}</b>
                      </dd>
                    </div>
                  ) : null}
                  <div title={`The final score of the players who played it: ${spreadText(c.scoreSpread)}`}>
                    <dt>Average final score</dt>
                    <dd>
                      <b>{r1(c.avgScore)}</b>
                    </dd>
                  </div>
                  <div title={`${Math.round(c.winRate * c.players)} of ${c.players} players won`}>
                    <dt>Won the game</dt>
                    <dd>
                      <b>{pct(c.winRate)}</b>
                    </dd>
                  </div>
                  <div title="The average round in which it was played">
                    <dt>Average round</dt>
                    <dd>
                      <b>{r1(c.avgRound)}</b>
                    </dd>
                  </div>
                </dl>
                <div
                  className="cs-rounds"
                  role="img"
                  aria-label={`Plays by round: ${roundList.map((r) => `round ${r}: ${c.rounds[r] ?? 0}`).join(", ")}`}
                >
                  {roundList.map((r) => (
                    <span
                      key={r}
                      className="cs-round"
                      title={`Round ${r}: played ${c.rounds[r] ?? 0} time${(c.rounds[r] ?? 0) === 1 ? "" : "s"}`}
                    >
                      <span
                        className="cs-bar"
                        style={{ height: `${Math.max(2, ((c.rounds[r] ?? 0) / Math.max(1, ...Object.values(c.rounds))) * 100)}%` }}
                      />
                      <span className="small muted">R{r}</span>
                    </span>
                  ))}
                </div>
                <div className="cs-orgs small" title={c.orgs.map((o) => `${ORG_NAMES[o.org] ?? o.org}: ${o.n}`).join("\n")}>
                  {c.orgs.length === 0 ? (
                    <span className="muted">No organization</span>
                  ) : (
                    <>
                      {c.orgs.slice(0, 3).map((o) => (
                        <span key={o.org} className="cs-org">
                          {ORG_NAMES[o.org] ?? o.org} <b>{o.n}</b>
                        </span>
                      ))}
                      {c.orgs.length > 3 ? <span className="muted"> and {c.orgs.length - 3} more</span> : null}
                    </>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      {shown.length > 120 ? <p className="muted small">The first 120 of {shown.length} cards are shown: narrow the list down.</p> : null}
    </div>
  );
}
