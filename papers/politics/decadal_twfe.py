"""Two-way FE on the full decadal construction panel (2,390 cities x 49 decades).

Outcomes: asinh construction (all / new / economic).
Regressors: political instability spells + ruler-change events + regime shares.
Controls: destruction incidents same decade. Cluster by city.
Also: Delta-parliament design on the Europe panel (does growth follow
INCREASES in parl_act?).
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

from analyze_europe import load as load_eu, fit as fit_ols

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def twfe(d, ycol, xcols, label, results):
    s = d.set_index(["city_id", "dec"])
    m = PanelOLS(s[ycol], s[xcols], entity_effects=True, time_effects=True
                 ).fit(cov_type="clustered", cluster_entity=True)
    results[label] = {"n": int(m.nobs),
                      "coef": {c: [round(m.params[c], 4), round(m.std_errors[c], 4),
                                   round(m.pvalues[c], 4)] for c in xcols}}
    print(f"\n=== {label} (n={int(m.nobs)}) ===")
    print(pd.DataFrame({"coef": m.params, "se": m.std_errors,
                        "p": m.pvalues}).round(4).to_string())


if __name__ == "__main__":
    results = {}
    d = pd.read_csv(OUT / "decadal_panel.csv")
    d["y"] = np.arcsinh(d.n_constr)
    d["ynew"] = np.arcsinh(d.n_new)
    d["yecon"] = np.arcsinh(d.n_econ)
    X = ["share_pledged", "share_occupied", "share_disputed", "share_contested",
         "share_foreign", "share_church", "share_self", "n_changes", "n_ext",
         "n_destroy"]
    twfe(d, "y", X, "G1_constr_all", results)
    twfe(d, "ynew", X, "G2_constr_new", results)
    twfe(d, "yecon", X, "G3_constr_econ", results)

    # Delta-parliament: growth on change in parl_act
    eu = load_eu()
    s = eu[eu.europe == 1].dropna(subset=["growth", "lpop"]).copy()
    s = s.sort_values(["citykey", "year"])
    g = s.groupby("citykey")
    s["dparl"] = s.parl_act - g.parl_act.shift(1)
    s["dparl_lead"] = g.parl_act.shift(-1) - s.parl_act
    sub = s.dropna(subset=["dparl", "dparl_lead"])
    fit_ols(sub, "growth ~ lpop + plund + capital + C(year) + C(citykey)"
                 " + dparl + dparl_lead", "T3_delta_parl", results)
    (OUT / "decadal_twfe.json").write_text(json.dumps(results, indent=2))
    print("\nwrote", OUT / "decadal_twfe.json")
