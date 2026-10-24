"use client";
// The log of the moves made in the game, as a panel floating at the bottom right. It can be folded to a tab; the newest move is at the bottom.
// The server sends every client the same log with the identity of hidden cards left out (apps/worker/src/core/publicLog.ts). A move is one line
// with what it gave and took, one line for each source (the engine's `gains` events), as icons; in the solo game what the rival did after it is a block of its own.
import { cardImage } from "@/lib/cardImages";
import type { GameEvent } from "@/lib/events";
import { ORG_NAMES, cardName, logText } from "@/lib/moves";
import { type DecisionSource, sourceLabel } from "@/lib/sources";
import { techName } from "@/lib/techs";
import { useBottomSpace, useDock } from "@/lib/useDock";
import { type ReactNode, type PointerEvent as ReactPointerEvent, useContext, useEffect, useRef, useState } from "react";
import assets from "../generated/assets.json";
import { CardText } from "./CardText";
import { PlayerColorsContext } from "./PlayerName";
import { Changes } from "./Reward";
import { TapZoomImage } from "./TapZoom";

export interface LogEntry {
  seq: number;
  seat: number;
  action: Record<string, unknown> & { type: string };
  events: GameEvent[];
}

/** What the log needs to know about the game to put names to the numbers of the events. */
export interface LogContext {
  who: (seat: number) => string;
  /** The star of each sector, by the number of the sector. */
  stars: string[];
  /** The name of each alien species slot ("Species 1" until it is discovered). */
  species: string[];
  /** The seat of the solo rival, if there is one. */
  rival: number | null;
  /** The seat of the player who looks at the log (null for a spectator). */
  me?: number | null;
  /** After the game: the address of the replay at the step of a move (the number of the move), so that a line of the log opens the board as it was then. */
  replayAt?: (seq: number) => string;
}

type Delta = GameEvent & { player: number; changes: Record<string, number> };

const RIVAL_CARDS = assets.rivalCards as Record<string, string>;
const cap = (s: unknown): string => {
  const t = String(s);
  return t.charAt(0).toUpperCase() + t.slice(1);
};
const techOf = (key: unknown): string => {
  const [category = "", glyph = ""] = String(key).split("-");
  return techName(category, glyph);
};

interface RewardItem {
  t: string;
  n: number;
}
interface AnomalyToken {
  sector: number;
  color: string;
  reward: RewardItem[];
}
const rewardText = (list: RewardItem[]): string =>
  list.map((r) => `${r.n} ${r.t.replace("card_any", "card").replace("vp", "VP")}`).join(" + ");
const sectorName = (ctx: LogContext, sector: number): string => ctx.stars[sector] ?? `sector ${sector}`;

type Source = { kind: string } & Record<string, unknown>;
type Gains = GameEvent & { player: number; source: Source; changes: Record<string, number>; turn?: string };

const MOVE_WORDS: Record<string, string> = {
  launch: "Launch",
  scan: "Scan",
  orbit: "Orbiting",
  land: "Landing",
  analyze: "Analyzing data",
  research: "Researching a tech",
  pass: "Passing",
  exchange: "Exchange",
  discard_free: "Discarding a card",
  place_data: "Placing data",
  tuck: "Tucking a card",
};

/** The name of a player in the log, in the color of the player. */
function Who({ seat, ctx, suffix = "" }: { seat: number; ctx: LogContext; suffix?: string }) {
  const color = useContext(PlayerColorsContext)[seat];
  return <b style={color ? { color } : undefined}>{`${ctx.who(seat)}${suffix}`}</b>;
}

