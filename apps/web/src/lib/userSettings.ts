// The settings of the game page kept with the account (so they follow the player to another device): a few known keys, each with a small value.
import type { Db } from "./db";

/** The keys that are kept, as the browser stores them (lib/gameSettings.ts), with what a value may be. */
export const SETTING_KEYS: Record<string, (v: string) => boolean> = {
  "seti-turn-sound": (v) => v === "0" || v === "1",
  "seti-confirm-irreversible": (v) => v === "0" || v === "1",
  "seti-turn-notify": (v) => v === "0" || v === "1",
  "seti-animations": (v) => v === "0" || v === "1",
  "seti-hand-scale": (v) => Number.isFinite(Number(v)) && Number(v) >= 0.5 && Number(v) <= 2,
};

/** Keeps only the known keys with a valid value. */
export function cleanSettings(input: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (typeof input !== "object" || input === null) return out;
  for (const [k, v] of Object.entries(input as Record<string, unknown>)) {
    const ok = SETTING_KEYS[k];
    if (ok && typeof v === "string" && v.length <= 8 && ok(v)) out[k] = v;
  }
  return out;
}

export async function getSettings(db: Db, userId: string): Promise<Record<string, string>> {
  const row = (await db.all<{ settings_json: string }>("SELECT settings_json FROM user_settings WHERE user_id = ?", userId))[0];
  if (!row) return {};
  try {
    return cleanSettings(JSON.parse(row.settings_json));
  } catch {
    return {};
  }
}

export async function saveSettings(db: Db, userId: string, input: unknown, now = Date.now()): Promise<Record<string, string>> {
  const settings = cleanSettings(input);
  await db.run(
    `INSERT INTO user_settings (user_id, settings_json, updated_at) VALUES (?, ?, ?)
     ON CONFLICT(user_id) DO UPDATE SET settings_json = excluded.settings_json, updated_at = excluded.updated_at`,
    userId,
    JSON.stringify(settings),
    now,
  );
  return settings;
}
