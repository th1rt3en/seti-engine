// The Turnstile challenge of a form. The Cloudflare script finds the div and puts the answer into the form as "cf-turnstile-response".
// Without a site key (development) nothing is shown.
import { loadConfig } from "@/lib/config";

export function TurnstileWidget() {
  const siteKey = loadConfig().turnstileSiteKey;
  if (siteKey === "") return null;
  return (
    <>
      <div className="cf-turnstile" data-sitekey={siteKey} />
      <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer />
    </>
  );
}
