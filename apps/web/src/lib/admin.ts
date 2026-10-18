// The administrator's page: a passphrase (only its scrypt hash is in the environment) gives a signed cookie that lasts two hours. The page has no link
// anywhere; its address is typed. A few wrong passphrases per address lock it for a quarter of an hour.
import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { checkPassword } from "./auth";
import { loadConfig } from "./config";
import type { Db } from "./db";

export const ADMIN_COOKIE = "seti_admin";
export const ADMIN_HOURS = 2;
const MAX_FAILURES = 5;
const WINDOW_MS = 15 * 60_000;

const sign = (value: string, key: string): string => createHmac("sha256", key).update(value).digest("base64url");

/** The cookie value for an administrator who logs in at `now`: when it expires, and the signature of that. */
export function adminToken(now: number, key = loadConfig().adminPassphraseHash): string {
  const expires = String(now + ADMIN_HOURS * 3_600_000);
  return `${expires}.${sign(expires, key)}`;
}

/** Whether a cookie value was made by `adminToken` with this key and has not expired. */
export function validAdminToken(token: string | undefined, now: number, key = loadConfig().adminPassphraseHash): boolean {
  if (!token || key === "") return false;
  const [expires, signature] = token.split(".");
  if (!expires || !signature) return false;
  const expected = Buffer.from(sign(expires, key));
  const given = Buffer.from(signature);
  return given.length === expected.length && timingSafeEqual(given, expected) && Number(expires) > now;
}

export async function isAdmin(): Promise<boolean> {
  return validAdminToken((await cookies()).get(ADMIN_COOKIE)?.value, Date.now());
}

/** True when the passphrase is right. Nothing is said about why it is not. */
export async function checkPassphrase(passphrase: string, hash = loadConfig().adminPassphraseHash): Promise<boolean> {
  return hash !== "" && (await checkPassword(passphrase, hash));
}

/** Too many wrong passphrases lately from this address? */
export async function lockedOut(db: Db, ip: string, now: number): Promise<boolean> {
  const rows = await db.all<{ n: number }>("SELECT COUNT(*) AS n FROM admin_attempts WHERE ip = ? AND at > ?", ip, now - WINDOW_MS);
  return (rows[0]?.n ?? 0) >= MAX_FAILURES;
}

export async function noteFailure(db: Db, ip: string, now: number): Promise<void> {
  await db.run("DELETE FROM admin_attempts WHERE at < ?", now - WINDOW_MS);
  await db.run("INSERT INTO admin_attempts (ip, at) VALUES (?, ?)", ip, now);
}
