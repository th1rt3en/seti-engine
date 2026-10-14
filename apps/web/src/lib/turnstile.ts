// Cloudflare Turnstile: the challenge on signup, login and guest play. The page shows the widget, which adds the field
// "cf-turnstile-response" to the form; the server action sends that token to Cloudflare to check it.
import { type Config, loadConfig } from "./config";

export const TURNSTILE_FIELD = "cf-turnstile-response";
const VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

/** True when the visitor passed the challenge. Without a secret key: allowed in development, refused in production (fail closed). */
export async function verifyTurnstile(
  token: string,
  ip: string | null,
  cfg: Config = loadConfig(),
  fetcher: typeof fetch = fetch,
  production: boolean = process.env.NODE_ENV === "production",
): Promise<boolean> {
  if (cfg.turnstileSecret === "") return !production;
  if (token === "") return false;
  const body = new URLSearchParams({ secret: cfg.turnstileSecret, response: token });
  if (ip) body.set("remoteip", ip);
  try {
    const res = await fetcher(VERIFY_URL, { method: "POST", body });
    if (!res.ok) {
      console.warn(`turnstile: siteverify answered ${res.status}`);
      return false;
    }
    const answer = (await res.json()) as { success?: boolean; "error-codes"?: string[]; hostname?: string };
    if (answer.success !== true)
      console.warn(`turnstile: refused (${(answer["error-codes"] ?? []).join(", ")}) for ${answer.hostname ?? "?"}`);
    return answer.success === true;
  } catch (e) {
    console.warn("turnstile: siteverify failed", e);
    return false;
  }
}
