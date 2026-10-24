// One step of a replay: the view of that state for a viewer (a seat, or the spectator), and the view before it. Only finished games can be replayed.
import { getDb } from "@/lib/db";
import { resolveGame } from "@/lib/ids";
import { replayStep } from "@/lib/replay";
import { gameReplay } from "@/lib/worker";

export const dynamic = "force-dynamic";

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id: param } = await params;
  const url = new URL(request.url);
  const resolved = await resolveGame(getDb(), param); // a number, or a long id
  if (resolved === null) return Response.json({ ok: false, message: "no such game" }, { status: 404 });
  const replay = await gameReplay(resolved.id);
  if (replay === null) return Response.json({ ok: false, message: "the game is not over or does not exist" }, { status: 404 });
  const step = Math.min(replay.actions.length, Math.max(0, Number(url.searchParams.get("step") ?? 0) || 0));
  const viewerParam = url.searchParams.get("viewer");
  const viewer = viewerParam === null || viewerParam === "spectator" ? null : Number(viewerParam);
  if (viewer !== null && !(Number.isInteger(viewer) && viewer >= 0 && viewer <= 3))
    return Response.json({ ok: false, message: "the viewer is a seat from 0 to 3, or spectator" }, { status: 400 });
  try {
    // a game with no `rngEncoding` was played before the random state became a string
    const got = await replayStep(replay.header.options, replay.actions, step, viewer, replay.header.rngEncoding ?? "double");
    return Response.json({ ok: true, step: got.step, view: got.view, previous: got.previous });
  } catch {
    return Response.json({ ok: false, message: "the engine could not replay this game" }, { status: 502 });
  }
}
