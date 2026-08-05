"""Pooled extinction DiD + the consolidation experiment.

For each extinction-driven ruler change: did the city pass to a BIGGER state
(new lineage rules >= 2x as many cities as the old) or to a similar/smaller one?
Stacked DiD, post = decades 0..+5, with treated x post x upsize interaction.
Outcome: asinh construction per decade; also economic-only construction.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

from event_studies import load, LEADS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
HIT = ROOT / "docs/territorial_histories/territorial_hit"
OUT = HERE.parent / "out" / "politics"


def ruler_sizes():
    p = pd.read_csv(HIT / "cities_polities.csv", usecols=["city_id", "year", "terr_id"])
    p["dec"] = (p.year // 10) * 10
    sz = (p.groupby(["terr_id", "dec"])["city_id"].nunique()
            .rename("n_cities").reset_index())
    return sz


def build_events():
    ev = pd.read_csv(OUT / "regime_events.csv")
    ext = ev[(ev.type_change == 3) & (ev.year >= 1350)].copy()
    ext["dec"] = (ext.year // 10) * 10
    ext = ext.sort_values("year").drop_duplicates("city_id", keep="first")
    sz = ruler_sizes()
    ext = ext.merge(sz.rename(columns={"terr_id": "old_terr", "n_cities": "old_n"}),
                    on=["old_terr", "dec"], how="left")
    ext = ext.merge(sz.rename(columns={"terr_id": "new_terr", "n_cities": "new_n"}),
                    on=["new_terr", "dec"], how="left")
    ext["old_n"] = ext.old_n.fillna(1)
    ext["new_n"] = ext.new_n.fillna(1)
    ext["upsize"] = (ext.new_n >= 2 * ext.old_n).astype(int)
    ext["downsize"] = (ext.new_n * 2 <= ext.old_n).astype(int)
    return ext


def pooled_did(d, ext, outcome, label, results):
    treated = ext.set_index("city_id")["dec"].to_dict()
    ups = ext.set_index("city_id")["upsize"].to_dict()
    frames = []
    tset = set(treated)
    ctrl = d[~d.city_id.isin(tset)]
    rng = np.random.default_rng(7)
    ctrl_ids = ctrl.city_id.unique()
    for cid, e0 in treated.items():
        sub = d[d.city_id == cid].copy()
        sub["rel"] = (sub.dec - e0) // 10
        sub = sub[sub.rel.isin(LEADS)]
        sub["stack"] = cid
        frames.append(sub)
        pick = rng.choice(ctrl_ids, size=25, replace=False)
        c = ctrl[ctrl.city_id.isin(pick) & (ctrl.dec >= e0 - 50) & (ctrl.dec <= e0 + 50)].copy()
        c["rel"] = (c.dec - e0) // 10
        c["stack"] = cid
        frames.append(c)
    s = pd.concat(frames, ignore_index=True)
    s["treated"] = s.city_id.isin(tset).astype(int)
    s["post"] = (s.rel >= 0).astype(int)
    s["tp"] = s.treated * s.post
    s["upsize"] = s.city_id.map(ups).fillna(0).astype(int)
    s["tp_up"] = s.tp * s.upsize
    s["cd"] = s["stack"].astype(str) + "_" + s.city_id.astype(str)
    s = s.set_index(["cd", "dec"])
    for X, lab in [(["tp", "n_destroy"], f"{label}_pooled"),
                   (["tp", "tp_up", "n_destroy"], f"{label}_upsize")]:
        m = PanelOLS(s[outcome], s[X], entity_effects=True, time_effects=True,
                     drop_absorbed=True).fit(cov_type="clustered", cluster_entity=True)
        results[lab + "_" + outcome] = {
            "n": int(m.nobs),
            "coef": {c: [round(m.params[c], 4), round(m.std_errors[c], 4),
                         round(m.pvalues[c], 4)] for c in X}}
        print(f"\n=== {lab} [{outcome}] n={int(m.nobs)} ===")
        print(pd.DataFrame({"coef": m.params, "se": m.std_errors,
                            "p": m.pvalues}).round(4).to_string())


if __name__ == "__main__":
    d = load()
    ext = build_events()
    print("extinction events:", len(ext), " upsize:", int(ext.upsize.sum()),
          " downsize:", int(ext.downsize.sum()))
    results = {}
    for oc in ["y", "ynew", "yecon"]:
        pooled_did(d, ext, oc, "EXTDID", results)
    (OUT / "extinction_consolidation.json").write_text(json.dumps(results, indent=2))
    print("\nwrote", OUT / "extinction_consolidation.json")
