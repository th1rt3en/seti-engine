"use client";
// The lobby of a game: who sits where, who is the host, the settings of the game, and the button that starts it. The game never starts by itself: the
// host starts it, and the button waits until every seat is taken. The page gives the lobby message of the room (it changes as people come and go).
import { describeClock } from "@/lib/queries";
import { useEffect, useRef, useState } from "react";
import { PlayerLink } from "./PlayerLink";

export interface LobbyInfo {
  seats: ({ name: string; num?: number; bot?: true } | null)[];
  /** Seat by seat: the player that the host has invited to the (still free) seat. */
  invites?: ({ name: string; num?: number; status: "pending" | "declined" } | null)[];
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

/** What the host's invitations need from the site (server actions). */
export interface InviteActions {
  search: (q: string) => Promise<{ name: string; num: number | null }[]>;
  invite: (gameId: string, seat: number, name: string) => Promise<{ ok: boolean; message: string }>;
  cancel: (gameId: string, seat: number) => Promise<{ ok: boolean; message: string }>;
}

/** The search box of a free seat: the host types part of a username, picks a registered player and the invitation is sent. */
function InviteBox({ gameId, seat, actions, onDone }: { gameId: string; seat: number; actions: InviteActions; onDone: () => void }) {
  const [q, setQ] = useState("");
  const [found, setFound] = useState<{ name: string; num: number | null }[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const latest = useRef(0);
  const field = useRef<HTMLInputElement>(null);

  useEffect(() => field.current?.focus(), []);

  useEffect(() => {
    const text = q.trim();
    if (text === "") {
      setFound([]);
      return;
    }
    const mine = ++latest.current;
    const timer = setTimeout(() => {
      actions
        .search(text)
        .then((r) => {
          if (mine === latest.current) setFound(r);
        })
        .catch(() => undefined);
    }, 250);
    return () => clearTimeout(timer);
  }, [q, actions]);

  const send = async (name: string) => {
    setBusy(true);
    setMessage("");
    const res = await actions.invite(gameId, seat, name).catch(() => ({ ok: false, message: "The invitation could not be sent." }));
    setBusy(false);
    if (res.ok) onDone();
    else setMessage(res.message);
  };

  return (
    <div className="invitebox">
      <div className="invitesearch">
        <input
          type="search"
          ref={field}
          value={q}
          placeholder="Search a player by username"
          aria-label="Search a registered player by username"
          maxLength={40}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") onDone();
          }}
        />
        <button type="button" className="secondary" onClick={onDone}>
          Close
        </button>
      </div>
      {found.length > 0 ? (
        <ul className="inviteresults">
          {found.map((p) => (
            <li key={p.name}>
              <button type="button" className="secondary" disabled={busy} onClick={() => void send(p.name)}>
                {p.name} <span className="muted small">Send an invitation</span>
              </button>
            </li>
          ))}
        </ul>
      ) : q.trim() !== "" ? (
        <p className="muted small">No registered player found.</p>
      ) : null}
      {message !== "" ? (
        <p className="small" role="alert">
          {message}
        </p>
      ) : null}
    </div>
  );
}

export function LobbyPanel({
  gameId,
  lobby,
  startAction,
  inviteActions,
}: { gameId: string; lobby: LobbyInfo; startAction?: (form: FormData) => Promise<void>; inviteActions?: InviteActions }) {
  const [inviting, setInviting] = useState<number | null>(null);
  const [inviteError, setInviteError] = useState("");
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
            {lobby.seats.map((s, i) => {
              const inv = s === null ? (lobby.invites?.[i] ?? null) : null;
              const canInvite = isHost && s === null && inviteActions !== undefined;
              const cls =
                s === null
                  ? inv
                    ? `lobbyseat invited ${inv.status}`
                    : "lobbyseat free"
                  : i === lobby.you
                    ? "lobbyseat mine"
                    : "lobbyseat";
              return (
                <li key={`${i}-${s?.name ?? inv?.name ?? "free"}-${inv?.status ?? ""}`} className={cls}>
                  <span className="avatar" aria-hidden="true">
                    {s ? (s.bot ? "AI" : s.name.charAt(0).toUpperCase()) : inv ? inv.name.charAt(0).toUpperCase() : "?"}
                  </span>
                  {s ? (
                    <span className="seatname">
                      <PlayerLink num={s.num} name={s.name} />
                    </span>
                  ) : inv ? (
                    <span className="seatname">
                      <PlayerLink num={inv.num} name={inv.name} />
                    </span>
                  ) : canInvite && inviting !== i ? (
                    <button type="button" className="seatinvite" onClick={() => setInviting(i)}>
                      Invite a player
                    </button>
                  ) : canInvite && inviteActions ? (
                    <InviteBox gameId={gameId} seat={i} actions={inviteActions} onDone={() => setInviting(null)} />
                  ) : (
                    <span className="seatname">Waiting for a player...</span>
                  )}
                  <span>
                    {s?.bot ? <span className="pill">AI</span> : null}
                    {s && i === lobby.hostSeat ? <span className="pill">host</span> : null}
                    {s && i === lobby.you ? <span className="pill">you</span> : null}
                    {inv ? <span className="pill">{inv.status === "pending" ? "Invited: waiting for an answer" : "Declined"}</span> : null}
                    {inv && isHost && inviteActions ? (
                      <button
                        type="button"
                        className="secondary seatcancel"
                        onClick={() => {
                          setInviteError("");
                          inviteActions
                            .cancel(gameId, i)
                            .then((r) => {
                              if (!r.ok) setInviteError(r.message);
                            })
                            .catch(() => setInviteError("The invitation could not be taken back."));
                        }}
                      >
                        {inv.status === "pending" ? "Cancel" : "Clear"}
                      </button>
                    ) : null}
                  </span>
                </li>
              );
            })}
          </ol>
          {inviteError !== "" ? (
            <p className="small" role="alert">
              {inviteError}
            </p>
          ) : null}
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
