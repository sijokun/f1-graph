"""Incrementally update f1_entries_all.csv: re-fetch only the current season
from the Jolpica-Ergast API and merge it in. Cheap enough to run daily.

    python scripts/update_entries.py              # current season only
    python scripts/update_entries.py --all        # refetch 1950–now
    python scripts/update_entries.py 1998 1999    # refetch specific seasons
"""

import csv
import sys
import time
from datetime import date
from pathlib import Path

import requests

BASE = "https://api.jolpi.ca/ergast/f1"
LIMIT = 100
FIRST_SEASON = 1950
ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "f1_entries_all.csv"
FIELDS = ["season", "round", "race_name", "date", "session",
          "team", "driver", "driver_number", "position", "points"]

session = requests.Session()
session.headers["User-Agent"] = "f1-entry-list-downloader/1.0 (github action)"


def get_json(url, params=None, retries=6):
    for attempt in range(retries):
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            time.sleep(2 ** attempt * 2)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Gave up: {url}")


def fetch_season(year):
    rows, offset = [], 0
    while True:
        data = get_json(f"{BASE}/{year}/results.json",
                        params={"limit": LIMIT, "offset": offset})
        total = int(data["MRData"]["total"])
        for race in data["MRData"]["RaceTable"]["Races"]:
            for res in race["Results"]:
                drv = res["Driver"]
                rows.append({
                    "season": race["season"], "round": race["round"],
                    "race_name": race["raceName"], "date": race.get("date", ""),
                    "session": "Race",
                    "team": res["Constructor"]["name"],
                    "driver": f'{drv["givenName"]} {drv["familyName"]}',
                    "driver_number": res.get("number", ""),
                    "position": res.get("position", ""),
                    "points": res.get("points", ""),
                })
        offset += LIMIT
        if offset >= total:
            return rows
        time.sleep(0.4)


def seasons_to_fetch(argv):
    today = date.today()
    if "--all" in argv:
        return list(range(FIRST_SEASON, today.year + 1))
    years = [int(a) for a in argv if a.isdigit()]
    if years:
        return sorted(years)
    if today.month <= 2:            # early season: last year's finale may be newer
        return [today.year - 1, today.year]
    return [today.year]


def main():
    years = seasons_to_fetch(sys.argv[1:])
    fresh = []
    for y in years:
        fresh += fetch_season(y)
        time.sleep(0.4)
    # the new season may have zero completed races yet (January) — that's fine
    old = list(csv.DictReader(open(CSV, encoding="utf-8")))
    refetched = {str(y) for y in years}
    kept = [{k: r.get(k, "") for k in FIELDS}
            for r in old if r["season"] not in refetched]
    merged = kept + fresh
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(merged)
    span = f"{years[0]}" if len(years) == 1 else f"{years[0]}–{years[-1]}"
    print(f"{span}: {len(fresh)} entries (was {len(old) - len(kept)}); "
          f"total {len(merged)}")
    if len(fresh) < len(old) - len(kept):
        print("WARNING: fewer rows than before for current season",
              file=sys.stderr)


if __name__ == "__main__":
    main()
