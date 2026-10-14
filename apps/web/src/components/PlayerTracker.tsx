// The tracker beside the board: for every player the score, the income of each kind (the income card plus the tucked cards), the cards
// tucked for each kind of income, the completed missions and the end-of-game scoring cards. The numbers come from the engine's view
// (`view.trackers`); nothing is worked out here.
import { PLAYER_COLOR } from "@/lib/geometry";
import type { View } from "@seti/protocol";
import type { ReactNode } from "react";
import { ScoreIcon } from "./Icons";

const KINDS = [
  { key: "credit", label: "Credits", swatch: "#e5b83a" },
  { key: "energy", label: "Energy", swatch: "#4fb06d" },
  { key: "card", label: "Cards", swatch: "#4c8fd6" },
] as const;

export function PlayerTracker({ view, names, previous }: { view: View; names: string[]; previous?: View | null }) {
  const s = view.state;
  const who = (i: number): string => (s.rival && i === s.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`));
  const trackers = view.trackers ?? []; // an older engine does not send them
  if (trackers.length === 0) return null;
  const columns = s.players.length + 1;

  const group = (title: string): ReactNode => (
    <tr className="group">
      <th scope="row" colSpan={columns}>
        {title}
      </th>
    </tr>
  );
  const row = (label: ReactNode, values: (number | string)[], className?: string, key?: string): ReactNode => (
    <tr key={key} className={className}>
      <th scope="row">{label}</th>
      {values.map((v, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: seat order
        <td key={i}>{v}</td>
      ))}
    </tr>
  );
  const kindLabel = (k: (typeof KINDS)[number]): ReactNode => (
    <>
      <span className="swatch" style={{ background: k.swatch }} />
      {k.label}
    </>
  );

  return (
    <section className="tracker" aria-label="Player tracker">
      <table>
        <thead>
          <tr>
            <th scope="col">
              <span className="sr">Player</span>
            </th>
            {s.players.map((p) => (
              <th key={p.index} scope="col" className={view.to_act === p.index ? "active" : undefined}>
                <span className="dot" style={{ background: PLAYER_COLOR[p.color] ?? "#fff" }} />
                <span className="pname">{who(p.index)}</span>
                {view.viewer === p.index ? <span className="pill">you</span> : null}
                {p.passed ? <span className="pill">passed</span> : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {row(
            <>
              <ScoreIcon size={18} /> Score
            </>,
            trackers.map((t) => t.score),
            "score",
          )}
          {group("Income each round")}
          {KINDS.map((k) =>
            row(
              kindLabel(k),
              trackers.map((t) => t.income[k.key] ?? 0),
              undefined,
              `income-${k.key}`,
            ),
          )}
          {group("Cards tucked for income")}
          {KINDS.map((k) =>
            row(
              kindLabel(k),
              trackers.map((t) => t.tucked[k.key] ?? 0),
              undefined,
              `tucked-${k.key}`,
            ),
          )}
          {group("Missions and end of game")}
          {row(
            "Missions done",
            trackers.map((t) => t.missions_done),
          )}
          {row(
            "End-game cards",
            trackers.map((t) => t.end_cards),
          )}
          {group("Now")}
          {row(
            "Credits",
            s.players.map((p) => p.credits),
          )}
          {row(
            "Energy",
            s.players.map((p) => p.energy),
          )}
          {row(
            "Publicity",
            s.players.map((p) => p.publicity),
          )}
          <tr>
            <th scope="row">Data pile</th>
            {s.players.map((p) => {
              const grew =
                previous !== null && previous !== undefined && p.data_pool > (previous.state.players[p.index]?.data_pool ?? p.data_pool);
              return (
                <td key={p.index} className={grew ? "flash" : undefined}>
                  <span className="datapile" title={`${p.data_pool} data in the pool`}>
                    <svg width={18} height={18} viewBox="-50 -50 100 100" aria-hidden="true">
                      <circle r={44} fill="url(#pc-data-top)" stroke="#0a2a66" strokeWidth={5} />
                      <circle r={30} fill="url(#pc-data-dimple)" />
                    </svg>
                    {p.data_pool}
                  </span>
                </td>
              );
            })}
          </tr>
          {row(
            "Cards in hand",
            s.players.map((p) => view.counts.hands[p.index] ?? 0),
          )}
        </tbody>
      </table>
    </section>
  );
}
