// The Turnstile challenge of a form (see TurnstileField). Without a site key (development) nothing is shown.
import { loadConfig } from "@/lib/config";
import { TurnstileField } from "./TurnstileField";

export function TurnstileWidget() {
  const siteKey = loadConfig().turnstileSiteKey;
  if (siteKey === "") return null;
  return <TurnstileField siteKey={siteKey} />;
}
