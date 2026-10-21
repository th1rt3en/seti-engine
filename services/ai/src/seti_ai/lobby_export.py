"""Copy the approved versions of the model into a folder for the image of the lobby service (weights are not in git; docs/deploy-ai.md).

    python -m seti_ai.lobby_export --models models_alpha --out serve_models

Only a version with `approved: true` in the index is copied (the owner approves with `seti_ai.publish --approve`), and only its weights and manifest.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .lobby import approved_versions


def export(models: Path, out: Path) -> list[str]:
    versions = approved_versions(models)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(models / "index.json", out / "index.json")
    for v in versions:
        (out / v).mkdir(exist_ok=True)
        for name in ("model.pt", "manifest.json"):
            shutil.copyfile(models / v / name, out / v / name)
    return versions


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", default="models_alpha")
    ap.add_argument("--out", default="serve_models")
    a = ap.parse_args()
    versions = export(Path(a.models), Path(a.out))
    print("copied:", ", ".join(versions) if versions else "nothing (no version is approved)")


if __name__ == "__main__":
    main()
