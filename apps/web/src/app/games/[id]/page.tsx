import { GameClient } from "@/components/GameClient";
import { GameSettings } from "@/components/GameSettings";
import { ShortcutsHelp } from "@/components/ShortcutsHelp";
import { loadConfig } from "@/lib/config";
import { currentUser } from "@/lib/session";
import { gameMeta } from "@/lib/worker";
import { headers } from "next/headers";
import Link from "next/link";
import { joinAction, leaveAction } from "../../actions";

export const dynamic = "force-dynamic";

interface Meta {
  status: string;
  rated: boolean;
  seats: ({ id: string; name: string } | null)[];
  host: string;
  options: { players: number };
}

export default async function Game({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
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
  return (
    <>
      <h1>
        Game {id.slice(0, 8)} <span className="pill">{meta.rated ? "rated" : "casual"}</span>{" "}
        <span className="pill">{meta.options.players === 1 ? "solo" : `${meta.options.players} players`}</span> <GameSettings />{" "}
        <ShortcutsHelp />
      </h1>
      {meta.status === "lobby" ? (
        <p className="small">
          {hostName ? `Host: ${hostName}. ` : ""}Invite players with this link:{" "}
          <input readOnly value={`${origin}/games/${id}`} aria-label="Invite link" style={{ width: "min(32rem, 100%)" }} />
        </p>
      ) : null}
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
      <GameClient gameId={id} wsBase={loadConfig().workerWsUrl} names={names} signedIn={user !== null} />
      {meta.status === "finished" ? (
        <p>
          <Link href={`/replay/${id}`}>Replay the game</Link>
        </p>
      ) : null}
    </>
  );
}
