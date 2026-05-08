"""Build the ConflictRisk 0-3 variable per (city, benchmark year).

Inputs:
  docs/conflicts_and_war/conflict_incidents.csv     (event-level)
  docs/construction_data/construction.csv           (fire-damage proxy)

type_conflict coding (verified from conflict_incidents_documentation.pdf):
  1 = Unspecified conflict
  2 = Conflict involving destruction of capital  <- MAJOR
  3 = Conflict involving occupation / financial loss  <- MAJOR
warlabel: 0 = no named war; non-zero = a specific named war ID.

A "major" conflict event = type_conflict in {2, 3} OR warlabel != 0.

Score:
  Count events and severity in [y-50, y]:
    0 events                 -> 0
    1 event, no major        -> 1
    2-3 events, no major     -> 2  (or 1 minor + 1 fire)
    4+ events
      OR any major event
      OR 3+ fire-damage records
                             -> 3
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from lib.crosswalk import attach_nodesid
from lib.paths import (BENCHMARKS, CITY_LOCATIONS_CSV, CONFLICT_CSV,
                       CONSTRUCTION_CSV)
from lib.scoring import write_long_and_wide

FIRE_RE = re.compile(r"brand|abgebrannt|feuer|verbrannt", re.IGNORECASE)


def main():
    print("Loading city_locations ...")
    cities = pd.read_csv(CITY_LOCATIONS_CSV)
    cities = cities[["city_id", "name", "latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"})

    print("Loading conflicts ...")
    cf = pd.read_csv(CONFLICT_CSV)
    cf["time_point"] = pd.to_numeric(cf["time_point"], errors="coerce")
    cf = cf.dropna(subset=["time_point", "city_id"])
    cf = cf[(cf["time_point"] >= 1100) & (cf["time_point"] <= 1550)].copy()
    print(f"  {len(cf):,} conflict events 1100-1550")

    # Major conflict: destruction of capital (2) OR occupation/financial loss (3),
    # OR any event tied to a named war (warlabel != 0).
    cf["is_major"] = (
        cf["type_conflict"].isin([2, 3]) | (cf["warlabel"].fillna(0) != 0)
    ).astype(int)

    print("Loading construction (fire-damage signal) ...")
    cons = pd.read_csv(CONSTRUCTION_CSV)
    cons = cons.dropna(subset=["time_point", "city_id"]).copy()
    cons["time_point"] = pd.to_numeric(cons["time_point"], errors="coerce")
    cons = cons[(cons["time_point"] >= 1100) & (cons["time_point"] <= 1550)]
    cons_fire = cons[cons["comment"].fillna("").apply(lambda s: bool(FIRE_RE.search(str(s))))]
    print(f"  {len(cons_fire):,} fire-damage construction rows")

    print("Building per-(city, year) frame ...")
    # Group conflicts by city_id for fast windowed lookup
    cf_by_city = {int(cid): g.sort_values("time_point") for cid, g in cf.groupby("city_id")}
    fire_by_city = {int(cid): g["time_point"].values
                    for cid, g in cons_fire.groupby("city_id")}

    rows = []
    for y in BENCHMARKS:
        prev_y = y - 50
        for _, c in cities.iterrows():
            cid = int(c["city_id"])
            sub = cf_by_city.get(cid)
            n_events = 0
            n_major = 0
            if sub is not None:
                w = sub[(sub["time_point"] >= prev_y) & (sub["time_point"] <= y)]
                n_events = len(w)
                n_major = int(w["is_major"].sum())

            fires = fire_by_city.get(cid)
            n_fires = 0
            if fires is not None:
                n_fires = int(((fires >= prev_y) & (fires <= y)).sum())

            # Severity weights: a major siege is worse than ordinary skirmishes;
            # a fire is meaningful but not catastrophic.
            if n_major >= 1 or n_events >= 4 or n_fires >= 3:
                score = 3
            elif n_events >= 2 or n_fires >= 2 or (n_events == 1 and n_fires >= 1):
                score = 2
            elif n_events >= 1 or n_fires >= 1:
                score = 1
            else:
                score = 0

            rows.append({
                "city_id": cid,
                "name": c["name"],
                "lat": c["lat"],
                "lon": c["lon"],
                "year": y,
                "n_conflicts_50yr": n_events,
                "n_major_conflicts_50yr": n_major,
                "n_fires_50yr": n_fires,
                "conflict_risk_score": score,
            })

    df = pd.DataFrame(rows)
    df = attach_nodesid(df)
    print(f"Built {len(df):,} (city, year) rows")

    feat = ["n_conflicts_50yr", "n_major_conflicts_50yr", "n_fires_50yr"]
    long_path, wide_path = write_long_and_wide(
        df, "conflict_risk", feat, "conflict_risk_score")
    print(f"Wrote {long_path}")
    print(f"Wrote {wide_path}")
    print("\n=== conflict_risk_score by year ===")
    print(df.groupby("year")["conflict_risk_score"].value_counts().unstack(fill_value=0))


if __name__ == "__main__":
    main()
