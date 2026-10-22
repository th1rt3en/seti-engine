// The statistics of one finished game (the game over panel asks for them a moment after the game ended: the Worker has the engine count them then).
import { getDb } from "@/lib/db";
import { resolveGame } from "@/lib/ids";
import { gameStatRows } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }): Promise<Response> {
  const { id: param } = await params;
  const resolved = await resolveGame(getDb(), param); // a number, or a long id
  if (resolved === null) return Response.json({ players: [] });
  return Response.json({ players: await gameStatRows(getDb(), resolved.id) });
}
