import { PlayersTable } from "@/components/PlayersTable";
import { getDb } from "@/lib/db";
import { allPlayers } from "@/lib/queries";
import Link from "next/link";

export const dynamic = "force-dynamic";
export const metadata = { title: "Players" };

export default async function Players({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const rows = await allPlayers(getDb(), q.trim().slice(0, 40));
  return (
    <>
      <h1>Players</h1>
      <form action="/players" method="get" className="inline">
        <input type="search" name="q" defaultValue={q} placeholder="Find a player" aria-label="Find a player" maxLength={40} />{" "}
        <button type="submit" className="primary small">
          Search
        </button>
      </form>
      <p className="muted">
        {rows.length} registered player{rows.length === 1 ? "" : "s"}
        {q ? ` with “${q}” in their name` : ""}. Players who have not played a rated game have the starting rating, 0.
      </p>
      {rows.length === 0 ? <p>No player found.</p> : <PlayersTable rows={rows} />}
    </>
  );
}
