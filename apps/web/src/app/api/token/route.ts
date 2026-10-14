import { mintToken } from "@/lib/auth";
import { loadConfig } from "@/lib/config";
import { currentUser } from "@/lib/session";
import { NextResponse } from "next/server";

// A short-lived token for the WebSocket to the Worker (decision D16). The browser asks for a new one each time it connects.
export async function GET() {
  const user = await currentUser();
  if (user === null) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  return NextResponse.json({ token: await mintToken(user, loadConfig()) }, { headers: { "cache-control": "no-store" } });
}
