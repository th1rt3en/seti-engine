"use client";
import { OPEN_BOARD_EVENT } from "@/lib/boardEvent";
import {
  type Move,
  describeMove,
  freeIsOnlyMovement,
  groupMoves,
  handHint,
  handMoveText,
  irreversibleText,
  isHandMove,
  rowMoveText,
  sameMove,
} from "@/lib/moves";
import { type Note, buildSpots } from "@/lib/targets";
import { TECH_INFO, techName } from "@/lib/techs";
import { useTurnSound } from "@/lib/turnSound";
// The live game: a WebSocket to the Worker's GameRoom. The server sends this player's view (with the legal moves); the player answers by
// choosing one of the moves, which is sent back unchanged. A lost connection is re-opened with a fresh token.
import type { View } from "@seti/protocol";
import { useCallback, useEffect, useRef, useState } from "react";
import assets from "../generated/assets.json";
import { GameView } from "./GameView";
import { ActionIcon, ScoreIcon } from "./Icons";
import { SampleReward } from "./Mascamites";
import { MoveGroup } from "./MoveGroupLabel";
import { type LogEntry, MoveLog } from "./MoveLog";
import { PlayerBoardPanel, type SlotChoice } from "./PlayerBoard";
import { SandboxPanel } from "./Sandbox";
import { SpotPrompt } from "./SpotPrompt";
import { TradeButtons } from "./Trade";

type Server =
  | { t: "lobby"; status: string; seats: ({ name: string } | null)[]; rated: boolean }
  | { t: "view"; seq: number; status: string; view: View; names: string[]; remaining: (number | null)[] | null }
  | { t: "error"; code: string; message: string; legal?: Move[] }
  | { t: "log"; from: number; entries: LogEntry[] }
  | { t: "ended"; result: { reason: string; winners: number[]; ranking: { seat: number; rank: number; score: number }[] } };

const GOLD_INFO = assets.gold as Record<string, { per: string; values: number[] }>;

