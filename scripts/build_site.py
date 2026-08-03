"""Assemble site/index.html from the template, the cosmos bundle, the photo
manifest (as relative photo URLs) and photo credits.

Graph data is *not* inlined: every data/graphs/<id>.json is copied to
site/data/ and fetched on demand, so adding a graph doesn't grow the page.
The graph index (with a content hash per graph for cache-busting) is inlined.
"""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
GRAPH_DIR = ROOT / "data" / "graphs"
SITE = ROOT / "site"
OUT = SITE / "index.html"


def copy_graphs():
    dest = SITE / "data"
    dest.mkdir(parents=True, exist_ok=True)
    index = json.load(open(GRAPH_DIR / "index.json", encoding="utf-8"))
    stale = {p.name for p in dest.glob("*.json")}
    total = 0
    for entry in index:
        src = GRAPH_DIR / f"{entry['id']}.json"
        raw = src.read_bytes()
        entry["v"] = hashlib.sha1(raw).hexdigest()[:8]
        (dest / src.name).write_bytes(raw)
        stale.discard(src.name)
        total += len(raw)
        print(f"  {entry['id']}.json: {len(raw) / 1e6:.2f} MB")
    for name in stale:                     # a graph that no longer exists
        (dest / name).unlink()
    return index, total


def main():
    tpl = (SCRIPTS / "template.html").read_text(encoding="utf-8")
    bundle = (SCRIPTS / "cosmos.bundle.js").read_text(encoding="utf-8")
    manifest = json.load(open(ROOT / "data" / "photo_manifest.json", encoding="utf-8"))
    photos = {name: f"photos/{fn}" for name, fn in manifest.items()}
    credits = (ROOT / "data" / "photo_credits.json").read_text(encoding="utf-8")
    index, data_bytes = copy_graphs()

    body = (tpl.replace("__COSMOS__", bundle, 1)
               .replace("__INDEX__", json.dumps(index, ensure_ascii=False), 1)
               .replace("__PHOTOS__", json.dumps(photos, ensure_ascii=False), 1)
               .replace("__CREDITS__", credits, 1))
    head_end = body.index("</style>") + len("</style>")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1" />
{body[:head_end]}
</head>
<body>
{body[head_end:]}
</body>
</html>"""
    OUT.write_text(page, encoding="utf-8")
    print(f"site/index.html: {len(page) / 1e6:.2f} MB "
          f"(+ {data_bytes / 1e6:.2f} MB graph data, {len(photos)} photo files)")


if __name__ == "__main__":
    main()
