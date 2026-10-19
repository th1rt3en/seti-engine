"use client";
import { OPEN_BOARD_EVENT } from "@/lib/boardEvent";
import { useGameSettings } from "@/lib/gameSettings";
import { type Reward, glyphIconReward, glyphToken } from "@/lib/glyphids";
import { lastMoveOf } from "@/lib/lastMove";
import {
  type Move,
  cardInfo,
  cardName,
  cardSector,
  cornerGlyph,
  describeMove,
  freeIsOnlyMovement,
  groupMoves,
  handHint,
  handMoveText,
  irreversibleText,
  isHandMove,
  logText,
  orgName,
  rewardWords,
  rowMoveText,
  sameMove,
} from "@/lib/moves";
import { type Note, buildSpots } from "@/lib/targets";
import { TECH_INFO, techName } from "@/lib/techs";
import { useTurnSound } from "@/lib/turnSound";
import { ALL_EVENT } from "@/lib/useDock";
// The live game: a WebSocket to the Worker's GameRoom. The server sends this player's view (with the legal moves); the player answers by
// choosing one of the moves, which is sent back unchanged. A lost connection is re-opened with a fresh token.
import type { View } from "@seti/protocol";
import type { ReactNode } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import assets from "../generated/assets.json";
import expansionAssets from "../generated/expansion-assets.json";
import type { CardAction } from "./CardActions";
import { FinalScores } from "./FinalScores";
import { GameView } from "./GameView";
import { Hint } from "./Hint";
import { ActionIcon, ScoreIcon } from "./Icons";
import { SampleReward } from "./Mascamites";
import { type CoverChoice, MissionCover } from "./MissionCover";
import { MoveGroup } from "./MoveGroupLabel";
import { type LogContext, type LogEntry, MoveLog, plainEntry } from "./MoveLog";
import { OrgFreePanel } from "./OrgFreePanel";
import { pieceColor } from "./Pieces";
import { PlayerBoardPanel, type SlotChoice } from "./PlayerBoard";
import { Cost } from "./Reward";
import { SandboxPanel } from "./Sandbox";
import { SetupChoice } from "./SetupChoice";
import { SpotPrompt } from "./SpotPrompt";
import { TradePanel } from "./TradePanel";

