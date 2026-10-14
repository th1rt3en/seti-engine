"use client";
import { type Move, describeMove, groupMoves } from "@/lib/moves";
// The live game: a WebSocket to the Worker's GameRoom. The server sends this player's view (with the legal moves); the player answers by
// choosing one of the moves, which is sent back unchanged. A lost connection is re-opened with a fresh token.
import type { View } from "@seti/protocol";
import { useCallback, useEffect, useRef, useState } from "react";
import { StateView } from "./StateView";

type Server =
  | { t: "lobby"; status: string; seats: ({ name: string } | null)[]; rated: boolean }
  | { t: "view"; seq: number; status: string; view: View; names: string[]; remaining: (number | null)[] | null }
  | { t: "error"; code: string; message: string; legal?: Move[] }
  | { t: "ended"; result: { reason: string; winners: number[]; ranking: { seat: number; rank: number; score: number }[] } };

/** h:mm:ss or m:ss; a clock in the negative shows a minus sign. */
const minutes = (ms: number | null | undefined): string => {
  if (ms == null) return "";
  const total = Math.floor(Math.abs(ms) / 1000);
  const h = Math.floor(total / 3600);
  const mm = String(Math.floor((total % 3600) / 60)).padStart(h > 0 ? 2 : 1, "0");
  const ss = String(total % 60).padStart(2, "0");
  return `${ms < 0 ? "-" : ""}${h > 0 ? `${h}:` : ""}${mm}:${ss}`;
};

export function GameClient({
  gameId,
  wsBase,
  names: lobbyNames,
  signedIn,
}: { gameId: string; wsBase: string; names: string[]; signedIn: boolean }) {
  const [lobby, setLobby] = useState<Extract<Server, { t: "lobby" }> | null>(null);
  const [view, setView] = useState<Extract<Server, { t: "view" }> | null>(null);
  const [ended, setEnded] = useState<Extract<Server, { t: "ended" }>["result"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [online, setOnline] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const seq = useRef(0);
  const [now, setNow] = useState(() => Date.now());
  const [receivedAt, setReceivedAt] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let closed = false;
    let retry = 1000;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let pinger: ReturnType<typeof setInterval> | undefined;
    async function open() {
      let token = "";
      if (signedIn) {
        const res = await fetch("/api/token", { cache: "no-store" });
        if (res.ok) token = ((await res.json()) as { token: string }).token;
      }
      if (closed) return;
      const ws = new WebSocket(`${wsBase}/games/${gameId}/ws${token ? `?token=${encodeURIComponent(token)}` : ""}`);
      socket.current = ws;
      ws.onopen = () => {
        setOnline(true);
        retry = 1000;
        // the room takes a player of a lobby who has not pinged for a minute to have left
        pinger = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ t: "ping" })), 15_000);
      };
      ws.onmessage = (e) => {
        const m = JSON.parse(String(e.data)) as Server;
        if (m.t === "lobby") setLobby(m);
        else if (m.t === "view") {
          seq.current = m.seq;
          setReceivedAt(Date.now());
          setView(m);
          setError(null);
        } else if (m.t === "error") setError(m.message);
        else if (m.t === "ended") setEnded(m.result);
      };
      ws.onclose = () => {
        if (pinger) clearInterval(pinger);
        setOnline(false);
        if (!closed) {
          timer = setTimeout(open, retry);
          retry = Math.min(retry * 2, 10_000);
        }
      };
    }
    void open();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      if (pinger) clearInterval(pinger);
      socket.current?.close();
    };
  }, [gameId, wsBase, signedIn]);

  const send = useCallback((msg: unknown) => socket.current?.send(JSON.stringify(msg)), []);
  const play = (move: Move) => send({ t: "action", seq: seq.current, action: move });

  if (view === null) {
    return (
      <section className="card">
        <h2>{lobby ? "Waiting for players" : "Connecting..."}</h2>
        {lobby ? (
          <ol>
            {lobby.seats.map((s, i) => (
              <li key={`${i}-${s?.name ?? "free"}`}>{s ? s.name : <span className="muted">free seat</span>}</li>
            ))}
          </ol>
        ) : null}
        {lobby ? <p className="muted">{lobby.rated ? "Rated game." : "Casual game."} The game starts when every seat is taken.</p> : null}
      </section>
    );
  }

  // the seats are drawn when the game starts, so the names come with the view and not from the page that was loaded in the lobby
  const names = view.names.length > 0 ? view.names : lobbyNames;
  const v = view.view;
  const mine = v.legal as Move[];
  const pending = v.state.pending.length > 0;
  // The clock of the player to act runs down on this screen; the server decides what it was when the view was sent.
  const left = (view.remaining ?? []).map((r, i) => (r === null ? null : i === v.to_act ? r - (now - receivedAt) : r));
  const canKick = v.viewer !== null && !ended && v.state.players.length >= 3;
  return (
    <>
      <p className="small muted">
        {online ? "Connected" : "Reconnecting..."} · action {view.seq}
        {view.remaining ? ` · clocks ${left.map((r, i) => `${names[i] ?? i + 1}: ${minutes(r) || "-"}`).join(" | ")}` : ""}
      </p>
      {ended ? (
        <section className="card turn">
          <h2>Game over ({ended.reason})</h2>
          <p>
            {ended.winners.length > 0 ? `Winner: ${ended.winners.map((w) => names[w] ?? w + 1).join(", ")}.` : "The rival won."}{" "}
            {ended.ranking.map((r) => `${names[r.seat] ?? r.seat + 1}: ${r.score} points`).join(" · ")}
          </p>
        </section>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      {mine.length > 0 && !ended ? (
        <section className="card turn">
          <h2>{pending ? "Your decision" : "Your turn"}</h2>
          {groupMoves(mine, pending).map((g) => (
            <div key={g.title}>
              <h3>{g.title}</h3>
              <div className="moves">
                {g.moves.map((m, i) => (
                  <button key={`${m.type}-${i}`} type="button" onClick={() => play(m)}>
                    {describeMove(m)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </section>
      ) : v.viewer !== null && !ended ? (
        <p className="muted">Waiting for {v.to_act === null ? "the game" : (names[v.to_act] ?? `player ${v.to_act + 1}`)}.</p>
      ) : null}
      <StateView view={v} names={names} />
      {canKick
        ? left.map((r, i) =>
            r !== null && r < 0 && i !== v.viewer ? (
              <p key={`kick-${names[i] ?? i}`} className="error">
                {names[i] ?? `Player ${i + 1}`} is out of time ({minutes(r)}).{" "}
                <button
                  type="button"
                  onClick={() =>
                    window.confirm(`Kick ${names[i] ?? "this player"}? The game ends and the other players share first place.`) &&
                    send({ t: "kick", seat: i })
                  }
                >
                  Kick
                </button>
              </p>
            ) : null,
          )
        : null}
      {v.viewer !== null && !ended ? (
        <p>
          <button type="button" className="secondary" onClick={() => window.confirm("Resign the game?") && send({ t: "resign" })}>
            Resign
          </button>
        </p>
      ) : null}
    </>
  );
}