/** The cause of a gain or a loss, as the engine named it (trail.py), in words that say which card, planet, sector, tech ... it was. */
function sourceText(src: Source, ctx: LogContext, action: LogEntry["action"]): string {
  const planet = cap(src.planet);
  switch (src.kind) {
    case "move":
      return MOVE_WORDS[action.type] ?? cap(action.type.replace(/_/g, " "));
    case "card":
      return `Playing ${cardName(src.card)}`;
    case "corner":
      return `Free corner of ${cardName(src.card)}`;
    case "signal":
      return `Signal in ${sectorName(ctx, Number(src.sector))}`;
    case "sector":
      return `Sector ${sectorName(ctx, Number(src.sector))} completed`;
    case "mission":
      return `Mission ${cardName(src.card)}`;
    case "anomaly":
      return `Earth reaches the ${String(src.color)} anomaly in ${sectorName(ctx, Number(src.sector))}`;
    case "planet":
      switch (src.what) {
        case "first_orbit":
          return `First orbiter of ${planet}`;
        case "orbit":
          return `Orbiting ${planet}`;
        case "first_land":
          return `First lander's data at ${planet}`;
        case "land":
          return `Landing on ${planet}`;
        case "moon":
          return `Landing on ${String(src.moon)} (${planet})`;
        default:
          return planet;
      }
    case "tech":
      return src.what === "first" ? `First to take ${techOf(src.tech)}` : `Tech ${techOf(src.tech)}`;
    case "trace": {
      const species = ctx.species[Number(src.slot)] ?? "a species";
      return `${cap(src.color)} trace on ${species}`;
    }
    case "glyph":
      return src.what === "decipher" ? `Placing the ${String(src.glyph)} glyph` : `The ${String(src.glyph)} glyph (icon of a card)`;
    case "explore":
      return `Exploration card ${String(src.card)} (${String(src.level)} reward)`;
    case "income":
      return "Income of the round";
    case "organization":
      return `Organization ${ORG_NAMES[String(src.org)] ?? String(src.org)}${src.what === "mission" ? " (a card with a mission is played)" : ""}`;
    case "rival_computer":
      return `The rival's computer, space ${String(src.space)}`;
    case "quick_start":
      return `Quick start card ${String(src.card)}`;
    case "rival_turn":
      return "The rival's turn";
    case "alien":
      return src.what === "card" && src.card !== undefined ? `Message card ${cardName(src.card)}` : cap(src.kind);
    default:
      return cap(src.kind.replace(/_/g, " "));
  }
}

/** What the rival did, one event at a time. */
function rivalLine(ev: GameEvent): ReactNode {
  switch (ev.type) {
    case "rival_card":
      return (
        <span className="rivalplay">
          plays action card <b>{String(ev.card)}</b>
          {RIVAL_CARDS[String(ev.card)] ? (
            <TapZoomImage src={RIVAL_CARDS[String(ev.card)] as string} alt="" width={44} height={49} className="logcard" />
          ) : null}
        </span>
      );
    case "rival_message":
      return `places a message marker on the scoring track at ${String(ev.target)} points`;
    case "rival_exertian":
      return "plays an Exertian card face down";
    case "rival_launch":
      return "launches a probe";
    case "rival_telescope":
      return "uses its telescope";
    case "rival_tech":
      return `takes the tech ${techOf(ev.tech)}`;
    case "rival_orbit":
      return `orbits ${cap(ev.planet)}`;
    case "rival_land":
      return ev.moon ? `lands on ${String(ev.moon)} (${cap(ev.planet)})` : `lands on ${cap(ev.planet)}`;
    case "rival_analyze":
      return "analyzes data";
    case "rival_pass":
      return "passes";
    case "rival_gold":
      return `marks the ${String(ev.tile)} gold scoring tile`;
    case "rival_grows":
      return "gets an advanced action card in its deck";
    default:
      return null;
  }
}

