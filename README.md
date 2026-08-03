# F1 Driver Graphs

Interactive networks of Formula 1 drivers since 1950, rendered with
[cosmos](https://github.com/cosmograph-org/cosmos) (Cosmograph's GPU engine).
Vertices are driver portraits, edge width is how often a pair is connected,
and a season range slider filters any era. Pick a graph from the switcher in
the header:

| Graph | An edge means |
|---|---|
| **Teammates** | the two drivers started a race for the same team |
| **Shared podiums** | the two drivers finished the same race in the top three |

By [Yan Khachko](https://slnk.icu).

## Play

**Play** deals you a random start and target driver and asks you to get from one
to the other in as few hops as possible — each hop moves to someone the driver
you're standing on is connected to (a teammate, a podium partner…), picked from
the list in the card. The target stays labelled on the canvas.

Stuck? **Hint** gives up two clues about the target, one at a time: the seasons
they were active, then the teams they drove for. How many you leaned on is
reported at the end.

The shortest possible route is solved up front with a breadth-first search over
the graph *as currently filtered*, so the season range is locked for the length
of a run. When you arrive — or hit **Show answer** — your route and the shortest
one are shown side by side with the step counts. Pairs are drawn 3–7 hops apart
when the graph allows it.

## Layout

| Path | What it is |
|---|---|
| `f1_entries_all.csv` | one row per driver per race, 1950–present, with finishing position (Jolpica-Ergast API) |
| `data/graphs/<id>.json` | one file per graph: `meta`, nodes/links with per-season counts, precomputed layout positions |
| `data/graphs/index.json` | the list of graphs the site offers |
| `data/photo_manifest.json` | driver → photo filename |
| `data/photo_credits.json` | driver → photo author / license / Commons page |
| `site/` | the deployable static site (`index.html` + `data/` + `photos/`) |
| `scripts/` | the update & build pipeline |
| `.github/workflows/update.yml` | daily/manual data refresh + GitHub Pages deploy |

## Adding a graph

Everything downstream of `build_data.py` is graph-agnostic, so a new graph is
one builder function:

1. In `scripts/build_data.py`, add a `*_META` dict (labels the site shows: the
   picker label, title, units for nodes/edges, legend suffix) and a builder
   that turns the CSV rows into `(counts, teams)` per driver and
   `(pair_counts, pair_teams)` per pair — both keyed by season.
2. Register the `(meta, builder)` pair in `GRAPHS`.
3. Re-run `build_data.py` → `layout.mjs` → `build_site.py`.

The site reads `data/graphs/index.json`, fetches each graph's JSON on demand
and keeps the season range across switches. Deep links work: `#podiums`.

## Setting up GitHub Pages

1. Push this repository to GitHub.
2. Repo **Settings → Pages → Source: GitHub Actions**.
3. Run the **"Update F1 data & deploy"** workflow from the Actions tab
   (it also runs automatically every day at 06:00 UTC).

## Local build

```bash
pip install requests pillow
python scripts/update_entries.py      # refresh current season (a few API calls)
                                      # --all refetches 1950–now (~260 calls)
python scripts/build_data.py          # CSV → data/graphs/*.json + last-race stamp
python scripts/fetch_photos.py        # Wikipedia portraits for new drivers only
python scripts/fetch_photo_credits.py # author/license for new photos only
node   scripts/layout.mjs             # offline force layout for every graph
python scripts/build_site.py          # assemble site/index.html + site/data/
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
