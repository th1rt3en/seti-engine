"""Publish the statistics of the model versions to the site: writes SQL for the table `bot_versions` (apps/worker/migrations/0007_bot_versions.sql).

    .venv/Scripts/python.exe -m seti_ai.publish --wrangler "node C:/.../wrangler.js" [--apply] [--live v003]

Only numbers go to the site (the manifest of each version: when, which rules, how trained, how it played). The weights do not leave this machine here.
`approved` and `live` are set by the owner with --approve and --live; training never sets them.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any


def sql(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def statements(models: Path, approve: list[str], live: str | None) -> list[str]:
    out: list[str] = []
    for manifest in sorted(models.glob("v[0-9][0-9][0-9]/manifest.json")):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        approved = bool(m.get("approved")) or m["version"] in approve or m["version"] == live
        out.append(
            "INSERT INTO bot_versions (version, created, rules_version, parent, players, training_json, evaluation_json, approved, live, note) "
            f"VALUES ({sql(m['version'])}, {sql(m['created'])}, {sql(m['rules_version'])}, {sql(m.get('parent'))}, {sql(m.get('players', 2))}, "
            f"{sql(json.dumps(m['training']))}, {sql(json.dumps(m['evaluation']))}, {sql(approved)}, {sql(m['version'] == live)}, {sql(m.get('note'))}) "
            "ON CONFLICT(version) DO UPDATE SET evaluation_json = excluded.evaluation_json, training_json = excluded.training_json, "
            "approved = MAX(approved, excluded.approved), note = excluded.note;"
        )
    if live:
        out.append(f"UPDATE bot_versions SET live = CASE WHEN version = {sql(live)} THEN 1 ELSE 0 END;")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default="models")
    ap.add_argument("--wrangler", default=None, help='how to run wrangler, for example "node C:/.../wrangler/bin/wrangler.js" (needed with --apply)')
    ap.add_argument("--db", default="seti")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--approve", action="append", default=[], help="a version that the owner approves")
    ap.add_argument("--live", default=None, help="the version that is served to the players")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default="publish_bot_versions.sql")
    a = ap.parse_args()
    lines = statements(Path(a.models), a.approve, a.live)
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} statement(s) written to {a.out}")
    if a.apply:
        assert a.wrangler, "--wrangler is needed with --apply"
        cmd = [*shlex.split(a.wrangler), "d1", "execute", a.db, "--local" if a.local else "--remote", "--file", a.out]
        subprocess.run(cmd, check=True)
        print("applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
