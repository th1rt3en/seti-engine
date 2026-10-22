import { GameClient } from "@/components/GameClient";
import { GameSettings } from "@/components/GameSettings";
import { PlayerLink } from "@/components/PlayerLink";
import { ShortcutsHelp } from "@/components/ShortcutsHelp";
import { type BotRecord, describeRecord, loadBotRecords } from "@/lib/botRecord";
import { loadConfig } from "@/lib/config";
import { getDb } from "@/lib/db";
import { resolveGame } from "@/lib/ids";
import { botVersions } from "@/lib/queries";
import { currentUser } from "@/lib/session";
import { gameMeta } from "@/lib/worker";
import { headers } from "next/headers";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { addBotAction, joinAction, leaveAction, removeBotAction } from "../../actions";

export const dynamic = "force-dynamic";

interface Meta {
  status: string;
  rated: boolean;
  seats: ({ id: string; name: string; num?: number; bot?: { model: string } } | null)[];
  host: string;
  options: { players: number };
}

export default async function Game({
  params,
  searchParams,
}: { params: Promise<{ id: string }>; searchParams: Promise<{ error?: string }> }) {
  const { id: param } = await params;
  const { error } = await searchParams;
  // the address is the number of the game; the long id (an address from before the numbers) goes to it
  const resolved = await resolveGame(getDb(), param);
  if (resolved === null) notFound();
  const found = resolved as NonNullable<typeof resolved>;
  if (found.redirect !== null) permanentRedirect(`/games/${found.redirect}`);
  const id = found.id;
  const num = Number(param);
  const user = await currentUser();
  const meta = (await gameMeta(id)) as Meta | null;
  if (meta === null) {
    return (
      <>
        <h1>Game not found</h1>
        <p>The address may be wrong, or the table was deleted: a table that everybody left is removed.</p>
        <p>
          <Link href="/lobby">Back to the lobby</Link>
        </p>
      </>
    );
  }
  const names = meta.seats.map((s) => s?.name ?? "free seat");
  const seated = user !== null && meta.seats.some((s) => s?.id === user.id);
  const h = await headers();
  const origin = `${h.get("x-forwarded-proto") ?? "http"}://${h.get("host") ?? "localhost:3000"}`;
  const hostName = meta.seats.find((x) => x?.id === meta.host)?.name;
  const open = meta.status === "lobby" && meta.seats.some((s) => s === null);
  const isHost = user !== null && meta.host === user.id && meta.status === "lobby";
  const models = isHost ? (await botVersions(getDb())).filter((v) => v.live) : [];
  const records = isHost ? await loadBotRecords(getDb()) : new Map<string, BotRecord>();
  return (
    <>
      <h1>
        Game #{num} <span className="pill">{meta.rated ? "rated" : "casual"}</span>{" "}
        <span className="pill">{meta.options.players === 1 ? "solo" : `${meta.options.players} players`}</span> <GameSettings />{" "}
        <ShortcutsHelp />
      </h1>
      {meta.status === "lobby" ? (
        <p className="small">
          {hostName ? (
            <>
              Host: <PlayerLink num={meta.seats.find((x) => x?.id === meta.host)?.num} name={hostName} />.{" "}
            </>
          ) : null}
          Invite players with this link:{" "}
          <input readOnly value={`${origin}/games/${num}`} aria-label="Invite link" style={{ width: "min(32rem, 100%)" }} />
        </p>
      ) : null}
      {error ? (
        <p className="card" role="alert">
          {error}
        </p>
      ) : null}
      {isHost && open && models.length > 0 && meta.options.players === 2 ? (
        <form action={addBotAction} className="card addai">
          <input type="hidden" name="id" value={id} />
          <h2>Add an AI player</h2>
          <label>
            Version
            <select name="model">
              {models.map((m) => (
                <option key={m.version} value={m.version}>
                  {m.version} · {describeRecord(records.get(m.version))}
                </option>
              ))}
            </select>
          </label>
          <label className="consent">
            <input type="checkbox" name="consent" required />
            <span>I agree that this game is recorded and used to train the AI. A game with an AI is never rated.</span>
          </label>
          <button type="submit" className="primary addai-button">
            Add the AI
          </button>
        </form>
      ) : null}
      {isHost
        ? meta.seats.flatMap((s, seat) =>
            s?.bot ? (
              <form action={removeBotAction} key={s.id}>
                <input type="hidden" name="id" value={id} />
                <input type="hidden" name="seat" value={seat} />
                <button type="submit" className="secondary">
                  Remove {s.name}
                </button>
              </form>
            ) : (
              []
            ),
          )
        : null}
      {user && !seated && open ? (
        <form action={joinAction}>
          <input type="hidden" name="id" value={id} />
          <button type="submit" className="primary">
            Take a seat
          </button>
        </form>
      ) : null}
      {user && seated && meta.status === "lobby" ? (
        <form action={leaveAction}>
          <input type="hidden" name="id" value={id} />
          <button type="submit" className="secondary">
            Leave the game
          </button>
        </form>
      ) : null}
      {!user && meta.status === "lobby" ? (
        <p>
          <Link href="/login">Log in</Link> or <Link href="/">play as a guest</Link> to take a seat.
        </p>
      ) : null}
      {meta.status === "cancelled" ? (
        <p className="card">
          This game was cancelled. Nobody won or lost and no rating changed. <Link href="/lobby">Back to the lobby</Link>
        </p>
      ) : null}
      <GameClient
        gameId={id}
        gameNum={num}
        wsBase={loadConfig().workerWsUrl}
        names={names}
        nums={meta.seats.map((s) => s?.num ?? null)}
        signedIn={user !== null}
      />
      {meta.status === "finished" ? (
        <p>
          <Link href={`/replay/${num}`}>Replay the game</Link>
        </p>
      ) : null}
    </>
  );
}
