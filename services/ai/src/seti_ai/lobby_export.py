"""Copy the approved versions of the model into a folder for the image of the lobby service (weights are not in git; docs/deploy-ai.md).

    python -m seti_ai.lobby_export --models models_alpha --out serve_models

Only a version with `approved: true` in the index is copied (the owner approves with `seti_ai.publish --approve`), and only its weights and manifest.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .lobby import approved_versions


def export(models: Path, out: Path) -> list[str]:
    """The approved versions, each in a folder of its name (the one the owner gave it; v001 keeps its own), and an index of the names."""
    versions = approved_versions(models)
    rows = {r["version"]: r for r in json.loads((models / "index.json").read_text(encoding="utf-8"))}
    out.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    # the versions that were exported from another folder of models stay (a service serves the approved versions of several runs)
    previous = out / "index.json"
    kept = json.loads(previous.read_text(encoding="utf-8")) if previous.exists() else []
    index: list[dict[str, object]] = [row for row in kept if row["version"] not in {str(rows[v].get("name") or v) for v in versions}]
    for v in versions:
        name = str(rows[v].get("name") or v)
        names.append(name)
        index.append({**rows[v], "version": name, "built_from": v})
        (out / name).mkdir(exist_ok=True)
        for f in ("model.pt", "manifest.json"):
            shutil.copyfile(models / v / f, out / name / f)
    (out / "index.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    return names


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", default="models_alpha")
    ap.add_argument("--out", default="serve_models")
    a = ap.parse_args()
    versions = export(Path(a.models), Path(a.out))
    print("copied:", ", ".join(versions) if versions else "nothing (no version is approved)")


if __name__ == "__main__":
    main()
