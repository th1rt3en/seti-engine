"use server";
// The actions of the administrator's page. Every action checks the administrator's cookie again: a form that is posted without it does nothing.
import { ADMIN_COOKIE, ADMIN_HOURS, adminToken, checkPassphrase, isAdmin, lockedOut, noteFailure } from "@/lib/admin";
import { allOpenGameIds, deleteAccount, resetRating, setRating } from "@/lib/adminData";
import { AuthFailure, setPasswordByAdmin } from "@/lib/auth";
import { getDb } from "@/lib/db";
import { resolveGame } from "@/lib/ids";
import { describeMove } from "@/lib/moves";
import { adminCancelGame, adminGameInfo, adminGameSeed, adminRecentActions, adminUndoGame } from "@/lib/worker";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

const field = (f: FormData, k: string): string => String(f.get(k) ?? "");

/** Back to the page the form came from (only addresses of the administrator's page), with a message. */
function back(form: FormData, notice: string, error = false): never {
  const to = field(form, "back");
  const base = to.startsWith("/admin") ? to : "/admin";
  const url = new URL(base, "https://admin.invalid");
  url.searchParams.delete("notice");
  url.searchParams.delete("error");
  url.searchParams.set(error ? "error" : "notice", notice);
  redirect(`${url.pathname}${url.search}`);
}

async function requireAdmin(form: FormData): Promise<void> {
  if (!(await isAdmin())) back(form, "Log in again.", true);
}

export async function adminLoginAction(form: FormData): Promise<void> {
  const h = await headers();
  const ip = h.get("cf-connecting-ip") ?? h.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const db = getDb();
  const now = Date.now();
  if (await lockedOut(db, ip, now)) redirect("/admin?error=Too+many+tries.+Wait+a+quarter+of+an+hour.");
  if (!(await checkPassphrase(field(form, "passphrase").trim()))) {
    await noteFailure(db, ip, now);
    redirect("/admin?error=That+is+not+it.");
  }
  (await cookies()).set(ADMIN_COOKIE, adminToken(now), {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/admin",
    maxAge: ADMIN_HOURS * 3600,
  });
  redirect("/admin");
}

export async function adminLogoutAction(): Promise<void> {
  (await cookies()).delete({ name: ADMIN_COOKIE, path: "/admin" });
  redirect("/admin");
}

export async function deleteAccountAction(form: FormData): Promise<void> {
  await requireAdmin(form);
  const done = await deleteAccount(getDb(), field(form, "user"));
  if (!done) back(form, "That account is in a lobby or in a game that is being played: cancel the game first.", true);
  back(form, `Deleted the account ${field(form, "name")}.`);
}

export async function setRatingAction(form: FormData): Promise<void> {
  await requireAdmin(form);
  const rating = Number(field(form, "rating"));
  if (!Number.isFinite(rating) || rating < 0 || rating > 4000) back(form, "The rating must be a number from 0 to 4000.", true);
  await setRating(getDb(), field(form, "user"), rating, Date.now());
  back(form, `${field(form, "name")} is rated ${Math.round(rating)} now.`);
}

/** The administrator sets a password for a player who lost both the password and the recovery code. The player's sessions end. */
export async function setPasswordAction(form: FormData): Promise<void> {
  await requireAdmin(form);
  try {
    const done = await setPasswordByAdmin(getDb(), field(form, "user"), field(form, "password"));
    if (!done) back(form, "That account does not exist, or it is a guest.", true);
  } catch (e) {
    if (e instanceof AuthFailure) back(form, e.message, true);
    throw e;
  }
  back(
    form,
    `The password of ${field(form, "name")} is changed and their sessions are ended. Tell them the new password; they can change it on their account page.`,
  );
}

export async function resetRatingAction(form: FormData): Promise<void> {
  await requireAdmin(form);
  await resetRating(getDb(), field(form, "user"));
  back(form, `The rating of ${field(form, "name")} is reset (unrated, 0).`);
}

/** What an action of the administrator's page says when it stays on the page: a message, and whether it is an error. */
export type Said = { ok: boolean; message: string };

