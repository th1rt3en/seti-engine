"use client";
// The replay of a finished game: step through every action, with the events the engine reported for it, and look at the game as the spectator or as
// any player saw it: the same game page as in play (the board, the player boards, the trackers, the hand, the tech stacks, the card row, the log),
// without the clocks and without moves to make. Every state comes from the engine (/api/replay); nothing is worked out here.
import { type GameEvent, describeEvent } from "@/lib/events";
import { lastMoveOf } from "@/lib/lastMove";
import { describeMove } from "@/lib/moves";
import type { ReplayData } from "@/lib/worker";
import type { View } from "@seti/protocol";
import { useEffect, useState } from "react";
import { GameView } from "./GameView";
import { ScoreIcon } from "./Icons";
import { type LogContext, type LogEntry, MoveLog } from "./MoveLog";
import { PlayerBoardPanel } from "./PlayerBoard";
import { PlayerNumsContext } from "./PlayerName";

const REASONS: Record<string, string> = {
  completed: "The game was played to the end.",
  resigned: "A player resigned.",
  timeout: "A player ran out of time.",
  kicked: "A player was kicked because their clock was in the negative.",
};

export function ReplayViewer({ id, replay }: { id: string; replay: ReplayData }) {
  const names = replay.header.seats.map((s) => s.name);
  const nums = replay.header.seats.map((s) => s.num ?? null);
  const who = (i: number): string => names[i] ?? `Player ${i + 1}`;
  const last = replay.actions.length;
  // a link to one move: #step=12 in the address (the page opens at that step)
  const [step, setStep] = useState(0);
  const [copied, setCopied] = useState(false);
  const [opened, setOpened] = useState(false);
  useEffect(() => {
    const m = /step=(\d+)/.exec(window.location.hash);
    if (m) setStep(Math.min(replay.actions.length, Number(m[1])));
    setOpened(true);
  }, [replay.actions.length]);
  const [viewer, setViewer] = useState("spectator");
  const [view, setView] = useState<View | null>(null);
  // the view of the step before, for what has just changed (the trackers show the difference)
  const [previous, setPrevious] = useState<View | null>(null);
  const [boardOpen, setBoardOpen] = useState(false);
  const [boardPlayer, setBoardPlayer] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setError(null);
    fetch(`/api/replay/${id}?step=${step}&viewer=${viewer}`)
      .then(async (res) => {
        const body = (await res.json()) as { ok: boolean; view?: View; previous?: View | null; message?: string };
        if (!current) return;
        if (body.ok && body.view) {
          setView(body.view);
          setPrevious(body.previous ?? null);
        } else setError(body.message ?? "could not load this step");
      })
      .catch(() => current && setError("could not load this step"));
    return () => {
      current = false;
    };
  }, [id, step, viewer]);

  // the address follows the step, so that it can be shared
  useEffect(() => {
    if (!opened) return;
    try {
      window.history.replaceState(null, "", step === 0 ? window.location.pathname : `#step=${step}`);
    } catch {
      // the address cannot be changed here
    }
  }, [step, opened]);
  // the first step of each round, for the "jump to round" list: a round starts with the move whose events say so
  const roundStarts: { round: number; step: number }[] = [{ round: 1, step: 0 }];
  replay.actions.forEach((a, i) => {
    for (const e of a.events as { type: string; round?: number }[])
      if (e.type === "round" && typeof e.round === "number") roundStarts.push({ round: e.round, step: i + 1 });
  });
  // the arrow keys step through the game
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA")) return;
      if (e.key === "ArrowRight") setStep((s) => Math.min(last, s + 1));
      else if (e.key === "ArrowLeft") setStep((s) => Math.max(0, s - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [last]);
  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${window.location.pathname}#step=${step}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // the address bar has the link
    }
  };

  useEffect(() => {
    if (!playing) return;
    if (step >= last) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => setStep((s) => Math.min(last, s + 1)), 1200);
    return () => clearTimeout(t);
  }, [playing, step, last]);

  const shown = step > 0 ? replay.actions[step - 1] : undefined;
  // the log of the moves made so far, as in play (the same entries the players saw, up to this step)
  const logEntries: LogEntry[] = replay.actions.slice(0, step).map((a) => ({
    seq: a.seq,
    seat: a.seat,
    action: a.action as LogEntry["action"],
    events: a.events as GameEvent[],
  }));
  const logCtx = (v: View): LogContext => ({
    who: (i: number) => (v.state.rival && i === v.state.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`)),
    stars: v.state.sectors.map((sec) => sec.star),
    species: v.state.species.map((sp, i) =>
      sp.discovered ? sp.species.charAt(0).toUpperCase() + sp.species.slice(1) : `Species ${i + 1}`,
    ),
    rival: v.state.rival ? v.state.rival.index : null,
    me: v.viewer,
  });
  const end = replay.result?.result;
  return (
    <PlayerNumsContext.Provider value={nums}>
      <section className="card">
        <div className="moves">
          <button type="button" className="secondary" onClick={() => setStep(0)} disabled={step === 0}>
            Start
          </button>
          <button type="button" className="secondary" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
            Previous
          </button>
          <button type="button" className="secondary" onClick={() => setPlaying(!playing)} disabled={step >= last && !playing}>
            {playing ? "Pause" : "Play"}
          </button>
          <button type="button" className="secondary" onClick={() => setStep(Math.min(last, step + 1))} disabled={step >= last}>
            Next
          </button>
          <button type="button" className="secondary" onClick={() => setStep(last)} disabled={step >= last}>
            End
          </button>
        </div>
        <p>
          <input
            type="range"
            min={0}
            max={last}
            value={step}
            aria-label="Step of the game"
            style={{ width: "100%" }}
            onChange={(e) => {
              setPlaying(false);
              setStep(Number(e.target.value));
            }}
          />
          <span className="small muted">
            Step {step} of {last} ·{" "}
            <select
              value={roundStarts.filter((r) => r.step <= step).at(-1)?.round ?? 1}
              onChange={(e) => {
                setPlaying(false);
                setStep(roundStarts.find((r) => r.round === Number(e.target.value))?.step ?? 0);
              }}
              aria-label="Jump to a round"
            >
              {roundStarts.map((r) => (
                <option key={r.round} value={r.round}>
                  Round {r.round}
                </option>
              ))}
            </select>{" "}
            <button type="button" className="secondary small" onClick={copyLink}>
              {copied ? "Link copied" : "Copy link to this move"}
            </button>{" "}
            · Seen as{" "}
            <select value={viewer} onChange={(e) => setViewer(e.target.value)} aria-label="Seen as">
              <option value="spectator">a spectator</option>
              {names.map((n, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: a seat number is the identity of a player
                <option key={i} value={i}>
                  {n}
                </option>
              ))}
            </select>
          </span>
        </p>
        {shown ? (
          <p>
            <b>{who(shown.seat)}:</b> {describeMove(shown.action as { type: string })}
          </p>
        ) : (
          <p className="muted">The start of the game.</p>
        )}
        {shown && shown.events.length > 0 ? (
          <ul className="small">
            {shown.events.map((e, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: the events of a step have a fixed order
              <li key={i}>{describeEvent(e as GameEvent, who)}</li>
            ))}
          </ul>
        ) : null}
        {step >= last && end ? (
          <p>
            <b>{REASONS[end.reason] ?? end.reason}</b>{" "}
            {end.winners.length > 0 ? `Winner${end.winners.length > 1 ? "s" : ""}: ${end.winners.map(who).join(", ")}. ` : ""}
            {end.ranking.map((r) => (
              <span key={r.seat} className="res">
                {who(r.seat)}: <ScoreIcon size={18} /> <b>{r.score}</b>{" "}
              </span>
            ))}
          </p>
        ) : null}
      </section>
      {error ? <p className="error">{error}</p> : null}
      {view ? (
        <GameView
          view={view}
          names={names}
          previous={previous}
          lastMove={lastMoveOf(shown?.events as never)}
          log={<MoveLog entries={logEntries} ctx={logCtx(view)} />}
          overlay={
            <>
              <button type="button" className="primary boardsfab" onClick={() => setBoardOpen(!boardOpen)} aria-expanded={boardOpen}>
                {boardOpen ? "Close player boards" : "Player boards"}
              </button>
              {boardOpen ? (
                <PlayerBoardPanel
                  view={view}
                  names={names}
                  shown={boardPlayer}
                  onShow={setBoardPlayer}
                  onClose={() => setBoardOpen(false)}
                />
              ) : null}
            </>
          }
          topExtra={
            <span className="small muted">
              Replay · step {step} of {last}
            </span>
          }
        />
      ) : (
        <p className="muted">Loading...</p>
      )}
      <section className="card">
        <h3>All events</h3>
        <ol className="small eventlog">
          {replay.actions.map((a, i) => (
            <li key={a.seq} value={i + 1} className={i + 1 === step ? "current" : undefined}>
              <button type="button" className="link" onClick={() => setStep(i + 1)}>
                {who(a.seat)}: {describeMove(a.action as { type: string })}
              </button>
              {a.events.length > 0 ? (
                <span className="muted"> — {a.events.map((e) => describeEvent(e as GameEvent, who)).join("; ")}</span>
              ) : null}
            </li>
          ))}
        </ol>
      </section>
    </PlayerNumsContext.Provider>
  );
}
