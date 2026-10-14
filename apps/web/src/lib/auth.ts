// Accounts, guests and sessions (decision D16): self-hosted, with anonymous guest tokens that can be upgraded to an account without
// losing the history. A session is a random token in a cookie; only its hash is stored. The Worker is given short-lived signed JWTs.
import { createHash, randomBytes, randomUUID, scrypt as scryptCb, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";
import type { Config } from "./config";
import type { Db } from "./db";
import { signJwt } from "./jwt";

const scrypt = promisify(scryptCb) as (password: string, salt: Buffer, keylen: number) => Promise<Buffer>;

export const SESSION_COOKIE = "seti_session";
export const SESSION_DAYS = 30;
export const TOKEN_SECONDS = 300;

export interface User {
  id: string;
  name: string;
  isGuest: boolean;
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
  return { id, name: name.trim(), isGuest: false };
}

export async function login(db: Db, name: string, password: string): Promise<User> {
  const rows = await db.all<UserRow>("SELECT * FROM users WHERE lower(name) = lower(?) AND is_guest = 0", name.trim());
  const row = rows[0];
  // the same message for an unknown username and a wrong password
  if (row?.password_hash == null || !(await checkPassword(password, row.password_hash)))
    throw new AuthFailure("The username or the password is wrong.");
  return toUser(row);
}

export async function createGuest(db: Db, name: string | undefined, now = Date.now()): Promise<User> {
  const id = `guest-${randomUUID()}`;
  let display = name?.trim() ? name.trim().slice(0, 32) : `Guest ${id.slice(-4)}`;
  // a guest cannot pose as a registered player
  if (await nameTaken(db, display)) display = `Guest ${id.slice(-4)}`;
  await db.run(
    "INSERT INTO users (id, name, email, password_hash, is_guest, created_at) VALUES (?, ?, NULL, NULL, 1, ?)",
    id,
    display,
    now,
  );
  return { id, name: display, isGuest: true };
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
  return { id: guestId, name: name.trim(), isGuest: false };
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
  const rows = await db.all<UserRow>(
    "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.id = ? AND s.expires_at > ?",
    digest(token),
    now,
  );
  return rows[0] ? toUser(rows[0]) : null;
}

export async function endSession(db: Db, token: string): Promise<void> {
  await db.run("DELETE FROM sessions WHERE id = ?", digest(token));
}

// --- tokens for the Worker -------------------------------------------------------------------------------------------------------

export async function mintToken(user: User, cfg: Pick<Config, "authPrivateKey" | "authIssuer" | "authAudience">): Promise<string> {
  if (cfg.authPrivateKey === "") throw new Error("AUTH_PRIVATE_KEY is not set");
  return signJwt(
    cfg.authPrivateKey,
    { name: user.name, reg: !user.isGuest, iss: cfg.authIssuer, aud: cfg.authAudience, sub: user.id },
    TOKEN_SECONDS,
  );
}
