"""Rewrite the overview table at the top of docs/spec/ambiguities.md from the entries below it. Run from the repo root: python tools/spec/ambiguity_overview.py"""

import re
import pathlib

F = pathlib.Path(__file__).resolve().parents[2] / "docs" / "spec" / "ambiguities.md"


def short(status: str) -> str:
    s = status.lower()
    for key, label in (("ruled", "ruled"), ("resolved", "resolved"), ("data supplied", "data supplied, to confirm"), ("open", "open"), ("proposed", "proposed (in use, to confirm)")):
        if s.startswith(key):
            return label
    return s.split(" ")[0]


t = F.read_text(encoding="utf-8")
t = re.sub(r"## Overview \(kept up to date.*?\n\n(?=Entry format)", "", t, flags=re.S)
rows = re.findall(r"^## (A-\d+): (.*?)\n- Status: (.*?)$", t, flags=re.M)
table = "## Overview (rewritten by tools/spec/ambiguity_overview.py; the entries below hold the details)\n\n| ID | Title | Status |\n|---|---|---|\n"
table += "".join(f"| {i} | {title} | {short(st)} |\n" for i, title, st in rows) + "\n"
F.write_text(t.replace("Entry format:", table + "Entry format:", 1), encoding="utf-8")
print(len(rows), "entries")
