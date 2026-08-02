"""Incrementally update f1_entries_all.csv: re-fetch only the current season
from the Jolpica-Ergast API and merge it in. Cheap enough to run daily."""

import csv
import sys
import time
from datetime import date
from pathlib import Path

import requests

BASE = "https://api.jolpi.ca/ergast/f1"
LIMIT = 100
ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "f1_entries_all.csv"
FIELDS = ["season", "round", "race_name", "date", "session",
          "team", "driver", "driver_number"]

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
                })
        offset += LIMIT
        if offset >= total:
            return rows
        time.sleep(0.4)


def main():
    today = date.today()
    years = [today.year]
    if today.month <= 2:            # early season: last year's finale may be newer
        years.insert(0, today.year - 1)
    fresh = []
    for y in years:
        fresh += fetch_season(y)
        time.sleep(0.4)
    # the new season may have zero completed races yet (January) — that's fine
    old = list(csv.DictReader(open(CSV, encoding="utf-8")))
    refetched = {str(y) for y in years}
    kept = [r for r in old if r["season"] not in refetched]
    merged = kept + fresh
    year = years[-1]
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(merged)
    print(f"{year}: {len(fresh)} entries (was {len(old) - len(kept)}); "
          f"total {len(merged)}")
    if len(fresh) < len(old) - len(kept):
        print("WARNING: fewer rows than before for current season",
              file=sys.stderr)


if __name__ == "__main__":
    main()
