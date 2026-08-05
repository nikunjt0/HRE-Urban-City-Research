"""League table of rulers: which dynasties/states delivered growth for their cities?

For every city x century window (1300-1800), attribute the window to the modal
primary ruler (terr_id). Compute the growth residual net of initial size, water
access, and century shocks. Average residuals by ruler lineage with
empirical-Bayes shrinkage toward 0 (prior variance from between-lineage spread).

Output: out/politics/dynasty_league.csv + top/bottom tables.
Sample: 278 Buringh-matched German cities (population outcome).
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "out"
HIT = ROOT / "docs/territorial_histories/territorial_hit"

MIN_WINDOWS = 8  # lineage must govern at least this many city-windows


def modal_ruler():
    p = pd.read_csv(HIT / "cities_polities.csv",
                    usecols=["city_id", "year", "terr_id"])
    wins = [(1300, 1400), (1400, 1500), (1500, 1600), (1600, 1700), (1700, 1800)]
    frames = []
    for a, b in wins:
        sub = p[(p.year >= a) & (p.year < min(b, 1790))]
        m = (sub.groupby(["city_id", "terr_id"]).size().rename("n").reset_index()
               .sort_values("n", ascending=False)
               .drop_duplicates("city_id"))
        m["share"] = m.n / (min(b, 1790) - a)
        m["y0"], m["y1"] = a, b
        frames.append(m[["city_id", "terr_id", "share", "y0", "y1"]])
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    gp = pd.read_csv(OUT / "growth_panel.csv")
    xw = pd.read_csv(OUT / "crosswalk_cid_cityid.csv")
    cm = pd.read_csv(HERE.parent / "city_growth" / "out" / "city_master.csv")
    gp = gp.merge(xw[["city_id", "cid"]], on="city_id").merge(
        cm[["cid", "on_river", "on_coast"]], on="cid", how="left")
    # century windows only (combine the half-century ones)
    gp = gp.dropna(subset=["dlog_pop"])
    gp["span"] = (gp.y1 - gp.y0) / 100.0
    gp["g"] = gp.dlog_pop / gp.span
    gp["lpop0"] = np.log(gp.pop0)
    gp["water"] = ((gp.on_river.fillna(0) + gp.on_coast.fillna(0)) > 0).astype(int)
    gp["cent"] = (gp.y0 // 100) * 100
    m = smf.ols("g ~ lpop0 + water + C(cent)", data=gp).fit()
    gp["resid"] = m.resid

    mr = modal_ruler()
    mr = mr[mr.share >= 0.5]  # ruler must have governed most of the window
    gp["ycent"] = gp.cent
    j = gp.merge(mr, left_on=["city_id", "ycent"], right_on=["city_id", "y0"],
                 how="inner", suffixes=("", "_mr"))

    tc = pd.read_csv(HIT / "territories/territory_codes.csv")
    rt = pd.read_csv(OUT / "ruler_types.csv")[["terr_id", "ruler_type"]]
    agg = (j.groupby("terr_id")
             .agg(mean_resid=("resid", "mean"), sd=("resid", "std"),
                  n=("resid", "size"), cities=("city_id", "nunique"))
             .reset_index()
             .merge(tc, on="terr_id", how="left")
             .merge(rt, on="terr_id", how="left"))
    big = agg[agg.n >= MIN_WINDOWS].copy()
    # empirical Bayes shrinkage
    tau2 = max(big.mean_resid.var() - (big.sd**2 / big.n).mean(), 1e-4)
    big["se2"] = big.sd**2 / big.n
    big["shrunk"] = big.mean_resid * tau2 / (tau2 + big.se2)
    big = big.sort_values("shrunk", ascending=False)
    big.to_csv(OUT / "dynasty_league.csv", index=False)
    cols = ["terr_name", "ruler_type", "n", "cities", "mean_resid", "shrunk"]
    print("=== TOP 15 lineages (shrunken growth residual, % per century) ===")
    print(big.head(15)[cols].round(3).to_string(index=False))
    print("\n=== BOTTOM 15 ===")
    print(big.tail(15)[cols].round(3).to_string(index=False))
    print("\nlineages ranked:", len(big))
