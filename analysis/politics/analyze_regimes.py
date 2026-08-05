"""Which rulers' politics actually served their cities? Core regressions.

A. Naive + FE panel: growth on ruler-type shares and instability.
B. Extinction natural experiment: quasi-random ruler change (male line died out)
   -> does the NEW ruler's type matter? does the change itself?
C. Self-rule transitions (free/imperial city gained; mediatization lost).
D. Instability decomposition: occupation, pledging, contested rule, turnover.

Outcome: dlog pop per window, normalized to per-century rates.
Sample: 278 Buringh-matched German cities, windows 1300-1800.
Cluster-robust SEs by city throughout.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "politics"
sys.path.insert(0, str(HERE.parent))

pd.set_option("display.width", 200)


def load() -> pd.DataFrame:
    gp = pd.read_csv(OUT / "growth_panel.csv")
    xw = pd.read_csv(OUT / "crosswalk_cid_cityid.csv")
    cm = pd.read_csv(HERE.parent / "out" / "city_master.csv")
    geo = xw.merge(cm[["cid", "on_river", "on_coast", "lat", "lon"]], on="cid", how="left")
    gp = gp.merge(geo[["city_id", "cid", "on_river", "on_coast"]], on="city_id", how="left")
    gp["span"] = (gp.y1 - gp.y0) / 100.0
    gp["g"] = gp.dlog_pop / gp.span          # growth per century
    gp["lpop0"] = np.log(gp.pop0.where(gp.pop0 > 0))
    gp["window"] = gp.y0.astype(str)
    gp["water"] = ((gp.on_river.fillna(0) + gp.on_coast.fillna(0)) > 0).astype(int)
    gp["turnover"] = gp.n_ruler_changes / gp.span   # changes per century
    return gp


def fit(df, formula, label, results):
    m = smf.ols(formula, data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df["city_id"]})
    results[label] = {
        "n": int(m.nobs), "r2": round(m.rsquared, 3),
        "coef": {k: [round(v, 4), round(m.bse[k], 4), round(m.pvalues[k], 4)]
                 for k, v in m.params.items() if not k.startswith("C(")},
    }
    print(f"\n=== {label} (n={int(m.nobs)}, R2={m.rsquared:.3f}) ===")
    rows = [k for k in m.params.index if not k.startswith("C(") and k != "Intercept"]
    print(pd.DataFrame({"coef": m.params[rows], "se": m.bse[rows],
                        "p": m.pvalues[rows]}).round(4).to_string())
    return m


def part_a_d(gp, results):
    d = gp.dropna(subset=["g", "lpop0"]).copy()
    base = "g ~ lpop0 + water + C(window)"
    fit(d, base + " + share_church + share_self + share_foreign", "A1_types_pooled", results)
    fit(d, base + " + share_church + share_self + share_foreign"
            " + share_occupied + share_pledged + share_contested + turnover",
        "A2_types_plus_instability", results)
    # city FE (within-city changes only)
    fit(d, "g ~ lpop0 + C(window) + C(city_id) + share_church + share_self"
           " + share_foreign + share_occupied + share_pledged + share_contested + turnover",
        "A3_city_FE", results)
    # D: instability alone with city FE
    fit(d, "g ~ lpop0 + C(window) + C(city_id) + share_unstable + turnover",
        "D1_instability_cityFE", results)


def part_b_extinction(gp, results):
    """Windows containing >=1 extinction-driven ruler change vs windows with no
    change at all, within city. Then: among extinction windows, new ruler type."""
    ev = pd.read_csv(OUT / "regime_events.csv")
    d = gp.dropna(subset=["g", "lpop0"]).copy()
    d["any_change"] = d.n_ruler_changes > 0
    d["ext_change"] = d.n_extinction > 0
    d["nonext_change"] = d.any_change & ~d.ext_change
    fit(d, "g ~ lpop0 + C(window) + C(city_id) + ext_change + nonext_change",
        "B1_change_ext_vs_nonext_cityFE", results)

    # what type of ruler did extinction deliver? attach the first extinction
    # event's new_type to each ext window
    ext = ev[ev.type_change == 3].copy()
    ext = ext.sort_values("year").drop_duplicates("city_id", keep="first")  # placeholder
    # per window: merge on all ext events in window
    evw = []
    for _, r in d[d.ext_change].iterrows():
        e = ev[(ev.city_id == r.city_id) & (ev.type_change == 3) &
               (ev.year >= r.y0) & (ev.year < r.y1)]
        if len(e):
            evw.append({"city_id": r.city_id, "y0": r.y0,
                        "new_type": e.iloc[0]["new_type"],
                        "old_type": e.iloc[0]["old_type"]})
    ew = pd.DataFrame(evw)
    d2 = d.merge(ew, on=["city_id", "y0"], how="left")
    d2["ext_to_church"] = d2.ext_change & d2.new_type.eq("church")
    d2["ext_to_noble"] = d2.ext_change & d2.new_type.eq("noble")
    d2["ext_other"] = d2.ext_change & ~(d2.ext_to_church | d2.ext_to_noble)
    fit(d2, "g ~ lpop0 + C(window) + C(city_id) + ext_to_church + ext_to_noble"
            " + ext_other + nonext_change", "B2_ext_by_new_ruler_type", results)


def part_c_selfrule(gp, results):
    d = gp.dropna(subset=["g", "lpop0"]).copy()
    d = d.sort_values(["city_id", "y0"])
    d["dself"] = d.groupby("city_id")["share_self"].diff()
    d["gain_self"] = (d.dself > 0.25).astype(int)
    d["lose_self"] = ((d.dself < -0.25) | (d.n_mediatized > 0)).astype(int)
    fit(d, "g ~ lpop0 + C(window) + gain_self + lose_self + share_self",
        "C1_selfrule_transitions", results)
    fit(d, "g ~ lpop0 + C(window) + C(city_id) + gain_self + lose_self",
        "C2_selfrule_transitions_cityFE", results)
    print("\n gain_self windows:", int(d.gain_self.sum()),
          " lose_self windows:", int(d.lose_self.sum()))


if __name__ == "__main__":
    gp = load()
    print("analysis rows with growth:", gp.dropna(subset=["g", "lpop0"]).shape)
    results = {}
    part_a_d(gp, results)
    part_b_extinction(gp, results)
    part_c_selfrule(gp, results)
    (OUT / "regime_regressions.json").write_text(json.dumps(results, indent=2))
    print("\nwrote", OUT / "regime_regressions.json")
