// Error reports of the website go to the engine service (PUT /errors), which stores each one as an object in the Google Cloud Storage bucket
// (seti-engine/errors/<day>/...). Best effort: it never throws, and at most 20 reports a minute leave one instance, so a loop of errors cannot flood the bucket.
import { engineAuth } from "./engineAuth";

const WINDOW_MS = 60_000;
let sent: number[] = [];

export async function reportError(
  config: { engineUrl: string; engineSigningKey: string },
  error: unknown,
  detail: Record<string, unknown> = {},
  fetcher: typeof fetch = (input, init) => fetch(input, init),
  now: () => number = () => Date.now(),
  perMinute = 20,
): Promise<void> {
  try {
    const t = now();
    sent = sent.filter((x) => t - x < WINDOW_MS);
    if (sent.length >= perMinute) return;
    sent.push(t);
    const e = error instanceof Error ? error : new Error(String(error));
    const payload = JSON.stringify({ source: "web", message: `${e.name}: ${e.message}`, detail: { ...detail, stack: e.stack } });
    await fetcher(`${config.engineUrl}/errors`, {
      method: "PUT",
      headers: { "content-type": "application/json", ...(await engineAuth(config.engineSigningKey, "PUT", "/errors", payload)) },
      body: payload,
    });
  } catch {
    // an error report that fails is dropped: it must not cause another error
  }
}

/** For the tests: forget the reports sent so far. */
export function resetReportLimit(): void {
  sent = [];
}
