"use client";
// The lobby of a game: who sits where, who is the host, the settings of the game, and the button that starts it. The game never starts by itself: the
// host starts it, and the button waits until every seat is taken. The page gives the lobby message of the room (it changes as people come and go).
import { describeClock } from "@/lib/queries";
import { PlayerLink } from "./PlayerLink";

export interface LobbyInfo {
  seats: ({ name: string; num?: number; bot?: true } | null)[];
  hostSeat: number;
  you: number | null;
  full: boolean;
  rated: boolean;
  /** The host chose the seed of the game. */
  seeded?: boolean;
  options: {
    players: number;
    difficulty?: number;
    expansion?: boolean;
    organizations?: boolean;
    beginner_organizations?: boolean;
    neutral_quick_start?: boolean;
    promo_cards?: boolean;
    promo_set_2?: boolean;
    sandbox?: boolean;
  };
  clock?: unknown;
}

/** The settings of a game as lines of a list: what the host chose when the table was made. */
export function settingLines(lobby: LobbyInfo): { label: string; value: string }[] {
  const o = lobby.options;
  const yes = (b: boolean | undefined): string => (b ? "yes" : "no");
  const lines = [
    { label: "Players", value: o.players === 1 ? "solo, against the rival" : String(o.players) },
    ...(o.players === 1 ? [{ label: "Rival difficulty", value: String(o.difficulty ?? 3) }] : []),
    { label: "Rating", value: lobby.rated ? "rated" : "friendly" },
    { label: "Clock", value: lobby.clock ? describeClock(JSON.stringify(lobby.clock)) : "no clock" },
    { label: "Space Agencies", value: yes(o.expansion) },
  ];
  if (o.expansion) {
    lines.push(
      { label: "Organizations", value: o.organizations ? (o.beginner_organizations ? "yes, the beginner ones" : "yes") : "no" },
      { label: "Neutral quick start cards", value: yes(o.neutral_quick_start) },
    );
  }
  if (o.promo_cards || o.promo_set_2) lines.push({ label: "Promo cards", value: o.promo_set_2 ? "both sets" : "set 1" });
  if (lobby.seeded) lines.push({ label: "Seed", value: "chosen by the host" });
  if (o.sandbox) lines.push({ label: "Practice game", value: "cards, resources and discs can be changed freely" });
  return lines;
}

export function LobbyPanel({
  gameId,
  lobby,
  startAction,
}: { gameId: string; lobby: LobbyInfo; startAction?: (form: FormData) => Promise<void> }) {
  const isHost = lobby.you !== null && lobby.you === lobby.hostSeat;
  const taken = lobby.seats.filter((s) => s !== null).length;
  const missing = lobby.seats.length - taken;
  const missingText = `Waiting for ${missing} more ${missing === 1 ? "player" : "players"}`;
  return (
    <section className="card lobbypanel" aria-label="The lobby of the game">
      <div className="lobbyhead">
        <h2>{lobby.full ? "Everybody is here" : "Waiting for players"}</h2>
        <span className="lobbycount">
          {taken} of {lobby.seats.length} seats taken
        </span>
      </div>
      <div className="lobbygrid">
        <div>
          <h3>Players</h3>
          <ol className="lobbyseats">
            {lobby.seats.map((s, i) => (
              <li
                key={`${i}-${s?.name ?? "free"}`}
                className={s === null ? "lobbyseat free" : i === lobby.you ? "lobbyseat mine" : "lobbyseat"}
              >
                <span className="avatar" aria-hidden="true">
                  {s ? (s.bot ? "AI" : s.name.charAt(0).toUpperCase()) : "?"}
                </span>
                {s ? (
                  <span className="seatname">
                    <PlayerLink num={s.num} name={s.name} />
                  </span>
                ) : (
                  <span className="seatname">Waiting for a player...</span>
                )}
                <span>
                  {s?.bot ? <span className="pill">AI</span> : null}
                  {s && i === lobby.hostSeat ? <span className="pill">host</span> : null}
                  {s && i === lobby.you ? <span className="pill">you</span> : null}
                </span>
              </li>
            ))}
          </ol>
        </div>
        <div>
          <h3>The game</h3>
          <dl className="lobbyconfig">
            {settingLines(lobby).map((l) => (
              <div key={l.label}>
                <dt>{l.label}</dt>
                <dd>{l.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
      {isHost && startAction ? (
        <form action={startAction} className="lobbystart">
          <input type="hidden" name="id" value={gameId} />
          <button type="submit" className="primary big" disabled={!lobby.full}>
            Start the game
          </button>
          <span className="muted small">
            {lobby.full ? "Everybody is seated." : `${missingText}: the button is on when every seat is taken.`}
          </span>
        </form>
      ) : (
        <p className="lobbywait">
          {lobby.full
            ? "Everybody is seated. The game starts when the host starts it."
            : `${missingText}. The host starts the game once every seat is taken.`}
        </p>
      )}
    </section>
  );
}
