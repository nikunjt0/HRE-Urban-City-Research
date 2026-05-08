"""Build the PeasantMobility 0-3 variable per (city, benchmark year).

DATA-GAP NOTICE: /docs has no Bürgerbücher (citizen-roll) dataset. There is
no direct evidence of rural-to-urban migration or new-citizen registration
in the available sources. This score is therefore IMPUTED from the three
already-computed variables that proxy the conditions enabling mobility:
  - LegalCapacity   (autonomy / "Stadtluft macht frei" privileges)
  - MerchantCapital (employment-pull from a working merchant economy)
  - NobleExtraction (low extraction = looser serf-binding nearby)

Every row in the output carries imputed=True so downstream consumers can
mask it. The score is deterministic given the three inputs.

Score (deterministic from the three):
  3: legal_capacity == 3 AND merchant_capital >= 2 AND noble_extraction <= 1
  2: legal_capacity >= 2 AND noble_extraction <= 1
  1: legal_capacity >= 1 OR merchant_capital >= 1
  0: else
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib.paths import OUT
from lib.scoring import write_long_and_wide


def main():
    legal = pd.read_csv(OUT / "cities_legal_capacity.csv")[
        ["city_id", "name", "lat", "lon", "year", "legal_capacity_score"]]
    merchant = pd.read_csv(OUT / "cities_merchant_capital.csv")[
        ["city_id", "year", "merchant_capital_score"]]
    noble = pd.read_csv(OUT / "cities_noble_extraction.csv")[
        ["city_id", "year", "noble_extraction_score"]]

    df = legal.merge(merchant, on=["city_id", "year"], how="left") \
              .merge(noble, on=["city_id", "year"], how="left")
    df["legal_capacity_score"] = df["legal_capacity_score"].fillna(0).astype(int)
    df["merchant_capital_score"] = df["merchant_capital_score"].fillna(0).astype(int)
    df["noble_extraction_score"] = df["noble_extraction_score"].fillna(0).astype(int)

    def score_row(r):
        lc = r["legal_capacity_score"]
        mc = r["merchant_capital_score"]
        ne = r["noble_extraction_score"]
        if lc == 3 and mc >= 2 and ne <= 1:
            return 3
        if lc >= 2 and ne <= 1:
            return 2
        if lc >= 1 or mc >= 1:
            return 1
        return 0

    df["peasant_mobility_score"] = df.apply(score_row, axis=1).astype(int)
    df["imputed"] = True

    print(f"Built {len(df):,} (city, year) rows")

    feat = ["legal_capacity_score", "merchant_capital_score",
            "noble_extraction_score", "imputed"]
    long_path, wide_path = write_long_and_wide(
        df, "peasant_mobility", feat, "peasant_mobility_score")
    print(f"Wrote {long_path}")
    print(f"Wrote {wide_path}")
    print("\n=== peasant_mobility_score by year ===")
    print(df.groupby("year")["peasant_mobility_score"].value_counts().unstack(fill_value=0))


if __name__ == "__main__":
    main()
