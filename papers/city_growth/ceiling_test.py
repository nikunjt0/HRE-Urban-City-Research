"""Is R2=0.56 a model failure or the information ceiling?

Test: give a flexible ML model (gradient boosting / random forest) EVERY
1200-vintage feature we possess — size, full geography incl. lat/lon, elevation,
privileges already granted by 1200, Carolingian (800) size where known — and
measure out-of-sample R2 for log pop1500. Two CV designs:
  - 5-fold random KFold over cities (the optimistic design), and
  - spatially BLOCKED CV (GroupKFold over 2°x2° lat/lon cells), so raw
    coordinates cannot let the trees simply recognise regions and memorise
    the region's 1500 outcome level.
If the kitchen sink cannot meaningfully beat the 3-parameter law under blocked
CV, the residual is unknowable-in-1200 noise, not missing factors.

Privilege features are coverage-aware: a grant dummy is only an observed zero
inside the source's universe; the universe flags themselves (in_via, in_stb)
are supplied as features so the model can tell "no grant" from "not covered".

Also: the horizon ladder (predicting 1500 from 1400/1300/1200/800) to show the
decay is what a noisy dynamical system produces.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import cross_val_score, KFold, GroupKFold
from coverage import viabundus_flag, stadtebuch_flag

OUT = Path(__file__).resolve().parent / "out"
TH = 1000.0

d = pd.read_csv(OUT / "synthesis_frame.csv")
d = d[d["in_cne"] == True].copy()
for y in [800, 1200, 1300, 1400, 1500]:
    d[f"l{y}"] = np.log(d[f"pop{y}"].where(d[f"pop{y}"] >= TH))
pw = pd.read_csv(OUT / "privilege_wide.csv")[["cid", "staple_year", "fair_year"]]
cp = pd.read_csv(OUT / "city_performers.csv")[["cid", "charter_year", "market_year"]]
d = d.merge(pw, on="cid", how="left").merge(cp, on="cid", how="left")
# a handful of lat/lon values are corrupted in the source (1e14-scale); mask to median
for c, lo, hi in [("lat", 35, 62), ("lon", -12, 32)]:
    bad = (d[c] < lo) | (d[c] > hi)
    d.loc[bad, c] = d.loc[~bad, c].median()
# coverage universes: grant-by-1200 dummies are observed zeros only in-universe
d["in_via"] = viabundus_flag(d).astype(float)
d["in_stb"] = stadtebuch_flag(d).astype(float)
for col, y in [("staple_by1200", "staple_year"), ("fair_by1200", "fair_year")]:
    d[col] = ((d[y] <= 1200).fillna(False) & (d["in_via"] == 1)).astype(float)
for col, y in [("charter_by1200", "charter_year"), ("market_by1200", "market_year")]:
    d[col] = ((d[y] <= 1200).fillna(False) & (d["in_stb"] == 1)).astype(float)
d["water"] = ((d["on_river"] == 1) | (d["on_coast"] == 1)).astype(float)
d["has_l800"] = d["l800"].notna().astype(float)
d["l800_f"] = d["l800"].fillna(d["l800"].mean())

s = d.dropna(subset=["l1200", "l1500"]).copy()
FEATS = ["l1200", "water", "on_river", "on_coast", "atlantic", "baltic", "northsea",
         "medit", "elev", "lat", "lon", "staple_by1200", "fair_by1200",
         "charter_by1200", "market_by1200", "in_via", "in_stb", "l800_f", "has_l800"]
X = s[FEATS].to_numpy()
yv = s["l1500"].to_numpy()
# spatial blocks: 2-degree lat/lon cells
blocks = (np.floor(s["lat"] / 2.0).astype(int).astype(str) + "_" +
          np.floor(s["lon"] / 2.0).astype(int).astype(str)).to_numpy()
cv_rand = KFold(n_splits=5, shuffle=True, random_state=11)
cv_spat = GroupKFold(n_splits=5)

print(f"n = {len(s)} cities; target var(l1500) = {yv.var():.3f}; "
      f"{len(set(blocks))} spatial blocks")
print(f"{'model (all 1200-vintage features)':44s} {'random 5-fold':>14s} {'spatial 5-fold':>15s}")
for name, mod in [
    ("linear, size only", LinearRegression()),
    ("linear (ridge), ALL features", Ridge(alpha=1.0)),
    ("random forest, ALL features", RandomForestRegressor(400, min_samples_leaf=5, random_state=0)),
    ("gradient boosting, ALL features", GradientBoostingRegressor(random_state=0)),
]:
    Xm = s[["l1200"]].to_numpy() if name == "linear, size only" else X
    sc_r = cross_val_score(mod, Xm, yv, cv=cv_rand, scoring="r2")
    sc_s = cross_val_score(mod, Xm, yv, cv=cv_spat, groups=blocks, scoring="r2")
    print(f"  {name:42s} {sc_r.mean():>10.3f} {sc_s.mean():>15.3f}")

# feature importance from GBM fit on all data
g = GradientBoostingRegressor(random_state=0).fit(X, yv)
imp = sorted(zip(FEATS, g.feature_importances_), key=lambda t: -t[1])
print("\nGBM feature importance:")
for f, v in imp[:8]:
    print(f"  {f:16s} {v:.3f}")

# horizon ladder
print("\nHorizon ladder — R2 predicting l1500 from size alone at each date:")
for y in [1400, 1300, 1200, 800]:
    ss = d.dropna(subset=[f"l{y}", "l1500"])
    r = np.corrcoef(ss[f"l{y}"], ss["l1500"])[0, 1] ** 2
    print(f"  from {y}: R2 = {r:.2f}  (n={len(ss)})")
