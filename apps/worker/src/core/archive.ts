// The game archive (decision D25): every game that started is written to Google Cloud Storage as plain JSON, so that a replay of
// everything that happened can be built later without the Durable Object. The bucket is shared with other projects, so everything lives
// under seti-engine/games/, one folder per game, in a folder of the day the game started (UTC):
//   seti-engine/games/YYYY/MM/DD/<id>/header.json           written when the game starts: options with the seed, clock, seats
//   seti-engine/games/YYYY/MM/DD/<id>/actions/<seq>.json    one file per action, written as it is played (a game that never ends is still logged)
//   seti-engine/games/YYYY/MM/DD/<id>/result.json           written when the game ends, however it ends
//   seti-engine/games/YYYY/MM/DD/<id>/replay.json           the three above in one file (a ReplayFile), written after result.json
// The service that writes them (services/engine/src/seti_engine/archive_store.py) accepts only these paths.
// The archive is private: it holds the seed and so the hidden information. A replay shown to other people comes from `publicReplay`.
import type { Options } from "@seti/protocol";
import type { ClockSettings } from "./clock.js";
import type { LogEntry, Meta, Result } from "./room.js";

export const ARCHIVE_FORMAT = "seti-game-log/1";

export interface Archive {
  /** Write one JSON document at this path (overwriting it). Throws when the write fails; the room retries. */
  put(path: string, body: unknown): Promise<void>;
}

export interface ArchiveHeader {
  format: typeof ARCHIVE_FORMAT;
  id: string;
  /** With the seed: the seed and the actions replay the game exactly. */
  options: Options;
  clock: ClockSettings;
  rated: boolean;
  seats: { seat: number; userId: string; name: string; registered: boolean }[];
  createdAt: number;
  startedAt: number;
}

export interface ArchiveResult {
  status: Meta["status"];
  endedAt: number;
  result: Result;
  actions: number;
  /** True when the result changed the ratings. */
  ratedCounted: boolean;
}

export interface ReplayFile {
  format: typeof ARCHIVE_FORMAT;
  header: ArchiveHeader;
  actions: LogEntry[];
  /** Null while the game is not over. */
  result: ArchiveResult | null;
}

/** The folder of a game: its id under the day it started. */
export function gameFolder(meta: Pick<Meta, "id" | "startedAt" | "createdAt">): string {
  const d = new Date(meta.startedAt ?? meta.createdAt);
  const p = (n: number): string => String(n).padStart(2, "0");
  return `seti-engine/games/${d.getUTCFullYear()}/${p(d.getUTCMonth() + 1)}/${p(d.getUTCDate())}/${meta.id}`;
}
export const headerPath = (meta: Pick<Meta, "id" | "startedAt" | "createdAt">): string => `${gameFolder(meta)}/header.json`;
export const actionPath = (meta: Pick<Meta, "id" | "startedAt" | "createdAt">, seq: number): string =>
  `${gameFolder(meta)}/actions/${String(seq).padStart(7, "0")}.json`;
export const resultPath = (meta: Pick<Meta, "id" | "startedAt" | "createdAt">): string => `${gameFolder(meta)}/result.json`;
export const replayPath = (meta: Pick<Meta, "id" | "startedAt" | "createdAt">): string => `${gameFolder(meta)}/replay.json`;

export function headerOf(meta: Meta): ArchiveHeader {
  return {
    format: ARCHIVE_FORMAT,
    id: meta.id,
    options: meta.options,
    clock: meta.clock,
    rated: meta.rated,
    seats: meta.seats.flatMap((s, seat) => (s === null ? [] : [{ seat, userId: s.id, name: s.name, registered: s.registered }])),
    createdAt: meta.createdAt,
    startedAt: meta.startedAt ?? meta.createdAt,
  };
}

export function replayOf(meta: Meta, log: LogEntry[], ratedCounted: boolean): ReplayFile {
  return {
    format: ARCHIVE_FORMAT,
    header: headerOf(meta),
    actions: log,
    result:
      meta.result === undefined
        ? null
        : { status: meta.status, endedAt: meta.endedAt ?? 0, result: meta.result, actions: log.length, ratedCounted },
  };
}

/** The replay as other people may see it: without the user ids. (The seed stays: it is needed to replay, and the game is over.) */
export function publicReplay(file: ReplayFile): ReplayFile {
  return { ...file, header: { ...file.header, seats: file.header.seats.map((s) => ({ ...s, userId: "" })) } };
}

/** An archive that keeps nothing (no bucket configured: local development and tests). */
export class NullArchive implements Archive {
  async put(): Promise<void> {}
}
