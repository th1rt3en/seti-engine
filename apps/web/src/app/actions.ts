"use server";
import {
  AuthFailure,
  SESSION_COOKIE,
  authLockedOut,
  changePassword,
  createGuest,
  endSession,
  issueRecoveryCode,
  login,
  noteAuthFailure,
  recoverAccount,
  renewRecoveryCode,
  signup,
  upgradeGuest,
} from "@/lib/auth";
import { loadConfig } from "@/lib/config";
import { getDb } from "@/lib/db";
import { gameNum } from "@/lib/ids";
import { botVersions, createdRecently } from "@/lib/queries";
import { RECOVERY_COOKIE, currentUser, showRecoveryCode, startSession } from "@/lib/session";
// Server actions: sign up, log in, play as a guest, upgrade a guest, log out, and the lobby buttons.
import { TURNSTILE_FIELD, verifyTurnstile } from "@/lib/turnstile";
import { CLOCK_PRESETS, addBot, createGame, gameMeta, joinGame, leaveGame, removeBot, resignGame, startGame } from "@/lib/worker";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

const field = (f: FormData, k: string): string => String(f.get(k) ?? "");
/** The address of a game's page: its number. (The forms keep the long id; the address is made here.) */
const gamePath = async (id: string): Promise<string> => `/games/${await gameNum(getDb(), id)}`;
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
    await showRecoveryCode(await issueRecoveryCode(getDb(), user.id));
  } catch (e) {
    if (e instanceof AuthFailure) back("/signup", e.message);
    throw e;
  }
  redirect("/recovery-code");
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
    const user = await upgradeGuest(getDb(), (me as NonNullable<typeof me>).id, field(form, "name"), field(form, "password"));
    await showRecoveryCode(await issueRecoveryCode(getDb(), user.id));
  } catch (e) {
    if (e instanceof AuthFailure) back("/account", e.message);
    throw e;
  }
  redirect("/recovery-code");
}

const clientIp = async (): Promise<string> => {
  const h = await headers();
  return h.get("cf-connecting-ip") ?? h.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
};

/** A lost password: the username, the recovery code and a new password. The player is logged in and shown the new recovery code. */
export async function recoverAction(form: FormData): Promise<void> {
  await challenge(form, "/recover");
  const db = getDb();
  const ip = await clientIp();
  if (await authLockedOut(db, ip)) back("/recover", "Too many tries. Wait a quarter of an hour.");
  try {
    const { user, code } = await recoverAccount(db, field(form, "name"), field(form, "code"), field(form, "password"));
    await startSession(user.id);
    await showRecoveryCode(code);
  } catch (e) {
    if (e instanceof AuthFailure) {
      await noteAuthFailure(db, ip);
      back("/recover", e.message);
    }
    throw e;
  }
  redirect("/recovery-code");
}

/** The player has written the code down: the page that showed it goes away. */
export async function recoverySavedAction(): Promise<void> {
  (await cookies()).delete(RECOVERY_COOKIE);
  redirect("/lobby");
}

export async function changePasswordAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const user = me as NonNullable<typeof me>;
  const db = getDb();
  const ip = await clientIp();
  if (await authLockedOut(db, ip)) back("/account", "Too many tries. Wait a quarter of an hour.");
  if (field(form, "password") !== field(form, "again")) back("/account", "The new password and its repetition are not the same.");
  try {
    await changePassword(db, user.id, field(form, "current"), field(form, "password"));
    await startSession(user.id); // the other sessions ended; this device keeps its own
  } catch (e) {
    if (e instanceof AuthFailure) {
      await noteAuthFailure(db, ip);
      back("/account", e.message);
    }
    throw e;
  }
  redirect("/account?notice=Your+password+is+changed.+Your+other+devices+are+logged+out.");
}

