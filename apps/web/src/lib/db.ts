// The database: the same schema as the Worker's D1 (apps/worker/migrations). The site reads and writes it through this small interface,
// backed by a local SQLite file in development and by the Cloudflare D1 REST API in production.
import { mkdirSync, readFileSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { type Config, loadConfig } from "./config";

export interface Db {
  all<T = Record<string, unknown>>(sql: string, ...params: unknown[]): Promise<T[]>;
  run(sql: string, ...params: unknown[]): Promise<void>;
}

/** SQLite (node:sqlite). It is loaded by require so the bundler leaves it alone. */
export class SqliteDb implements Db {
  private readonly sql: import("node:sqlite").DatabaseSync;

  constructor(path: string, migrations: string[]) {
    const { DatabaseSync } = createRequire(import.meta.url)("node:sqlite") as typeof import("node:sqlite");
    if (path !== ":memory:") mkdirSync(dirname(resolve(path)), { recursive: true });
    this.sql = new DatabaseSync(path);
    for (const m of migrations) this.sql.exec(m);
  }

  async all<T>(sql: string, ...params: unknown[]): Promise<T[]> {
    return this.sql.prepare(sql).all(...(params as never[])) as T[];
  }

  async run(sql: string, ...params: unknown[]): Promise<void> {
    this.sql.prepare(sql).run(...(params as never[]));
  }
}

/** The part of a Cloudflare D1 binding that is used. */
interface D1Binding {
  prepare(sql: string): { bind(...values: unknown[]): { all(): Promise<{ results: unknown[] }>; run(): Promise<unknown> } };
}

/** Cloudflare D1 through the binding of the site's own Worker (production: the site runs on Cloudflare, decision D30). */
export class D1BindingDb implements Db {
  constructor(private readonly d1: D1Binding) {}

  async all<T>(sql: string, ...params: unknown[]): Promise<T[]> {
    return (
      await this.d1
        .prepare(sql)
        .bind(...params)
        .all()
    ).results as T[];
  }

  async run(sql: string, ...params: unknown[]): Promise<void> {
    await this.d1
      .prepare(sql)
      .bind(...params)
      .run();
  }
}

/** Cloudflare D1 through its REST API (for tools and development outside Cloudflare). */
export class D1RestDb implements Db {
  constructor(
    private readonly accountId: string,
    private readonly databaseId: string,
    private readonly token: string,
    private readonly fetcher: typeof fetch = fetch,
  ) {}

  private async query<T>(sql: string, params: unknown[]): Promise<T[]> {
    const res = await this.fetcher(`https://api.cloudflare.com/client/v4/accounts/${this.accountId}/d1/database/${this.databaseId}/query`, {
      method: "POST",
      headers: { authorization: `Bearer ${this.token}`, "content-type": "application/json" },
      body: JSON.stringify({ sql, params }),
    });
    const body = (await res.json()) as { success: boolean; errors?: { message: string }[]; result?: { results: T[] }[] };
    if (!res.ok || !body.success) throw new Error(`D1 query failed: ${body.errors?.map((e) => e.message).join("; ") ?? res.status}`);
    return body.result?.[0]?.results ?? [];
  }

  all<T>(sql: string, ...params: unknown[]): Promise<T[]> {
    return this.query<T>(sql, params);
  }

  async run(sql: string, ...params: unknown[]): Promise<void> {
    await this.query(sql, params);
  }
}

export function migrationSql(): string[] {
  // The Worker owns the migrations; the development database applies the same file.
  const dir = process.env.MIGRATIONS_DIR ?? resolve(process.cwd(), "../worker/migrations");
  return readdirSync(dir)
    .filter((f) => f.endsWith(".sql"))
    .sort()
    .map((f) => readFileSync(resolve(dir, f), "utf8"));
}

let shared: Db | undefined;

/** The D1 binding of the Worker this code runs in, or undefined outside Cloudflare (development, tests). */
function boundD1(): D1Binding | undefined {
  try {
    return (getCloudflareContext().env as { DB?: D1Binding }).DB;
  } catch {
    return undefined;
  }
}

export function getDb(cfg: Config = loadConfig()): Db {
  const bound = boundD1();
  if (bound !== undefined) return new D1BindingDb(bound);
  if (shared === undefined) {
    shared =
      cfg.dbMode === "d1" ? new D1RestDb(cfg.cfAccountId, cfg.cfDatabaseId, cfg.cfApiToken) : new SqliteDb(cfg.sqlitePath, migrationSql());
  }
  return shared;
}
