// Error reports go to the engine service (PUT /errors), which writes each one as an object in the Google Cloud Storage bucket next to the game
// archive (seti-engine/errors/<day>/...). Reporting is best effort: it never throws, and at most `perMinute` reports are sent by one isolate, so
// a loop of errors cannot flood the bucket.
import type { Signer } from "./engineAuth.js";

export interface ErrorReporter {
  report(source: string, error: unknown, detail?: Record<string, unknown>): Promise<void>;
}

const WINDOW_MS = 60_000;

export function makeErrorReporter(
  baseUrl: string,
  sign?: Signer,
  fetcher: typeof fetch = (input, init) => fetch(input, init),
  now: () => number = () => Date.now(),
  perMinute = 20,
): ErrorReporter {
  let sent: number[] = [];
  return {
    async report(source, error, detail) {
      try {
        const t = now();
        sent = sent.filter((x) => t - x < WINDOW_MS);
        if (sent.length >= perMinute) return;
        sent.push(t);
        const e = error instanceof Error ? error : new Error(String(error));
        const payload = JSON.stringify({ source, message: `${e.name}: ${e.message}`, detail: { ...detail, stack: e.stack } });
        await fetcher(`${baseUrl}/errors`, {
          method: "PUT",
          headers: { "content-type": "application/json", ...(sign ? await sign("PUT", "/errors", payload) : {}) },
          body: payload,
        });
      } catch {
        // an error report that fails is dropped: it must not cause another error
      }
    },
  };
}
