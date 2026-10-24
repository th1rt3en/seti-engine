// Accounts, guests and sessions (decision D16): self-hosted, with anonymous guest tokens that can be upgraded to an account without
// losing the history. A session is a random token in a cookie; only its hash is stored. The Worker is given short-lived signed JWTs.
import { createHash, randomBytes, randomUUID, scrypt as scryptCb, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";
import type { Config } from "./config";
import type { Db } from "./db";
import { userNum } from "./ids";
import { signJwt } from "./jwt";

const scrypt = promisify(scryptCb) as (password: string, salt: Buffer, keylen: number) => Promise<Buffer>;

export const SESSION_COOKIE = "seti_session";
export const SESSION_DAYS = 30;
export const TOKEN_SECONDS = 300;

export interface User {
  id: string;
  name: string;
  isGuest: boolean;
  /** The player's number: the integer in the address of their profile (lib/ids.ts). */
  num?: number;
}

export class AuthFailure extends Error {}

// --- passwords -------------------------------------------------------------------------------------------------------------------

export async function hashPassword(password: string): Promise<string> {
  const salt = randomBytes(16);
  const hash = await scrypt(password, salt, 64);
  return `scrypt$${salt.toString("base64")}$${hash.toString("base64")}`;
}

export async function checkPassword(password: string, stored: string): Promise<boolean> {
  const [kind, salt, hash] = stored.split("$");
  if (kind !== "scrypt" || salt === undefined || hash === undefined) return false;
  const expected = Buffer.from(hash, "base64");
  const actual = await scrypt(password, Buffer.from(salt, "base64"), expected.length);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

/** A username: 3 to 24 letters, digits, dots, dashes or underscores (it is shown to other players and used to log in). */
export const USERNAME = /^[A-Za-z0-9_.-]{3,24}$/;

function validate(name: string, password: string): void {
  if (!USERNAME.test(name.trim())) throw new AuthFailure("The username must have 3 to 24 letters, digits, dots, dashes or underscores.");
  if (password.length < 8) throw new AuthFailure("The password must have at least 8 characters.");
  if (password.length > 200) throw new AuthFailure("The password is too long.");
}

async function nameTaken(db: Db, name: string, exceptId = ""): Promise<boolean> {
  const rows = await db.all<{ id: string }>(
    "SELECT id FROM users WHERE lower(name) = lower(?) AND is_guest = 0 AND id != ?",
    name.trim(),
    exceptId,
  );
  return rows.length > 0;
}

// --- users -----------------------------------------------------------------------------------------------------------------------

interface UserRow {
  id: string;
  name: string;
  password_hash: string | null;
  is_guest: number;
}

const toUser = (r: UserRow): User => ({ id: r.id, name: r.name, isGuest: r.is_guest === 1 });

export async function signup(db: Db, name: string, password: string, now = Date.now()): Promise<User> {
  validate(name, password);
  if (await nameTaken(db, name)) throw new AuthFailure("That username is taken.");
  const id = randomUUID();
  await db.run(
    "INSERT INTO users (id, name, email, password_hash, is_guest, created_at) VALUES (?, ?, NULL, ?, 0, ?)",
    id,
    name.trim(),
    await hashPassword(password),
    now,
  );
  return { id, name: name.trim(), isGuest: false, num: await userNum(db, id) };
}

export async function login(db: Db, name: string, password: string): Promise<User> {
  const rows = await db.all<UserRow>("SELECT * FROM users WHERE lower(name) = lower(?) AND is_guest = 0", name.trim());
  const row = rows[0];
  // the same message for an unknown username and a wrong password
  if (row?.password_hash == null || !(await checkPassword(password, row.password_hash)))
    throw new AuthFailure("The username or the password is wrong.");
  return { ...toUser(row), num: await userNum(db, row.id) };
}

/** A name that a guest typed, made safe to show to other players: only the letters A to Z, digits, spaces, dots, dashes and underscores (no control, invisible, direction
 * or look-alike characters that could hide, reverse or copy another name), single spaces, at most 24 characters. An empty result means that there is no usable name. */
export function cleanGuestName(raw: string | undefined): string {
  return (raw ?? "")
    .normalize("NFKD")
    .replace(/[^A-Za-z0-9 ._-]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 24)
    .trim();
}

export async function createGuest(db: Db, name: string | undefined, now = Date.now()): Promise<User> {
  const id = `guest-${randomUUID()}`;
  const typed = cleanGuestName(name);
  let display = typed !== "" ? typed : `Guest ${id.slice(-4)}`;
  // a guest cannot pose as a registered player
  if (await nameTaken(db, display)) display = `Guest ${id.slice(-4)}`;
  await db.run(
    "INSERT INTO users (id, name, email, password_hash, is_guest, created_at) VALUES (?, ?, NULL, NULL, 1, ?)",
    id,
    display,
    now,
  );
  return { id, name: display, isGuest: true, num: await userNum(db, id) };
}

/** A guest becomes an account and keeps the same id, so its games and history stay with it (decision D16). */
export async function upgradeGuest(db: Db, guestId: string, name: string, password: string): Promise<User> {
  validate(name, password);
  const rows = await db.all<UserRow>("SELECT * FROM users WHERE id = ?", guestId);
  if (rows[0]?.is_guest !== 1) throw new AuthFailure("Only a guest can be upgraded.");
  if (await nameTaken(db, name, guestId)) throw new AuthFailure("That username is taken.");
  await db.run(
    "UPDATE users SET name = ?, password_hash = ?, is_guest = 0 WHERE id = ?",
    name.trim(),
    await hashPassword(password),
    guestId,
  );
  return { id: guestId, name: name.trim(), isGuest: false, num: await userNum(db, guestId) };
}

// --- recovery code, password change ----------------------------------------------------------------------------------------------

const CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // no 0, O, 1, I: the code is copied by hand
const CODE_GROUPS = 4;
const CODE_GROUP_LENGTH = 5;

/** A recovery code is 20 letters and digits in four groups (about 100 bits), for example `K7RT2-QW9HD-3MXPB-ZE4NA`. */
export function newRecoveryCode(): string {
  const bytes = randomBytes(CODE_GROUPS * CODE_GROUP_LENGTH);
  const chars = Array.from(bytes, (b) => CODE_ALPHABET[b % CODE_ALPHABET.length]);
  const groups: string[] = [];
  for (let g = 0; g < CODE_GROUPS; g++) groups.push(chars.slice(g * CODE_GROUP_LENGTH, (g + 1) * CODE_GROUP_LENGTH).join(""));
  return groups.join("-");
}

/** The code as it is compared: capitals, without the dashes and spaces that a person adds or drops when typing it. */
export const normalizeCode = (code: string): string => code.toUpperCase().replace(/[^A-Z0-9]/g, "");

/** Makes a new recovery code for the account (the old one stops working) and returns it. Only its hash is kept. */
export async function issueRecoveryCode(db: Db, userId: string, now = Date.now()): Promise<string> {
  const code = newRecoveryCode();
  const hash = await hashPassword(normalizeCode(code));
  await db.run(
    "INSERT INTO recovery_codes (user_id, code_hash, created_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET code_hash = excluded.code_hash, created_at = excluded.created_at",
    userId,
    hash,
    now,
  );
  return code;
}

async function endSessionsOf(db: Db, userId: string): Promise<void> {
  await db.run("DELETE FROM sessions WHERE user_id = ?", userId);
}

/**
 * A lost password: the recovery code and a new password. The code works once; a new one is made and returned (to be shown to the player).
 * The same message for an unknown username, an account without a code and a wrong code.
 */
export async function recoverAccount(
  db: Db,
  name: string,
  code: string,
  newPassword: string,
  now = Date.now(),
): Promise<{ user: User; code: string }> {
  const wrong = new AuthFailure("The username or the recovery code is wrong.");
  const rows = await db.all<UserRow>("SELECT * FROM users WHERE lower(name) = lower(?) AND is_guest = 0", name.trim());
  const row = rows[0];
  if (row === undefined) throw wrong;
  const stored = (await db.all<{ code_hash: string }>("SELECT code_hash FROM recovery_codes WHERE user_id = ?", row.id))[0];
  if (stored === undefined || !(await checkPassword(normalizeCode(code), stored.code_hash))) throw wrong;
  validate(row.name, newPassword);
  await db.run("UPDATE users SET password_hash = ? WHERE id = ?", await hashPassword(newPassword), row.id);
  await endSessionsOf(db, row.id);
  return { user: { ...toUser(row), num: await userNum(db, row.id) }, code: await issueRecoveryCode(db, row.id, now) };
}

/** The player changes their own password (they give the old one). Their other sessions end. */
export async function changePassword(db: Db, userId: string, current: string, next: string): Promise<void> {
  const row = (await db.all<UserRow>("SELECT * FROM users WHERE id = ? AND is_guest = 0", userId))[0];
  if (row?.password_hash == null || !(await checkPassword(current, row.password_hash)))
    throw new AuthFailure("The current password is wrong.");
  validate(row.name, next);
  await db.run("UPDATE users SET password_hash = ? WHERE id = ?", await hashPassword(next), userId);
  await endSessionsOf(db, userId);
}

/** The administrator sets a password for an account (the player lost both the password and the recovery code). Its sessions end. */
export async function setPasswordByAdmin(db: Db, userId: string, next: string): Promise<boolean> {
  const row = (await db.all<UserRow>("SELECT * FROM users WHERE id = ? AND is_guest = 0", userId))[0];
  if (row === undefined) return false;
  validate(row.name, next);
  await db.run("UPDATE users SET password_hash = ? WHERE id = ?", await hashPassword(next), userId);
  await endSessionsOf(db, userId);
  return true;
}

/** The player makes a new recovery code (the old one stops working); they give their password. */
export async function renewRecoveryCode(db: Db, userId: string, password: string): Promise<string> {
  const row = (await db.all<UserRow>("SELECT * FROM users WHERE id = ? AND is_guest = 0", userId))[0];
  if (row?.password_hash == null || !(await checkPassword(password, row.password_hash))) throw new AuthFailure("The password is wrong.");
  return issueRecoveryCode(db, userId);
}

// A few wrong tries per address and quarter of an hour (recovery and password change): a recovery code cannot be guessed.
const MAX_AUTH_FAILURES = 5;
const AUTH_WINDOW_MS = 15 * 60_000;

export async function authLockedOut(db: Db, ip: string, now = Date.now()): Promise<boolean> {
  const rows = await db.all<{ n: number }>("SELECT COUNT(*) AS n FROM auth_attempts WHERE ip = ? AND at > ?", ip, now - AUTH_WINDOW_MS);
  return (rows[0]?.n ?? 0) >= MAX_AUTH_FAILURES;
}

export async function noteAuthFailure(db: Db, ip: string, now = Date.now()): Promise<void> {
  await db.run("DELETE FROM auth_attempts WHERE at < ?", now - AUTH_WINDOW_MS);
  await db.run("INSERT INTO auth_attempts (ip, at) VALUES (?, ?)", ip, now);
}

// --- sessions --------------------------------------------------------------------------------------------------------------------

const digest = (token: string): string => createHash("sha256").update(token).digest("hex");

export async function createSession(db: Db, userId: string, now = Date.now()): Promise<{ token: string; expiresAt: number }> {
  const token = randomBytes(32).toString("base64url");
  const expiresAt = now + SESSION_DAYS * 86_400_000;
  await db.run("INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)", digest(token), userId, now, expiresAt);
  return { token, expiresAt };
}

export async function userForSession(db: Db, token: string | undefined, now = Date.now()): Promise<User | null> {
  if (!token) return null;
  const rows = await db.all<UserRow & { num: number | null }>(
    "SELECT u.*, n.num AS num FROM sessions s JOIN users u ON u.id = s.user_id LEFT JOIN user_nums n ON n.user_id = u.id WHERE s.id = ? AND s.expires_at > ?",
    digest(token),
    now,
  );
  const row = rows[0];
  return row ? { ...toUser(row), num: row.num ?? (await userNum(db, row.id)) } : null;
}

export async function endSession(db: Db, token: string): Promise<void> {
  await db.run("DELETE FROM sessions WHERE id = ?", digest(token));
}

// --- tokens for the Worker -------------------------------------------------------------------------------------------------------

export async function mintToken(user: User, cfg: Pick<Config, "authPrivateKey" | "authIssuer" | "authAudience">): Promise<string> {
  if (cfg.authPrivateKey === "") throw new Error("AUTH_PRIVATE_KEY is not set");
  return signJwt(
    cfg.authPrivateKey,
    {
      name: user.name,
      reg: !user.isGuest,
      ...(user.num === undefined ? {} : { num: user.num }),
      iss: cfg.authIssuer,
      aud: cfg.authAudience,
      sub: user.id,
    },
    TOKEN_SECONDS,
  );
}