type Server =
  | { t: "lobby"; status: string; seats: ({ name: string } | null)[]; rated: boolean }
  | { t: "view"; seq: number; status: string; view: View; names: string[]; remaining: (number | null)[] | null }
  | { t: "error"; code: string; message: string; legal?: Move[] }
  | { t: "log"; from: number; entries: LogEntry[] }
  | { t: "ended"; result: { reason: string; winners: number[]; ranking: { seat: number; rank: number; score: number }[] } }
  | { t: "cancelled" };

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
  const logRef = useRef<LogEntry[]>([]); // the same log, to check that a new entry follows the ones that were received
  const [online, setOnline] = useState(false);
  const [seenUpTo, setSeenUpTo] = useState(0); // the length of the log when the player last closed the summary of what happened since their turn
  const socket = useRef<WebSocket | null>(null);
  const seq = useRef(0);
  // what the player has picked for the move being made: a card of the hand, a probe and how much energy to turn into movement for it
  // the places in the hand of the cards that are picked (one for a card's own move, two for a trade), a card of the display or the deck picked
  // to buy, and the trade moves that wait for the player to click a card of the display
  const [picked, setPicked] = useState<number[]>([]);
  const [pickedBuy, setPickedBuy] = useState<string | null>(null);
  // the end-of-round card picked to keep (after passing)
  const [pickedOffer, setPickedOffer] = useState<string | null>(null);
  const [pickedCover, setPickedCover] = useState<CoverChoice | null>(null);
  const [pickedExertian, setPickedExertian] = useState<string | null>(null);
  const [xenoResearch, setXenoResearch] = useState(false);
  // the quick start cards picked to keep (two at once)
  const [pickedQuick, setPickedQuick] = useState<string[]>([]);
  // the place picked for a probe to move to, until the player confirms
  const [pendingMove, setPendingMove] = useState<{ to: [number, number]; cost: number; path: [number, number][] } | null>(null);
  const [rowMode, setRowMode] = useState<Move[] | null>(null);
  // a tech picked in the stacks (its place in the state)
  const [pickedTech, setPickedTech] = useState<number | null>(null);
  // the player boards: shown or not, and whose; the slot of the computer picked for a tech that was just researched
  const [boardOpen, setBoardOpen] = useState(false);
  // the panel of the free trade
  const [tradeOpen, setTradeOpen] = useState(false);
  // the panel of an organization's free action that is made with a card of the hand
  const [orgFreeOpen, setOrgFreeOpen] = useState(false);
  const [boardPlayer, setBoardPlayer] = useState(0);
  const [pickedSlot, setPickedSlot] = useState<number | null>(null);
  // the gold scoring tile picked to mark (by name)
  const [pickedGold, setPickedGold] = useState<string | null>(null);
  // a place picked on the board (land, orbit, signal, trace)
  const [pickedSpot, setPickedSpot] = useState<string | null>(null);
  // the glyph token picked for a hole of the translation board that takes several (with the hole it was picked for)
  const [pickedGlyph, setPickedGlyph] = useState<{ spot: string; glyph: string } | null>(null);
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

  const send = useCallback((msg: unknown) => socket.current?.send(JSON.stringify(msg)), []);
  // A move that has been sent and is waiting for the server's answer: the prompt is hidden behind a loading symbol and no second move goes out until
  // the new view (or an error) arrives, so that a click repeated on a slow connection cannot send the move twice. A guard of 20 seconds frees the page.
  const [waiting, setWaiting] = useState(false);
  const waitingRef = useRef(false);
  const waitTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const endWait = useCallback(() => {
    waitingRef.current = false;
    setWaiting(false);
    if (waitTimer.current !== null) clearTimeout(waitTimer.current);
    waitTimer.current = null;
  }, []);
  const sendAction = useCallback(
    (action: unknown) => {
      if (waitingRef.current) return; // the answer to the last move has not come yet
      waitingRef.current = true;
      setWaiting(true);
      waitTimer.current = setTimeout(() => {
        endWait();
        setError("The server did not answer in time. Check your connection and try again.");
      }, 20_000);
      send({ t: "action", seq: seq.current, action });
    },
    [send, endWait],
  );

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
          endWait();
          setPrevious(latest.current);
          latest.current = m.view;
          setReceivedAt(Date.now());
          setView(m);
          setError(null);
          setPicked([]);
          setPickedBuy(null);
          setPickedOffer(null);
          setPickedCover(null);
          setPickedExertian(null);
          setXenoResearch(false);
          setPickedQuick([]);
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
              waitingRef.current = true; // the next step of the plan is on its way too
              setWaiting(true);
            } else plan.current = [];
          }
        } else if (m.t === "log") {
          // a message that does not follow the entries held means one was missed: connect again, the server then sends the whole log
          if (m.from === 0) logRef.current = m.entries;
          else if (m.from === logRef.current.length) logRef.current = [...logRef.current, ...m.entries];
          else {
            ws.close();
            return;
          }
          setLog(logRef.current);
        } else if (m.t === "error") {
          plan.current = [];
          endWait();
          setError(m.message);
        }
        if (m.t === "ended") setEnded(m.result);
        // an administrator cancelled the game: it is over for everybody, with no winner and no rating change
        if (m.t === "cancelled") setEnded({ reason: "cancelled", winners: [], ranking: [] });
      };
      ws.onclose = () => {
        if (pinger) clearInterval(pinger);
        setOnline(false);
        endWait(); // the answer to a move sent on a lost connection will not come: the view that follows the reconnection says what happened
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
  }, [gameId, wsBase, signedIn, endWait]);

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

  // a move that shows something hidden cannot be taken back: the player confirms it first (UNDO-01)
  const [unsure, setUnsure] = useState<Move | null>(null);
  const { confirmIrreversible } = useGameSettings(); // the player can turn the question off in the settings
  const play = (move: Move) => {
    const current = latest.current;
    const at = current ? (current.legal as Move[]).findIndex((l) => sameMove(l, move)) : -1;
    const note = at >= 0 ? (current?.notes[at] as Note | null | undefined) : null;
    if (note?.irreversible && confirmIrreversible) {
      setUnsure(move);
      return;
    }
    sendAction(move);
  };
  const playConfirmed = (move: Move) => {
    setUnsure(null);
    sendAction(move);
  };

  // D34: a ting when it becomes the player's turn to act
  const myTurn = view !== null && view.view.viewer !== null && view.view.to_act === view.view.viewer && !ended;
  useTurnSound(myTurn); // the sound and the size of the cards are set with the gear in the heading (GameSettings)

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
  // what researching a tech costs in publicity: the engine says (an organization can lower it); 6 when it does not
  const researchCost = (m: Move | undefined): number => (m ? ((v.notes[mine.indexOf(m)] as Note)?.cost?.publicity ?? 6) : 6);
  const pending = v.state.pending.length > 0;
  const me = v.viewer === null ? null : (v.state.players[v.viewer] ?? null);
  const hand = me?.hand ?? [];
  // moves with a card of the hand are made by picking the card; moving a probe is made on the board
  const handMoves = mine.filter((m) => isHandMove(m, hand));
  const reach = ended || v.reach.length === 0 ? [] : v.reach;
  // exchanges and buying a card are made by picking cards (of the hand, of the display) and not with buttons of their own
  const exchanges = mine.filter((m) => m.type === "exchange");
  // the free actions of an organization that name a card of the hand (Helion Assembly, Deep Sky Survey, Futurespan prepare)
  const orgCardMoves = mine.filter((m) => m.type === "org_free" && (typeof m.card === "string" || typeof m.tech === "string"));
  const buys = mine.filter((m) => m.type === "buy_card");
  // taking a card, and discarding a card of the display for a signal, are made by clicking the card of the display (or the deck) too
  const ROW_MOVES = ["buy_card", "take_card", "row_pick", "scan_discard", "scan_token"];
  // the cards that are offered to keep one of (end-of-round cards, organizations, quick start cards)
  const isOffer = (m: Move): boolean => m.type === "take_round_card" || m.type === "choose_org" || m.type === "choose_quick";
  const offerId = (m: Move): string => String(m.type === "choose_org" ? m.org : m.card);
  const quickCards = (m: Move): string[] => ((m.cards as string[] | undefined) ?? []).map(String);
  // the free actions of an organization that take a card of the display or the deck (Fenwick Research Center, Mission Relay, Cosmos Strategy Group)
  // are made like these: click the card, then the button over it
  const rowMoves = mine.filter((m) => (ROW_MOVES.includes(m.type) || m.type === "org_free") && m.source !== undefined);
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
      !(m.type === "org_main" && typeof m.tile === "string") && // the tiles of Xenolab are buttons of the main actions
      m.type !== "play_exertian" && // an Exertian card is picked in its tab of the hand, and played with the buttons over it
      !orgCardMoves.includes(m) && // the free actions that name a card or a tech have their own button and panel
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
  const pickable = [...new Set(handMoves.map((m) => String(m.card)))];
  const pickedIds = picked.map((i) => hand[i]).filter((c): c is string => c !== undefined);
  const cardOptions = pickedIds.length === 1 ? handMoves.filter((m) => m.card === pickedIds[0]) : [];
  // what the glyph icon of a Glyphids card's corner gives now (EXP-GLY-06), to show it before the card is discarded
  const glyphExtra = v.state.species.find((sp) => sp.discovered && sp.species === "glyphids")?.extra as
    | { sides?: number[]; top?: (string | null)[]; bottom?: (string | null)[] }
    | undefined;
  const cornerBonus = (card: unknown): { reward: Reward | null } | undefined => {
    const g = cornerGlyph(card);
    return g === null ? undefined : { reward: glyphIconReward(glyphExtra, g) };
  };
  // the buttons over a card of the hand that is the only one picked: play it, use its free action, tuck it ...
  const handActions: CardAction[] = cardOptions.map((m, i) => {
    const info = cardInfo(m.card);
    if (m.type === "play_card")
      return {
        key: `${m.type}-${i}`,
        label:
          info && info.cost > 0 ? `Play: ${info.cost} ${info.pays_energy ? "energy" : "credit"}${info.cost > 1 ? "s" : ""}` : "Play (free)",
        primary: true,
        title: handMoveText(m),
        onClick: () => play(m),
      };
    if (m.type === "discard_free") {
      const bonus = cornerBonus(m.card);
      const idle = noProbe && freeIsOnlyMovement(m.card);
      const nothing = bonus !== undefined && bonus.reward === null;
      return {
        key: `${m.type}-${i}`,
        label: bonus
          ? bonus.reward
            ? `Free effect: ${rewardWords(bonus.reward)}`
            : "Free effect: nothing"
          : "Discard for its free effect",
        disabled: idle,
        title: idle ? "You have no probe on the map to move" : handMoveText(m, bonus),
        warn: nothing ? `The ${cornerGlyph(m.card)} glyph is not on the translation board: you would gain nothing.` : undefined,
        onClick: () => play(m),
      };
    }
    const label = m.type === "tuck" ? `Tuck: ${info?.income ?? "no"} income` : handMoveText(m).replace(/\?$/, "");
    return { key: `${m.type}-${i}`, label, title: handMoveText(m), onClick: () => play(m) };
  });
  // the main action is taken (or the card cannot be afforded): Play stays in sight, greyed out
  if (
    cardOptions.length > 0 &&
    !cardOptions.some((m) => m.type === "play_card") &&
    cardOptions.some((m) => m.type === "discard_free" || m.type === "tuck")
  )
    handActions.unshift({
      key: "play-off",
      label: "Play",
      disabled: true,
      title: v.state.main_done ? "You have already taken your main action this turn" : "You cannot play this card now",
      onClick: () => undefined,
    });
  // The move bar has only the actions of a turn (launch, scan, analyze, pass, end the turn) and the free trade; the question of everything else is
  // asked in the context bar above it, where the answers that are no choice on the board are buttons (skip, yes, no, take the data ...).
  const BAR_MOVES = new Set(["launch", "scan", "analyze", "pass", "end_turn"]);
  const barMoves = otherMoves.filter((m) => BAR_MOVES.has(m.type));
  // a free action that moves a probe is no answer for a player with no probe on the map
  // the circles of a mission that a trigger can cover are clicked on the mission card, shown in the context bar
  const exertianMoves = mine.filter((m) => m.type === "play_exertian");
  const exertianMove = exertianMoves.find((m) => m.card === pickedExertian);
  const exertianCost = Number(v.state.pending[0]?.data?.cost ?? 0);
  const exertianActions: CardAction[] = exertianMove
    ? [
        {
          key: "play",
          label: exertianCost > 0 ? `Play face down (${exertianCost} credit)` : "Play face down",
          primary: true,
          title: describeMove(exertianMove),
          onClick: () => play(exertianMove),
        },
        { key: "cancel", label: "Cancel", onClick: () => setPickedExertian(null) },
      ]
    : [];
  const coverMoves = otherMoves.filter((m) => m.type === "cover");
  const coverOptions: CoverChoice[] = coverMoves.map((m) => ({ card: String(m.card), circle: Number(m.circle) }));
  const coverMove =
    pickedCover === null ? undefined : coverMoves.find((m) => m.card === pickedCover.card && m.circle === pickedCover.circle);
  const coverUsed: Record<string, boolean[]> = Object.fromEntries(
    (v.state.players[v.viewer ?? 0]?.missions ?? []).map((m) => [m.card, m.used]),
  );
  const coverNode =
    coverOptions.length > 0 ? (
      <MissionCover
        options={coverOptions}
        used={coverUsed}
        color={pieceColor(v.state.players[v.viewer ?? 0]?.color)}
        picked={pickedCover}
        onPick={setPickedCover}
      />
    ) : null;
  // free actions that have their own place (energy for movement: the probe's move; data: the computer and the lower spaces of the player board) are no
  // buttons here: placing data is done on the player board
  // completing a quick mission is a free action: its buttons are in the move bar
  const completeMoves = otherMoves.filter((m) => m.type === "complete_mission");
  const answerMoves = otherMoves.filter(
    (m) =>
      !BAR_MOVES.has(m.type) &&
      m.type !== "cover" &&
      m.type !== "complete_mission" &&
      m.type !== "move_energy" &&
      m.type !== "place_data" &&
      m.type !== "place_lower",
  );
  const moveGroups = groupMoves(barMoves, pending, v.state.pending[0]?.kind === "data_overflow");
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
  // Xenolab: its three tiles are main actions with their own buttons; the research tile then asks for a tech stack like any research
  const xenoMoves = mine.filter((m) => m.type === "org_main" && typeof m.tile === "string");
  const xenoResearchMoves = xenoMoves.filter((m) => m.tile === "research");
  const techMoves = mine.filter((m) => m.type === "research" || m.type === "take_tech" || (xenoResearch && xenoResearchMoves.includes(m)));
  const techOption = pickedTech === null ? undefined : techMoves.find((m) => m.stack === pickedTech);
  const techStack = pickedTech === null ? undefined : v.state.tech_stacks[pickedTech];
  const spotOption = spots.find((sp) => sp.id === pickedSpot);
  // a hole of the translation board takes any of the glyph tokens the player owns: one alone is taken, else the player picks
  const glyphChoices = spotOption?.choices;
  const glyphChoice =
    glyphChoices === undefined
      ? undefined
      : glyphChoices.length === 1
        ? glyphChoices[0]
        : glyphChoices.find((c) => pickedGlyph !== null && pickedGlyph.spot === spotOption?.id && pickedGlyph.glyph === c.glyph);
  const spotMove = spotOption === undefined ? undefined : mine[glyphChoice ? glyphChoice.move : glyphChoices ? -1 : spotOption.move];
  // after passing the player is offered the end-of-round cards: they lie with the hand for the moment and the player picks one to keep
  // the same goes for the organizations and quick start cards offered at the start of a game with the organization module
  // the first choice of a game with organizations (organization, then quick start cards) has a screen of its own
  const setupMoves = mine.filter((m) => m.type === "choose_org" || m.type === "choose_quick");
  const setupKind = setupMoves[0]?.type === "choose_org" ? "org" : "quick";
  // the quick start cards are kept two at once: every legal move names a pair, and the page offers the cards that are in some pair
  const setupOffers = [...new Set(setupMoves.flatMap((m) => (m.type === "choose_quick" ? quickCards(m) : [offerId(m)])))];
  const quickNeed = setupMoves[0]?.type === "choose_quick" ? quickCards(setupMoves[0]).length : 1;
  const offers = [...new Set(mine.filter((m) => isOffer(m) && !setupMoves.includes(m)).map(offerId))];
  const offerMove =
    pickedOffer === null ? undefined : mine.find((m) => isOffer(m) && !setupMoves.includes(m) && offerId(m) === pickedOffer);
  const setupMove =
    setupKind === "quick"
      ? pickedQuick.length === quickNeed
        ? setupMoves.find((m) => quickCards(m).length === quickNeed && quickCards(m).every((c) => pickedQuick.includes(c)))
        : undefined
      : pickedOffer === null
        ? undefined
        : setupMoves.find((m) => offerId(m) === pickedOffer);
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
  const ROW_SIGNAL_MOVES = ["scan_discard", "scan_token", "row_pick", "org_free"];
  // what the button over the card says for each organization
  const ORG_ROW_LABEL: Record<string, string> = {
    mission_relay: "Mission Relay: 2 publicity",
    fenwick_research_center: "Fenwick: 1 publicity",
    cosmos_strategy_group: "Cosmos Strategy: take it",
    futurespan_institute: "Futurespan: token +3 and take it",
  };
  const pickedRowMoves = pickedBuy === null ? [] : rowMoves.filter((m) => m.source === pickedBuy);
  // discarding a card of the display for a signal (during a scan) is confirmed by a button on the card itself; the other moves keep the bar
  // the context bar asks the question of a tech that is picked; the confirm button lies on the tech itself
  const techContext =
    techOption && techStack ? (
      <>
        {techOption.type === "org_main"
          ? `Confirm researching ${techName(techStack.category, techStack.glyph)} with the Xenolab research tile (4 publicity)?`
          : techOption.type === "research"
            ? `Confirm spending ${researchCost(techOption)} publicity to research ${techName(techStack.category, techStack.glyph)}?`
            : `Confirm taking ${techName(techStack.category, techStack.glyph)}?`}{" "}
        <button type="button" className="secondary small" onClick={() => setPickedTech(null)}>
          Cancel
        </button>
      </>
    ) : xenoResearch && xenoResearchMoves.length > 0 ? (
      <>
        Xenolab research tile: click the tech stack that you want (4 publicity).{" "}
        <button type="button" className="secondary small" onClick={() => setXenoResearch(false)}>
          Cancel
        </button>
      </>
    ) : undefined;
  const buyOptions = pickedRowMoves.filter((m) => !ROW_SIGNAL_MOVES.includes(m.type));
  const rowCardId = pickedBuy === null || pickedBuy === "deck" ? undefined : v.state.card_row[Number(pickedBuy.slice(4))];
  const rowActions: CardAction[] = pickedRowMoves.map((m) => {
    const sector = rowCardId === undefined ? "a" : cardSector(rowCardId);
    const signal = ROW_SIGNAL_MOVES.includes(m.type);
    return {
      key: `${m.type}-${String(m.org ?? "")}`,
      label: signal
        ? m.type === "org_free"
          ? (ORG_ROW_LABEL[String(m.org)] ?? `${orgName(m.org)}: free action`)
          : m.type === "scan_token"
            ? `Use a signal token: ${sector} signal`
            : `Discard to mark a ${sector} signal`
        : buyOptions.length > 1
          ? describeMove(m)
          : "Confirm",
      primary: true,
      title: m.type === "org_free" ? describeMove(m) : rowMoveText(m, v.state.card_row),
      onClick: () => play(m),
    };
  });
  // taking a card that was picked is confirmed (or given up) on the card itself
  if (rowActions.length > 0 && !rowMode) rowActions.push({ key: "cancel", label: "Cancel", onClick: () => setPickedBuy(null) });
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
  const sendingPrompt = (
    // biome-ignore lint/a11y/useSemanticElements: a small notice with a spinner, not an <output> of a form
    <div className="sendingmove" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Sending your move...</span>
    </div>
  );
  // what is asked now, if the player has picked something to confirm: the text goes to the context bar, the buttons to the move bar
  type Ask = {
    inContext?: boolean;
    /** The buttons are laid over the picked card itself (a card of the display, an alien card): the bars have none. */
    onCard?: boolean;
    text: ReactNode;
    buttons: { label: string; onClick: () => void; disabled?: boolean }[];
    onCancel: () => void;
  };
  const confirm = (label: string, onClick: () => void, disabled = false) => ({ label, onClick, disabled });
  let ask: Ask | null = null;
  if (unsure) {
    ask = {
      text: (
        <>
          <b>Are you sure? This cannot be undone.</b> {irreversibleText(unsure)}
        </>
      ),
      buttons: [confirm("Continue", () => playConfirmed(unsure))],
      onCancel: () => setUnsure(null),
      inContext: true, // the question that a move cannot be undone has its buttons in the context bar, where the eye is
    };
  } else if (coverMove && coverNode) {
    ask = {
      text: (
        <>
          Cover circle {Number(coverMove.circle) + 1} of {cardName(coverMove.card)}? {coverNode}
        </>
      ),
      buttons: [confirm("Confirm", () => play(coverMove))],
      onCancel: () => setPickedCover(null),
      inContext: true,
    };
  } else if (pendingMove && probe) {
    ask = {
      text: moveText(pendingMove),
      buttons: [
        confirm("Confirm", () => {
          const t = pendingMove;
          setPendingMove(null);
          moveTo(t);
        }),
      ],
      onCancel: () => setPendingMove(null),
    };
  } else if (slotMove && slotTech) {
    ask = {
      text: (
        <>
          Confirm placing {techName(slotTech.split("-")[0] ?? "", slotTech.split("-")[1] ?? "")} on computer space{" "}
          {Number(slotMove.slot) + 1}? <span className="muted small">{TECH_INFO[slotTech]?.effect}</span>
        </>
      ),
      buttons: [confirm("Confirm", () => play(slotMove))],
      onCancel: () => setPickedSlot(null),
    };
  } else if (goldMove && goldTile) {
    ask = {
      text: (
        <>
          Confirm marking the <b>{goldTile.tile}</b> gold scoring tile ({GOLD_INFO[`${goldTile.tile}-${goldTile.side}`]?.per})? You would be
          the {["first", "second", "third or later"][Math.min(goldTile.markers.length, 2)]} to mark it:{" "}
          <b>{GOLD_INFO[`${goldTile.tile}-${goldTile.side}`]?.values[Math.min(goldTile.markers.length, 2)]} points</b> for each.
        </>
      ),
      buttons: [confirm("Confirm", () => play(goldMove))],
      onCancel: () => setPickedGold(null),
    };
  } else if (offerMove) {
    ask = { text: handMoveText(offerMove), buttons: [confirm("Confirm", () => play(offerMove))], onCancel: () => setPickedOffer(null) };
  } else if (spotOption) {
    ask = {
      text: glyphChoices ? (
        <span className="spotprompt glyphpick">
          Place which glyph token in this {spotOption.id.split(":")[1]} slot?
          {glyphChoices.map((c) => {
            const owned = (v.state.players[v.viewer ?? 0]?.glyphs ?? []).filter((g) => g === c.glyph).length;
            return (
              <button
                key={c.glyph}
                type="button"
                className={glyphChoice?.glyph === c.glyph ? "glyphchoice on" : "glyphchoice"}
                aria-pressed={glyphChoice?.glyph === c.glyph}
                title={`Place a ${c.glyph} glyph token (you have ${owned})`}
                onClick={() => setPickedGlyph({ spot: spotOption.id, glyph: c.glyph })}
              >
                <img src={glyphToken(c.glyph)} alt={`${c.glyph} glyph token`} width={34} height={39} />
                {owned > 1 ? <b>×{owned}</b> : null}
              </button>
            );
          })}
        </span>
      ) : (
        <SpotPrompt note={(v.notes[spotOption.move] ?? null) as Note} fallback={spotMove ? describeMove(spotMove) : undefined} />
      ),
      buttons: [confirm("Confirm", () => spotMove && play(spotMove), !spotMove)],
      onCancel: () => setPickedSpot(null),
      onCard: spotOption.id.startsWith("alien:"), // an alien card: its buttons lie on the card on the board
    };
  } else if (rowMode) {
    ask = { text: "Click the card of the display that you want.", buttons: [], onCancel: () => setRowMode(null) };
  } else if (buyOptions.length > 0 && !rowMode) {
    ask = {
      text: buyOptions.map((m) => rowMoveText(m, v.state.card_row)).join(" "),
      buttons: [],
      onCancel: () => setPickedBuy(null),
      onCard: true,
    };
  }
  // moving a probe: what the context bar says while a probe is picked (the budget and its energy are set there)
  const probeContext =
    reach.length > 0 && probe !== null ? (
      <span className="budget">
        Moving probe {probe.probe} from {probe.label}: budget <b>{budget}</b> = {movement} movement +
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
        <span className="muted small"> Click a highlighted space; its number is what it costs.</span>
      </span>
    ) : reach.length > 0 && movement > 0 ? (
      // movement left over (from the organization or from a card played as the main action) asks for a probe to spend it on
      <>
        Select a probe to move ({movement} {movement === 1 ? "move" : "moves"} left)
      </>
    ) : undefined;
  // the reminders of what can be done now: one ? button in the context bar
  const hints: string[] = [];
  if (reach.length > 0)
    hints.push(
      probe === null
        ? "Click a probe on the board, then a highlighted space."
        : targets.length === 0
          ? "No space is in reach: add energy."
          : "Click a highlighted space; its number is what the move costs.",
    );
  if (pickable.length > 0) hints.push(`${handHint(new Set(handMoves.map((m) => m.type)))}`);
  if (goldMoves.length > 0) hints.push("Click the highlighted place of a gold scoring tile beside the board to mark it.");
  if (slotMoves.length > 0) hints.push("Click the slot of the computer on your player board where the new tech goes.");
  if (mine.some((m) => m.type === "place_data" || m.type === "place_lower"))
    hints.push(
      "Place data by clicking the computer or a lower space of a computer tech on your player board (the Player boards button opens it).",
    );
  if (offers.length > 0) hints.push("Pick 1 of the end-of-round cards in your hand to keep. The cards you had are greyed out.");
  if (spots.length > 0) hints.push("Click a highlighted place on the board or on a panel beside it.");
  if (techMoves.length > 0)
    hints.push(
      `Click a tech stack to take that tech${techMoves[0]?.type === "research" ? ` (${researchCost(techMoves[0])} publicity, and the solar system rotates)` : ""}.`,
    );
  if (rowMoves.length > 0 && buys.length === 0 && !rowMode)
    hints.push(`Click a card of the display${rowSources.includes("deck") ? " or the deck" : ""}.`);
  if (buys.length > 0) hints.push("Click a card of the display or the deck to buy it for 3 publicity.");
  if (coverNode) hints.push("Click the circle of the mission card that you want to cover, or decline.");
  // Arkhos: the overflow space lets the player take the security card of that color into the hand
  const breachDecision = v.state.pending[0]?.kind === "breach" && mine.some((m) => m.type === "breach");
  const breachColor = breachDecision ? String(v.state.pending[0]?.data?.color ?? "") : "";
  const breachCard = (v.state.players[v.viewer ?? 0]?.security as Record<string, string> | undefined)?.[breachColor];
  const breachNode =
    breachDecision && !ask ? (
      <span className="breachbar">
        Breach your {breachColor} security card? It goes to your hand and opens a deeper level of the Arkhos board.
        {breachCard ? (
          <img
            src={(expansionAssets as Record<string, string>)[`arkhos/security-back-${breachColor}`]}
            alt={`${breachColor} security card, face down until it is breached`}
            width={86}
          />
        ) : null}
      </span>
    ) : null;
  const contextNode: ReactNode =
    ask?.text ?? breachNode ?? (coverNode ? <>Cover a circle of a mission? {coverNode}</> : null) ?? techContext ?? probeContext;
  // the answers that are not choices on the board are buttons in the context bar
  const contextActions = ask?.inContext ? (
    <>
      {ask.buttons.map((b) => (
        <button key={b.label} type="button" className="primary small" disabled={b.disabled} onClick={b.onClick}>
          {b.label}
        </button>
      ))}
      <button type="button" className="secondary small" onClick={ask.onCancel}>
        Cancel
      </button>
    </>
  ) : answerMoves.length > 0 && !ask && !ended ? (
    <>
      {answerMoves.map((m, i) => {
        const idle = m.type === "move_energy" && noProbe;
        return (
          <button
            key={`${m.type}-${i}`}
            type="button"
            className="secondary small"
            disabled={idle}
            title={idle ? "You have no probe on the map to move" : undefined}
            onClick={() => play(m)}
          >
            {describeMove(m)}
            {m.type === "pick_sample" || m.type === "deliver_sample" ? (
              <SampleReward note={v.notes[v.legal.findIndex((x) => sameMove(x as Move, m))]} />
            ) : null}
          </button>
        );
      })}
    </>
  ) : undefined;
  // Xenolab: its three tiles (launch, scan, research) are main actions, each with the picture of its tile at the size of the other action icons and its cost
  const xenoTiles = [
    { tile: "launch", name: "Launch", cost: { credit: 1 } },
    { tile: "scan", name: "Scan", cost: { energy: 2 } },
    { tile: "research", name: "Research", cost: { publicity: 4 } },
  ] as const;
  const xenoButtons = xenoTiles.flatMap((t, i) => {
    const move = xenoMoves.find((m) => m.tile === t.tile);
    if (move === undefined) return [];
    const src = (expansionAssets as Record<string, string>)[`tokens/xenolab-tile-${i + 1}`];
    return [
      <button
        key={`xeno-${t.tile}`}
        type="button"
        className={t.tile === "research" && xenoResearch ? "xenotile on" : "xenotile"}
        title={describeMove(move)}
        onClick={() => (t.tile === "research" ? setXenoResearch(!xenoResearch) : play(move))}
      >
        {src ? <img src={src} alt="" width={28} height={30} className="xenoicon" /> : null}
        {t.name} (Xenolab) <Cost cost={t.cost} />
      </button>,
    ];
  });
  const MAIN_NAMES = { launch: "Launch a probe", scan: "Scan", analyze: "Analyze" } as const;
  const costOf = (m: Move): Record<string, number> => {
    const at = v.legal.findIndex((x) => sameMove(x as Move, m));
    return ((v.notes[at] as Note)?.cost ?? {}) as Record<string, number>;
  };
  const logCtx: LogContext = {
    who: (i: number) => (v.state.rival && i === v.state.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`)),
    stars: v.state.sectors.map((sec) => sec.star),
    species: v.state.species.map((sp, i) =>
      sp.discovered ? sp.species.charAt(0).toUpperCase() + sp.species.slice(1) : `Species ${i + 1}`,
    ),
    rival: v.state.rival ? v.state.rival.index : null,
    me: v.viewer,
  };
  // what the others did since this player's last move, for the player whose turn it is
  const lastMine = myTurn ? log.map((e) => e.seat).lastIndexOf(v.viewer as number) : -1;
  const since = myTurn ? log.slice(lastMine + 1) : [];
  const sinceBar =
    myTurn && since.length > 0 && seenUpTo < log.length ? (
      <section className="sincebar" aria-label="What happened since your last turn">
        <b>Since your last turn:</b>
        <ul>
          {since.slice(-8).map((e) => (
            <li key={e.seq}>{plainEntry(e, logCtx).join(" · ").replace(/ {2,}/g, " ")}</li>
          ))}
        </ul>
        {since.length > 8 ? <span className="muted small">and {since.length - 8} earlier moves (see the log)</span> : null}
        <button type="button" className="secondary small" onClick={() => setSeenUpTo(log.length)}>
          Got it
        </button>
      </section>
    ) : null;
  // the undo button says what it takes back: the last move in the log
  const lastEntry = log.at(-1);
  const undoText = lastEntry ? `Undo: take back "${logText(lastEntry.action as Move)}"` : "Undo the last move";
  // keyboard shortcuts: Enter confirms, Escape cancels, e ends the turn, u takes the last move back, f folds or unfolds every panel, ? opens the list
  const foldedAll = useRef(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (e.ctrlKey || e.metaKey || e.altKey || (t && ["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(t.tagName) && e.key !== "Escape"))
        return;
      if (ended) return;
      if (e.key === "Enter" && ask && ask.buttons.length > 0) {
        const b = ask.buttons.find((x) => !x.disabled);
        if (b) {
          e.preventDefault();
          b.onClick();
        }
      } else if (e.key === "Escape" && ask) {
        ask.onCancel();
      } else if (e.key === "e" && !ask) {
        const m = mine.find((x) => x.type === "end_turn");
        if (m) play(m);
      } else if (e.key === "u" && !ask) {
        const m = mine.find((x) => x.type === "undo");
        if (m) play(m);
      } else if (e.key === "f") {
        foldedAll.current = !foldedAll.current;
        window.dispatchEvent(new CustomEvent(ALL_EVENT, { detail: !foldedAll.current }));
      } else if (e.key === "?") {
        window.dispatchEvent(new Event("seti-open-settings"));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  const moves = (
    <>
      {ended ? (
        <section className="gameover">
          <h2>{ended.reason === "cancelled" ? "This game was cancelled" : `Game over (${ended.reason})`}</h2>
          <p>
            {ended.reason === "cancelled"
              ? "An administrator cancelled it. Nobody wins or loses, and no rating changes."
              : ended.winners.length > 0
                ? `Winner: ${ended.winners.map((w) => names[w] ?? w + 1).join(", ")}.`
                : "The rival won."}{" "}
            {ended.ranking.map((r) => (
              <span key={r.seat} className="res">
                {names[r.seat] ?? r.seat + 1}: <ScoreIcon size={18} /> <b>{r.score}</b>{" "}
              </span>
            ))}
          </p>
          {ended.reason !== "cancelled" ? <FinalScores view={v} names={names} gameId={gameId} winners={ended.winners} /> : null}
        </section>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      {sinceBar}
      {!online && !ended ? (
        // biome-ignore lint/a11y/useSemanticElements: a plain message line, not an <output> of a form
        <p className="error" role="status">
          The connection was lost. Reconnecting... a move you make now waits until it is back.
        </p>
      ) : null}
      {sandboxMarker && !ended ? <SandboxPanel marker={sandboxMarker as never} send={(a) => sendAction(a)} handCards={hand} /> : null}
      {ask && !ask.inContext && !ask.onCard ? (
        <div className="confirmbar">
          {ask.buttons.map((b) => (
            <button key={b.label} type="button" className="primary" disabled={b.disabled} onClick={b.onClick}>
              {b.label}
            </button>
          ))}
          <button type="button" className="secondary" onClick={ask.onCancel}>
            Cancel
          </button>
        </div>
      ) : null}
      {mine.length > 0 && !ended && !ask && !rowMode ? (
        <div className="movegroups">
          {moveGroups.map((g) => (
            <MoveGroup key={g.title} title={g.title} foldable={false}>
              <div className="moves">
                {g.moves.map((m, i) => (
                  <button key={`${m.type}-${i}`} type="button" onClick={() => play(m)}>
                    {m.type === "launch" || m.type === "scan" || m.type === "analyze" ? <ActionIcon name={m.type} /> : null}
                    {m.type === "launch" || m.type === "scan" || m.type === "analyze" ? (
                      // the name, then the cost as icons (the engine's note of the move says what it costs)
                      <>
                        {Object.keys(costOf(m)).length === 0 ? (
                          `${MAIN_NAMES[m.type]} (free)`
                        ) : (
                          <>
                            {MAIN_NAMES[m.type]} <Cost cost={costOf(m)} />
                          </>
                        )}
                      </>
                    ) : m.type === "undo" ? (
                      undoText
                    ) : (
                      describeMove(m)
                    )}
                  </button>
                ))}
                {g.title === "Main action" ? xenoButtons : null}
              </div>
            </MoveGroup>
          ))}
          {exchanges.length > 0 || orgCardMoves.length > 0 || completeMoves.length > 0 ? (
            <MoveGroup title="Free action" foldable={false}>
              <div className="moves">
                {exchanges.length > 0 ? (
                  <button type="button" onClick={() => setTradeOpen(true)}>
                    Trade resources
                  </button>
                ) : null}
                {orgCardMoves.length > 0 ? (
                  <button type="button" onClick={() => setOrgFreeOpen(true)}>
                    {orgName(orgCardMoves[0]?.org)}: free action
                  </button>
                ) : null}
                {completeMoves.map((m) => (
                  <button key={String(m.card)} type="button" onClick={() => play(m)}>
                    {describeMove(m)}
                  </button>
                ))}
              </div>
            </MoveGroup>
          ) : null}
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
  const clocks = view.remaining ? (
    <span className="clocks">
      {left.map((r, i) => (
        <span
          // biome-ignore lint/suspicious/noArrayIndexKey: seat order
          key={i}
          className={
            r !== null && r < 0
              ? "clock over"
              : r !== null && r < 60_000 && i === v.to_act
                ? "clock running low"
                : i === v.to_act
                  ? "clock running"
                  : "clock"
          }
          title={r !== null && r >= 0 && r < 60_000 ? "Less than a minute left" : undefined}
        >
          {names[i] ?? i + 1} {minutes(r) || "-"}
        </span>
      ))}
    </span>
  ) : null;
  return (
    <GameView
      view={v}
      names={names}
      moves={waiting && !ended ? sendingPrompt : moves}
      previous={previous}
      lastMove={lastMoveOf(log.at(-1)?.events as never)}
      log={<MoveLog entries={log} ctx={logCtx} />}
      goldChoice={
        goldMoves.length > 0
          ? { tiles: goldMoves.map((m) => String(m.tile)), selected: pickedGold, onPick: (t) => setPickedGold(pickedGold === t ? null : t) }
          : undefined
      }
      overlay={
        <>
          {setupOffers.length > 0 && !ended ? (
            <SetupChoice
              kind={setupKind}
              offers={setupOffers}
              selected={setupKind === "quick" ? pickedQuick : pickedOffer === null ? [] : [pickedOffer]}
              need={setupKind === "quick" ? quickNeed : 1}
              quickOffered={(me?.offered_quick ?? []).filter((q) => q !== "?")}
              onSelect={(id) =>
                setupKind === "quick"
                  ? setPickedQuick((old) => (old.includes(id) ? old.filter((c) => c !== id) : [...old, id].slice(-quickNeed)))
                  : setPickedOffer(pickedOffer === id ? null : id)
              }
              onConfirm={() => {
                if (setupMove) {
                  setPickedOffer(null);
                  setPickedQuick([]);
                  sendAction(setupMove); // the choice dialog is the confirmation: no second question about a move that cannot be undone
                }
              }}
            />
          ) : null}
          {tradeOpen && !ended && exchanges.length > 0 ? (
            <TradePanel moves={exchanges} hand={hand} onPlay={play} onPickCard={setRowMode} onClose={() => setTradeOpen(false)} />
          ) : null}
          {orgFreeOpen && !ended && orgCardMoves.length > 0 ? (
            <OrgFreePanel moves={orgCardMoves} hand={hand} display={v.state.card_row} onPlay={play} onClose={() => setOrgFreeOpen(false)} />
          ) : null}
          <button type="button" className="primary boardsfab" onClick={() => setBoardOpen(!boardOpen)} aria-expanded={boardOpen}>
            {boardOpen ? "Close player boards" : "Player boards"}
          </button>
          {boardOpen ? (
            <PlayerBoardPanel
              view={v}
              names={names}
              shown={boardPlayer}
              onShow={setBoardPlayer}
              onClose={() => setBoardOpen(false)}
              choice={slotChoice}
              onPlaceData={mine.some((m) => m.type === "place_data") && !ended ? () => play({ type: "place_data" }) : undefined}
              lower={
                ended
                  ? undefined
                  : {
                      slots: mine.filter((m) => m.type === "place_lower").map((m) => Number(m.slot)),
                      onPlace: (slot) => {
                        const m = mine.find((x) => x.type === "place_lower" && x.slot === slot);
                        if (m) play(m);
                      },
                    }
              }
            />
          ) : null}
        </>
      }
      hand={{
        selectable: pickable,
        selected: picked,
        onSelect: selectCard,
        autoOpen: pending && handMoves.length > 0,
        exertian: {
          selectable: exertianMoves.map((m) => String(m.card)),
          selected: pickedExertian,
          onSelect: (c) => setPickedExertian(pickedExertian === c ? null : c),
          actions: exertianActions,
        },
        actions: handActions,
        offered: offers,
        offeredSelected: pickedOffer,
        onOffer: (c) => setPickedOffer(pickedOffer === c ? null : c),
      }}
      tech={{
        selectable: techMoves.map((m) => Number(m.stack)),
        selected: pickedTech,
        onSelect: (i) => setPickedTech(pickedTech === i ? null : i),
        onConfirm: techOption ? () => play(techOption) : undefined,
      }}
      context={contextNode}
      contextActions={contextActions}
      hint={hints.length > 0 && !ask ? hints.map((h) => <p key={h}>{h}</p>) : undefined}
      spots={{
        items: spots,
        selected: pickedSpot,
        onSelect: (id) => setPickedSpot(pickedSpot === id ? null : id),
        onConfirm: () => spotMove && play(spotMove),
        onCancel: () => setPickedSpot(null),
      }}
      rowFlash={rowMode !== null}
      row={{ selectable: rowSources, selected: pickedBuy, onSelect: selectSource, actions: rowActions }}
      interaction={
        reach.length > 0
          ? {
              probes: reach.map((r) => r.probe),
              selected: probe?.probe ?? null,
              onSelectProbe: (id) => {
                setPendingMove(null);
                setPickedProbe(id === pickedProbe ? null : id);
              },
              // once the destination is confirmed the spaces and their costs go away while the move is carried out
              targets: waiting
                ? []
                : targets.map((t) => ({ to: t.to as [number, number], cost: t.cost, path: t.path as [number, number][] })),
              onTarget: (t) => setPendingMove(t),
              chosen: pendingMove ? `${pendingMove.to[0]}-${pendingMove.to[1]}` : null,
            }
          : undefined
      }
      topExtra={
        <>
          {clocks}
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