/** The events of a move that say something the move itself does not (signals, traces, wins, rounds). */
function eventLine(ev: GameEvent, ctx: LogContext, action?: LogEntry["action"]): ReactNode {
  const who = typeof ev.player === "number" ? ctx.who(ev.player) : "";
  switch (ev.type) {
    case "launch": {
      // the Launch action and the actions of an organization say so themselves; any other launch is a free one, and the line says what gave it
      if (action?.type === "launch" || action?.type === "org_main" || action?.type === "scan_probe") return null;
      const by =
        action?.type === "play_card"
          ? ` (${cardName(action.card)})`
          : action?.type === "choose_org"
            ? ` (${ORG_NAMES[String(action.org)] ?? "organization"})`
            : action?.type === "setup_lock"
              ? " (organization)" // everybody's choice is made public with the last lock (EXP-ORG-14)
              : "";
      return `${who} launches a probe for free${by}`;
    }
    case "explore": {
      const pic = cardImage(String(ev.card));
      return (
        <>
          {who} reveals an exploration card and takes its {String(ev.level)} reward
          {pic ? <TapZoomImage src={pic} alt={`Exploration card ${String(ev.card)}`} width={44} height={31} className="logcard" /> : null}
        </>
      );
    }
    case "setup_done": {
      const names = (ids: unknown): string => (Array.isArray(ids) ? ids.map((c) => cardName(c)).join(", ") : "");
      const parts = [
        ev.organization ? `organization ${ORG_NAMES[String(ev.organization)] ?? String(ev.organization)}` : "",
        Array.isArray(ev.quick_start) && ev.quick_start.length > 0 ? `quick start cards ${names(ev.quick_start)}` : "",
        Array.isArray(ev.tucks) && ev.tucks.length > 0 ? `tucked ${names(ev.tucks)} for income` : "",
      ].filter((x) => x !== "");
      return `${who} is set up: ${parts.join("; ")}`;
    }
    case "organelle_skipped":
      return `${who} has no ${String(ev.color)} organelle to trigger`;
    case "draw_card":
      // the player who drew it sees the card; the others (and the spectators) are only told that a card was drawn
      return ev.card ? `${who} draws ${cardName(ev.card)}` : `${who} draws a card from the deck`;
    case "play_card":
      // the prepared card of Futurespan Institute is played from where it lay face down: the log names it now
      return action?.type === "org_main" && ev.card
        ? `${who} plays the prepared card ${cardName(ev.card)} for free (Futurespan Institute)`
        : null;
    case "research_none": {
      const kind =
        { probe: "orange", telescope: "pink", computer: "blue", any: "", probe_telescope: "orange or pink" }[String(ev.cat)] ?? "";
      const what = kind ? `a ${kind} tech` : "a tech";
      const why =
        ev.reason === "owned"
          ? "they already have every tech of that type"
          : ev.reason === "empty"
            ? "the stacks of the techs they are missing are empty"
            : "no other player has a tech they are missing";
      return `${who} cannot take ${what}: ${why}`;
    }
    case "glyph": {
      // a Glyphids token taken from the place it lay at: a planet, a sector that was won, a tech stack or a well of the Glyphids board
      const [kind = "", first = "", second = ""] = String(ev.where).split(":");
      const from =
        kind === "planet"
          ? `the space of ${cap(first)}`
          : kind === "sector"
            ? `the space of the ${String(ev.star ?? sectorName(ctx, Number(first)))} sector`
            : kind === "tech"
              ? `the space of the tech ${String(ev.tech ?? "stack")}`
              : kind === "board"
                ? `the ${first} well of the Glyphids board${Number(second) === 0 ? "" : ` (space ${Number(second) + 1})`}`
                : "the board";
      return `${who} takes the ${String(ev.glyph)} glyph token from ${from}`;
    }
    case "exertian_loss":
      return `${who} has the most danger (${String(ev.danger)}) and loses a tenth of their ${String(ev.before)} points: -${String(ev.loss)}`;
    case "endgame_card":
      return `${who}: end-of-game scoring card ${cardName(ev.card)}: +${String(ev.points)} points`;
    case "endgame_gold": {
      const info = (assets.gold as Record<string, { per: string }>)[`${String(ev.tile)}-${String(ev.side)}`];
      return `${who}: gold scoring tile ${String(ev.tile)}${info ? ` (${info.per})` : ""}: ${String(ev.sets)} × ${String(ev.per)} = +${String(ev.points)} points`;
    }
    case "take_display_card":
      return `${who} takes ${cardName(ev.card)} from the display`;
    case "breach":
      return `${who} breaches their ${String(ev.color)} security card (it goes to their hand)`;
    case "land":
    case "orbit": {
      if (ev.free !== true) return null; // a landing or an orbit of the main action is the move itself
      const cause = sourceLabel(ev.source as DecisionSource | undefined, ctx.stars, ctx.species);
      const where = ev.moon ? `${cap(ev.moon)} (${cap(ev.planet)})` : cap(ev.planet);
      return `${who} ${ev.type === "land" ? "lands a probe on" : "orbits"} ${where} for free${cause ? ` (${cause})` : ""}`;
    }
    case "capped": {
      // RES-01, RES-02: a gain that did not fit
      const kind = String(ev.kind);
      const cause = ev.source ? sourceText(ev.source as Source, ctx, action as LogEntry["action"]) : "";
      return `${who} can't gain ${String(ev.n)} ${kind} because already at the maximum (${kind === "data" ? "6 in the pool" : "10"})${cause ? `: ${cause}` : ""}`;
    }
    case "signal":
      return `${who} marks a signal in ${ctx.stars[Number(ev.sector)] ?? `sector ${ev.sector}`}`;
    case "glyph_resource":
      return (ev.reward as RewardItem[]).length > 0
        ? `${who}: the ${String(ev.glyph)} glyph is deciphered and gives ${rewardText(ev.reward as RewardItem[])}`
        : `${who}: the ${String(ev.glyph)} glyph has not been deciphered yet, so its icon has no effect`;
    case "signal_tile":
      return `${who} marks a signal on the 'Oumuamua tile`;
    case "trace":
      return `${who} marks a trace (${String(ev.space)} space of ${ctx.species[Number(ev.slot)] ?? "a species"})`;
    case "sector_won":
      return `${who} wins the sector of ${ctx.stars[Number(ev.sector)] ?? `sector ${ev.sector}`}`;
    case "discovered":
      return `${cap(ev.species)} is discovered`;
    case "pluto":
      return `${who} plays Not a planet since 2006: Pluto can now be orbited or landed on by them (outermost ring)`;
    case "anomalies_placed":
      return `anomaly tokens placed: ${(ev.tokens as AnomalyToken[]).map((k) => `${cap(k.color)} in ${sectorName(ctx, k.sector)} (${rewardText(k.reward)})`).join("; ")}`;
    case "messages_placed":
      return `message milestones placed: ${(ev.targets as { player: number; target: number }[]).map((k) => `${ctx.who(k.player)} at ${k.target}`).join(", ")}`;
    case "message_reached":
      return `${who} reaches their message milestone (${String(ev.target)})`;
    case "message_reward":
      return `${who} covers a message reward and gains ${rewardText(ev.reward as RewardItem[])}`;
    case "message_card_placed":
      return `${who} places a message marker at ${String(ev.target)} (${String(ev.card)})`;
    case "message_resolved":
      return `${who} reaches the message marker of ${String(ev.card)} (${String(ev.target)}) and resolves it`;
    case "exertian_milestones":
      return `Exertian milestones placed at ${(ev.milestones as { at: number; cost: number }[]).map((m) => `${m.at} (${m.cost > 0 ? `${m.cost} credit` : "free"})`).join(" and ")}, ahead of the leader (${String(ev.leader_score)})`;
    case "samples_placed":
      return `Mascamite samples placed: ${Object.entries(ev.planets as Record<string, number>)
        .map(([planet, n]) => `${n} face down on ${cap(planet)}`)
        .join(", ")}; one lies face up on the species board (${rewardText((ev.face_up as { reward: RewardItem[] }).reward)})`;
    case "sample_collected":
      return `${who} collects a sample on ${cap(ev.planet)} (it stays hidden under their capsule)`;
    case "sample_delivered":
      return `${who} delivers a sample: ${rewardText(ev.reward as RewardItem[])}${Number(ev.times) > 1 ? " (twice)" : ""}; the token lies on sample space ${Number(ev.space) + 1}`;
    case "sample_space_marked":
      return `${who} marks sample space ${Number(ev.space) + 1} and gains ${rewardText(ev.reward as RewardItem[])}`;
    case "anomaly":
      return `Earth reaches the ${String(ev.color)} anomaly in ${sectorName(ctx, Number(ev.sector))}: ${
        typeof ev.player === "number"
          ? `${ctx.who(ev.player)} (highest ${String(ev.color)} trace) gains ${rewardText(ev.reward as RewardItem[])}`
          : "nobody has a trace there, no reward"
      }`;
    case "tech":
      return `${who} takes the tech ${techOf(ev.tech)}`;
    case "show_card":
      return `${who} shows ${cardName(ev.card)} from their hand`;
    case "mission_completed":
      return `${who} completes a mission`;
    case "neutral_marker":
      return `a neutral marker blocks a discovery space (${String(ev.milestone)} points)`;
    case "round":
      return `Round ${String(ev.round)} begins`;
    case "rotate":
      return `the solar system rotates (disc ${String(ev.disc)})`;
    case "objectives_uncompleted":
      // SOLO-OBJ-07: at the end of round 5 the rival scores 5 points for each objective that was not completed
      return `${String(ev.count)} objective${Number(ev.count) === 1 ? " is" : "s are"} not completed: the rival scores 5 points for each (${Number(ev.count) * 5})`;
    case "long_term_penalty":
      return `${String(ev.tasks)} task${Number(ev.tasks) === 1 ? "" : "s"} of the long-term objectives not done: the rival advances ${String(ev.tasks)}`;

    case "objectives_spent":
      return `objectives spent: ${String(ev.spent)}${Number(ev.short) > 0 ? `, ${String(ev.short)} short: the rival advances` : ""}`;
    case "game_over":
      return "the game is over";
    default:
      return null;
  }
}

