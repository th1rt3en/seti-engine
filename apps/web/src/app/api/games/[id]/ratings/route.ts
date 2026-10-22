// The rating changes of a finished rated game (the game over panel asks for them a moment after the game ended: the Worker writes them to D1 then).
import { getDb } from "@/lib/db";
import { resolveGame } from "@/lib/ids";
import { gameRatingChanges } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }): Promise<Response> {
  const { id: param } = await params;
  const resolved = await resolveGame(getDb(), param); // a number, or a long id
  if (resolved === null) return Response.json({ changes: [] });
  return Response.json({ changes: await gameRatingChanges(getDb(), resolved.id) });
}
