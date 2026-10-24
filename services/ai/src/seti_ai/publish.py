"""Publish the statistics of the model versions to the site: writes SQL for the table `bot_versions` (apps/worker/migrations/0007_bot_versions.sql).

    .venv/Scripts/python.exe -m seti_ai.publish --models models_v3 --approve v003=orion --enable orion --wrangler "node C:/.../wrangler.js" [--apply]

Only numbers go to the site (the manifest of each version: when, which rules, how trained, how it played). The weights do not leave this machine here.

Every version that is published has a NAME that the owner gives (`--approve v003=orion`: letters, digits, `.`, `_` and `-`, up to 40, not used
before). The name is what the lobby, the page of the AIs, the seat of the game and the folder of the AI service call the version; the folder
`v003` of the training stays what it is. `v001` (published before the names) keeps its own name. `--enable` and `--disable` list the names that a host
can add to a game (`bot_versions.live`); the administrator's page does the same with a button. Training never approves, names or enables anything.
"""

from __future__ import annotations

import argparse
import json
import re
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


NAME = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


def display_name(m: dict[str, Any]) -> str:
    """The name of a version: the one the owner gave, or its folder (v001, published before the names)."""
    return str(m.get("name") or m["version"])


def check_name(models: Path, folder: str, name: str) -> None:
    """A name is new, well formed, and not another version's folder."""
    if not NAME.match(name):
        raise SystemExit(f"{name!r} is not a name: letters, digits, '.', '_' and '-', up to 40")
    if re.fullmatch(r"v\d{3}", name) and name != folder:
        raise SystemExit(f"{name!r} looks like the number of a version: choose a name")
    taken = {display_name(json.loads(p.read_text(encoding="utf-8"))): p.parent.name for p in models.glob("v[0-9][0-9][0-9]/manifest.json")}
    if name in taken and taken[name] != folder:
        raise SystemExit(f"the name {name!r} is already the name of {taken[name]}")


def statements(models: Path, approve: list[str], enable: list[str] | None = None, disable: list[str] | None = None) -> list[str]:
    out: list[str] = []
    for manifest in sorted(models.glob("v[0-9][0-9][0-9]/manifest.json")):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        if not (m.get("approved") or m["version"] in approve):
            continue  # a version that the owner has not approved is not on the site
        name = display_name(m)
        training = {**m["training"], "built_from": m["version"]} if name != m["version"] else m["training"]
        out.append(
            "INSERT INTO bot_versions (version, created, rules_version, parent, players, training_json, evaluation_json, approved, live, note) "
            f"VALUES ({sql(name)}, {sql(m['created'])}, {sql(m['rules_version'])}, {sql(m.get('parent'))}, {sql(m.get('players', 2))}, "
            f"{sql(json.dumps(training))}, {sql(json.dumps(m['evaluation']))}, 1, 0, {sql(m.get('note'))}) "
            "ON CONFLICT(version) DO UPDATE SET evaluation_json = excluded.evaluation_json, training_json = excluded.training_json, "
            "approved = MAX(approved, excluded.approved), note = excluded.note;"
        )
    for names, flag in ((enable or [], 1), (disable or [], 0)):
        for n in names:
            out.append(f"UPDATE bot_versions SET live = {flag} WHERE version = {sql(n)};")
    return out


def parse_approvals(models: Path, items: list[str]) -> dict[str, str]:
    """`v003=orion` -> {folder: name}. A version without a name is refused, unless it already has one (or is v001, from before the names)."""
    out: dict[str, str] = {}
    for item in items:
        folder, _, name = item.partition("=")
        manifest = models / folder / "manifest.json"
        if not manifest.exists():
            raise SystemExit(f"there is no version {folder!r} in {models}")
        m = json.loads(manifest.read_text(encoding="utf-8"))
        if not name:
            if m.get("name") or folder == "v001":
                name = display_name(m)
            else:
                raise SystemExit(f"give {folder} a name: --approve {folder}=<name>")
        if name != display_name(m) or m.get("name"):
            check_name(models, folder, name)
        out[folder] = name
    return out


def mark_approved(models: Path, versions: list[str] | dict[str, str]) -> None:
    """Write the approval (and the name) into the manifests and the index too: the export for the lobby service (`lobby_export`) reads them there."""
    names = versions if isinstance(versions, dict) else {v: "" for v in versions}
    for v, name in names.items():
        manifest = models / v / "manifest.json"
        m = json.loads(manifest.read_text(encoding="utf-8"))
        m["approved"] = True
        if name and name != v:
            m["name"] = name
        manifest.write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    index = models / "index.json"
    if index.exists():
        rows = json.loads(index.read_text(encoding="utf-8"))
        for row in rows:
            if row["version"] in names:
                row["approved"] = True
                if names[row["version"]] and names[row["version"]] != row["version"]:
                    row["name"] = names[row["version"]]
        index.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default="models")
    ap.add_argument("--wrangler", default=None, help='how to run wrangler, for example "node C:/.../wrangler/bin/wrangler.js" (needed with --apply)')
    ap.add_argument("--db", default="seti")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--approve", action="append", default=[], help="a version that the owner approves and names: v003=orion")
    ap.add_argument("--enable", default="", help="names (comma separated) that a host can add to a game")
    ap.add_argument("--disable", default="", help="names (comma separated) that a host can no longer add")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default="publish_bot_versions.sql")
    a = ap.parse_args()
    models = Path(a.models)
    approvals = parse_approvals(models, a.approve)
    mark_approved(models, approvals)
    lines = statements(models, list(approvals), [n for n in a.enable.split(",") if n], [n for n in a.disable.split(",") if n])
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
