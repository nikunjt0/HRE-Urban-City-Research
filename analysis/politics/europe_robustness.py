"""Stress tests for the 'constrained executives caused growth' result.

R1  cluster by country (parl_act is a country-level regressor)
R2  Atlantic-port x post-1500 control (AJR 2005 confound)
R3  drop England + Netherlands (the classic success stories)
R4  free_prince within country-century (does it vary sub-nationally?)
R5  longer event study for free_prince incl. t-3, balanced window
R6  placebo: does free_prince 'predict' growth BEFORE the switch?
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from analyze_europe import load, fit

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "politics"

ATLANTIC = {"United Kingdom", "Ireland", "Netherlands", "Belgium", "France",
            "Spain", "Portugal", "England", "Scotland"}


if __name__ == "__main__":
    d = load()
    d["atlantic_port"] = ((d.sea == 1) & d.country.isin(ATLANTIC)).astype(int)
    d["post1500"] = (d.year >= 1500).astype(int)
    d["atl_post"] = d.atlantic_port * d.post1500
    s = d[(d.europe == 1)].dropna(subset=["growth", "lpop"]).copy()
    print("countries present:", sorted(s.country.unique()))
    results = {}
    fe = ("growth ~ lpop + plund + capital + university + C(year) + C(citykey)"
          " + commune + free_prince_dls + parl_act")
    fit(s, fe, "R1_cluster_country", results, cluster="country")
    fit(s, fe + " + atl_post", "R2_atlantic_control", results)
    s3 = s[~s.country.isin({"United Kingdom", "Netherlands"})]
    fit(s3, fe, "R3_drop_UK_NL", results)
    # R4: free_prince within country-century
    s["cc"] = s.country + s.year.astype(str)
    var_within = s.groupby("cc").free_prince_dls.nunique()
    print("country-centuries with within variation in free_prince:",
          (var_within > 1).sum(), "of", len(var_within))
    fit(s, "growth ~ lpop + plund + capital + university + C(cc) + C(citykey)"
           " + commune + free_prince_dls", "R4_countryXcentury_FE", results)
    # R5/R6: richer event study with placebo leads
    dd = d[d.europe == 1].sort_values(["citykey", "year"]).copy()
    first = dd[dd.free_prince_dls == 1].groupby("citykey")["year"].min().rename("t0")
    dd = dd.merge(first, on="citykey", how="left")
    dd["rel"] = (dd.year - dd.t0) / 100.0
    for k in [-3, -2, 0, 1, 2, 3]:
        dd[f"es_{'m' if k<0 else 'p'}{abs(k)}"] = (dd.rel == k).astype(int)
    sub = dd.dropna(subset=["growth", "lpop"])
    fit(sub, "growth ~ lpop + plund + C(year) + C(citykey)"
             " + es_m3 + es_m2 + es_p0 + es_p1 + es_p2 + es_p3",
        "R5_freeprince_es_long", results)
    # R6: losing free status (reversals: e.g. Italy under Spanish absolutism)
    dd = dd.sort_values(["citykey", "year"])
    dd["fp_prev"] = dd.groupby("citykey").free_prince_dls.shift()
    dd["lost_free"] = ((dd.free_prince_dls == 0) & (dd.fp_prev == 1)).astype(int)
    dd["gain_free"] = ((dd.free_prince_dls == 1) & (dd.fp_prev == 0)).astype(int)
    lost_ever = dd.groupby("citykey").lost_free.max()
    print("cities that LOST free status at some point:", int(lost_ever.sum()))
    sub2 = dd.dropna(subset=["growth", "lpop"])
    fit(sub2, "growth ~ lpop + plund + C(year) + C(citykey) + gain_free + lost_free",
        "R6_gain_vs_loss", results)
    (OUT / "europe_robustness.json").write_text(json.dumps(results, indent=2))
    print("\nwrote", OUT / "europe_robustness.json")
