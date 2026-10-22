"""Make the statistics of the finished games that have none yet (table game_stats, services/engine/src/seti_engine/stats.py).

    python tools/engine/backfill_stats.py --wrangler "node path/to/wrangler.js" [--db seti] [--local] [--apply]

New games get their statistics when they end; this is for the games that ended before, and for a new counter (use --all to make every game's
again). The tool reads the finished games that were played to their end from D1, replays each with the engine package (run it from services/engine
with `python -m uv run python ../../tools/engine/backfill_stats.py ...`), and writes `backfill_stats.sql` (INSERT OR REPLACE statements). With
--apply it runs that file against D1; without it, it only writes the file for a look. --local reads and writes the local D1 of `wrangler dev`.
"""

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from seti_engine import replay, stats


def d1(wrangler: list[str], db: str, remote: bool, *, command: str | None = None, file: str | None = None) -> list[dict[str, Any]]:
    args = [*wrangler, "d1", "execute", db, "--remote" if remote else "--local", "--json"]
    args += ["--command", command] if command else ["--file", str(file)]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    data = json.loads(out[out.index("[") :])
    return list(data[0]["results"])


def stats_of(file: dict[str, Any], result: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """The statistics of a game and the random-state encoding that replays it. The database does not say which encoding a game was played with
    (games before the 2026-10-21 fix were played with a rounded random state, `rngEncoding` "double"), so both are tried, "exact" first, and the one
    that replays the game to the final scores that were recorded is taken."""
    recorded = {r["seat"]: r["score"] for r in result["ranking"]}
    last_error: Exception | None = None
    for encoding in ("exact", "double"):
        file["header"]["rngEncoding"] = encoding
        try:
            final = None
            for _, _, res in replay.steps(file):
                final = res
            assert final is not None and final.state.phase == "finished"
            totals = {int(r["player"]): int(r["total"]) for r in final.state.final_scores}
            if all(totals.get(seat) == score for seat, score in recorded.items()):
                return stats.game_stats(file), encoding
        except Exception as e:  # this encoding does not replay the game
            last_error = e
    raise ValueError(f"no encoding replays it to the recorded scores ({last_error})")


def sql(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wrangler", required=True, help='how to run wrangler, e.g. "node C:/.../wrangler/bin/wrangler.js"')
    ap.add_argument("--db", default="seti")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--all", action="store_true", help="also the games that already have statistics")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default="backfill_stats.sql")
    a = ap.parse_args()
    wrangler = shlex.split(a.wrangler)
    remote = not a.local
    skip = "" if a.all else " AND NOT EXISTS (SELECT 1 FROM game_stats s WHERE s.game_id = g.id)"
    games = d1(
        wrangler,
        a.db,
        remote,
        command=f"SELECT g.id, g.options_json, g.result_json, g.rated, g.ended_at FROM games g WHERE g.status = 'finished' AND g.reason = 'completed'{skip}",
    )
    print(f"{len(games)} finished game(s) to do")
    lines: list[str] = []
    for g in games:
        gid = g["id"]
        rows = d1(wrangler, a.db, remote, command=f"SELECT log_json FROM game_logs WHERE game_id = '{gid}'")
        seats = d1(wrangler, a.db, remote, command=f"SELECT seat, user_id FROM game_players WHERE game_id = '{gid}' ORDER BY seat")
        if not rows:
            print(f"  {gid[:8]}: no log, skipped")
            continue
        log = json.loads(rows[0]["log_json"])
        options = json.loads(g["options_json"])
        result = json.loads(g["result_json"])
        file = {
            "format": replay.FORMAT,
            "header": {"options": options},
            "actions": [{"seq": i, "action": e["action"]} for i, e in enumerate(log)],
        }
        try:
            st, encoding = stats_of(file, result)
        except Exception as e:  # a game that the engine can no longer replay (the rules changed): left out, and said
            print(f"  {gid[:8]}: cannot be replayed ({type(e).__name__}: {str(e)[:80]}), skipped")
            continue
        user = {s["seat"]: s["user_id"] for s in seats}
        for p in st["players"]:
            ranked = next((r for r in result["ranking"] if r["seat"] == p["seat"]), None)
            if ranked is None or p["seat"] not in user:
                continue
            values = [
                gid,
                p["seat"],
                user[p["seat"]],
                len(seats),
                g["rated"],
                st["expansion"],
                ranked["rank"],
                p["seat"] in result["winners"],
                ranked["score"],
                p["org"],
                json.dumps(p["org_offered"]),
                json.dumps(st["species"]),
                json.dumps(p["counters"], separators=(",", ":")),
                g["ended_at"] or 0,
            ]
            lines.append(
                "INSERT OR REPLACE INTO game_stats (game_id, seat, user_id, players, rated, expansion, rank, won, score, org, org_offered_json, "
                f"species_json, counters_json, ended_at) VALUES ({', '.join(sql(v) for v in values)});"
            )
        print(f"  {gid[:8]}: {len(st['players'])} player(s) (random state: {encoding})")
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} row(s) written to {a.out}")
    if a.apply and lines:
        d1(wrangler, a.db, remote, file=a.out)
        print("applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
