"use client";
// The replay of a finished game: step through every action, with the events the engine reported for it, and look at the board
// as the spectator or as any player saw it. Every state comes from the engine (/api/replay); nothing is worked out here.
import { type GameEvent, describeEvent } from "@/lib/events";
import { describeMove } from "@/lib/moves";
import type { ReplayData } from "@/lib/worker";
import type { View } from "@seti/protocol";
import { useEffect, useState } from "react";
import { StateView } from "./StateView";

const REASONS: Record<string, string> = {
  completed: "The game was played to the end.",
  resigned: "A player resigned.",
  timeout: "A player ran out of time.",
  kicked: "A player was kicked because their clock was in the negative.",
};

export function ReplayViewer({ id, replay }: { id: string; replay: ReplayData }) {
  const names = replay.header.seats.map((s) => s.name);
  const who = (i: number): string => names[i] ?? `Player ${i + 1}`;
  const last = replay.actions.length;
  const [step, setStep] = useState(0);
  const [viewer, setViewer] = useState("spectator");
  const [view, setView] = useState<View | null>(null);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setError(null);
    fetch(`/api/replay/${id}?step=${step}&viewer=${viewer}`)
      .then(async (res) => {
        const body = (await res.json()) as { ok: boolean; view?: View; message?: string };
        if (!current) return;
        if (body.ok && body.view) setView(body.view);
        else setError(body.message ?? "could not load this step");
      })
      .catch(() => current && setError("could not load this step"));
    return () => {
      current = false;
    };
  }, [id, step, viewer]);

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
  const end = replay.result?.result;
  return (
    <>
      <section className="card">
        <div className="moves">
          <button type="button" className="secondary" onClick={() => setStep(0)} disabled={step === 0}>
            Start
          </button>
          <button type="button" className="secondary" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
            Previous
          </button>
          <button type="button" onClick={() => setPlaying(!playing)} disabled={step >= last && !playing}>
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
            Step {step} of {last} · Seen as{" "}
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
            {end.ranking.map((r) => `${who(r.seat)}: ${r.score} points`).join(" · ")}
          </p>
        ) : null}
      </section>
      {error ? <p className="error">{error}</p> : null}
      {view ? <StateView view={view} names={names} /> : <p className="muted">Loading...</p>}
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
    </>
  );
}