/** The administrator asks for the seed of a table (the number of the game, or its long id). It gives the hidden cards away: it is shown to the administrator only. */
export async function seedLookupAction(form: FormData): Promise<Said> {
  if (!(await isAdmin())) return { ok: false, message: "Log in again." };
  const table = field(form, "table").trim().replace(/^#/, "");
  const found = table === "" ? null : await resolveGame(getDb(), table);
  if (found === null) return { ok: false, message: "No such table." };
  const out = await adminGameSeed(found.id);
  if (out === null) return { ok: false, message: "The Worker does not know that table (it may be older than its records, or deleted)." };
  if (out.seed === null) return { ok: false, message: `Table ${table} (${out.status}) has no seed yet: it is drawn when the game starts.` };
  return { ok: true, message: `Table ${table} (${out.status}): seed ${out.seed}${out.seeded ? " (chosen by the host)" : ""}` };
}

/** The last actions of a table that is being played, for the administrator to see what to take back. */
export async function recentActionsAction(form: FormData): Promise<Said> {
  if (!(await isAdmin())) return { ok: false, message: "Log in again." };
  const table = field(form, "table").trim().replace(/^#/, "");
  const found = table === "" ? null : await resolveGame(getDb(), table);
  if (found === null) return { ok: false, message: "No such table." };
  const out = await adminRecentActions(found.id, 8);
  if (!out.ok || out.recent === undefined)
    return { ok: false, message: `Table ${table}: ${out.message ?? "the game is not being played"}.` };
  const lines = out.recent.map((e) => `#${e.seq + 1} seat ${e.seat + 1}: ${describeMove(e.action as { type: string })}`);
  return { ok: true, message: [`Table ${table} is at action ${out.total}. The last ones, the most recent last:`, ...lines].join("\n") };
}

/** Takes back the last actions of a table that is being played (whoever made them, whatever they showed); the players see the table as it was. */
export async function undoActionsAction(form: FormData): Promise<Said> {
  if (!(await isAdmin())) return { ok: false, message: "Log in again." };
  const table = field(form, "table").trim().replace(/^#/, "");
  const count = Number(field(form, "count"));
  const found = table === "" ? null : await resolveGame(getDb(), table);
  if (found === null) return { ok: false, message: "No such table." };
  if (!Number.isInteger(count) || count < 1 || count > 200) return { ok: false, message: "Take back 1 to 200 actions." };
  const out = await adminUndoGame(found.id, count);
  if (!out.ok) return { ok: false, message: `Table ${table}: ${out.message}` };
  return {
    ok: true,
    message: `Table ${table}: ${out.removed} action${out.removed === 1 ? "" : "s"} taken back; the game is at action ${out.left} now.`,
  };
}

/** The administrator lets a host add an AI model to a game, or not (`bot_versions.live`). A model that is not approved cannot be enabled. */
export async function setBotEnabledAction(form: FormData): Promise<Said> {
  if (!(await isAdmin())) return { ok: false, message: "Log in again." };
  const version = field(form, "version");
  const enable = field(form, "enable") === "1";
  await getDb().run("UPDATE bot_versions SET live = ? WHERE version = ? AND approved = 1", enable ? 1 : 0, version);
  const row = (await getDb().all<{ live: number }>("SELECT live FROM bot_versions WHERE version = ? AND approved = 1", version))[0];
  if (row === undefined) return { ok: false, message: `${version} is not an approved version.` };
  return { ok: true, message: `${version} is ${row.live === 1 ? "available to hosts" : "off: hosts cannot add it"} now.` };
}

/** Cancels one game; the page stays where it is and its list of games is read again (the form is an `InlineForm` with `refresh`). */
export async function cancelGameAction(form: FormData): Promise<Said> {
  if (!(await isAdmin())) return { ok: false, message: "Log in again." };
  const out = await adminCancelGame(field(form, "game"));
  if (!out.ok) return { ok: false, message: `The game could not be cancelled: ${out.message}` };
  return { ok: true, message: "The game is cancelled. Nobody's rating changed." };
}

/** Cancels every lobby and every game being played that has had no move (and, in a lobby, nobody there) for this long. */
export async function cancelStaleAction(form: FormData): Promise<Said> {
  if (!(await isAdmin())) return { ok: false, message: "Log in again." };
  const amount = Number(field(form, "amount"));
  const days = field(form, "unit") === "days";
  if (!Number.isFinite(amount) || amount <= 0) return { ok: false, message: "Say how many hours or days." };
  const cutoff = Date.now() - amount * (days ? 86_400_000 : 3_600_000);
  const db = getDb();
  let cancelled = 0;
  let checked = 0;
  for (const id of (await allOpenGameIds(db)).slice(0, 200)) {
    checked += 1;
    const info = await adminGameInfo(id);
    if (info === null) {
      // the Worker does not know this game any more: the row of the database is all that is left of it
      await db.run(
        "UPDATE games SET status = 'cancelled', reason = 'cancelled', ended_at = ? WHERE id = ? AND status IN ('lobby', 'playing')",
        Date.now(),
        id,
      );
      cancelled += 1;
    } else if (info.lastActivity < cutoff && (await adminCancelGame(id)).ok) cancelled += 1;
  }
  return {
    ok: true,
    message: `Cancelled ${cancelled} of ${checked} open games (no move for ${amount} ${days ? "days" : "hours"}). No rating changed.`,
  };
}
