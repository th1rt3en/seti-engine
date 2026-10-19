// The settings of the game page of the signed-in player (GET), and saving them (PUT). A visitor who is not signed in has none: 401.
import { getDb } from "@/lib/db";
import { currentUser } from "@/lib/session";
import { getSettings, saveSettings } from "@/lib/userSettings";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  const user = await currentUser();
  if (user === null) return Response.json({ settings: {} }, { status: 401 });
  return Response.json({ settings: await getSettings(getDb(), user.id) });
}

export async function PUT(req: Request): Promise<Response> {
  const user = await currentUser();
  if (user === null) return Response.json({ settings: {} }, { status: 401 });
  const body = (await req.json().catch(() => null)) as { settings?: unknown } | null;
  return Response.json({ settings: await saveSettings(getDb(), user.id, body?.settings) });
}