/** A new recovery code (the old one stops working), for the player who has lost it or has an account from before the codes. */
export async function newRecoveryCodeAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const db = getDb();
  const ip = await clientIp();
  if (await authLockedOut(db, ip)) back("/account", "Too many tries. Wait a quarter of an hour.");
  try {
    await showRecoveryCode(await renewRecoveryCode(db, (me as NonNullable<typeof me>).id, field(form, "password")));
  } catch (e) {
    if (e instanceof AuthFailure) {
      await noteAuthFailure(db, ip);
      back("/account", e.message);
    }
    throw e;
  }
  redirect("/recovery-code");
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
  // a second press, or a second tab, a moment after the first made a second game by accident: one new game per player every 15 seconds
  if (await createdRecently(getDb(), user.id, Date.now()))
    back("/lobby", "You have just created a game. Open it from the list, or wait a few seconds before creating another.");
  const players = Math.min(4, Math.max(1, Number(field(form, "players")) || 2));
  const difficulty = Math.min(5, Math.max(1, Number(field(form, "difficulty")) || 3));
  const rated = form.get("rated") === "on" && players >= 2;
  const sandbox = players === 1 && form.get("sandbox") === "on";
  // the Space Agencies expansion: organizations work in every game, solo included (EXP-SOLO-01); the neutral pieces are for 1 to 2 players (D35)
  const expansion = form.get("expansion") === "on";
  const organizations = expansion && form.get("organizations") === "on";
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
  redirect(await gamePath((reply as unknown as { id: string }).id));
}

/** From the end of a game: a new table with the same options, the same clock and the same rating, for the same players to join (they get the link of the table). */
export async function playAgainAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const user = me as NonNullable<typeof me>;
  const id = field(form, "id");
  const meta = (await gameMeta(id)) as {
    status?: string;
    rated?: boolean;
    clock?: Parameters<typeof createGame>[1]["clock"];
    options?: Record<string, unknown> & { players?: number };
    seats?: ({ id: string } | null)[];
  } | null;
  if (meta === null || meta.status !== "finished" || !meta.options || !meta.seats?.some((s) => s?.id === user.id))
    redirect(await gamePath(id));
  if (await createdRecently(getDb(), user.id, Date.now()))
    back("/lobby", "You have just created a game. Open it from the list, or wait a few seconds before creating another.");
  const { seed: _seed, ...options } = (meta as NonNullable<typeof meta>).options as Record<string, unknown>;
  const reply = await createGame(user, {
    options: options as never,
    clock: (meta as NonNullable<typeof meta>).clock ?? { kind: "none" },
    rated: (meta as NonNullable<typeof meta>).rated === true && (options.players as number) >= 2,
  } as never);
  if (!reply.ok) back("/lobby", reply.message);
  redirect(await gamePath((reply as unknown as { id: string }).id));
}

export async function joinAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const id = field(form, "id");
  const reply = await joinGame(me as NonNullable<typeof me>, id);
  if (!reply.ok) back("/lobby", reply.message);
  redirect(await gamePath(id));
}

/** The host adds an AI to the lobby. Only a released version can be chosen, and the box that says the game is collected has to be ticked. */
export async function addBotAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const id = field(form, "id");
  const model = field(form, "model");
  const live = (await botVersions(getDb())).some((v) => v.live && v.version === model);
  if (!live) back(await gamePath(id), "That version of the AI is not available.");
  const reply = await addBot(me as NonNullable<typeof me>, id, model, field(form, "consent") === "on");
  if (!reply.ok) back(await gamePath(id), reply.message);
  redirect(await gamePath(id));
}

export async function removeBotAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const id = field(form, "id");
  const reply = await removeBot(me as NonNullable<typeof me>, id, Number(field(form, "seat")));
  if (!reply.ok) back(await gamePath(id), reply.message);
  redirect(await gamePath(id));
}

/** Resign one of the user's own solo games (from the profile page): the game ends as resigned, as when the player resigns at the table. */
export async function resignSoloAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const user = me as NonNullable<typeof me>;
  const id = field(form, "id");
  const meta = (await gameMeta(id)) as { options?: { players?: number } } | null;
  if (meta?.options?.players === 1) await resignGame(user, id); // the Worker checks that the user is the player and that the game is being played
  redirect(`/players/${user.num ?? user.id}`);
}

/** The host starts the game: the Worker checks that the user is the host and that every seat is taken. */
export async function startGameAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  const id = field(form, "id");
  const reply = await startGame(me as NonNullable<typeof me>, id);
  if (!reply.ok) back(await gamePath(id), reply.message);
  redirect(await gamePath(id));
}

export async function leaveAction(form: FormData): Promise<void> {
  const me = await currentUser();
  if (me === null) redirect("/login");
  await leaveGame(me as NonNullable<typeof me>, field(form, "id"));
  redirect("/lobby");
}
