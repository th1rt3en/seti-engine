// The current user of a request, from the session cookie (server components, route handlers and server actions).
import { cookies } from "next/headers";
import { SESSION_COOKIE, SESSION_DAYS, type User, createSession, userForSession } from "./auth";
import { getDb } from "./db";

export async function currentUser(): Promise<User | null> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  return userForSession(getDb(), token);
}

export async function startSession(userId: string): Promise<void> {
  const { token } = await createSession(getDb(), userId);
  (await cookies()).set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_DAYS * 86_400,
  });
}
