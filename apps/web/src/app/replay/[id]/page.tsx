import { ReplayViewer } from "@/components/ReplayViewer";
import { gameReplay } from "@/lib/worker";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function Replay({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const replay = await gameReplay(id);
  if (replay === null) {
    return (
      <>
        <h1>Replay</h1>
        <p>This game is not finished (or does not exist), so it cannot be replayed yet.</p>
        <p>
          <Link href={`/games/${id}`}>Go to the game</Link>
        </p>
      </>
    );
  }
  return (
    <>
      <h1>Replay of game {id.slice(0, 8)}</h1>
      <p className="muted small">
        {replay.header.seats.map((s) => s.name).join(", ")} · {replay.header.rated ? "rated" : "casual"} · {replay.actions.length} actions
      </p>
      <ReplayViewer id={id} replay={replay} />
    </>
  );
}
