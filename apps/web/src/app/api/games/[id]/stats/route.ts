// The statistics of one finished game (the game over panel asks for them a moment after the game ended: the Worker has the engine count them then).
import { getDb } from "@/lib/db";
import { gameStatRows } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }): Promise<Response> {
  const { id } = await params;
  return Response.json({ players: await gameStatRows(getDb(), id) });
}
