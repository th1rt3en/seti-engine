// The invitations that wait for an answer from the signed-in player (the toast at the corner of every page asks for them every few seconds).
import { getDb } from "@/lib/db";
import { pendingInvites } from "@/lib/invites";
import { currentUser } from "@/lib/session";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  const user = await currentUser();
  if (user === null || user.isGuest) return Response.json({ invites: [] }, { status: 401 });
  return Response.json({ invites: await pendingInvites(getDb(), user.id) });
}
