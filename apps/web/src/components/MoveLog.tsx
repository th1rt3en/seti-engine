"use client";
// The log of the moves made in the game, as a panel floating at the bottom right. It can be folded to a tab; the newest move is at the bottom.
// The server sends every client the same log with the identity of hidden cards left out (apps/worker/src/core/publicLog.ts).
import { type GameEvent, describeEvent } from "@/lib/events";
import { logText } from "@/lib/moves";
import { useEffect, useRef, useState } from "react";

export interface LogEntry {
  seq: number;
  seat: number;
  action: Record<string, unknown> & { type: string };
  events: GameEvent[];
}

const KEY = "seti-log-folded";
/** The events worth a line of their own besides the move: what the rival did and what the game did by itself. */
const NOTABLE = new Set(["round", "rotate", "sector_won", "mission_completed", "game_over", "objectives_spent", "neutral_marker"]);

export function MoveLog({ entries, who }: { entries: LogEntry[]; who: (seat: number) => string }) {
  const [folded, setFolded] = useState(false);
  useEffect(() => {
    try {
      setFolded(localStorage.getItem(KEY) === "1");
    } catch {
      // the browser does not keep it: the log starts open
    }
  }, []);
  const toggle = () => {
    const next = !folded;
    setFolded(next);
    try {
      localStorage.setItem(KEY, next ? "1" : "0");
    } catch {
      // not remembered
    }
  };
  const body = useRef<HTMLOListElement>(null);
  const last = entries.at(-1)?.seq;
  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll to the newest move when one is added
  useEffect(() => {
    const el = body.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [last, folded]);
  return (
    <aside className={folded ? "movelog folded" : "movelog"} aria-label="Log of the moves">
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>Log ({entries.length})</span>
        <span aria-hidden="true">{folded ? "▴" : "▾"}</span>
      </button>
      {folded ? null : (
        <ol ref={body} className="logbody">
          {entries.length === 0 ? <li className="muted">No move yet.</li> : null}
          {entries.map((e) => (
            <li key={e.seq}>
              <span className="lognum">{e.seq + 1}</span>
              <span className="logmove">
                <b>{who(e.seat)}</b> {logText(e.action)}
              </span>
              {e.events
                .filter((ev) => ev.type.startsWith("rival_") || NOTABLE.has(ev.type))
                .map((ev, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: the events of one move come in a fixed order
                  <span key={i} className="logevent">
                    {describeEvent(ev, who)}
                  </span>
                ))}
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}
