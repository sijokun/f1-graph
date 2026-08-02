"""Fetch author/license/source-page for photos that don't have credits yet.
Reads data/photo_manifest.json, writes data/photo_credits.json."""

import json
import re
import time
from pathlib import Path

from fetch_photos import OVERRIDES, api_get

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "photo_manifest.json"
CREDITS = ROOT / "data" / "photo_credits.json"

TAGS = re.compile(r"<[^>]+>")


def clean(html):
    return TAGS.sub("", html).replace("\n", " ").strip()


def pageimage_file(title):
    r = api_get({"action": "query", "format": "json", "redirects": 1,
                 "titles": title, "prop": "pageimages", "piprop": "name"})
    for page in r["query"]["pages"].values():
        if page.get("pageimage"):
            return "File:" + page["pageimage"]
    return None


def search_title(name):
    r = api_get({"action": "query", "format": "json", "list": "search",
                 "srsearch": f"{name} Formula One driver", "srlimit": 1})
    hits = r["query"]["search"]
    return hits[0]["title"] if hits else None


def imageinfo(file_titles):
    r = api_get({"action": "query", "format": "json",
                 "titles": "|".join(file_titles),
                 "prop": "imageinfo", "iiprop": "extmetadata|url",
                 "iiextmetadatafilter": "Artist|LicenseShortName"})
    out = {}
    normalized = {n["to"]: n["from"] for n in r["query"].get("normalized", [])}
    for page in r["query"]["pages"].values():
        title = page.get("title", "")
        orig = normalized.get(title, title)
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        out[orig] = {
            "author": clean(meta.get("Artist", {}).get("value", "")),
            "license": clean(meta.get("LicenseShortName", {}).get("value", "")),
            "url": info.get("descriptionurl", ""),
        }
    return out


def main():
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    credits = json.load(open(CREDITS, encoding="utf-8")) if CREDITS.exists() else {}
    todo = [n for n in manifest if n not in credits]
    if not todo:
        print("no new credits needed")
        return
    print(f"fetching credits for {len(todo)} photos")
    files = {}
    for i, name in enumerate(todo):
        f = pageimage_file(OVERRIDES.get(name, name))
        if not f:
            st = search_title(name)
            if st:
                f = pageimage_file(st)
        if f:
            files[name] = f
        time.sleep(0.12)
    infos = {}
    file_list = list(set(files.values()))
    for k in range(0, len(file_list), 50):
        infos.update(imageinfo(file_list[k:k + 50]))
        time.sleep(0.3)
    for name, f in files.items():
        info = infos.get(f)
        if info and (info["author"] or info["license"]):
            credits[name] = info
    json.dump(credits, open(CREDITS, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"credits now cover {len(credits)}/{len(manifest)} photos")


if __name__ == "__main__":
    main()