/** h:mm:ss or m:ss; a clock in the negative shows a minus sign. */
const minutes = (ms: number | null | undefined): string => {
  if (ms == null) return "";
  const total = Math.floor(Math.abs(ms) / 1000);
  if (total >= 86400) {
    // turn-based clocks run for days: "3d 9h" (D34)
    const d = Math.floor(total / 86400);
    const hh = Math.floor((total % 86400) / 3600);
    return `${ms < 0 ? "-" : ""}${d}d ${hh}h`;
  }
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
  // the moves made so far (the server sends all of them when the page connects, then each new one)
  const [log, setLog] = useState<LogEntry[]>([]);
  const [online, setOnline] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const seq = useRef(0);
  // what the player has picked for the move being made: a card of the hand, a probe and how much energy to turn into movement for it
  // the places in the hand of the cards that are picked (one for a card's own move, two for a trade), a card of the display or the deck picked
  // to buy, and the trade moves that wait for the player to click a card of the display
  const [picked, setPicked] = useState<number[]>([]);
  const [pickedBuy, setPickedBuy] = useState<string | null>(null);
  // the end-of-round card picked to keep (after passing)
  const [pickedOffer, setPickedOffer] = useState<string | null>(null);
  // the place picked for a probe to move to, until the player confirms
  const [pendingMove, setPendingMove] = useState<{ to: [number, number]; cost: number; path: [number, number][] } | null>(null);
  const [rowMode, setRowMode] = useState<Move[] | null>(null);
  // a tech picked in the stacks (its place in the state)
  const [pickedTech, setPickedTech] = useState<number | null>(null);
  // the player boards: shown or not, and whose; the slot of the computer picked for a tech that was just researched
  const [boardOpen, setBoardOpen] = useState(false);
  const [boardPlayer, setBoardPlayer] = useState(0);
  const [pickedSlot, setPickedSlot] = useState<number | null>(null);
  // the gold scoring tile picked to mark (by name)
  const [pickedGold, setPickedGold] = useState<string | null>(null);
  // a place picked on the board (land, orbit, signal, trace)
  const [pickedSpot, setPickedSpot] = useState<string | null>(null);
  const [pickedProbe, setPickedProbe] = useState<string | null>(null);
  const [extraEnergy, setExtraEnergy] = useState(0);
  // The moves still to send of a plan (a probe's whole way, with the energy it needs): each goes out when the view of the one before arrives.
  const plan = useRef<Move[]>([]);
  const latest = useRef<View | null>(null);
  const [previous, setPrevious] = useState<View | null>(null);
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
          setPrevious(latest.current);
          latest.current = m.view;
          setReceivedAt(Date.now());
          setView(m);
          setError(null);
          setPicked([]);
          setPickedBuy(null);
          setPickedOffer(null);
          setPendingMove(null);
          setUnsure(null);
          setRowMode(null);
          setPickedTech(null);
          setPickedSpot(null);
          setPickedSlot(null);
          setPickedGold(null);
          setExtraEnergy(0);
          const next = plan.current.shift();
          if (next !== undefined) {
            // go on only while the next step is still legal (a decision such as a slingshot stops the plan)
            const legal = m.view.legal as Move[];
            if (m.view.to_act === m.view.viewer && legal.some((l) => sameMove(l, next))) {
              ws.send(JSON.stringify({ t: "action", seq: m.seq, action: next }));
            } else plan.current = [];
          }
        } else if (m.t === "log") {
          setLog((old) => (m.from === 0 ? m.entries : m.from === old.length ? [...old, ...m.entries] : old));
        } else if (m.t === "error") {
          plan.current = [];
          setError(m.message);
        }
        if (m.t === "ended") setEnded(m.result);
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

  // the boards open at the request of the tracker, and by themselves when a computer tech has to be put in a slot
  useEffect(() => {
    const onOpen = (e: Event) => {
      setBoardPlayer((e as CustomEvent<number>).detail);
      setBoardOpen(true);
    };
    window.addEventListener(OPEN_BOARD_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_BOARD_EVENT, onOpen);
  }, []);
  const choosing = view?.view.legal.some((m) => m.type === "place_computer_tech") ?? false;
  const viewer = view?.view.viewer ?? null;
  useEffect(() => {
    if (choosing && viewer !== null) {
      setBoardPlayer(viewer);
      setBoardOpen(true);
    }
  }, [choosing, viewer]);

  const send = useCallback((msg: unknown) => socket.current?.send(JSON.stringify(msg)), []);
  // a move that shows something hidden cannot be taken back: the player confirms it first (UNDO-01)
  const [unsure, setUnsure] = useState<Move | null>(null);
  const play = (move: Move) => {
    const current = latest.current;
    const at = current ? (current.legal as Move[]).findIndex((l) => sameMove(l, move)) : -1;
    const note = at >= 0 ? (current?.notes[at] as Note | null | undefined) : null;
    if (note?.irreversible) {
      setUnsure(move);
      return;
    }
    send({ t: "action", seq: seq.current, action: move });
  };
  const playConfirmed = (move: Move) => {
    setUnsure(null);
    send({ t: "action", seq: seq.current, action: move });
  };

  // D34: a ting when it becomes the player's turn to act
  const myTurn = view !== null && view.view.viewer !== null && view.view.to_act === view.view.viewer && !ended;
  const [soundOn, toggleSound] = useTurnSound(myTurn);

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
  const me = v.viewer === null ? null : (v.state.players[v.viewer] ?? null);
  const hand = me?.hand ?? [];
  // moves with a card of the hand are made by picking the card; moving a probe is made on the board
  const handMoves = mine.filter((m) => isHandMove(m, hand));
  const reach = ended || v.reach.length === 0 ? [] : v.reach;
  // exchanges and buying a card are made by picking cards (of the hand, of the display) and not with buttons of their own
  const exchanges = mine.filter((m) => m.type === "exchange");
  const buys = mine.filter((m) => m.type === "buy_card");
  // taking a card, and discarding a card of the display for a signal, are made by clicking the card of the display (or the deck) too
  const ROW_MOVES = ["buy_card", "take_card", "row_pick", "scan_discard", "scan_token"];
  const rowMoves = mine.filter((m) => ROW_MOVES.includes(m.type) && m.source !== undefined);
  // landing, orbiting, signals and traces are made by clicking the highlighted place on the board
  const { spots, handled } = ended ? { spots: [], handled: new Set<number>() } : buildSpots(v);
  const placed = new Set([...handled].map((i) => mine[i]));
  const sandboxMarker = mine.find((m) => m.type === "sandbox");
  const otherMoves = mine.filter(
    (m) =>
      !placed.has(m) &&
      m.type !== "sandbox" &&
      !isOffer(m) &&
      !rowMoves.includes(m) &&
      m.type !== "place_computer_tech" &&
      m.type !== "choose_gold" &&
      !handMoves.includes(m) &&
      m.type !== "exchange" &&
      m.type !== "buy_card" &&
      m.type !== "research" &&
      m.type !== "take_tech" &&
      !(reach.length > 0 && (m.type === "move_energy" || m.type === "move_probe")),
  );
  // a free action that gives movement does nothing without a probe on the map
  const noProbe = !v.state.probes.some((x) => x.player === v.viewer);
  const cardTrades = exchanges.filter((m) => m.give === "card");
  const tradable = new Set(cardTrades.flatMap((m) => m.cards as string[]));
  const pickable = [...new Set([...handMoves.map((m) => String(m.card)), ...tradable])];
  const pickedIds = picked.map((i) => hand[i]).filter((c): c is string => c !== undefined);
  const cardOptions = pickedIds.length === 1 ? handMoves.filter((m) => m.card === pickedIds[0]) : [];
  const tradeMoves =
    pickedIds.length === 2 ? cardTrades.filter((m) => [...(m.cards as string[])].sort().join() === [...pickedIds].sort().join()) : [];
  const resourceTrades = ["credit", "energy"].map((g) => exchanges.filter((m) => m.give === g)).filter((l) => l.length > 0);
  const selectCard = (i: number) =>
    setPicked(picked.includes(i) ? picked.filter((x) => x !== i) : picked.length >= 2 ? [picked[1] as number, i] : [...picked, i]);
  // the display and the deck: clicked to buy a card, or to take the card of a trade
  const rowSources = rowMode ? rowMode.map((m) => String(m.source)) : [...new Set(rowMoves.map((m) => String(m.source)))];
  const selectSource = (source: string) => {
    if (rowMode) {
      const m = rowMode.find((x) => x.source === source);
      if (m) play(m);
    } else setPickedBuy(pickedBuy === source ? null : source);
  };
  // techs are taken by clicking the stack
  const techMoves = mine.filter((m) => m.type === "research" || m.type === "take_tech");
  const techOption = pickedTech === null ? undefined : techMoves.find((m) => m.stack === pickedTech);
  const techStack = pickedTech === null ? undefined : v.state.tech_stacks[pickedTech];
  const spotOption = spots.find((sp) => sp.id === pickedSpot);
  const spotMove = spotOption === undefined ? undefined : mine[spotOption.move];
  // after passing the player is offered the end-of-round cards: they lie with the hand for the moment and the player picks one to keep
  // the same goes for the organizations and quick start cards offered at the start of a game with the organization module
  const isOffer = (m: Move): boolean => m.type === "take_round_card" || m.type === "choose_org" || m.type === "choose_quick";
  const offerId = (m: Move): string => String(m.type === "choose_org" ? m.org : m.card);
  const offers = [...new Set(mine.filter(isOffer).map(offerId))];
  const offerMove = pickedOffer === null ? undefined : mine.find((m) => isOffer(m) && offerId(m) === pickedOffer);
  // a tech for the computer goes in a slot picked on the player board
  const slotMoves = mine.filter((m) => m.type === "place_computer_tech");
  const slotMove = pickedSlot === null ? undefined : slotMoves.find((m) => m.slot === pickedSlot);
  const slotTech = String(v.state.pending[0]?.data?.tech ?? "");
  const slotChoice: SlotChoice | undefined =
    slotMoves.length > 0 ? { slots: slotMoves.map((m) => Number(m.slot)), selected: pickedSlot, onPick: setPickedSlot } : undefined;
  // a gold scoring tile is marked by clicking its free place on the board
  const goldMoves = mine.filter((m) => m.type === "choose_gold");
  const goldTile = pickedGold === null ? undefined : v.state.gold_tiles.find((g) => g.tile === pickedGold);
  const goldMove = goldTile === undefined ? undefined : goldMoves.find((m) => m.tile === goldTile.tile);
  const buyOptions = pickedBuy === null ? [] : rowMoves.filter((m) => m.source === pickedBuy);
  // the movement that the player has, and the budget with the energy they turn into movement
  const movement = me?.movement ?? 0;
  const energy = me?.energy ?? 0;
  const extra = Math.min(extraEnergy, energy);
  const budget = movement + extra;
  const probe = reach.find((r) => r.probe === pickedProbe) ?? null;
  const targets = (probe?.cells ?? []).filter((c) => c.cost <= budget);
  // the movement and the energy that a move to `t` uses: the movement the player has first, then energy
  const moveText = (t: { to: [number, number]; cost: number }): string => {
    const at = v.state.probes.find((x) => x.id === probe?.probe);
    const from = probe === null ? "here" : `${probe.label} (ring ${at?.ring}, sector ${at?.sector})`;
    const cell = probe?.cells.find((c) => c.to[0] === t.to[0] && c.to[1] === t.to[1]);
    const used = Math.min(movement, t.cost);
    return `Confirm using ${used} movement and ${t.cost - used} energy to move a probe from ${from} to ${cell?.label ?? "there"} (ring ${t.to[0]}, sector ${t.to[1]})?`;
  };
  const moveTo = (t: { to: [number, number]; cost: number; path: [number, number][] }) => {
    if (probe === null) return;
    const steps: Move[] = [
      ...Array.from({ length: Math.max(0, t.cost - movement) }, () => ({ type: "move_energy" }) as Move),
      ...t.path.map(([ring, sector]) => ({ type: "move_probe", probe: probe.probe, to: [ring, sector] }) as Move),
    ];
    const first = steps.shift();
    if (first === undefined) return;
    plan.current = steps;
    play(first);
  };
  // The clock of the player to act runs down on this screen; the server decides what it was when the view was sent.
  const left = (view.remaining ?? []).map((r, i) => (r === null ? null : i === v.to_act ? r - (now - receivedAt) : r));
  const canKick = v.viewer !== null && !ended && v.state.players.length >= 3;
  const moves = (
    <>
      {ended ? (
        <section className="gameover">
          <h2>Game over ({ended.reason})</h2>
          <p>
            {ended.winners.length > 0 ? `Winner: ${ended.winners.map((w) => names[w] ?? w + 1).join(", ")}.` : "The rival won."}{" "}
            {ended.ranking.map((r) => (
              <span key={r.seat} className="res">
                {names[r.seat] ?? r.seat + 1}: <ScoreIcon size={18} /> <b>{r.score}</b>{" "}
              </span>
            ))}
          </p>
        </section>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      {sandboxMarker && !ended ? (
        <SandboxPanel marker={sandboxMarker as never} send={(a) => send({ t: "action", seq: seq.current, action: a })} handCards={hand} />
      ) : null}
      {unsure ? (
        <div className="confirmbar">
          <div className="confirm warn">
            <span>
              <b>Cannot be undone.</b> {irreversibleText(unsure)} Continue with “{describeMove(unsure)}”?
            </span>
            <button type="button" className="primary" onClick={() => playConfirmed(unsure)}>
              Continue
            </button>
            <button type="button" className="secondary" onClick={() => setUnsure(null)}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}
      {mine.length > 0 && !ended ? (
        <div className="movegroups">
          {groupMoves(otherMoves, pending, v.state.pending[0]?.kind === "data_overflow").map((g) => (
            <MoveGroup key={g.title} title={g.title} count={g.moves.length} foldable={g.title === "Free actions"}>
              <div className="moves">
                {g.moves.map((m, i) => {
                  const idle = m.type === "move_energy" && noProbe;
                  return (
                    <button
                      key={`${m.type}-${i}`}
                      type="button"
                      disabled={idle}
                      title={idle ? "You have no probe on the map to move" : undefined}
                      onClick={() => play(m)}
                    >
                      {m.type === "launch" || m.type === "scan" || m.type === "analyze" ? <ActionIcon name={m.type} /> : null}
                      {describeMove(m)}
                      {m.type === "pick_sample" || m.type === "deliver_sample" ? (
                        <SampleReward note={v.notes[v.legal.findIndex((x) => sameMove(x as Move, m))]} />
                      ) : null}
                    </button>
                  );
                })}
              </div>
            </MoveGroup>
          ))}
          {reach.length > 0 ? (
            <MoveGroup title="Move a probe" count={reach.length} foldable forceOpen={pickedProbe !== null} className="moveui">
              <div className="moves">
                {reach.map((r) => {
                  const at = v.state.probes.find((x) => x.id === r.probe);
                  return (
                    <button
                      key={r.probe}
                      type="button"
                      className={r.probe === pickedProbe ? "chip on" : "chip"}
                      aria-pressed={r.probe === pickedProbe}
                      onClick={() => setPickedProbe(r.probe === pickedProbe ? null : r.probe)}
                    >
                      {at?.capsule ? "Capsule" : "Probe"} {r.probe}
                      {at ? ` (ring ${at.ring}, sector ${at.sector})` : ""}
                    </button>
                  );
                })}
              </div>
              <span className="budget">
                Move budget <b>{budget}</b> = {movement} movement +
                <button
                  type="button"
                  className="step"
                  aria-label="Use one energy less"
                  disabled={extra <= 0}
                  onClick={() => setExtraEnergy(extra - 1)}
                >
                  −
                </button>
                <b>{extra}</b> energy
                <button
                  type="button"
                  className="step"
                  aria-label="Use one energy more"
                  disabled={extra >= energy}
                  onClick={() => setExtraEnergy(extra + 1)}
                >
                  +
                </button>
                <span className="muted small">({energy} available)</span>
              </span>
              <span className="handhint">
                {probe === null
                  ? "Select a probe on the board or here, then a highlighted space."
                  : targets.length === 0
                    ? "No space is in reach: add energy."
                    : "Click a highlighted space; its number is what the move costs."}
              </span>
            </MoveGroup>
          ) : null}
          {resourceTrades.map((list) => (
            <div key={String(list[0]?.give)} className="mgroup">
              <span className="glabel">Free action</span>
              <TradeButtons moves={list} onPlay={play} onPickRow={setRowMode} />
            </div>
          ))}
          {pickable.length > 0 ? (
            <div className="mgroup">
              <span className="glabel">Cards in hand</span>
              <span className="handhint">
                {handHint(new Set(handMoves.map((m) => m.type)))}
                {tradable.size > 0 ? " Select 2 cards to trade them for a credit, an energy or a card." : ""}
              </span>
            </div>
          ) : null}
          {goldMoves.length > 0 ? (
            <div className="mgroup">
              <span className="glabel">Your choice</span>
              <span className="handhint">Click the highlighted place of a gold scoring tile beside the board to mark it.</span>
            </div>
          ) : null}
          {slotMoves.length > 0 ? (
            <div className="mgroup">
              <span className="glabel">Your choice</span>
              <span className="handhint">Click the slot of the computer on your player board where the new tech goes.</span>
            </div>
          ) : null}
          {offers.length > 0 ? (
            <div className="mgroup">
              <span className="glabel">Your choice</span>
              <span className="handhint">Pick 1 of the end-of-round cards in your hand to keep. The cards you had are greyed out.</span>
            </div>
          ) : null}
          {spots.length > 0 ? (
            <div className="mgroup">
              <span className="glabel">Your choice</span>
              <span className="handhint">Click a highlighted place on the board or on a panel beside it.</span>
            </div>
          ) : null}
          {techMoves.length > 0 ? (
            <div className="mgroup">
              <span className="glabel">{techMoves[0]?.type === "research" ? "Main action" : "Your choice"}</span>
              <span className="handhint">
                Click a tech stack to take that tech
                {techMoves[0]?.type === "research" ? " (6 publicity, and the solar system rotates)" : ""}.
              </span>
            </div>
          ) : null}
          {rowMoves.length > 0 && buys.length === 0 && !rowMode ? (
            <div className="mgroup">
              <span className="glabel">Your choice</span>
              <span className="handhint">Click a card of the display{rowSources.includes("deck") ? " or the deck" : ""}.</span>
            </div>
          ) : null}
          {buys.length > 0 ? (
            <div className="mgroup">
              <span className="glabel">Free action</span>
              <span className="handhint">Click a card of the display or the deck to buy it for 3 publicity.</span>
            </div>
          ) : null}
        </div>
      ) : null}
      {cardOptions.length > 0 ? (
        <div className="confirmbar">
          {cardOptions.map((m, i) => {
            const idle = m.type === "discard_free" && noProbe && freeIsOnlyMovement(m.card);
            return (
              // biome-ignore lint/suspicious/noArrayIndexKey: the options come in the order of the engine
              <div key={i} className="confirm">
                <span>{handMoveText(m)}</span>
                <button
                  type="button"
                  className="primary"
                  disabled={idle}
                  title={idle ? "You have no probe on the map to move" : undefined}
                  onClick={() => play(m)}
                >
                  Confirm
                </button>
                {idle ? <span className="muted small">You have no probe on the map.</span> : null}
              </div>
            );
          })}
          <button type="button" className="secondary" onClick={() => setPicked([])}>
            Cancel
          </button>
        </div>
      ) : null}
      {tradeMoves.length > 0 && !rowMode ? (
        <div className="confirmbar">
          <TradeButtons moves={tradeMoves} onPlay={play} onPickRow={setRowMode} />
          <button type="button" className="secondary" onClick={() => setPicked([])}>
            Cancel
          </button>
        </div>
      ) : null}
      {rowMode ? (
        <div className="confirmbar">
          <span className="confirm">Click the card of the display that you want.</span>
          <button type="button" className="secondary" onClick={() => setRowMode(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {pendingMove && probe ? (
        <div className="confirmbar">
          <div className="confirm">
            <span>{moveText(pendingMove)}</span>
            <button
              type="button"
              className="primary"
              onClick={() => {
                const t = pendingMove;
                setPendingMove(null);
                moveTo(t);
              }}
            >
              Confirm
            </button>
          </div>
          <button type="button" className="secondary" onClick={() => setPendingMove(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {slotMove && slotTech ? (
        <div className="confirmbar">
          <div className="confirm">
            <span>
              Confirm placing {techName(slotTech.split("-")[0] ?? "", slotTech.split("-")[1] ?? "")} on computer space{" "}
              {Number(slotMove.slot) + 1}? <span className="muted small">{TECH_INFO[slotTech]?.effect}</span>
            </span>
            <button type="button" className="primary" onClick={() => play(slotMove)}>
              Confirm
            </button>
          </div>
          <button type="button" className="secondary" onClick={() => setPickedSlot(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {goldMove && goldTile ? (
        <div className="confirmbar">
          <div className="confirm">
            <span>
              Confirm marking the <b>{goldTile.tile}</b> gold scoring tile ({GOLD_INFO[`${goldTile.tile}-${goldTile.side}`]?.per})? You
              would be the {["first", "second", "third or later"][Math.min(goldTile.markers.length, 2)]} to mark it:{" "}
              <b>{GOLD_INFO[`${goldTile.tile}-${goldTile.side}`]?.values[Math.min(goldTile.markers.length, 2)]} points</b> for each.
            </span>
            <button type="button" className="primary" onClick={() => play(goldMove)}>
              Confirm
            </button>
          </div>
          <button type="button" className="secondary" onClick={() => setPickedGold(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {offerMove ? (
        <div className="confirmbar">
          <div className="confirm">
            <span>{handMoveText(offerMove)}</span>
            <button type="button" className="primary" onClick={() => play(offerMove)}>
              Confirm
            </button>
          </div>
          <button type="button" className="secondary" onClick={() => setPickedOffer(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {spotMove ? (
        <div className="confirmbar">
          <div className="confirm">
            <SpotPrompt note={(v.notes[spotOption?.move ?? 0] ?? null) as Note} fallback={describeMove(spotMove)} />
            <button type="button" className="primary" onClick={() => play(spotMove)}>
              Confirm
            </button>
          </div>
          <button type="button" className="secondary" onClick={() => setPickedSpot(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {techOption && techStack ? (
        <div className="confirmbar">
          <div className="confirm">
            <span>
              Confirm taking {techName(techStack.category, techStack.glyph)}?
              {techOption.type === "research" ? " It costs 6 publicity and the solar system rotates." : ""}
            </span>
            <button type="button" className="primary" onClick={() => play(techOption)}>
              Confirm
            </button>
          </div>
          <button type="button" className="secondary" onClick={() => setPickedTech(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {buyOptions.length > 0 && !rowMode ? (
        <div className="confirmbar">
          {buyOptions.map((m) => (
            <div key={m.type} className="confirm">
              <span>{rowMoveText(m, v.state.card_row)}</span>
              <button type="button" className="primary" onClick={() => play(m)}>
                Confirm
              </button>
            </div>
          ))}
          <button type="button" className="secondary" onClick={() => setPickedBuy(null)}>
            Cancel
          </button>
        </div>
      ) : null}
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
    </>
  );
  const soundButton = (
    <button
      type="button"
      className="secondary small soundtoggle"
      aria-pressed={soundOn}
      title={soundOn ? "A ting plays when it is your turn: click to switch it off" : "Click to hear a ting when it is your turn"}
      onClick={toggleSound}
    >
      {soundOn ? "🔔 Sound on" : "🔕 Sound off"}
    </button>
  );
  const clocks = view.remaining ? (
    <span className="clocks">
      {left.map((r, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: seat order
        <span key={i} className={r !== null && r < 0 ? "clock over" : i === v.to_act ? "clock running" : "clock"}>
          {names[i] ?? i + 1} {minutes(r) || "-"}
        </span>
      ))}
    </span>
  ) : null;
  return (
    <GameView
      view={v}
      names={names}
      moves={moves}
      previous={previous}
      log={
        <MoveLog
          entries={log}
          ctx={{
            who: (i) => (v.state.rival && i === v.state.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`)),
            stars: v.state.sectors.map((sec) => sec.star),
            species: v.state.species.map((sp, i) =>
              sp.discovered ? sp.species.charAt(0).toUpperCase() + sp.species.slice(1) : `Species ${i + 1}`,
            ),
            rival: v.state.rival ? v.state.rival.index : null,
          }}
        />
      }
      goldChoice={
        goldMoves.length > 0
          ? { tiles: goldMoves.map((m) => String(m.tile)), selected: pickedGold, onPick: (t) => setPickedGold(pickedGold === t ? null : t) }
          : undefined
      }
      overlay={
        boardOpen ? (
          <PlayerBoardPanel
            view={v}
            names={names}
            shown={boardPlayer}
            onShow={setBoardPlayer}
            onClose={() => setBoardOpen(false)}
            choice={slotChoice}
            onPlaceData={mine.some((m) => m.type === "place_data") && !ended ? () => play({ type: "place_data" }) : undefined}
          />
        ) : null
      }
      hand={{
        selectable: pickable,
        selected: picked,
        onSelect: selectCard,
        offered: offers,
        offeredSelected: pickedOffer,
        onOffer: (c) => setPickedOffer(pickedOffer === c ? null : c),
      }}
      tech={{
        selectable: techMoves.map((m) => Number(m.stack)),
        selected: pickedTech,
        onSelect: (i) => setPickedTech(pickedTech === i ? null : i),
      }}
      spots={{ items: spots, selected: pickedSpot, onSelect: (id) => setPickedSpot(pickedSpot === id ? null : id) }}
      row={{ selectable: rowSources, selected: pickedBuy, onSelect: selectSource }}
      interaction={
        reach.length > 0
          ? {
              probes: reach.map((r) => r.probe),
              selected: probe?.probe ?? null,
              onSelectProbe: (id) => {
                setPendingMove(null);
                setPickedProbe(id === pickedProbe ? null : id);
              },
              targets: targets.map((t) => ({ to: t.to as [number, number], cost: t.cost, path: t.path as [number, number][] })),
              onTarget: (t) => setPendingMove(t),
              chosen: pendingMove ? `${pendingMove.to[0]}-${pendingMove.to[1]}` : null,
            }
          : undefined
      }
      topExtra={
        <>
          {clocks}
          {v.viewer !== null ? soundButton : null}
          {v.state.players.length > 0 ? (
            <button type="button" className="secondary small" onClick={() => setBoardOpen(!boardOpen)}>
              Player boards
            </button>
          ) : null}
          <span className="small muted">
            {online ? "Connected" : "Reconnecting..."} · action {view.seq}
          </span>
          {v.viewer !== null && !ended ? (
            <button type="button" className="secondary small" onClick={() => window.confirm("Resign the game?") && send({ t: "resign" })}>
              Resign
            </button>
          ) : null}
        </>
      }
    />
  );
}
