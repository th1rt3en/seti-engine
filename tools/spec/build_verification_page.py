"""Build the owner's verification page for the Space Agencies transcriptions (docs/spec/data/expansion-transcription.json): every picture beside
what was read from it, with a Correct / Needs fix choice and a note. Prints the files map for the Artifact tool.

Usage: python tools/spec/build_verification_page.py OUT.html   (writes OUT.html and OUT.files.json)
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "spec" / "data" / "expansion-transcription.json"
MANIFEST = ROOT / "apps" / "web" / "src" / "generated" / "expansion-assets.json"
PUBLIC = ROOT / "apps" / "web" / "public"
TEMPLATE = pathlib.Path(__file__).with_name("verification_page.template.html")


def main(out: pathlib.Path) -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files: dict[str, str] = {}
    items = []
    for it in data["items"]:
        pics = []
        for p in it["pics"]:
            url = manifest[p]
            name = url.removeprefix("/assets/expansion/")  # published beside the page, with root = apps/web/public/assets/expansion
            files[name] = str(PUBLIC / url.lstrip("/"))
            pics.append(name)
        items.append({**it, "pics": pics})
    payload = json.dumps({"items": items}, ensure_ascii=False).replace("</", "<\\/")
    out.write_text(TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload), encoding="utf-8")
    out.with_suffix(".files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    print(len(items), "items,", len(files), "pictures")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
