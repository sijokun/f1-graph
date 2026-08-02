# F1 Teammate Graph

Interactive network of every Formula 1 teammate pairing since 1950, rendered
with [cosmos](https://github.com/cosmograph-org/cosmos) (Cosmograph's GPU
engine). Vertices are driver portraits, edge width is how many races a pair
started together, and a season range slider filters any era.

By [Yan Khachko](https://slnk.icu).

## Layout

| Path | What it is |
|---|---|
| `f1_entries_all.csv` | one row per driver per race, 1950–present (Jolpica-Ergast API) |
| `data/graph_data_all.json` | nodes/links with per-season counts + precomputed layout positions |
| `data/photo_manifest.json` | driver → photo filename |
| `data/photo_credits.json` | driver → photo author / license / Commons page |
| `site/` | the deployable static site (`index.html` + `photos/`) |
| `scripts/` | the update & build pipeline |
| `.github/workflows/update.yml` | daily/manual data refresh + GitHub Pages deploy |

## Setting up GitHub Pages

1. Push this repository to GitHub.
2. Repo **Settings → Pages → Source: GitHub Actions**.
3. Run the **"Update F1 data & deploy"** workflow from the Actions tab
   (it also runs automatically every day at 06:00 UTC).

## Local build

```bash
pip install requests pillow
python scripts/update_entries.py      # refresh current season (a few API calls)
python scripts/build_data.py          # CSV → graph data + last-race stamp
python scripts/fetch_photos.py        # Wikipedia portraits for new drivers only
python scripts/fetch_photo_credits.py # author/license for new photos only
node   scripts/layout.mjs             # offline force layout (no jiggle at runtime)
python scripts/build_site.py          # assemble site/index.html
python -m http.server -d site 8000    # preview at http://localhost:8000
```

## Data sources

- **Race data**: [Jolpica-F1 API](https://github.com/jolpica/jolpica-f1)
  (`api.jolpi.ca`), the community-maintained successor to the
  [Ergast](https://ergast.com/mrd/) Formula 1 database. One row per classified
  driver per championship race, 1950–present (includes the 1950–1960
  Indianapolis 500s, which counted toward the World Championship).
- **Photos**: Wikipedia / [Wikimedia Commons](https://commons.wikimedia.org)
  page images, downscaled to 72px thumbnails. Each driver card shows the
  photographer and license, linked to the source file page.
- **Rendering**: [cosmos](https://github.com/cosmograph-org/cosmos) by
  Cosmograph (CC-BY-NC 4.0, non-commercial).
