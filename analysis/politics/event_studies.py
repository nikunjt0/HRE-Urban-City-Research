"""Event studies on the decadal construction panel (all 2,390 cities).

Treatments:
  EXT   first extinction-driven ruler change (type_change=3) after 1350
  PLG   first pledge spell start (share_pledged goes 0 -> >0)
  OCC   first occupation spell start
  SELF+ first transition into self-rule; SELF- first transition out
Outcome: asinh(construction events per decade); also new-builds only.
Design: stacked event study, event decades -5..+5, two-way FE (city, decade),
controls: destruction incidents. Cluster by city.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "politics"

LEADS = range(-5, 6)


def load():
    d = pd.read_csv(OUT / "decadal_panel.csv")
    d["y"] = np.arcsinh(d.n_constr)
    d["ynew"] = np.arcsinh(d.n_new)
    d["yecon"] = np.arcsinh(d.n_econ)
    return d


def first_event_decades(d):
    ev = {}
    g = d.sort_values(["city_id", "dec"]).groupby("city_id")
    # extinction
    ext = d[(d.n_ext > 0) & (d.dec >= 1350)].groupby("city_id")["dec"].min()
    ev["EXT"] = ext
    # pledge / occupation spell starts
    for name, col in [("PLG", "share_pledged"), ("OCC", "share_occupied")]:
        started = []
        for cid, sub in g:
            s = sub[col].fillna(0).to_numpy()
            dec = sub["dec"].to_numpy()
            prev0 = np.r_[True, s[:-1] == 0]
            hit = np.where((s > 0) & prev0 & (dec >= 1350))[0]
            if len(hit):
                started.append((cid, dec[hit[0]]))
        ev[name] = pd.Series(dict(started))
    # self-rule in/out
    for name, sign in [("SELFGAIN", 1), ("SELFLOSS", -1)]:
        hits = []
        for cid, sub in g:
            s = sub["share_self"].fillna(0).to_numpy()
            dec = sub["dec"].to_numpy()
            ds = np.r_[0, np.diff((s > 0.5).astype(int))]
            hit = np.where((ds == sign) & (dec >= 1350))[0]
            if len(hit):
                hits.append((cid, dec[hit[0]]))
        ev[name] = pd.Series(dict(hits))
    return ev


def stacked_es(d, event: pd.Series, label, results, outcome="y"):
    """Treated cities: event at e0. Controls: cities with no event ever (for this
    treatment), matched within the same calendar decades."""
    frames = []
    treated = set(event.index)
    ctrl = d[~d.city_id.isin(treated)]
    for cid, e0 in event.items():
        sub = d[d.city_id == cid].copy()
        sub["rel"] = (sub.dec - e0) // 10
        sub = sub[sub.rel.isin(LEADS)]
        sub["stack"] = cid
        frames.append(sub)
        c = ctrl[(ctrl.dec >= e0 - 50) & (ctrl.dec <= e0 + 50)].copy()
        c = c.sample(min(len(c), 40 * 11), random_state=int(cid))
        c["rel"] = (c.dec - e0) // 10
        c["stack"] = cid
        frames.append(c)
    s = pd.concat(frames, ignore_index=True)
    s["treated"] = s.city_id.isin(treated).astype(int)
    for k in LEADS:
        if k == -1:
            continue
        s[f"ev_{'m' if k<0 else 'p'}{abs(k)}"] = ((s.treated == 1) & (s.rel == k)).astype(int)
    evcols = [c for c in s.columns if c.startswith("ev_")]
    s["cd"] = s["stack"].astype(str) + "_" + s.city_id.astype(str)
    s = s.set_index(["cd", "dec"])
    X = s[evcols + ["n_destroy"]]
    m = PanelOLS(s[outcome], X, entity_effects=True, time_effects=True,
                 drop_absorbed=True).fit(cov_type="clustered",
                                         clusters=s.city_id)
    est = {c: [round(m.params.get(c, np.nan), 4), round(m.std_errors.get(c, np.nan), 4),
               round(m.pvalues.get(c, np.nan), 4)] for c in evcols}
    post = [m.params.get(f"ev_p{k}", np.nan) for k in range(0, 6)]
    pre = [m.params.get(f"ev_m{k}", np.nan) for k in range(2, 6)]
    results[f"{label}_{outcome}"] = {
        "n_treated": len(event), "n_obs": int(m.nobs),
        "coefs": est,
        "mean_post": round(float(np.nanmean(post)), 4),
        "mean_pre": round(float(np.nanmean(pre)), 4),
    }
    print(f"\n=== {label} [{outcome}] treated={len(event)} n={int(m.nobs)} ===")
    print("  pre  (t-5..t-2):", " ".join(f"{m.params.get(f'ev_m{k}', np.nan):+.3f}" for k in range(5, 1, -1)))
    print("  post (t0..t+5): ", " ".join(f"{m.params.get(f'ev_p{k}', np.nan):+.3f}" for k in range(0, 6)))
    print(f"  mean pre {np.nanmean(pre):+.4f}  mean post {np.nanmean(post):+.4f}")
    return m


if __name__ == "__main__":
    d = load()
    ev = first_event_decades(d)
    for k, v in ev.items():
        print(k, "events:", len(v))
    results = {}
    for label in ["EXT", "PLG", "OCC", "SELFGAIN", "SELFLOSS"]:
        if len(ev[label]) >= 8:
            stacked_es(d, ev[label], label, results, outcome="y")
            stacked_es(d, ev[label], label, results, outcome="ynew")
    (OUT / "event_studies.json").write_text(json.dumps(results, indent=2))
    print("\nwrote", OUT / "event_studies.json")
