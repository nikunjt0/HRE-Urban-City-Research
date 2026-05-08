"""Build the NobleExtraction 0-3 variable per (city, benchmark year).

Higher score = more lordly extraction (enters composite with negative weight).

Inputs:
  docs/territorial_histories/territorial_hit/cities_polities.csv
  docs/territorial_histories/territorial_hit/territories_all.csv
  docs/town_charters_and_first_mentions/towncharter_data/towncharter.csv
  docs/city_locations_and_border_maps/dataverse_files/city_locations.csv

city_status coding (verified from territory_documentation.pdf):
  0 = no data or regular (default territorial city under a lord — ambiguous!)
  1 = free city (autonomy via burgher league; e.g., Speyer, Worms, Mainz, Köln, Regensburg)
  2 = imperial city (subordinate directly to emperor)
  3 = free imperial city (both 1 and 2)

type_change != 0 events flag transitions: 4=conquest (worst), 11=inheritance,
  5=purchase, 9=emperor decision, etc.

Score:
  0 = free imperial / imperial city (status >= 2), stable
  1 = free city (status == 1), OR stable lord rule (no transitions, no foreign rule)
  2 = 1-2 transitions, OR foreign rule in window, OR prince-bishop seat
       (a lord-controlled city under a clerical principality is not the same as
       a city of mere unknown status — extraction is documented elsewhere)
  3 = 3+ transitions OR (prince-bishop seat AND foreign rule)
       OR (prince-bishop seat AND multiple conquests in window)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib.crosswalk import attach_nodesid
from lib.paths import (BENCHMARKS, CITIES_POLITIES_CSV, CITY_LOCATIONS_CSV,
                       TERRITORIES_ALL_CSV)
from lib.scoring import write_long_and_wide

# Hand-coded set of city_ids that are known prince-bishop / archbishop SEATS.
# These cities sat under direct ecclesiastical-prince rule for most of the
# medieval period and bore the heaviest ongoing extraction. Sourced from the
# standard list of HRE Hochstifte. Bairoch city_ids verified by spot-check.
PRINCE_BISHOP_SEATS = {
    11039,  # Erfurt (under Mainz archbishopric)
    11094,  # Magdeburg (until 1648 archbishopric — burgher autonomy varied)
    14060,  # Köln (technically archbishop, but Köln was free city after 1288;
            # leave OUT — handled by city_status >= 2)
    18087,  # Speyer (prince-bishopric — but the city itself was free imperial
            # from 1294; LEAVE OUT)
    22016,  # Bamberg (prince-bishopric)
    22145,  # Würzburg (prince-bishopric)
}
# Conservative removal: only the genuinely lord-controlled bishop seats
PRINCE_BISHOP_SEATS = {11039, 22016, 22145}  # Erfurt, Bamberg, Würzburg


def main():
    print("Loading city_locations ...")
    cities = pd.read_csv(CITY_LOCATIONS_CSV)
    cities = cities[["city_id", "name", "latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"})

    print("Loading cities_polities ...")
    pol = pd.read_csv(CITIES_POLITIES_CSV,
                      usecols=["city_id", "year", "terr_id", "type_change", "foreign_rule"])
    pol = pol[(pol["year"] >= 1200) & (pol["year"] <= 1550)]
    # Detect REAL polity transitions: years where this city's terr_id differs
    # from the prior year's. Filter to those for downstream counting.
    pol = pol.sort_values(["city_id", "year"])
    pol["prev_terr"] = pol.groupby("city_id")["terr_id"].shift(1)
    pol["is_transition"] = ((pol["terr_id"] != pol["prev_terr"])
                            & pol["prev_terr"].notna()).astype(int)
    pol_by_city = {int(cid): g for cid, g in pol.groupby("city_id")}
    print(f"  {len(pol):,} polity rows kept (years 1200-1550); "
          f"{pol['is_transition'].sum():,} terr_id transitions")

    print("Loading territories_all (city_status) ...")
    terr = pd.read_csv(TERRITORIES_ALL_CSV, low_memory=False)
    terr_by_city = {}
    for cid, g in terr.dropna(subset=["beginning_reign"]).groupby("city_id"):
        terr_by_city[int(cid)] = g[["beginning_reign", "end_reign", "city_status"]]

    def status_at_year(cid: int, y: int) -> int:
        sub = terr_by_city.get(cid)
        if sub is None:
            return 0
        end = sub["end_reign"].fillna(9999)
        m = (sub["beginning_reign"] <= y) & (end > y)
        if m.any():
            return int(sub.loc[m, "city_status"].max())
        return 0

    print("Building per-(city, year) frame ...")
    rows = []
    for y in BENCHMARKS:
        prev_y = y - 50
        for _, c in cities.iterrows():
            cid = int(c["city_id"])
            cstatus = status_at_year(cid, y)
            sub = pol_by_city.get(cid)
            n_changes = 0
            n_foreign = 0
            if sub is not None:
                window = sub[(sub["year"] >= prev_y) & (sub["year"] <= y)]
                if len(window) > 0:
                    n_changes = int(window["is_transition"].sum())
                    n_foreign = int(window["foreign_rule"].notna().sum())

            is_pb_seat = cid in PRINCE_BISHOP_SEATS

            # Score logic
            if cstatus >= 2 and n_foreign == 0:
                score = 0
            elif cstatus == 1 or (cstatus >= 2 and n_foreign > 0):
                score = 1
            elif (n_changes == 0 and n_foreign == 0 and not is_pb_seat):
                score = 1  # stable lord rule, predictable
            elif (n_changes >= 3) or (is_pb_seat and cstatus == 0 and n_foreign > 0):
                score = 3
            elif (n_changes >= 1) or n_foreign > 0 or is_pb_seat:
                score = 2
            else:
                score = 1

            # Continuous (pre-bucket) signal — predictive-model input. Higher
            # value = more lord-extraction; mirrors the 0-3 sign (negative
            # weight in the composite).
            noble_continuous = (
                1.0 * float(n_changes)
                + 1.0 * float(n_foreign)
                + 1.5 * float(int(is_pb_seat))
                - 1.0 * float(cstatus)
            )

            rows.append({
                "city_id": cid,
                "name": c["name"],
                "lat": c["lat"],
                "lon": c["lon"],
                "year": y,
                "city_status": cstatus,
                "n_polity_changes_50yr": n_changes,
                "n_foreign_rule_years_50yr": n_foreign,
                "is_prince_bishop_seat": int(is_pb_seat),
                "noble_extraction_score": score,
                "noble_extraction_continuous": round(float(noble_continuous), 4),
            })

    df = pd.DataFrame(rows)
    df = attach_nodesid(df)
    print(f"Built {len(df):,} (city, year) rows")

    feat = ["city_status", "n_polity_changes_50yr", "n_foreign_rule_years_50yr",
            "is_prince_bishop_seat", "noble_extraction_continuous"]
    long_path, wide_path = write_long_and_wide(
        df, "noble_extraction", feat, "noble_extraction_score")
    print(f"Wrote {long_path}")
    print(f"Wrote {wide_path}")
    print("\n=== noble_extraction_score by year ===")
    print(df.groupby("year")["noble_extraction_score"].value_counts().unstack(fill_value=0))


if __name__ == "__main__":
    main()