/** The lines of the events of a move; the same line twice in a row (two signals in one sector) is one line with a count. */
function noteLines(notes: GameEvent[], ctx: LogContext, action: LogEntry["action"]): { text: ReactNode; count: number }[] {
  const out: { text: ReactNode; count: number }[] = [];
  for (const ev of notes) {
    const text = eventLine(ev, ctx, action);
    if (!text) continue;
    const last = out.at(-1);
    if (last && typeof text === "string" && last.text === text) last.count += 1;
    else out.push({ text, count: 1 });
  }
  return out;
}

type LogFilter = "all" | "mine" | "opponents" | "rival" | "gains";
const FILTERS: [LogFilter, string][] = [
  ["all", "All moves"],
  ["mine", "Mine"],
  ["opponents", "Opponents"],
  ["rival", "The rival"],
  ["gains", "With gains"],
];

/** An entry of the log as plain lines of text, for the search, the copy and the download. */
export function plainEntry(e: LogEntry, ctx: LogContext): string[] {
  const lines = [`${e.seq + 1}. ${ctx.who(e.seat)} ${logText(e.action)}`];
  for (const ev of e.events) {
    if (ev.type === "gains") {
      const g = ev as unknown as Gains;
      const what = Object.entries(g.changes)
        .map(([k, n]) => `${n > 0 ? "+" : ""}${n} ${k}`)
        .join(", ");
      lines.push(`   ${g.player !== e.seat ? `${ctx.who(g.player)}: ` : ""}${sourceText(g.source, ctx, e.action)}: ${what}`);
      continue;
    }
    if (ev.type === "delta" || ev.type.startsWith("rival_")) {
      if (ev.type.startsWith("rival_"))
        lines.push(`   Rival: ${ev.type.replace("rival_", "").replace(/_/g, " ")}${ev.card ? ` ${String(ev.card)}` : ""}`);
      continue;
    }
    const text = eventLine(ev, ctx, e.action);
    if (typeof text === "string") lines.push(`   ${text}`);
  }
  return lines;
}

