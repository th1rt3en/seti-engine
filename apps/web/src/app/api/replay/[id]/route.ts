// One step of a replay: the view of that state for a viewer (a seat, or the spectator), and the view before it. Only finished games can be replayed.
import { replayStep } from "@/lib/replay";
import { gameReplay } from "@/lib/worker";

export const dynamic = "force-dynamic";

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const url = new URL(request.url);
  const replay = await gameReplay(id);
  if (replay === null) return Response.json({ ok: false, message: "the game is not over or does not exist" }, { status: 404 });
  const step = Math.min(replay.actions.length, Math.max(0, Number(url.searchParams.get("step") ?? 0) || 0));
  const viewerParam = url.searchParams.get("viewer");
  const viewer = viewerParam === null || viewerParam === "spectator" ? null : Number(viewerParam);
  try {
    // a game with no `rngEncoding` was played before the random state became a string
    const got = await replayStep(replay.header.options, replay.actions, step, viewer, replay.header.rngEncoding ?? "double");
    return Response.json({ ok: true, step: got.step, view: got.view, previous: got.previous });
  } catch {
    return Response.json({ ok: false, message: "the engine could not replay this game" }, { status: 502 });
  }
}
