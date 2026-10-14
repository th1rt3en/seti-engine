// The archive is written through the engine service (PUT /archive), which runs on Cloud Run and writes to Google Cloud Storage with the
// credentials of its own service account (decision D25). The Worker therefore holds no Google key.
import type { Archive } from "./archive.js";
import type { Signer } from "./engineAuth.js";

export class EngineArchive implements Archive {
  private readonly fetcher: typeof fetch;

  constructor(
    private readonly baseUrl: string,
    fetcher?: typeof fetch,
    private readonly sign?: Signer,
  ) {
    this.fetcher = fetcher ?? ((input, init) => fetch(input, init));
  }

  async put(path: string, body: unknown): Promise<void> {
    const payload = JSON.stringify({ path, body });
    const res = await this.fetcher(`${this.baseUrl}/archive`, {
      method: "PUT",
      headers: { "content-type": "application/json", ...(this.sign ? await this.sign("PUT", "/archive", payload) : {}) },
      body: payload,
    });
    if (!res.ok) throw new Error(`archive write of ${path} answered ${res.status}`);
  }
}
