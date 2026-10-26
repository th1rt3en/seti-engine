import { glyphToken } from "@/lib/glyphids";
// Gains and costs as small icons with a number: the log shows what a move gave and took, and the confirmation of a move shows what it costs and
// what it gives. The kinds are the engine's ("vp", "credit", "energy", "publicity", "data", "card", ...).
import type { ReactNode } from "react";
import {
  AlienCardIcon,
  CreditIcon,
  DataIcon,
  DeckCardIcon,
  EnergyIcon,
  ExofossilIcon,
  IncomeIcon,
  MoveIcon,
  PublicityIcon,
  RandomCardIcon,
  ScoreIcon,
  SignalTokenIcon,
  TraceIcon,
} from "./Icons";

/** A glyph token of the Glyphids: the icon of the resource. */
function GlyphTokenIcon({ size }: { size: number }) {
  const src = glyphToken("orange");
  return src ? <img src={src} alt="glyph token" width={size} height={size} /> : <span className="muted small">token</span>;
}

const ICONS: Record<string, (size: number) => ReactNode> = {
  vp: (s) => <ScoreIcon size={s} />,
  credit: (s) => <CreditIcon size={s} />,
  energy: (s) => <EnergyIcon size={s} />,
  publicity: (s) => <PublicityIcon size={s} />,
  data: (s) => <DataIcon size={s} />,
  card: (s) => <DeckCardIcon size={s} />,
  card_random: (s) => <RandomCardIcon size={s} />,
  tuck: (s) => <IncomeIcon size={s} />,
  card_any: (s) => <DeckCardIcon size={s} />,
  alien_card: (s) => <AlienCardIcon size={s} />,
  exofossil: (s) => <ExofossilIcon size={s} />,
  trace: (s) => <TraceIcon size={s} />,
  signal_token: (s) => <SignalTokenIcon size={s} />,
  move: (s) => <MoveIcon size={s} />,
  token: (s) => <GlyphTokenIcon size={s} />,
};

const NAMES: Record<string, string> = {
  vp: "points",
  credit: "credit",
  energy: "energy",
  publicity: "publicity",
  data: "data",
  card: "card",
  card_random: "random card",
  tuck: "tuck for income",
  card_any: "card",
  alien_card: "alien card",
  exofossil: "exofossil",
  trace: "trace",
  signal_token: "signal token",
  move: "movement",
  token: "glyph token",
};

/** Only the icon of a kind of resource (credit, energy, card ...), or its name when it has none. */
export function KindIcon({ kind, size = 18 }: { kind: string; size?: number }) {
  const icon = ICONS[kind];
  return icon ? <span title={NAMES[kind] ?? kind}>{icon(size)}</span> : <span>{NAMES[kind] ?? kind}</span>;
}

/** One amount with its icon: "+2" with the globe, "−1" with a credit. `signed` shows a plus sign for a gain. */
export function Amount({ kind, n, signed = false, size = 18 }: { kind: string; n: number; signed?: boolean; size?: number }) {
  const icon = ICONS[kind];
  const text = signed ? (n > 0 ? `+${n}` : `−${Math.abs(n)}`) : String(n);
  return (
    <span className={signed ? (n > 0 ? "amount gain" : "amount loss") : "amount"} title={`${text} ${NAMES[kind] ?? kind}`}>
      {icon ? icon(size) : <span className="muted small">{NAMES[kind] ?? kind}</span>}
      <b>{text}</b>
    </span>
  );
}

/** The net changes of a step ({ vp: 2, credit: -1 }) as signed amounts. */
export function Changes({ changes, size }: { changes: Record<string, number>; size?: number }) {
  return (
    <span className="amounts">
      {Object.entries(changes).map(([kind, n]) => (
        <Amount key={kind} kind={kind} n={n} signed size={size} />
      ))}
    </span>
  );
}

/** What a move or space gives, as the engine lists it ([{ t: "vp", n: 5 }, { t: "publicity", n: 1 }]). */
export function Rewards({ list, size }: { list: { t: string; n: number }[]; size?: number }) {
  if (list.length === 0) return <span className="muted">nothing</span>;
  return (
    <span className="amounts">
      {list.map((r) => (
        <Amount key={r.t} kind={r.t} n={r.n} size={size} />
      ))}
    </span>
  );
}

/** A cost ({ credit: 1, energy: 1 }) as amounts, or "free". */
export function Cost({ cost, size }: { cost: Record<string, number>; size?: number }) {
  const list = Object.entries(cost).map(([t, n]) => ({ t, n }));
  if (list.length === 0) return <b>free</b>;
  return <Rewards list={list} size={size} />;
}