function matches(e: LogEntry, filter: LogFilter, ctx: LogContext): boolean {
  const me = ctx.me ?? null;
  if (filter === "mine") return me !== null && e.seat === me;
  if (filter === "opponents") return e.seat !== me && e.seat !== ctx.rival;
  if (filter === "rival") return e.seat === ctx.rival || e.events.some((ev) => ev.type.startsWith("rival_"));
  if (filter === "gains") return e.events.some((ev) => ev.type === "gains" || ev.type === "delta");
  return true;
}

const LEGEND: [string, string][] = [
  ["vp", "victory points"],
  ["credit", "credits"],
  ["energy", "energy"],
  ["publicity", "publicity"],
  ["data", "data"],
  ["card", "cards (a card to the hand)"],
  ["move", "movement"],
];

export function MoveLog({ entries: all, ctx }: { entries: LogEntry[]; ctx: LogContext }) {
  // the choices of the setup that the server keeps from the others (and that were possibly taken back) are not lines of the log
  const entries = all.filter((e) => e.action?.type !== "setup_hidden");
  const [folded, toggle] = useDock("log");
  const body = useRef<HTMLOListElement>(null);
  const dock = useRef<HTMLElement>(null);
  useBottomSpace(dock, "log");
  // on a desktop the log is made taller or shorter by dragging its top edge; the height is remembered
  const [height, setHeight] = useState<number | null>(null);
  useEffect(() => {
    try {
      const saved = Number(localStorage.getItem("seti.logHeight"));
      if (saved >= 120 && window.matchMedia("(min-width: 761px)").matches) setHeight(saved); // not on a phone
    } catch {
      // storage is not available: the log keeps its usual height
    }
  }, []);
  const startResize = (e: ReactPointerEvent<HTMLDivElement>) => {
    const startY = e.clientY;
    const startH = body.current?.getBoundingClientRect().height ?? 300;
    const move = (m: PointerEvent) => setHeight(Math.max(120, Math.min(window.innerHeight - 140, startH + startY - m.clientY)));
    const stop = (m: PointerEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      try {
        localStorage.setItem(
          "seti.logHeight",
          String(Math.round(Math.max(120, Math.min(window.innerHeight - 140, startH + startY - m.clientY)))),
        );
      } catch {
        // not remembered
      }
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
    e.preventDefault();
  };
  const [filter, setFilter] = useState<LogFilter>("all");
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const shown = entries.filter((e) => matches(e, filter, ctx) && (q === "" || plainEntry(e, ctx).join(" ").toLowerCase().includes(q)));
  const asText = (): string => entries.flatMap((e) => plainEntry(e, ctx)).join("\n");
  const [note, setNote] = useState("");
  const say = (t: string) => {
    setNote(t);
    setTimeout(() => setNote(""), 1800);
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(asText());
      say("Copied");
    } catch {
      say("Could not copy: use Download");
    }
  };
  const download = () => {
    const url = URL.createObjectURL(new Blob([asText()], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "seti-game-log.txt";
    a.click();
    URL.revokeObjectURL(url);
  };
  const last = entries.at(-1)?.seq;
  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll to the newest move when one is added
  useEffect(() => {
    const el = body.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [last, folded]);
  return (
    <aside ref={dock} className={folded ? "movelog dock folded" : "movelog dock"} aria-label="Log of the moves">
      {folded ? null : <div className="loggrip" aria-hidden="true" title="Drag to resize the log" onPointerDown={startResize} />}
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>Log ({entries.length})</span>
        <span aria-hidden="true">{folded ? "▴" : "▾"}</span>
      </button>
      {folded ? null : (
        <div className="logtools">
          <select value={filter} onChange={(e) => setFilter(e.target.value as LogFilter)} aria-label="Show these moves">
            {FILTERS.filter(([k]) => k !== "rival" || ctx.rival !== null).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </select>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the log"
            aria-label="Search the log"
          />
          <button type="button" className="secondary small" onClick={copy}>
            Copy
          </button>
          <button type="button" className="secondary small" onClick={download}>
            Download
          </button>
          {note ? <span className="muted small">{note}</span> : null}
          <details className="loglegend">
            <summary>Legend</summary>
            <ul>
              {LEGEND.map(([kind, word]) => (
                <li key={kind}>
                  <Changes changes={{ [kind]: 1 }} size={16} /> {word}
                </li>
              ))}
              <li>
                <b>Name:</b> + or − before an amount is what the player gained or lost; the name before it says what caused it (a card, a
                planet, a sector, a tech).
              </li>
              <li>
                <b>(×2)</b> the same line twice in a row. <b>Rival's turn</b> the moves of the solo rival after the player's move.
              </li>
            </ul>
          </details>
        </div>
      )}
      {folded ? null : (
        <ol ref={body} className="logbody" style={height === null ? undefined : { maxHeight: `${height}px`, height: `${height}px` }}>
          {entries.length === 0 ? <li className="muted">No move yet.</li> : null}
          {entries.length > 0 && shown.length === 0 ? <li className="muted">No move matches.</li> : null}
          {shown.map((e) => {
            const deltas = e.events.filter((ev) => ev.type === "delta") as Delta[];
            // newer entries list each gain or loss under its source; older ones only have the net change of the move
            // a card drawn from the deck has its own line ("draws ..."): it is taken out of the count of the gains
            const drawn = new Map<number, number>();
            for (const ev of e.events) if (ev.type === "draw_card") drawn.set(Number(ev.player), (drawn.get(Number(ev.player)) ?? 0) + 1);
            const rawGains = e.events.filter((ev) => ev.type === "gains") as Gains[];
            const gains = rawGains
              .map((g) => {
                const left = drawn.get(g.player) ?? 0;
                const cards = g.changes.card ?? 0;
                if (left <= 0 || cards <= 0) return g;
                const take = Math.min(left, cards);
                drawn.set(g.player, left - take);
                const { card: _cards, ...rest } = g.changes;
                return { ...g, changes: cards - take > 0 ? { ...rest, card: cards - take } : rest };
              })
              .filter((g) => Object.keys(g.changes).length > 0);
            const itemised = rawGains.length > 0;
            const ownGains = gains.filter((g) => g.source.kind !== "rival_turn" && !(ctx.rival !== null && g.player === ctx.rival));
            const rivalGains = gains.filter((g) => ctx.rival !== null && g.player === ctx.rival);
            const mine = deltas.find((d) => d.player === e.seat);
            const rival = ctx.rival;
            const rivalDelta = rival === null ? undefined : deltas.find((d) => d.player === rival);
            const others = deltas.filter((d) => d.player !== e.seat && d.player !== rival);
            const byRival = (ev: GameEvent): boolean => rival !== null && ev.player === rival;
            // the move can end the round (the last player to pass): what follows it, the income and the turns of the new round, comes after a line
            // that says so, in the order it happened
            const roundAt = e.events.findIndex((ev) => ev.type === "round");
            const newRound = roundAt >= 0 ? Number(e.events[roundAt]?.round) : null;
            const notes = e.events.filter(
              (ev) => !ev.type.startsWith("rival_") && ev.type !== "delta" && ev.type !== "round" && !byRival(ev),
            );
            // the rival can take several turns in one move (when the player has passed it plays on until it passes too): one block for each,
            // starting at the card it plays or at its pass, with what it caused (signals, wins) in the order the engine reported it
            const turns: GameEvent[][] = [];
            const turnAt: number[] = []; // the place in the events where each turn starts
            e.events.forEach((ev, at) => {
              if (ev.type === "rival_card" || ev.type === "rival_pass") {
                turns.push([ev]);
                turnAt.push(at);
              } else if (turns.length > 0 && ev.type !== "delta" && (ev.type.startsWith("rival_") || byRival(ev)))
                turns[turns.length - 1]?.push(ev);
            });
            // what the engine calls the turn of a card in a move: the card and how many cards the rival played before it in the move
            const turnId = (n: number): string =>
              `${String(turns[n]?.[0]?.card)}:${turns.slice(0, n).filter((t) => t[0]?.type === "rival_card").length}`;
            const after = (n: number): boolean => roundAt >= 0 && (turnAt[n] ?? 0) > roundAt;
            const roundOf = (n: number): number | null => (newRound === null ? null : after(n) ? newRound : newRound - 1);
            const income = (g: Gains): boolean => g.source.kind === "income";
            const renderTurn = (turn: GameEvent[], n: number) => (
              <span key={`rt${n}`} className="logrival">
                <b className="logrivalhead">
                  {turns.length > 1 ? `Rival's turn ${n + 1} of ${turns.length}` : "Rival's turn"}
                  {roundOf(n) !== null ? ` (round ${roundOf(n)})` : ""}
                </b>
                {turn.map((ev, k) => {
                  const line = ev.type.startsWith("rival_") ? rivalLine(ev) : eventLine(ev, ctx, e.action);
                  // biome-ignore lint/suspicious/noArrayIndexKey: events of a turn are never reordered
                  return line ? <span key={k}>{line}</span> : null;
                })}
                {rivalGains
                  .filter((g) => (g.turn !== undefined ? g.turn === turnId(n) : n === turns.length - 1))
                  .map((g) => (
                    <span key={`rg${n}-${JSON.stringify(g.source)}`} className="logsource">
                      {g.source.kind === "rival_turn" ? "Gains" : <CardText text={`${sourceText(g.source, ctx, e.action)}:`} />}{" "}
                      <Changes changes={g.changes} size={16} />
                    </span>
                  ))}
                {!itemised && n === turns.length - 1 && rivalDelta ? <Changes changes={rivalDelta.changes} size={16} /> : null}
              </span>
            );
            return (
              <li key={e.seq}>
                <span className="lognum">
                  {ctx.replayAt ? (
                    <a href={ctx.replayAt(e.seq + 1)} target="_blank" rel="noreferrer" title="See the board after this move (replay)">
                      {e.seq + 1}
                    </a>
                  ) : (
                    e.seq + 1
                  )}
                </span>
                <span className="logmove">
                  <Who seat={e.seat} ctx={ctx} /> <CardText text={logText(e.action)} />{" "}
                  {mine && !itemised ? <Changes changes={mine.changes} size={16} /> : null}
                </span>
                {noteLines(notes, ctx, e.action).map((line, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: the same line can come twice in a row (two signals in the same sector)
                  <span key={i} className="logevent">
                    {typeof line.text === "string" ? <CardText text={line.text} /> : line.text}
                    {line.count > 1 ? ` (×${line.count})` : ""}
                  </span>
                ))}
                {ownGains
                  .filter((g) => !(roundAt >= 0 && income(g)))
                  .map((g) => (
                    <span key={`g${g.player}-${JSON.stringify(g.source)}`} className="logevent logsource">
                      {g.player !== e.seat ? <Who seat={g.player} ctx={ctx} suffix=": " /> : null}
                      <CardText text={`${sourceText(g.source, ctx, e.action)}:`} /> <Changes changes={g.changes} size={16} />
                    </span>
                  ))}
                {itemised
                  ? null
                  : others.map((d) => (
                      <span key={`d${d.player}`} className="logevent">
                        {ctx.who(d.player)} <Changes changes={d.changes} size={16} />
                      </span>
                    ))}
                {turns.map((turn, n) => (after(n) ? null : renderTurn(turn, n)))}
                {roundAt >= 0 ? (
                  <span className="logevent logroundbegin">
                    <b>Round {newRound} begins</b>
                  </span>
                ) : null}
                {roundAt >= 0
                  ? ownGains.filter(income).map((g) => (
                      <span key={`gi${g.player}-${JSON.stringify(g.source)}`} className="logevent logsource">
                        {g.player !== e.seat ? <Who seat={g.player} ctx={ctx} suffix=": " /> : null}
                        <CardText text={`${sourceText(g.source, ctx, e.action)}:`} /> <Changes changes={g.changes} size={16} />
                      </span>
                    ))
                  : null}
                {turns.map((turn, n) => (after(n) ? renderTurn(turn, n) : null))}
                {turns.length === 0 && !itemised && rivalDelta ? (
                  <span className="logrival">
                    <b className="logrivalhead">Rival's turn</b>
                    <Changes changes={rivalDelta.changes} size={16} />
                  </span>
                ) : null}
              </li>
            );
          })}
        </ol>
      )}
    </aside>
  );
}
