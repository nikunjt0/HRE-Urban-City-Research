"""Combine the seven 0-3 variables into a weighted composite "launch potential" score.

Inputs (long CSVs, all keyed on city_id + year):
  cities_legal_capacity.csv
  cities_merchant_capital.csv
  cities_agricultural_surplus.csv
  cities_peasant_mobility.csv
  cities_noble_extraction.csv     (negative weight in default)
  cities_conflict_risk.csv        (negative weight in default)
  cities_trade_access.csv         (Viabundus-keyed; joined via crosswalk)

Outputs:
  output/cities_composite.csv         (long; one row per city-year)
  output/cities_composite_wide.csv    (one row per city)

Weights default to lib.targets.DEFAULT_WEIGHTS. Override with --weights path.json.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from lib.paths import OUT
from lib.scoring import bucket_by_quartile, write_long_and_wide
from lib.targets import DEFAULT_WEIGHTS


def load_var(name: str, score_col: str = None) -> pd.DataFrame:
    if score_col is None:
        score_col = f"{name}_score"
    df = pd.read_csv(OUT / f"cities_{name}.csv")
    return df[["city_id", "year", score_col]].rename(columns={score_col: name})


def load_trade_access() -> pd.DataFrame:
    """Trade-access CSV is Viabundus-keyed (city_id == nodesid). Join to
    Bairoch via the crosswalk so this variable lines up with the others."""
    cw_path = OUT / "crosswalk_nodesid_cityid.csv"
    cw = pd.read_csv(cw_path)
    cw = cw.dropna(subset=["city_id", "nodesid"]) \
           .drop_duplicates("nodesid")[["nodesid", "city_id"]]
    cw["nodesid"] = cw["nodesid"].astype(int)
    cw["city_id"] = cw["city_id"].astype(int)

    ta = pd.read_csv(OUT / "cities_trade_access.csv")
    # In TradeAccess CSV city_id is actually the Viabundus nodesid.
    ta = ta[["city_id", "year", "trade_access_score"]].rename(
        columns={"city_id": "nodesid", "trade_access_score": "trade_access"})
    out = ta.merge(cw, on="nodesid", how="left")
    out = out.dropna(subset=["city_id"])
    out["city_id"] = out["city_id"].astype(int)
    out = out.drop_duplicates(["city_id", "year"], keep="first")
    return out[["city_id", "year", "trade_access"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default=None, help="optional weights .json")
    args = parser.parse_args()

    weights = dict(DEFAULT_WEIGHTS)
    if args.weights:
        with open(args.weights) as f:
            weights.update(json.load(f))
    print("Using weights:", weights)

    print("Loading variable CSVs ...")
    parts = [
        load_var("legal_capacity"),
        load_var("merchant_capital"),
        load_var("agricultural_surplus"),
        load_var("peasant_mobility"),
        load_var("noble_extraction"),
        load_var("conflict_risk"),
    ]
    try:
        parts.append(load_trade_access())
    except FileNotFoundError as e:
        print(f"  WARNING: {e}; trade_access dropped from composite")
        weights.pop("trade_access", None)

    # base identity from legal_capacity (Bairoch-keyed, has all 2,390 cities)
    base = pd.read_csv(OUT / "cities_legal_capacity.csv")[
        ["city_id", "name", "lat", "lon", "year"]]
    df = base
    for p in parts:
        df = df.merge(p, on=["city_id", "year"], how="left")
    # missing values default to 0 (cities not in Viabundus get trade_access=0)
    for col in weights:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(float)

    print(f"Joined frame: {len(df):,} rows")

    # Weighted sum
    raw = np.zeros(len(df))
    for col, w in weights.items():
        if col in df.columns:
            raw += w * df[col].values
    df["composite_raw"] = raw
    # GLOBAL bucketing: cutoffs derived from the 1500 distribution so earlier
    # years legitimately show fewer tier-3 cities (the "launch over time" story).
    base_year = df["year"].max()
    base_dist = df[df["year"] == base_year]["composite_raw"]
    q1, q2, q3 = base_dist.quantile([0.40, 0.65, 0.85]).tolist()

    def to_tier(v):
        if v >= q3:
            return 3
        if v >= q2:
            return 2
        if v >= q1:
            return 1
        return 0

    df["composite_0_3"] = df["composite_raw"].apply(to_tier).astype(int)
    print(f"\nGlobal cutoffs (from {base_year}): "
          f"1>={q1:.2f}, 2>={q2:.2f}, 3>={q3:.2f}")

    # nodesid attached for downstream maps; reuse from the legal capacity file
    nd = pd.read_csv(OUT / "cities_legal_capacity.csv")[["city_id", "nodesid"]]
    nd = nd.drop_duplicates("city_id")
    df = df.merge(nd, on="city_id", how="left")

    feat = list(weights.keys()) + ["composite_raw"]
    long_path, wide_path = write_long_and_wide(
        df, "composite", feat, "composite_0_3")
    print(f"Wrote {long_path}")
    print(f"Wrote {wide_path}")

    # Diagnostics
    print("\n=== composite_0_3 by year ===")
    print(df.groupby("year")["composite_0_3"].value_counts().unstack(fill_value=0))
    print("\n=== composite_raw distribution by year ===")
    print(df.groupby("year")["composite_raw"].agg(["min", "median", "max"]).round(2))


if __name__ == "__main__":
    main()
