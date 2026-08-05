"""T1: timing placebo for parliament activity (lead vs lag).
T2: succession policy (primogeniture) -> ruler stability -> urban growth.

T1 logic: growth_t = f(parl_act_t) vs f(parl_act_{t+1}).
If the lead 'works' as well as the level, parliaments follow prosperity
rather than cause it. Also parl_act_{t-1} (deep lag).

T2: Kokkonen & Sundell 2020 monarch database (1000-1799): collapse to
country x century: share of years under primogeniture, mean tenure,
depositions per century. Join to Bosker city panel by country. Within-city:
does succession policy predict growth? Primogeniture is a constitutional rule
usually adopted long before outcomes - the classic slow-moving 'policy'.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_europe import load, fit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE.parent / "out" / "politics"
KS = ROOT / "docs/external/kokkonen_sundell_monarchs/bloodisthicker_data.dta"

# Bosker country names -> KS country names (inspect and adjust at run time)
CMAP = {
    "UK": "England", "Czech rep.": "Bohemia", "Rumenia": None,
    "Yugoslavia": None, "Israel": None, "Lebanon": None, "Turkey": None,
    "Cyprus": None, "Malta": None, "Albania": None, "Greece": None,
    "Switzerland": None, "Finland": None, "Ireland": None,
}


def load_ks():
    k = pd.read_stata(KS, convert_categoricals=False)
    keep = [c for c in ["country", "year", "primogeniture", "tenure_final",
                        "deposed_our", "order"] if c in k.columns]
    k = k[keep]
    k["century"] = (k.year // 100) * 100
    agg = k.groupby(["country", "century"]).agg(
        primo=("primogeniture", "mean"),
        depositions=("deposed_our", "sum"),
        n_years=("year", "size"),
    ).reset_index()
    agg["depo_rate"] = agg.depositions / agg.n_years * 100.0
    return k, agg


if __name__ == "__main__":
    results = {}
    d = load()
    s = d[d.europe == 1].dropna(subset=["growth", "lpop"]).copy()
    s = s.sort_values(["citykey", "year"])
    g = s.groupby("citykey")
    # note: rows are century-spaced; shift(-1) = next century's parl_act
    s["parl_lead"] = g.parl_act.shift(-1)
    s["parl_lag"] = g.parl_act.shift(1)
    base = "growth ~ lpop + plund + capital + university + C(year) + C(citykey)"
    fit(s.dropna(subset=["parl_lead"]), base + " + parl_act + parl_lead",
        "T1a_level_vs_lead", results)
    fit(s.dropna(subset=["parl_lag"]), base + " + parl_act + parl_lag",
        "T1b_level_vs_lag", results)

    kraw, ks = load_ks()
    print("KS countries:", sorted(kraw.country.unique())[:40])
    d2 = d[d.europe == 1].copy()
    d2["ks_country"] = d2.country.map(lambda c: CMAP.get(c, c))
    m = d2.merge(ks, left_on=["ks_country", "year"],
                 right_on=["country", "century"], how="inner",
                 suffixes=("", "_ks"))
    print("matched rows:", len(m), "countries:", m.ks_country.nunique())
    sm = m.dropna(subset=["growth", "lpop", "primo"]).copy()
    print("analysis rows:", len(sm))
    fit(sm, "growth ~ lpop + plund + capital + C(year) + C(citykey)"
            " + primo + depo_rate", "T2a_succession_cityFE", results)
    fit(sm, "growth ~ lpop + plund + capital + C(year) + C(citykey)"
            " + primo + depo_rate + parl_act", "T2b_succession_plus_parl",
        results)
    fit(sm, "growth ~ lpop + plund + capital + C(year) + C(citykey)"
            " + primo + depo_rate + parl_act", "T2c_cluster_country",
        results, cluster="country")
    (OUT / "timing_succession.json").write_text(json.dumps(results, indent=2))
    print("\nwrote", OUT / "timing_succession.json")
