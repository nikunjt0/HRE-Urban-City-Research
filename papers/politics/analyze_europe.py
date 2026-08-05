"""Europe-wide (Bosker et al. 2013 panel): which political regimes caused growth?

Redo De Long-Shleifer 'Princes and Merchants' *within cities*:
  - free_prince_dls : DS classification, city under non-absolutist ('free') rule
  - commune         : city self-governance
  - parl_act        : parliament activity (country-level index mapped to cities)
  - capital, university, plundered as policy/state variables

Specs: (1) pooled naive, (2) city FE, (3) commune adoption event study,
(4) free-prince switches event study. Outcome: dlog citypop (le5) per century.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "out"
DTA = ROOT / "docs/external/bosker_baghdad_london/bagdad_london_final_restat.dta"


def load():
    d = pd.read_stata(DTA)
    d = d.sort_values(["city", "country", "year"])
    d["citykey"] = d.country + "|" + d.city
    d["pop"] = d.citypop_le5.astype(float)
    d["lpop"] = np.log(d["pop"].where(d["pop"] > 0))
    g = d.groupby("citykey")
    d["lpop_next"] = g["lpop"].shift(-1)
    d["growth"] = d.lpop_next - d.lpop            # growth over following century
    d["plund"] = (d.plundered > 0).astype(int)
    d["europe"] = 1 - d.muslim
    return d


def fit(df, formula, label, results, cluster="citykey"):
    m = smf.ols(formula, data=df).fit(cov_type="cluster",
                                      cov_kwds={"groups": df[cluster]})
    keep = [k for k in m.params.index if not k.startswith("C(") and k != "Intercept"]
    results[label] = {"n": int(m.nobs), "r2": round(m.rsquared, 3),
                      "coef": {k: [round(m.params[k], 4), round(m.bse[k], 4),
                                   round(m.pvalues[k], 4)] for k in keep}}
    print(f"\n=== {label} (n={int(m.nobs)}, R2={m.rsquared:.3f}) ===")
    print(pd.DataFrame({"coef": m.params[keep], "se": m.bse[keep],
                        "p": m.pvalues[keep]}).round(4).to_string())
    return m


def event_study(d, var, label, results):
    """Within-city: growth in centuries around first adoption of `var`."""
    d = d.sort_values(["citykey", "year"]).copy()
    first = (d[d[var] == 1].groupby("citykey")["year"].min().rename("t0"))
    d = d.merge(first, on="citykey", how="left")
    d["rel"] = (d.year - d.t0) / 100.0
    for k in [-2, 0, 1, 2]:
        nm = f"es_{'m' if k<0 else 'p'}{abs(k)}"
        d[nm] = (d.rel == k).astype(int)
    sub = d.dropna(subset=["growth"])
    fit(sub, "growth ~ lpop + plund + C(year) + C(citykey)"
             " + es_m2 + es_p0 + es_p1 + es_p2", f"{label}_eventstudy", results)


if __name__ == "__main__":
    d = load()
    s = d.dropna(subset=["growth", "lpop"]).copy()
    print("growth obs:", len(s), "cities:", s.citykey.nunique())
    print("commune adopters:", d[d.commune == 1].citykey.nunique(),
          "free_prince switches:",
          (d.groupby("citykey").free_prince_dls.apply(lambda x: (x.diff() != 0).sum() - 1)).sum())
    results = {}
    base = "growth ~ lpop + plund + sea + river + capital + university + C(year)"
    fit(s, base + " + commune + free_prince_dls + parl_act", "E1_naive_pooled", results)
    fit(s[s.europe == 1], base + " + commune + free_prince_dls + parl_act",
        "E1b_naive_europe_only", results)
    fe = ("growth ~ lpop + plund + capital + university + C(year) + C(citykey)"
          " + commune + free_prince_dls + parl_act")
    fit(s, fe, "E2_city_FE", results)
    fit(s[s.europe == 1], fe, "E2b_city_FE_europe", results)
    event_study(d[d.europe == 1], "commune", "E3_commune", results)
    event_study(d[d.europe == 1], "free_prince_dls", "E4_freeprince", results)
    (OUT / "europe_regressions.json").write_text(json.dumps(results, indent=2))
    print("\nwrote", OUT / "europe_regressions.json")
