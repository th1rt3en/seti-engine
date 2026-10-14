"use client";
// The log of the moves made in the game, as a panel floating at the bottom right. It can be folded to a tab; the newest move is at the bottom.
// The server sends every client the same log with the identity of hidden cards left out (apps/worker/src/core/publicLog.ts). A move is one line
// with what it gave and took (the engine's `delta` events) as icons; in the solo game what the rival did after it is a block of its own.
import type { GameEvent } from "@/lib/events";
import { logText } from "@/lib/moves";
import { techName } from "@/lib/techs";
import { useBottomSpace, useDock } from "@/lib/useDock";
import { type ReactNode, useEffect, useRef } from "react";
import assets from "../generated/assets.json";
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
function eventLine(ev: GameEvent, ctx: LogContext): ReactNode {
  const who = typeof ev.player === "number" ? ctx.who(ev.player) : "";
  switch (ev.type) {
    case "signal":
      return `${who} marks a signal in ${ctx.stars[Number(ev.sector)] ?? `sector ${ev.sector}`}`;
    case "signal_tile":
      return `${who} marks a signal on the 'Oumuamua tile`;
    case "trace":
      return `${who} marks a trace (${String(ev.space)} space of ${ctx.species[Number(ev.slot)] ?? "a species"})`;
    case "sector_won":
      return `${who} wins the sector of ${ctx.stars[Number(ev.sector)] ?? `sector ${ev.sector}`}`;
    case "discovered":
      return `${cap(ev.species)} is discovered`;
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
    case "mission_completed":
      return `${who} completes a mission`;
    case "neutral_marker":
      return `a neutral marker blocks a discovery space (${String(ev.milestone)} points)`;
    case "round":
      return `Round ${String(ev.round)} begins`;
    case "rotate":
      return `the solar system rotates (disc ${String(ev.disc)})`;
    case "objectives_spent":
      return `objectives spent: ${String(ev.spent)}${Number(ev.short) > 0 ? `, ${String(ev.short)} short: the rival advances` : ""}`;
    case "game_over":
      return "the game is over";
    default:
      return null;
  }
}

export function MoveLog({ entries, ctx }: { entries: LogEntry[]; ctx: LogContext }) {
  const [folded, toggle] = useDock("log");
  const body = useRef<HTMLOListElement>(null);
  const dock = useRef<HTMLElement>(null);
  useBottomSpace(dock, "log");
  const last = entries.at(-1)?.seq;
  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll to the newest move when one is added
  useEffect(() => {
    const el = body.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [last, folded]);
  return (
    <aside ref={dock} className={folded ? "movelog dock folded" : "movelog dock"} aria-label="Log of the moves">
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>Log ({entries.length})</span>
        <span aria-hidden="true">{folded ? "▴" : "▾"}</span>
      </button>
      {folded ? null : (
        <ol ref={body} className="logbody">
          {entries.length === 0 ? <li className="muted">No move yet.</li> : null}
          {entries.map((e) => {
            const deltas = e.events.filter((ev) => ev.type === "delta") as Delta[];
            const mine = deltas.find((d) => d.player === e.seat);
            const rival = ctx.rival;
            const rivalEvents = e.events.filter((ev) => ev.type.startsWith("rival_"));
            const rivalDelta = rival === null ? undefined : deltas.find((d) => d.player === rival);
            const others = deltas.filter((d) => d.player !== e.seat && d.player !== rival);
            const byRival = (ev: GameEvent): boolean => rival !== null && ev.player === rival;
            const notes = e.events.filter((ev) => !ev.type.startsWith("rival_") && ev.type !== "delta" && !byRival(ev));
            const rivalMore = e.events.filter((ev) => ev.type !== "delta" && !ev.type.startsWith("rival_") && byRival(ev));
            return (
              <li key={e.seq}>
                <span className="lognum">{e.seq + 1}</span>
                <span className="logmove">
                  <b>{ctx.who(e.seat)}</b> {logText(e.action)} {mine ? <Changes changes={mine.changes} size={16} /> : null}
                </span>
                {notes.map((ev) => {
                  const line = eventLine(ev, ctx);
                  return line ? (
                    <span key={JSON.stringify(ev)} className="logevent">
                      {line}
                    </span>
                  ) : null;
                })}
                {others.map((d) => (
                  <span key={`d${d.player}`} className="logevent">
                    {ctx.who(d.player)} <Changes changes={d.changes} size={16} />
                  </span>
                ))}
                {rivalEvents.length > 0 || rivalMore.length > 0 || rivalDelta ? (
                  <span className="logrival">
                    <b className="logrivalhead">Rival's turn</b>
                    {rivalEvents.map((ev) => {
                      const line = rivalLine(ev);
                      return line ? <span key={JSON.stringify(ev)}>{line}</span> : null;
                    })}
                    {rivalMore.map((ev) => {
                      const line = eventLine(ev, ctx);
                      return line ? <span key={`m${JSON.stringify(ev)}`}>{line}</span> : null;
                    })}
                    {rivalDelta ? <Changes changes={rivalDelta.changes} size={16} /> : null}
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
