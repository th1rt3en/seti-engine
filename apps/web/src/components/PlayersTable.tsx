"use client";
// The table of the players: every column sorts when its head is clicked (a second click reverses it). The rows come sorted by name from the server.
import type { PlayerRow } from "@/lib/queries";
import { useMemo, useState } from "react";
import { PlayerLink } from "./PlayerLink";

type Key = "name" | "rating" | "rated_games" | "games" | "joined" | "last_active";
const COLUMNS: { key: Key; label: string; title?: string }[] = [
  { key: "name", label: "Player" },
  { key: "rating", label: "Rating" },
  { key: "rated_games", label: "Rated games" },
  { key: "games", label: "Games" },
  { key: "joined", label: "Joined" },
  {
    key: "last_active",
    label: "Last activity",
    title: "The latest of signing up, the last login and the last game the player sat in (the site keeps no other trace of a visit)",
  },
];

const day = (ms: number): string => new Date(ms).toISOString().slice(0, 10);
const moment = (ms: number): string => `${new Date(ms).toISOString().slice(0, 16).replace("T", " ")} UTC`;

export function PlayersTable({ rows }: { rows: PlayerRow[] }) {
  const [sort, setSort] = useState<{ key: Key; down: boolean }>({ key: "name", down: false });
  const sorted = useMemo(() => {
    const sign = sort.down ? -1 : 1;
    return [...rows].sort((a, b) => {
      const x = a[sort.key];
      const y = b[sort.key];
      const by =
        typeof x === "string" && typeof y === "string" ? x.localeCompare(y, undefined, { sensitivity: "base" }) : Number(x) - Number(y);
      return by * sign || a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });
  }, [rows, sort]);
  return (
    <table>
      <thead>
        <tr>
          {COLUMNS.map((c) => (
            <th key={c.key} scope="col" title={c.title} aria-sort={sort.key === c.key ? (sort.down ? "descending" : "ascending") : "none"}>
              <button
                type="button"
                className="sort-head"
                onClick={() => setSort((s) => ({ key: c.key, down: s.key === c.key ? !s.down : c.key !== "name" }))}
              >
                {c.label}
                <span aria-hidden="true">{sort.key === c.key ? (sort.down ? " ▼" : " ▲") : ""}</span>
              </button>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sorted.map((r) => (
          <tr key={r.user_id}>
            <td>
              <PlayerLink num={r.num} name={r.name} />
            </td>
            <td>{r.rating}</td>
            <td>{r.rated_games}</td>
            <td>{r.games}</td>
            <td>{day(r.joined)}</td>
            <td title={moment(r.last_active)}>{moment(r.last_active)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
