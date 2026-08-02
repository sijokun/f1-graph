"""Fetch Wikipedia portraits for drivers that don't have one yet.
Writes site/photos/<slug>.jpg and updates data/photo_manifest.json.
Guards against non-portrait page images (flags, maps, logos) and against
the same image being reused for several drivers (search-fallback misses)."""

import hashlib
import io
import json
import re
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PHOTOS_DIR = ROOT / "site" / "photos"
MANIFEST = ROOT / "data" / "photo_manifest.json"
GRAPH = ROOT / "data" / "graph_data_all.json"
NO_PHOTO = ROOT / "data" / "photo_missing.json"  # negative cache: don't retry daily

API = "https://en.wikipedia.org/w/api.php"
SIZE = 72
BAD_FILE = re.compile(
    r"(?i)flag|coat[_ ]?of[_ ]?arms|_map|map_of|logo|bandera|escudo|insignia"
    r"|blank|silhouette|no_image|placeholder|question_mark")

OVERRIDES = {
    "Alexander Albon": "Alex Albon",
    "Carlos Sainz": "Carlos Sainz Jr.",
    "George Russell": "George Russell (racing driver)",
    "Guanyu Zhou": "Zhou Guanyu",
    "Andrea Kimi Antonelli": "Kimi Antonelli",
}

session = requests.Session()
session.headers["User-Agent"] = "f1-driver-graph/1.0 (github action)"


def api_get(params):
    for attempt in range(6):
        resp = session.get(API, params=params, timeout=30)
        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError:
                pass
        time.sleep(2 ** attempt)
    raise RuntimeError(f"API kept failing: {params}")


def slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def page_thumb(title):
    r = api_get({"action": "query", "format": "json", "redirects": 1,
                 "titles": title, "prop": "pageimages",
                 "piprop": "thumbnail", "pithumbsize": 300})
    for page in r["query"]["pages"].values():
        thumb = page.get("thumbnail")
        if thumb:
            return thumb["source"]
    return None


def resolve_thumb(name):
    url = page_thumb(OVERRIDES.get(name, name))
    if url:
        return url, False
    r = api_get({"action": "query", "format": "json", "list": "search",
                 "srsearch": f"{name} Formula One driver", "srlimit": 1})
    hits = r["query"]["search"]
    return (page_thumb(hits[0]["title"]), True) if hits else (None, True)


def to_jpeg(url):
    for attempt in range(5):
        try:
            raw = session.get(url, timeout=30).content
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            break
        except Exception:
            time.sleep(3 * (attempt + 1))
    else:
        return None
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = min((h - side) // 3, h - side)
    img = img.crop((left, top, left + side, top + side)).resize(
        (SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=72, optimize=True)
    return buf.getvalue()


def main():
    manifest = json.load(open(MANIFEST, encoding="utf-8")) if MANIFEST.exists() else {}
    skip = set(json.load(open(NO_PHOTO, encoding="utf-8"))) if NO_PHOTO.exists() else set()
    names = [n["name"] for n in json.load(open(GRAPH, encoding="utf-8"))["nodes"]]
    todo = [n for n in names if n not in manifest and n not in skip]
    if not todo:
        print("no new drivers")
        return
    print(f"fetching {len(todo)} new driver photos")

    # hashes of existing photos, to reject shared/fallback images
    seen_hashes = {hashlib.md5(p.read_bytes()).hexdigest() for p in PHOTOS_DIR.glob("*.jpg")}

    added = 0
    for name in todo:
        try:
            url, from_search = resolve_thumb(name)
        except Exception as e:
            print(f"  {name}: resolve failed ({e})")
            continue  # transient — retry next run, don't cache
        if not url or BAD_FILE.search(url.rsplit("/", 1)[-1]):
            skip.add(name)
            continue
        data = to_jpeg(url)
        if not data:
            continue  # transient download failure — retry next run
        h = hashlib.md5(data).hexdigest()
        if h in seen_hashes:
            # identical to another driver's photo → wrong match, skip for good
            skip.add(name)
            continue
        # search fallback is risky: extra guard — reject if search result image
        # duplicates anything (already checked) and note it in the log
        fn = slug(name) + ".jpg"
        (PHOTOS_DIR / fn).write_bytes(data)
        manifest[name] = fn
        seen_hashes.add(h)
        added += 1
        if from_search:
            print(f"  {name}: via search — verify {fn}")
        time.sleep(0.4)
    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    json.dump(sorted(skip), open(NO_PHOTO, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    print(f"added {added}, manifest {len(manifest)}/{len(names)}, "
          f"{len(skip)} known-missing")


if __name__ == "__main__":
    main()
