"""Build data/graph_data_all.json from f1_entries_all.csv:
nodes/links with per-season race counts, races-per-season table, and the
most recent completed race. Layout positions are added later by layout.mjs."""

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "f1_entries_all.csv"
OUT = ROOT / "data" / "graph_data_all.json"


def main():
    race_team = defaultdict(set)
    races = defaultdict(lambda: defaultdict(int))
    teams = defaultdict(set)
    races_per_season = defaultdict(int)
    seen = set()
    last = ("", "", "")  # (date, name, season)
    for r in csv.DictReader(open(CSV, encoding="utf-8")):
        y = int(r["season"])
        race_team[(y, r["round"], r["team"])].add(r["driver"])
        races[r["driver"]][y] += 1
        teams[r["driver"]].add(r["team"])
        if (y, r["round"]) not in seen:
            seen.add((y, r["round"]))
            races_per_season[y] += 1
            if r["date"] > last[0]:
                last = (r["date"], r["race_name"], r["season"])

    pairs = defaultdict(lambda: defaultdict(int))
    pair_teams = defaultdict(set)
    for (y, rnd, team), drivers in race_team.items():
        for a, b in combinations(sorted(drivers), 2):
            pairs[(a, b)][y] += 1
            pair_teams[(a, b)].add(team)

    names = sorted(races)
    idx = {n: i for i, n in enumerate(names)}
    nodes = [{"name": n,
              "ys": sorted([y, c] for y, c in races[n].items()),
              "teams": sorted(teams[n])} for n in names]
    links = [{"s": idx[a], "t": idx[b],
              "ys": sorted([y, c] for y, c in ys.items()),
              "teams": sorted(pair_teams[(a, b)])}
             for (a, b), ys in pairs.items()]
    links.sort(key=lambda l: -sum(c for _, c in l["ys"]))
    out = {
        "nodes": nodes, "links": links,
        "racesPerSeason": {str(y): c for y, c in sorted(races_per_season.items())},
        "lastRace": {"date": last[0], "name": last[1], "season": last[2]},
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(nodes)} drivers, {len(links)} pairings, "
          f"last race: {last[1]} {last[0]}")


if __name__ == "__main__":
    main()
