// The game archive (decision D25): every game that started is written to Google Cloud Storage as plain JSON, so that a replay of
// everything that happened can be built later without the Durable Object. The bucket is shared with other projects, so everything lives
// under seti-engine/games/, in a folder of the day the game started (UTC), and a game is ONE file named by its table number:
//   seti-engine/games/YYYY/MM/DD/<table number>.json       a ReplayFile: the header, the actions and the result of the whole game
// While the game is played the file is written again every ARCHIVE_EVERY actions (a game that never ends is still logged), and for the last time when
// the game ends, however it ends. `undo` and the moves that were taken back are not in the file (`withoutUndone`).
// The service that writes it (services/engine/src/seti_engine/archive_store.py) accepts only this path.
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
  /** `num` is the player's number (the integer in the address of their profile); the public replay keeps it and drops `userId`. */
  seats: { seat: number; userId: string; name: string; registered: boolean; num?: number; bot?: { model: string } }[];
  /** Present when an AI model sat in the game: the host agreed that the game is collected and used for training (docs/AI-TURN-BUNDLES.md). */
  consent?: { by: string; at: number };
  createdAt: number;
  startedAt: number;
  /** "double": the game was played when JavaScript rounded the random state after every move, and the replay has to do the same (engine `replay.steps`). */
  rngEncoding: "exact" | "double";
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
  /** The number of the table (the address of its page); the long id of the game is in the header. */
  table?: number;
  header: ArchiveHeader;
  actions: LogEntry[];
  /** Null while the game is not over. */
  result: ArchiveResult | null;
}

/** The file of a game: under the day it started, named by its table number (the long id when the number is not known, as in a test). */
export function gamePath(meta: Pick<Meta, "id" | "startedAt" | "createdAt">, table?: number | null): string {
  const d = new Date(meta.startedAt ?? meta.createdAt);
  const p = (n: number): string => String(n).padStart(2, "0");
  return `seti-engine/games/${d.getUTCFullYear()}/${p(d.getUTCMonth() + 1)}/${p(d.getUTCDate())}/${table ?? meta.id}.json`;
}

/** The log without `undo` and without the moves that it took back (UNDO-01): what is left replays to the same game. The moves are numbered again. */
export function withoutUndone(log: LogEntry[]): LogEntry[] {
  const kept: LogEntry[] = [];
  for (const e of log) {
    if ((e.action as { type?: string }).type === "undo") kept.pop();
    else kept.push(e);
  }
  return kept.map((e, seq) => ({ ...e, seq }));
}

export function headerOf(meta: Meta): ArchiveHeader {
  return {
    format: ARCHIVE_FORMAT,
    id: meta.id,
    options: meta.options,
    clock: meta.clock,
    rated: meta.rated,
    seats: meta.seats.flatMap((s, seat) =>
      s === null
        ? []
        : [
            {
              seat,
              userId: s.id,
              name: s.name,
              registered: s.registered,
              ...(s.num ? { num: s.num } : {}),
              ...(s.bot ? { bot: s.bot } : {}),
            },
          ],
    ),
    ...(meta.consent ? { consent: meta.consent } : {}),
    createdAt: meta.createdAt,
    startedAt: meta.startedAt ?? meta.createdAt,
    rngEncoding: meta.rng === "exact" ? "exact" : "double",
  };
}

export function replayOf(meta: Meta, log: LogEntry[], ratedCounted: boolean, table?: number | null): ReplayFile {
  const actions = withoutUndone(log);
  return {
    format: ARCHIVE_FORMAT,
    ...(table ? { table } : {}),
    header: headerOf(meta),
    actions,
    result:
      meta.result === undefined
        ? null
        : { status: meta.status, endedAt: meta.endedAt ?? 0, result: meta.result, actions: actions.length, ratedCounted },
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
