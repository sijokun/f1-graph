"""Build one JSON per graph from f1_entries_all.csv into data/graphs/.

Every graph shares the same shape — nodes/links with per-season counts, a
races-per-season table and the most recent completed race — plus a `meta`
block that tells the site how to label it. Layout positions are added later
by layout.mjs. data/graphs/index.json lists the graphs for the picker.

Add a graph by writing a builder that returns (nodes-per-driver, pairs) and
registering it in GRAPHS.
"""

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "f1_entries_all.csv"
OUT_DIR = ROOT / "data" / "graphs"


def load_rows():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    for r in rows:
        r["season"] = int(r["season"])
        r["pos"] = int(r["position"]) if r.get("position", "").isdigit() else 0
    return rows


def season_table(rows):
    """races per season + the most recent completed race."""
    races_per_season = defaultdict(int)
    seen = set()
    last = ("", "", "")  # (date, name, season)
    for r in rows:
        key = (r["season"], r["round"])
        if key in seen:
            continue
        seen.add(key)
        races_per_season[r["season"]] += 1
        if r["date"] > last[0]:
            last = (r["date"], r["race_name"], str(r["season"]))
    return races_per_season, last


def assemble(meta, per_driver, pairs, races_per_season, last):
    """per_driver: name -> {season: count}, teams; pairs: (a, b) -> {season: count}, teams"""
    counts, teams = per_driver
    pair_counts, pair_teams = pairs
    names = sorted(counts)
    idx = {n: i for i, n in enumerate(names)}
    nodes = [{"name": n,
              "ys": sorted([y, c] for y, c in counts[n].items()),
              "teams": sorted(teams[n])} for n in names]
    links = [{"s": idx[a], "t": idx[b],
              "ys": sorted([y, c] for y, c in ys.items()),
              "teams": sorted(pair_teams[(a, b)])}
             for (a, b), ys in pair_counts.items()]
    links.sort(key=lambda l: -sum(c for _, c in l["ys"]))
    return {
        "meta": meta,
        "nodes": nodes, "links": links,
        "racesPerSeason": {str(y): c for y, c in sorted(races_per_season.items())},
        "lastRace": {"date": last[0], "name": last[1], "season": last[2]},
    }


# ---------------------------------------------------------------- teammates

TEAMMATES_META = {
    "id": "teammates",
    "label": "Teammates",
    "title": "Who raced alongside whom",
    "blurb": "Every Formula 1 teammate pairing since 1950.",
    "aria": "Network graph of Formula 1 teammate pairings since 1950",
    "nodeUnit": ["race start", "race starts"],
    "peerUnit": ["teammate", "teammates"],
    "linkUnit": ["race as teammates", "races as teammates"],
    "linkShort": ["race", "races"],
    "listLabel": "Teammates · when · races",
    "legendSuffix": "races together",
    "statNodes": "drivers",
    "statLinks": "pairings",
    "search": "Find a driver…",
}


def build_teammates(rows):
    race_team = defaultdict(set)
    counts = defaultdict(lambda: defaultdict(int))
    teams = defaultdict(set)
    for r in rows:
        race_team[(r["season"], r["round"], r["team"])].add(r["driver"])
        counts[r["driver"]][r["season"]] += 1
        teams[r["driver"]].add(r["team"])

    pair_counts = defaultdict(lambda: defaultdict(int))
    pair_teams = defaultdict(set)
    for (y, _rnd, team), drivers in race_team.items():
        for a, b in combinations(sorted(drivers), 2):
            pair_counts[(a, b)][y] += 1
            pair_teams[(a, b)].add(team)
    return (counts, teams), (pair_counts, pair_teams)


# ------------------------------------------------------------------ podiums

PODIUMS_META = {
    "id": "podiums",
    "label": "Shared podiums",
    "title": "Who shared the podium",
    "blurb": "Two drivers are linked when they finished a race in the top three together.",
    "aria": "Network graph of Formula 1 drivers who shared a podium since 1950",
    "nodeUnit": ["podium", "podiums"],
    "peerUnit": ["podium partner", "podium partners"],
    "linkUnit": ["shared podium", "shared podiums"],
    "linkShort": ["podium", "podiums"],
    "listLabel": "Podium partners · when · times",
    "legendSuffix": "podiums together",
    "statNodes": "drivers",
    "statLinks": "pairings",
    "search": "Find a driver…",
}


def build_podiums(rows):
    """Nodes are podium finishers; a link is a race both stood on the podium in.

    Shared drives (two drivers classified in the same car) can put the same
    name on a podium twice in one race — dedupe per (race, driver).
    """
    race_podium = defaultdict(dict)   # (season, round) -> driver -> team
    counts = defaultdict(lambda: defaultdict(int))
    teams = defaultdict(set)
    for r in rows:
        if not 1 <= r["pos"] <= 3:
            continue
        key = (r["season"], r["round"])
        if r["driver"] in race_podium[key]:
            continue
        race_podium[key][r["driver"]] = r["team"]
        counts[r["driver"]][r["season"]] += 1
        teams[r["driver"]].add(r["team"])

    pair_counts = defaultdict(lambda: defaultdict(int))
    pair_teams = defaultdict(set)
    for (y, _rnd), drivers in race_podium.items():
        for a, b in combinations(sorted(drivers), 2):
            pair_counts[(a, b)][y] += 1
            pair_teams[(a, b)].update((drivers[a], drivers[b]))
    return (counts, teams), (pair_counts, pair_teams)


GRAPHS = [
    (TEAMMATES_META, build_teammates),
    (PODIUMS_META, build_podiums),
]


def main():
    rows = load_rows()
    races_per_season, last = season_table(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = []
    for meta, builder in GRAPHS:
        per_driver, pairs = builder(rows)
        graph = assemble(meta, per_driver, pairs, races_per_season, last)
        path = OUT_DIR / f"{meta['id']}.json"   # layout.mjs adds `pos` afterwards
        json.dump(graph, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        index.append({k: meta[k] for k in ("id", "label", "title", "blurb")})
        print(f"{meta['id']}: {len(graph['nodes'])} drivers, "
              f"{len(graph['links'])} pairings")
    json.dump(index, open(OUT_DIR / "index.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"last race: {last[1]} {last[0]}")


if __name__ == "__main__":
    main()
