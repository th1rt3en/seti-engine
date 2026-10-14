// One step of a replay: the view of that state for a viewer (a seat, or the spectator). Only finished games can be replayed.
import { replayStates, spectate } from "@/lib/replay";
import { gameReplay } from "@/lib/worker";
import type { View } from "@seti/protocol";

export const dynamic = "force-dynamic";

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const url = new URL(request.url);
  const replay = await gameReplay(id);
  if (replay === null) return Response.json({ ok: false, message: "the game is not over or does not exist" }, { status: 404 });
  const states = await replayStates(id, replay.header.options, replay.actions);
  const step = Math.min(states.length - 1, Math.max(0, Number(url.searchParams.get("step") ?? 0) || 0));
  const viewerParam = url.searchParams.get("viewer");
  const viewer = viewerParam === null || viewerParam === "spectator" ? null : Number(viewerParam);
  const state = states[step];
  if (state === undefined) return Response.json({ ok: false, message: "no such step" }, { status: 404 });
  const view: View = await spectate(state, viewer);
  return Response.json({ ok: true, step, view });
}
