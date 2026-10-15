"use server";
import { AuthFailure, SESSION_COOKIE, createGuest, endSession, login, signup, upgradeGuest } from "@/lib/auth";
import { loadConfig } from "@/lib/config";
import { getDb } from "@/lib/db";
import { currentUser, startSession } from "@/lib/session";
// Server actions: sign up, log in, play as a guest, upgrade a guest, log out, and the lobby buttons.
import { TURNSTILE_FIELD, verifyTurnstile } from "@/lib/turnstile";
import { CLOCK_PRESETS, createGame, gameMeta, joinGame, leaveGame, resignGame } from "@/lib/worker";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

const field = (f: FormData, k: string): string => String(f.get(k) ?? "");
const back = (path: string, error: string): never => redirect(`${path}?error=${encodeURIComponent(error)}`);

/** The Turnstile challenge of a form; a visitor who fails it goes back to the page with a message. */
async function challenge(form: FormData, path: string): Promise<void> {
  const h = await headers();
  const ip = h.get("cf-connecting-ip") ?? h.get("x-forwarded-for")?.split(",")[0]?.trim() ?? null;
  const token = field(form, TURNSTILE_FIELD);
  if (loadConfig().turnstileSecret !== "" && token === "")
    back(path, "The security check has not finished. Wait until it shows as passed, then try again.");
  if (!(await verifyTurnstile(token, ip))) back(path, "The security check failed. Please try again.");
}

export async function signupAction(form: FormData): Promise<void> {
  await challenge(form, "/signup");
  try {
    const user = await signup(getDb(), field(form, "name"), field(form, "password"));
    await startSession(user.id);
  } catch (e) {
    if (e instanceof AuthFailure) back("/signup", e.message);
    throw e;
  }
  redirect("/lobby");
}

export async function loginAction(form: FormData): Promise<void> {
  await challenge(form, "/login");
  try {
    const user = await login(getDb(), field(form, "name"), field(form, "password"));
    await startSession(user.id);
  } catch (e) {
    if (e instanceof AuthFailure) back("/login", e.message);
    throw e;
  }
  redirect("/lobby");
}

export async function guestAction(form: FormData): Promise<void> {
  await challenge(form, "/");
  const user = await createGuest(getDb(), field(form, "name") || undefined);
  await startSession(user.id);
  redirect("/lobby");
}

export async function upgradeAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  await challenge(form, "/account");
  try {
    await upgradeGuest(getDb(), (me as NonNullable<typeof me>).id, field(form, "name"), field(form, "password"));
  } catch (e) {
    if (e instanceof AuthFailure) back("/account", e.message);
    throw e;
  }
  redirect("/lobby");
}

export async function logoutAction(): Promise<void> {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (token) await endSession(getDb(), token);
  jar.delete(SESSION_COOKIE);
  redirect("/");
}

export async function createGameAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const user = me as NonNullable<typeof me>;
  const players = Math.min(4, Math.max(1, Number(field(form, "players")) || 2));
  const difficulty = Math.min(5, Math.max(1, Number(field(form, "difficulty")) || 3));
  const rated = form.get("rated") === "on" && players >= 2;
  const sandbox = players === 1 && form.get("sandbox") === "on";
  // the Space Agencies expansion: organizations need 2 to 4 players or the sandbox, the neutral pieces 1 to 2 (D35)
  const expansion = form.get("expansion") === "on";
  const organizations = expansion && form.get("organizations") === "on" && (players > 1 || sandbox);
  const expansionOptions = expansion
    ? {
        expansion: true,
        ...(organizations
          ? {
              organizations: true,
              beginner_organizations: form.get("beginner") === "on",
              neutral_quick_start: players <= 2 && form.get("neutral") === "on",
            }
          : {}),
      }
    : {};
  const preset = CLOCK_PRESETS[field(form, "clock")] ?? CLOCK_PRESETS.none;
  const reply = await createGame(user, {
    options: {
      players,
      ...(players === 1 ? { difficulty, sandbox: form.get("sandbox") === "on" } : {}),
      ...(players === 1 && form.get("sandbox") === "on"
        ? { sandbox_species: [field(form, "species1") || null, field(form, "species2") || null] }
        : {}),
      promo_cards: form.get("promo") === "on",
      promo_set_2: form.get("promo2") === "on",
      ...expansionOptions,
    },
    clock: (preset as NonNullable<typeof preset>).clock,
    rated,
  });
  if (!reply.ok) back("/lobby", reply.message);
  redirect(`/games/${(reply as unknown as { id: string }).id}`);
}

export async function joinAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const id = field(form, "id");
  const reply = await joinGame(me as NonNullable<typeof me>, id);
  if (!reply.ok) back("/lobby", reply.message);
  redirect(`/games/${id}`);
}

/** Resign one of the user's own solo games (from the profile page): the game ends as resigned, as when the player resigns at the table. */
export async function resignSoloAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const user = me as NonNullable<typeof me>;
  const id = field(form, "id");
  const meta = (await gameMeta(id)) as { options?: { players?: number } } | null;
  if (meta?.options?.players === 1) await resignGame(user, id); // the Worker checks that the user is the player and that the game is being played
  redirect(`/players/${user.id}`);
}

export async function leaveAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  await leaveGame(me as NonNullable<typeof me>, field(form, "id"));
  redirect("/lobby");
}
