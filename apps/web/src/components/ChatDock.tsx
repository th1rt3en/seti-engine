"use client";
// The chat of the table, a panel like the log and to the left of it: the lines come top down in the order they were said, the newest at the bottom, and
// the box to write in is under them. Everybody who is signed in can write (a spectator too); somebody who is not signed in reads. The room keeps the last 100
// lines, so the chat is the same after a refresh and on another device. The text is shown as text, never as HTML.
import { PLAYER_COLOR } from "@/lib/geometry";
import { useBottomSpace, useDock } from "@/lib/useDock";
import { type FormEvent, type PointerEvent as ReactPointerEvent, useEffect, useRef, useState } from "react";
import { PlayerLink } from "./PlayerLink";

export interface ChatLine {
  n: number;
  name: string;
  seat: number | null;
  num?: number;
  text: string;
  at: number;
}

const HEIGHT_KEY = "seti.chatHeight";
const MAX_CHARS = 300;

const clock = (ms: number): string => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

export function ChatDock({
  lines,
  colors,
  mySeat,
  canWrite,
  note,
  onSend,
}: {
  lines: ChatLine[];
  /** The color of each seat, to put a dot before the name of a player. */
  colors: string[];
  mySeat: number | null;
  /** Signed in: a guest too. */
  canWrite: boolean;
  /** What the server said about the last line that was refused (too fast ...). */
  note: string | null;
  onSend: (text: string) => void;
}) {
  const [folded, toggle] = useDock("chat", () => true);
  const body = useRef<HTMLOListElement>(null);
  const dock = useRef<HTMLElement>(null);
  useBottomSpace(dock, "chat");
  const [text, setText] = useState("");
  // the height is dragged like the one of the log, and kept in this browser
  const [height, setHeight] = useState<number | null>(null);
  useEffect(() => {
    try {
      const saved = Number(localStorage.getItem(HEIGHT_KEY));
      if (saved >= 120 && window.matchMedia("(min-width: 761px)").matches) setHeight(saved);
    } catch {
      // storage is not available: the chat keeps its usual height
    }
  }, []);
  const startResize = (e: ReactPointerEvent<HTMLDivElement>) => {
    const startY = e.clientY;
    const startH = body.current?.getBoundingClientRect().height ?? 260;
    const next = (y: number): number => Math.max(120, Math.min(window.innerHeight - 160, startH + startY - y));
    const move = (m: PointerEvent) => setHeight(next(m.clientY));
    const stop = (m: PointerEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      try {
        localStorage.setItem(HEIGHT_KEY, String(Math.round(next(m.clientY))));
      } catch {
        // not remembered
      }
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
    e.preventDefault();
  };
  // the newest line is in view; while the panel is folded the lines that came are counted on its tab
  const last = lines.at(-1)?.n ?? 0;
  // the lines that were there on connecting (the history) are not new: the first lines that come, or two seconds without any, set the mark
  const seen = useRef<number | null>(null);
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (seen.current === null) seen.current = 0;
    }, 2000);
    return () => window.clearTimeout(t);
  }, []);
  // biome-ignore lint/correctness/useExhaustiveDependencies: on every new line, and when the panel opens or closes
  useEffect(() => {
    const el = body.current;
    if (seen.current === null && last > 0) seen.current = last;
    if (!folded) {
      if (el) el.scrollTop = el.scrollHeight;
      seen.current = last;
      setUnread(0);
    } else setUnread(lines.filter((l) => l.n > (seen.current ?? 0)).length);
  }, [last, folded]);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (t === "") return;
    onSend(t);
    setText("");
  };
  return (
    <aside ref={dock} className={folded ? "chatdock dock folded" : "chatdock dock"} aria-label="Chat of the table">
      {folded ? null : <div className="loggrip" aria-hidden="true" title="Drag to resize the chat" onPointerDown={startResize} />}
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>
          Chat{lines.length > 0 ? ` (${lines.length})` : ""}
          {unread > 0 ? (
            <b className="chatunread" title={`${unread} new messages`}>
              {unread > 9 ? "9+" : unread}
            </b>
          ) : null}
        </span>
        <span aria-hidden="true">{folded ? "▴" : "▾"}</span>
      </button>
      {folded ? null : (
        <>
          <ol className="chatbody" ref={body} style={height === null ? undefined : { height, maxHeight: "none" }} aria-live="polite">
            {lines.length === 0 ? <li className="muted">Nobody has said anything yet.</li> : null}
            {lines.map((l) => (
              <li key={l.n} className={l.seat !== null && l.seat === mySeat ? "chatline mine" : "chatline"}>
                <span className="chattime muted small">{clock(l.at)}</span>{" "}
                {l.seat !== null ? <span className="dot" style={{ background: PLAYER_COLOR[colors[l.seat] ?? ""] ?? "#fff" }} /> : null}
                <b className="chatname" style={l.seat !== null ? { color: PLAYER_COLOR[colors[l.seat] ?? ""] } : undefined}>
                  <PlayerLink num={l.num} name={l.name} />
                </b>
                {l.seat === null ? <span className="muted small"> (watching)</span> : null}
                <span className="chattext">{l.text}</span>
              </li>
            ))}
          </ol>
          {canWrite ? (
            <form className="chatform" onSubmit={submit}>
              <input
                type="text"
                value={text}
                maxLength={MAX_CHARS}
                onChange={(e) => setText(e.target.value)}
                placeholder="Say something to the table"
                aria-label="Write to the table"
                autoComplete="off"
              />
              <button type="submit" className="primary small" disabled={text.trim() === ""}>
                Send
              </button>
            </form>
          ) : (
            <p className="muted small chatnote">Sign in (or play as a guest) to write in the chat.</p>
          )}
          {note ? <p className="error small chatnote">{note}</p> : null}
        </>
      )}
    </aside>
  );
}
