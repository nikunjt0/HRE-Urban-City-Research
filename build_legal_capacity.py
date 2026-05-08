"""Build the LegalCapacity 0-3 variable per (city, benchmark year).

Inputs:
  docs/town_charters_and_first_mentions/towncharter_data/towncharter.csv
  docs/town_charters_and_first_mentions/towncharter_data/legal_families.csv
  docs/construction_data/construction.csv          (filter building==5 = town hall)
  docs/city_locations_and_border_maps/dataverse_files/city_locations.csv
  hard-coded pre-1500 university list (lib.paths.PRE_1500_UNIVERSITIES)

type_origin coding (verified from towncharter_documentation.pdf):
  0 = evidence of city character prior to formal charter
  1 = formal bestowal of town charter         <-- POSITIVE signal
  2 = WITHDRAWAL of town charter              <-- NEGATIVE signal
  3 = changes to town charter                 <-- neutral
  4 = no information on charter
  5 = first recorded mention only             <-- weak

Score:
  3 if city_status >= 2 (imperial / free imperial) — strongest legal autonomy
       OR has_formal_charter (type_origin==1) AND (townhall OR strong family)
  2 if city_status == 1 (free city)
       OR has_formal_charter
       OR (any charter signal AND townhall)
  1 if any pre-charter or first-mention attestation
  0 nothing
  Apply -1 penalty if charter was WITHDRAWN (type_origin==2 in window).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib.crosswalk import attach_nodesid
from lib.geo import EARTH_KM, haversine_nearest
from lib.paths import (BENCHMARKS, CITY_LOCATIONS_CSV, CONSTRUCTION_CSV,
                       LEGAL_FAMILIES_CSV, PRE_1500_UNIVERSITIES,
                       STRONG_LEGAL_FAMILIES, TERRITORIES_ALL_CSV,
                       TOWNCHARTER_CSV)
from lib.scoring import write_long_and_wide


def main():
    print("Loading city_locations ...")
    cities = pd.read_csv(CITY_LOCATIONS_CSV)
    cities = cities[["city_id", "name", "latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"})
    print(f"  {len(cities):,} cities")

    print("Loading towncharter ...")
    charter = pd.read_csv(TOWNCHARTER_CSV)
    # only pre-1600 evidence is useful for medieval scoring
    charter = charter[charter["time_point"] <= 1600].copy()
    charter["time_point"] = pd.to_numeric(charter["time_point"], errors="coerce")
    charter["type_origin"] = pd.to_numeric(charter["type_origin"], errors="coerce")
    charter = charter.dropna(subset=["time_point", "city_id"])
    print(f"  {len(charter):,} charter rows pre-1600")

    print("Loading territories_all (city_status: 0=lord, 1/2/3=imperial/free imperial) ...")
    terr = pd.read_csv(TERRITORIES_ALL_CSV, low_memory=False)
    # Status applies during [beginning_reign, end_reign]. Group by city, take
    # the max status that applies in each benchmark year.
    terr_by_city = {}
    for cid, g in terr.dropna(subset=["beginning_reign"]).groupby("city_id"):
        terr_by_city[int(cid)] = g[["beginning_reign", "end_reign", "city_status"]].copy()

    def status_at_year(cid: int, y: int) -> int:
        sub = terr_by_city.get(cid)
        if sub is None:
            return 0
        end = sub["end_reign"].fillna(9999)
        m = (sub["beginning_reign"] <= y) & (end > y)
        if m.any():
            return int(sub.loc[m, "city_status"].max())
        return 0

    print("Loading construction (town halls = building==5) ...")
    cons = pd.read_csv(CONSTRUCTION_CSV)
    townhalls = cons[(cons["building"] == 5) & (cons["time_point"] <= 1600)].copy()
    townhalls["time_point"] = pd.to_numeric(townhalls["time_point"], errors="coerce")
    townhalls = townhalls.dropna(subset=["time_point", "city_id"])
    # earliest town-hall mention per city
    earliest_townhall = townhalls.groupby("city_id")["time_point"].min().to_dict()
    print(f"  {len(townhalls):,} town-hall rows; {len(earliest_townhall):,} cities w/ townhall")

    # legal_family per city: take the most-frequent code, preferring `legal_family`
    # (= adopted from) but falling back to `legal_family_own` (= namesake/own code).
    def primary_family(row):
        return row["legal_family"] if pd.notna(row["legal_family"]) else row["legal_family_own"]
    charter["effective_family"] = charter.apply(primary_family, axis=1)
    fam = charter.dropna(subset=["effective_family"])
    family_per_city = fam.groupby("city_id")["effective_family"].apply(
        lambda s: s.value_counts().index[0]
    ).to_dict()

    # earliest charter time per city, plus best (= lowest nonzero) type_origin per city
    ch_nonzero = charter[(charter["type_origin"] > 0) & (charter["type_origin"] < 5)]
    earliest_charter = ch_nonzero.groupby("city_id")["time_point"].min().to_dict()
    # earliest first-mention (type_origin == 5) per city
    fm = charter[charter["type_origin"] == 5]
    earliest_mention = fm.groupby("city_id")["time_point"].min().to_dict()

    # Pre-compute, per benchmark year:
    #   - has_formal_charter[y][cid]   : type_origin==1 attested by year y
    #   - charter_withdrawn[y][cid]    : type_origin==2 attested by year y
    #   - has_changes[y][cid]          : type_origin==3 attested by year y
    has_formal_by_year = {}
    withdrawn_by_year = {}
    has_changes_by_year = {}
    for y in BENCHMARKS:
        sub = charter[charter["time_point"] <= y]
        has_formal_by_year[y] = set(sub.loc[sub["type_origin"] == 1, "city_id"].unique())
        withdrawn_by_year[y] = set(sub.loc[sub["type_origin"] == 2, "city_id"].unique())
        has_changes_by_year[y] = set(sub.loc[sub["type_origin"] == 3, "city_id"].unique())

    print("Computing distance to nearest pre-1500 university ...")
    uni = pd.DataFrame(PRE_1500_UNIVERSITIES,
                       columns=["uni", "founded", "lat", "lon"])
    city_xy = np.deg2rad(cities[["lat", "lon"]].to_numpy())
    # per benchmark year, only universities with founded <= year are eligible
    dist_uni_by_year = {}
    for y in BENCHMARKS:
        elig = uni[uni["founded"] <= y]
        if elig.empty:
            dist_uni_by_year[y] = np.full(len(cities), np.nan)
        else:
            tgt = np.deg2rad(elig[["lat", "lon"]].to_numpy())
            dist_uni_by_year[y] = haversine_nearest(city_xy, tgt)

    print("Building per-(city, year) frame ...")
    rows = []
    cities_idx = cities.reset_index(drop=True)
    for y in BENCHMARKS:
        formal_y = has_formal_by_year[y]
        withdrawn_y = withdrawn_by_year[y]
        changes_y = has_changes_by_year[y]
        for i, c in cities_idx.iterrows():
            cid = int(c["city_id"])
            em = earliest_mention.get(cid, np.nan)
            has_formal = cid in formal_y
            charter_withdrawn = cid in withdrawn_y
            has_changes = cid in changes_y
            has_mention = np.isfinite(em) and em <= y
            th = earliest_townhall.get(cid, np.nan)
            has_townhall = np.isfinite(th) and th <= y
            family = family_per_city.get(cid, None)
            strong_family = family in STRONG_LEGAL_FAMILIES if family else False
            d_uni = dist_uni_by_year[y][i]
            cstatus = status_at_year(cid, y)

            # Score:
            #   3 = imperial / free imperial (status >= 2),
            #       OR (formal charter AND (townhall OR strong family))
            #   2 = free city (status == 1), OR formal charter,
            #       OR (any charter signal + townhall)
            #   1 = any charter or first-mention attestation
            #   0 = nothing attested
            #   then: -1 penalty if withdrawn (capped at 0).
            if cstatus >= 2 or (has_formal and (has_townhall or strong_family)):
                score = 3
            elif cstatus == 1 or has_formal or ((has_changes or has_mention) and has_townhall):
                score = 2
            elif has_formal or has_changes or has_mention:
                score = 1
            else:
                score = 0
            if charter_withdrawn:
                score = max(0, score - 1)

            rows.append({
                "city_id": cid,
                "name": c["name"],
                "lat": c["lat"],
                "lon": c["lon"],
                "year": y,
                "has_formal_charter_by_y": int(has_formal),
                "charter_withdrawn_by_y": int(charter_withdrawn),
                "has_charter_changes_by_y": int(has_changes),
                "has_mention_by_y": int(has_mention),
                "has_townhall_by_y": int(has_townhall),
                "legal_family": family if family else "",
                "strong_legal_family": int(strong_family),
                "city_status": cstatus,
                "dist_university_km": (round(float(d_uni), 1) if np.isfinite(d_uni) else np.nan),
                "legal_capacity_score": score,
            })
    df = pd.DataFrame(rows)
    df = attach_nodesid(df)
    print(f"Built {len(df):,} (city, year) rows")

    feat = ["has_formal_charter_by_y", "charter_withdrawn_by_y",
            "has_charter_changes_by_y", "has_mention_by_y",
            "has_townhall_by_y", "strong_legal_family", "city_status",
            "dist_university_km"]
    long_path, wide_path = write_long_and_wide(
        df, "legal_capacity", feat, "legal_capacity_score")
    print(f"Wrote {long_path}")
    print(f"Wrote {wide_path}")
    print("\n=== legal_capacity_score by year ===")
    print(df.groupby("year")["legal_capacity_score"].value_counts().unstack(fill_value=0))


if __name__ == "__main__":
    main()
