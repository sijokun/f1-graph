"""Assemble site/index.html from the template, the cosmos bundle, graph data,
the photo manifest (as relative photo URLs) and photo credits."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
OUT = ROOT / "site" / "index.html"


def main():
    tpl = (SCRIPTS / "template.html").read_text(encoding="utf-8")
    bundle = (SCRIPTS / "cosmos.bundle.js").read_text(encoding="utf-8")
    data = (ROOT / "data" / "graph_data_all.json").read_text(encoding="utf-8")
    manifest = json.load(open(ROOT / "data" / "photo_manifest.json", encoding="utf-8"))
    photos = {name: f"photos/{fn}" for name, fn in manifest.items()}
    credits = (ROOT / "data" / "photo_credits.json").read_text(encoding="utf-8")

    body = (tpl.replace("__COSMOS__", bundle, 1)
               .replace("__DATA__", data, 1)
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
          f"(+ {len(photos)} photo files)")


if __name__ == "__main__":
    main()
