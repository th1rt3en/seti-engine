"use client";
import { OPEN_BOARD_EVENT } from "@/lib/boardEvent";
// The tracker beside the board: for every player the score, the income of each kind (the income card plus the tucked cards), the cards
// tucked for each kind of income, the completed missions and the end-of-game scoring cards. The numbers come from the engine's view
// (`view.trackers`); nothing is worked out here.
import { PLAYER_COLOR } from "@/lib/geometry";
import { cardName } from "@/lib/moves";
import { ORG_NAMES } from "@/lib/moves";
import type { View } from "@seti/protocol";
import type { ReactNode } from "react";
import { CreditIcon, DataIcon, DeckCardIcon, EnergyIcon, ExofossilIcon, PublicityIcon, ScoreIcon, SignalTokenIcon } from "./Icons";

const KINDS = [
  { key: "credit", label: "Credits", icon: <CreditIcon size={18} /> },
  { key: "energy", label: "Energy", icon: <EnergyIcon size={18} /> },
  { key: "card", label: "Cards", icon: <DeckCardIcon size={18} /> },
] as const;

/** A label with its icon in front of it. */
const labelled = (icon: ReactNode, text: string): ReactNode => (
  <span className="rowlabel">
    {icon}
    {text}
  </span>
);

/** The square that stands for completed missions (silver) and end-of-game scoring cards (gold). */
const metal = (kind: "silver" | "gold", text: string): ReactNode => (
  <span className="rowlabel">
    <span className={`metal ${kind}`} aria-hidden="true" />
    {text}
  </span>
);

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
  const kindLabel = (k: (typeof KINDS)[number]): ReactNode => labelled(k.icon, k.label);

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
                {s.rival && p.index === s.rival.index ? null : (
                  <button
                    type="button"
                    className="boardlink"
                    title={`Look at the board of ${who(p.index)}: its computer and techs`}
                    onClick={() => window.dispatchEvent(new CustomEvent(OPEN_BOARD_EVENT, { detail: p.index }))}
                  >
                    board
                  </button>
                )}
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
            metal("silver", "Missions done"),
            trackers.map((t) => t.missions_done),
            "metalrow silverrow",
          )}
          {row(
            metal("gold", "End-game cards"),
            trackers.map((t) => t.end_cards),
            "metalrow goldrow",
          )}
          {group("Now")}
          {row(
            labelled(<CreditIcon size={18} />, "Credits"),
            s.players.map((p) => p.credits),
          )}
          {row(
            labelled(<EnergyIcon size={18} />, "Energy"),
            s.players.map((p) => p.energy),
          )}
          {row(
            labelled(<PublicityIcon size={18} />, "Publicity"),
            s.players.map((p) => p.publicity),
          )}
          <tr>
            <th scope="row">{labelled(<DataIcon size={18} />, "Data pile")}</th>
            {s.players.map((p) => {
              const grew =
                previous !== null && previous !== undefined && p.data_pool > (previous.state.players[p.index]?.data_pool ?? p.data_pool);
              return (
                <td key={p.index} className={grew ? "flash" : undefined}>
                  <span className="datapile" title={`${p.data_pool} data in the pool`}>
                    {p.data_pool}
                  </span>
                </td>
              );
            })}
          </tr>
          {s.species.some((sp) => sp.discovered && sp.species === "oumuamua")
            ? row(
                labelled(<ExofossilIcon size={18} />, "Exofossils"),
                s.players.map((p) => p.exofossils),
              )
            : null}
          {s.options.expansion
            ? row(
                labelled(<SignalTokenIcon size={18} />, "Signal tokens"),
                s.players.map((p) => p.signal_tokens),
              )
            : null}
          {s.options.organizations
            ? row(
                labelled(<span className="muted small">Org</span>, "Organization"),
                s.players.map((p) => (p.organization ? (ORG_NAMES[p.organization] ?? p.organization) : "—")),
              )
            : null}
          {row(
            labelled(<DeckCardIcon size={18} />, "Cards in hand"),
            s.players.map((p) => view.counts.hands[p.index] ?? 0),
          )}
          {s.pluto_owner !== null && s.pluto_owner !== undefined && s.planets.pluto ? (
            <tr>
              <th scope="row">{labelled(<ScoreIcon size={18} />, "Pluto (promo card)")}</th>
              <td colSpan={s.players.length}>
                {who(s.pluto_owner)} only. Orbiter:{" "}
                {s.planets.pluto.orbiters.length > 0 ? who(s.planets.pluto.orbiters[0] as number) : "free"}
                {" · "}Lander: {s.planets.pluto.landers.length > 0 ? who(s.planets.pluto.landers[0] as number) : "free"}
              </td>
            </tr>
          ) : null}
          {s.species.some((sp) => sp.discovered && sp.species === "exertians") ? (
            <>
              {group("Exertian danger (the most danger loses a tenth of its points)")}
              {row(
                labelled(<ScoreIcon size={18} />, "Species board"),
                trackers.map((t) => t.danger_board),
              )}
              {row(
                labelled(<DeckCardIcon size={18} />, "Played cards"),
                // only the owner sees the danger of the cards; the others see how many lie face down
                trackers.map((t) =>
                  t.danger_cards === null || t.danger_cards === undefined ? `${t.exertian_played} face down` : t.danger_cards,
                ),
              )}
              {row(
                labelled(<ScoreIcon size={18} />, "Danger"),
                trackers.map((t) =>
                  t.danger_cards === null || t.danger_cards === undefined
                    ? `${t.danger_board} + ${t.exertian_played} card${t.exertian_played === 1 ? "" : "s"}`
                    : t.danger_board + t.danger_cards,
                ),
                "score",
              )}
            </>
          ) : null}
          {s.species.some((sp) => sp.discovered && sp.species === "centaurians") ? (
            <>
              {group("Centaurian messages, resolved in the order sent")}
              <tr>
                <th scope="row">{labelled(<ScoreIcon size={18} />, "Messages waiting (first on top)")}</th>
                {s.players.map((p) => {
                  // ALIEN-CEN-03: the message milestone comes first (placed at discovery), then the message cards in the order played
                  const queue = [
                    ...p.messages.map((target) => ({ target, label: "Milestone tile" })),
                    ...p.message_cards.map((m) => ({ target: m.target, label: cardName(m.card) })),
                  ];
                  return (
                    <td key={p.index}>
                      {queue.length === 0 ? (
                        "none"
                      ) : (
                        <ol className="messagequeue">
                          {queue.map((m, n) => (
                            // biome-ignore lint/suspicious/noArrayIndexKey: the position in the queue is the identity
                            <li key={n} title={`Reached at ${m.target} points`}>
                              {m.label} at {m.target}
                            </li>
                          ))}
                        </ol>
                      )}
                    </td>
                  );
                })}
              </tr>
            </>
          ) : null}
        </tbody>
      </table>
    </section>
  );
}
