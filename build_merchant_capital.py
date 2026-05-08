"""Build the MerchantCapital 0-3 variable per (city, benchmark year).

Inputs:
  docs/territorial_histories/territorial_hit/cities_polities.csv  (hanse flag, year-granular)
  docs/markets/markets_data/markets.csv                            (market presence)
  docs/viabundus/Viabundus-2-csv/fairs.csv                         (regional/interregional fairs)
  docs/viabundus/Viabundus-2-csv/nodes.csv                         (Is_Staple)
  output/crosswalk_nodesid_cityid.csv                              (Viabundus -> Bairoch link)

Score:
  3 if (Hanseatic AND interregional fair attested) OR (own staple right active)
  2 if Hanseatic OR regional fair OR interregional fair
  1 if any pre-attested market entry
  0 else
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib.crosswalk import load_crosswalk
from lib.nodes_loader import load_towns
from lib.paths import (BENCHMARKS, CITIES_POLITIES_CSV, CITY_LOCATIONS_CSV,
                       MARKETS_CSV, VIABUNDUS)
from lib.scoring import write_long_and_wide
from lib.yearutils import is_active


def main():
    print("Loading city_locations ...")
    cities = pd.read_csv(CITY_LOCATIONS_CSV)
    cities = cities[["city_id", "name", "latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"})

    print("Loading cities_polities (filtering to BENCHMARKS at load time) ...")
    pol = pd.read_csv(CITIES_POLITIES_CSV, usecols=["city_id", "year", "hanse"])
    pol = pol[pol["year"].isin(BENCHMARKS)].copy()
    print(f"  {len(pol):,} polity rows at benchmark years")
    hanse_by_cy = pol.set_index(["city_id", "year"])["hanse"].to_dict()

    print("Loading markets ...")
    mk = pd.read_csv(MARKETS_CSV)
    # Filter to plausible medieval evidence: time_point <= 1600. The 1939 /
    # 1900-tagged rows are placeholder reference years; skip them.
    mk = mk[mk["time_point"] <= 1600].copy()
    earliest_market = mk.groupby("city_id")["time_point"].min().to_dict()
    # type_market == 6 (Messe / Jahrmarkt = major annual fair) is the strongest
    # market signal for southern German cities not covered by Viabundus.
    mk_messe = mk[mk["type_market"] == 6].groupby("city_id")["time_point"].min().to_dict()
    print(f"  {len(mk):,} market rows pre-1600; "
          f"{len(earliest_market):,} cities with markets, "
          f"{len(mk_messe):,} with Messe (annual fair)")

    print("Loading Viabundus fairs ...")
    fairs = pd.read_csv(VIABUNDUS / "fairs.csv", low_memory=False, na_values=["null", ""])
    print(f"  {len(fairs):,} fair entries")

    print("Loading Viabundus nodes (for Is_Staple) ...")
    towns_v, nodes_v, resolve_to_parent = load_towns()
    # parent cascade: collect staples whose parent town is identifiable
    staples = nodes_v[nodes_v["Is_Staple"] == "y"].copy()
    print(f"  {len(staples):,} staple-active nodes (post cascade)")

    print("Loading crosswalk ...")
    cw = load_crosswalk()
    # nodesid -> bairoch city_id
    node_to_city = cw.dropna(subset=["city_id"]).set_index("nodesid")["city_id"].astype(int).to_dict()

    # Helpers
    fair_cat_rank = {"local": 1, "regional": 2, "interregional": 3}

    print("Building per-(city, year) frame ...")
    rows = []
    for y in BENCHMARKS:
        # Active fairs in y
        af = fairs[is_active(fairs["fromyear"], fairs["toyear"], y, default_from=1300)].copy()
        af["cat_rank"] = af["category"].map(fair_cat_rank).fillna(1).astype(int)
        # Map fair node to parent town nodesid, then to Bairoch city_id
        af["town_nodesid"] = af["nodesid"].map(
            lambda n: resolve_to_parent(int(n)) if pd.notna(n) else None)
        af["bairoch_id"] = af["town_nodesid"].map(
            lambda n: node_to_city.get(int(n)) if pd.notna(n) else None)
        # best fair category per Bairoch city
        af_b = af.dropna(subset=["bairoch_id"])
        best_fair_per_city = af_b.groupby("bairoch_id")["cat_rank"].max().to_dict()

        # Active staples in y
        st = staples[is_active(staples["Staple_From"], staples["Staple_To"], y,
                               default_from=1300)].copy()
        st["town_nodesid"] = st["id"].map(
            lambda n: resolve_to_parent(int(n)) if pd.notna(n) else None)
        st["bairoch_id"] = st["town_nodesid"].map(
            lambda n: node_to_city.get(int(n)) if pd.notna(n) else None)
        staple_cities = set(st["bairoch_id"].dropna().astype(int))

        for _, c in cities.iterrows():
            cid = int(c["city_id"])
            hanse = int(hanse_by_cy.get((cid, y), 0) == 1)
            best_fair = int(best_fair_per_city.get(cid, 0))
            has_regional = int(best_fair >= 2)
            has_interregional = int(best_fair >= 3)
            has_staple = int(cid in staple_cities)
            em = earliest_market.get(cid, np.nan)
            has_market = int(np.isfinite(em) and em <= y)
            mm = mk_messe.get(cid, np.nan)
            has_messe = int(np.isfinite(mm) and mm <= y)

            # Score:
            #   3: has_staple, OR Viabundus interregional fair,
            #      OR (Hanseatic AND any fair/Messe)
            #   2: Hanseatic, OR Viabundus regional fair, OR has_messe
            #      (Bairoch Jahrmarkt) — captures south-German Messestädte
            #   1: any market attested
            if has_staple or has_interregional or (hanse and (has_regional or has_messe)):
                score = 3
            elif hanse or has_regional or has_messe:
                score = 2
            elif has_market:
                score = 1
            else:
                score = 0

            # Continuous (pre-bucket) signal — predictive-model input.
            # best_fair_category is already 0/1/2/3, preserving fair-tier info
            # that the bucket-score collapses.
            merchant_continuous = (
                1.5 * float(best_fair)
                + 1.5 * float(has_staple)
                + 1.0 * float(hanse)
                + 0.7 * float(has_messe)
                + 0.3 * float(has_market)
            )

            rows.append({
                "city_id": cid,
                "name": c["name"],
                "lat": c["lat"],
                "lon": c["lon"],
                "year": y,
                "is_hanseatic": hanse,
                "best_fair_category": best_fair,  # 0/1/2/3 = none/local/regional/interregional
                "has_regional_fair": has_regional,
                "has_interregional_fair": has_interregional,
                "has_staple": has_staple,
                "has_messe_by_y": has_messe,
                "has_market_by_y": has_market,
                "merchant_capital_score": score,
                "merchant_capital_continuous": round(float(merchant_continuous), 4),
            })

    df = pd.DataFrame(rows)
    # attach nodesid for downstream mapping/joining
    cw_attach = cw[["city_id", "nodesid"]].dropna(subset=["city_id"]).drop_duplicates("city_id")
    df = df.merge(cw_attach, on="city_id", how="left")
    print(f"Built {len(df):,} (city, year) rows")

    feat = ["is_hanseatic", "best_fair_category", "has_regional_fair",
            "has_interregional_fair", "has_staple", "has_messe_by_y",
            "has_market_by_y", "merchant_capital_continuous"]
    long_path, wide_path = write_long_and_wide(
        df, "merchant_capital", feat, "merchant_capital_score")
    print(f"Wrote {long_path}")
    print(f"Wrote {wide_path}")
    print("\n=== merchant_capital_score by year ===")
    print(df.groupby("year")["merchant_capital_score"].value_counts().unstack(fill_value=0))


if __name__ == "__main__":
    main()
