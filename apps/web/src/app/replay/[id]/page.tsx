import { PlayerNames } from "@/components/PlayerLink";
import { ReplayViewer } from "@/components/ReplayViewer";
import { getDb } from "@/lib/db";
import { resolveGame } from "@/lib/ids";
import { gameReplay } from "@/lib/worker";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function Replay({ params }: { params: Promise<{ id: string }> }) {
  const { id: param } = await params;
  const resolved = await resolveGame(getDb(), param);
  if (resolved === null) notFound();
  const found = resolved as NonNullable<typeof resolved>;
  if (found.redirect !== null) permanentRedirect(`/replay/${found.redirect}`);
  const id = found.id;
  const replay = await gameReplay(id);
  if (replay === null) {
    return (
      <>
        <h1>Replay</h1>
        <p>This game is not finished (or does not exist), so it cannot be replayed yet.</p>
        <p>
          <Link href={`/games/${param}`}>Go to the game</Link>
        </p>
      </>
    );
  }
  return (
    <>
      <h1>Replay of game #{param}</h1>
      <p className="muted small">
        <PlayerNames seats={replay.header.seats.map((s) => ({ name: s.name, num: s.num ?? null }))} separator=", " /> ·{" "}
        {replay.header.rated ? "rated" : "casual"} · {replay.actions.length} actions
      </p>
      <ReplayViewer id={id} replay={replay} />
    </>
  );
}
