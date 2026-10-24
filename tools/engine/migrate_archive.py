"""Move the games of the archive from the old layout (a folder of files for each game) to the new one (one file for each game; docs/PLAN.md D25).

    python tools/engine/migrate_archive.py --wrangler "node path/to/wrangler.js" [--work DIR] [--apply] [--delete-old]

Old:  seti-engine/games/YYYY/MM/DD/<game id>/{header.json, actions/<seq>.json, result.json, replay.json}
New:  seti-engine/games/YYYY/MM/DD/<table number>.json   (a game whose number is not known keeps its id)

The new file is the replay file (format seti-game-log/1) without `undo` and without the moves that it took back, the moves numbered again, with `table`.
Steps (each is safe to run again):
  1. downloads the old games into DIR/old (gcloud storage rsync),
  2. reads the table numbers from D1 (wrangler d1 execute ... --remote),
  3. writes the new files into DIR/new and says how many it made,
  4. with --apply: uploads DIR/new (it never deletes anything in the bucket),
  5. with --delete-old (after --apply): checks that every new file is in the bucket and then removes the old folders of the games it made.
Run it from the repository root with Python 3.12 (it needs nothing but the standard library and gcloud).
"""

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BUCKET = "gs://temp-common-storage"
ROOT = f"{BUCKET}/seti-engine/games"


def run(args: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, **kw)


def gcloud(*args: str, **kw: Any) -> subprocess.CompletedProcess[str]:
    exe = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
    return run([exe, *args], **kw)


def table_numbers(wrangler: list[str], db: str) -> dict[str, int]:
    out = run([*wrangler, "d1", "execute", db, "--remote", "--json", "--command", "SELECT game_id, num FROM game_nums"], capture_output=True).stdout
    return {r["game_id"]: int(r["num"]) for r in json.loads(out[out.index("[") :])[0]["results"]}


def without_undone(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The same as `withoutUndone` of apps/worker/src/core/archive.ts."""
    kept: list[dict[str, Any]] = []
    for e in actions:
        if e["action"].get("type") == "undo":
            if kept:
                kept.pop()
        else:
            kept.append(e)
    return [{**e, "seq": i} for i, e in enumerate(kept)]


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def old_game(folder: Path) -> dict[str, Any] | None:
    """The replay file of an old game folder (None when it has no header)."""
    if (folder / "replay.json").exists():
        file: dict[str, Any] = read(folder / "replay.json")
        return file
    if not (folder / "header.json").exists():
        return None
    actions = [read(p) for p in sorted((folder / "actions").glob("*.json"))]
    result = read(folder / "result.json") if (folder / "result.json").exists() else None
    return {"format": "seti-game-log/1", "header": read(folder / "header.json"), "actions": actions, "result": result}


def convert(file: dict[str, Any], table: int | None) -> dict[str, Any]:
    actions = without_undone(file["actions"])
    result = file.get("result")
    if result is not None:
        result = {**result, "actions": len(actions)}
    out: dict[str, Any] = {"format": file["format"]}
    if table:
        out["table"] = table
    return {**out, "header": file["header"], "actions": actions, "result": result}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wrangler", default="npx wrangler")
    ap.add_argument("--db", default="seti")
    ap.add_argument("--work", default=str(Path(tempfile.gettempdir()) / "seti-archive-migration"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--delete-old", action="store_true")
    a = ap.parse_args()
    work = Path(a.work)
    old, new = work / "old", work / "new"
    old.mkdir(parents=True, exist_ok=True)
    print("downloading the old games ...")
    gcloud("storage", "rsync", "-r", ROOT, str(old))
    numbers = table_numbers(shlex.split(a.wrangler, posix=False), a.db)
    print(f"{len(numbers)} table numbers from D1")
    made: list[tuple[Path, str]] = []  # (old folder, the new path under games/)
    skipped = 0
    for header in sorted(old.rglob("header.json")):
        folder = header.parent
        rel = folder.relative_to(old)  # YYYY/MM/DD/<id>
        if len(rel.parts) != 4:
            continue
        file = old_game(folder)
        if file is None:
            skipped += 1
            continue
        game_id = rel.parts[3]
        table = numbers.get(game_id)
        name = f"{'/'.join(rel.parts[:3])}/{table or game_id}.json"
        target = new / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(convert(file, table), separators=(",", ":")), encoding="utf-8")
        made.append((folder, name))
    unnumbered = sum(1 for _, n in made if not n.rsplit("/", 1)[1].removesuffix(".json").isdigit())
    print(f"{len(made)} games written to {new} ({unnumbered} without a table number, {skipped} folders without a header skipped)")
    if not a.apply:
        print("nothing uploaded (add --apply)")
        return 0
    gcloud("storage", "rsync", "-r", str(new), ROOT)
    print("uploaded")
    if not a.delete_old:
        return 0
    listing = set(gcloud("storage", "ls", "-r", f"{ROOT}/**", capture_output=True).stdout.split())
    missing = [n for _, n in made if f"{ROOT}/{n}" not in listing]
    if missing:
        print(f"{len(missing)} new files are not in the bucket (first: {missing[0]}): nothing deleted")
        return 1
    urls = [f"{ROOT}/{folder.relative_to(old).as_posix()}" for folder, _ in made]
    for k in range(0, len(urls), 40):  # a call removes many folders at once
        gcloud("storage", "rm", "-r", *urls[k : k + 40])
        print(f"removed {min(k + 40, len(urls))}/{len(urls)} old folders")
    print("old folders removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
