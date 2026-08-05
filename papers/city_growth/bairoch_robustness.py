"""Re-run every core finding on the Bairoch (1988) population panel and compare
to Buringh (2021), holding geography and privileges fixed. If the conclusions
survive the swap, they hold across the two standard independent reconstructions.
"""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
from itertools import combinations
import math
from pathlib import Path
from sklearn.neighbors import BallTree
from panel import load_buringh, wide_pop
from bairoch_panel import load_bairoch_wide
from privileges import privilege_years, _nearest_grant
from charter_did import load_treatment_years

TH = 1000.0
EARTH_KM = 6371.0088
OUT = Path(__file__).resolve().parent / "out"


def attach_privileges(w):
    """Add staple_year, fair_year, charter_year, market_year to a wide panel
    (needs lat/lon) by nearest-neighbour, identical rule to the main pipeline."""
    w = w.copy()
    st, fa = privilege_years()
    w["staple_year"] = _nearest_grant(w, st)
    w["fair_year"] = _nearest_grant(w, fa)
    loc = load_treatment_years()  # city_id, name, lat, lon, charter_year, market_year
    for col in ["charter_year", "market_year"]:
        g = loc.dropna(subset=[col])
        tree = BallTree(np.deg2rad(w[["lat", "lon"]].to_numpy()), metric="haversine")
        d, idx = tree.query(np.deg2rad(g[["lat", "lon"]].to_numpy()), k=1)
        dist = d.flatten() * EARTH_KM
        out = pd.Series(np.nan, index=w.index)
        gg = g.reset_index(drop=True).copy(); gg["cidx"] = idx.flatten(); gg["dist"] = dist
        gg = gg[gg["dist"] <= 6.0]
        for cidx, sub in gg.groupby("cidx"):
            out.iloc[cidx] = sub[col].min()
        w[col] = out.to_numpy()
    return w


def gibrat(w, y0, y1):
    s = w[(w[f"pop{y0}"] >= TH) & (w[f"pop{y1}"] >= TH)].copy()
    s["g"] = np.log(s[f"pop{y1}"]) - np.log(s[f"pop{y0}"])
    r = sm.OLS(s["g"], sm.add_constant(np.log(s[f"pop{y0}"]))).fit()
    return r.params.iloc[1], r.rsquared, len(s)


def persistence(w, y0, y1):
    s = w[(w[f"pop{y0}"] >= TH) & (w[f"pop{y1}"] >= TH)]
    return np.corrcoef(np.log(s[f"pop{y0}"]), np.log(s[f"pop{y1}"]))[0, 1] ** 2, len(s)


def water_premium(w, y0, y1):
    s = w[(w[f"pop{y0}"] >= TH) & (w[f"pop{y1}"] >= TH)].copy()
    s["g"] = np.log(s[f"pop{y1}"]) - np.log(s[f"pop{y0}"])
    s["water"] = ((s["on_river"] == 1) | (s["on_coast"] == 1)).astype(float)
    X = sm.add_constant(s[["water"]]); X["l0"] = np.log(s[f"pop{y0}"])
    r = sm.OLS(s["g"], X).fit(cov_type="HC1")
    return r.params["water"], r.pvalues["water"], len(s)


def variance_decomp(w, anchor=1300):
    """Shapley split of log(pop1500) among geography / deep-anchor / momentum."""
    d = w.copy()
    d["water"] = ((d["on_river"] == 1) | (d["on_coast"] == 1)).astype(float)
    d["lA"] = np.log(d[f"pop{anchor}"].where(d[f"pop{anchor}"] >= TH))
    d["l1500"] = np.log(d["pop1500"].where(d["pop1500"] >= TH))
    groups = {"geography": ["water", "on_coast", "on_river"], "anchor": ["lA"]}
    dd = d.dropna(subset=["l1500"] + [c for g in groups.values() for c in g])
    def R2(sel):
        cols = [c for g in sel for c in groups[g]]
        if not cols:
            return 0.0
        return sm.OLS(dd["l1500"], sm.add_constant(dd[cols])).fit().rsquared
    names = list(groups); k = len(names); phi = {n: 0 for n in names}
    for n in names:
        others = [x for x in names if x != n]
        for r in range(len(others)+1):
            for S in combinations(others, r):
                wgt = math.factorial(len(S))*math.factorial(k-len(S)-1)/math.factorial(k)
                phi[n] += wgt*(R2(list(S)+[n]) - R2(list(S)))
    tot = R2(names)
    return phi, tot, len(dd)


def did(w, ycol):
    d = w.copy(); d["gc"] = np.floor(d[ycol] / 100.0) * 100
    rows = []
    for c in [1200, 1300, 1400]:
        c0, c1, c2 = f"pop{int(c-100)}", f"pop{int(c)}", f"pop{int(c+100)}"
        if c0 not in d or c2 not in d:
            continue
        base = d[(d[c0] >= TH) & (d[c1] >= TH) & (d[c2] >= TH)].copy()
        if len(base) < 6:
            continue
        base["pre"] = np.log(base[c1]) - np.log(base[c0])
        base["post"] = np.log(base[c2]) - np.log(base[c1])
        tr = base[base["gc"] == c]; ct = base[base[ycol].isna() | (base[ycol] > c)]
        if len(tr) < 3 or len(ct) < 3:
            continue
        rows.append((len(tr), (tr["post"].mean()-tr["pre"].mean())-(ct["post"].mean()-ct["pre"].mean())))
    if not rows:
        return np.nan, 0
    return sum(n*v for n, v in rows)/sum(n for n, _ in rows), sum(n for n, _ in rows)


def naive_gap(w, ycol):
    """Cross-sectional size gap: log pop1500 for cities that ever had the privilege vs not."""
    d = w[w["pop1500"] >= TH].copy()
    d["ever"] = d[ycol].notna().astype(float)
    r = sm.OLS(np.log(d["pop1500"]), sm.add_constant(d[["ever"]])).fit()
    return np.exp(r.params["ever"]) - 1


def run(name, w):
    w = attach_privileges(w[w["in_cne"]].copy())
    R = {}
    gs, gr, gn = gibrat(w, 1300, 1500)
    R["gibrat_slope"], R["gibrat_r2"], R["gibrat_n"] = gs, gr, gn
    pr, pn = persistence(w, 1300, 1500)
    R["persist_1300"], R["persist_1300_n"] = pr, pn
    pr8, pn8 = persistence(w, 800, 1500)
    R["persist_800"], R["persist_800_n"] = pr8, pn8
    wp, wpv, wn = water_premium(w, 1300, 1500)
    R["water"], R["water_p"], R["water_n"] = wp, wpv, wn
    phi, tot, vn = variance_decomp(w, anchor=1300)
    R["decomp_geo"] = phi["geography"] / tot
    R["decomp_momentum"] = phi["anchor"] / tot
    R["decomp_total_r2"], R["decomp_n"] = tot, vn
    for kind, ycol in [("staple", "staple_year"), ("fair", "fair_year"),
                       ("charter", "charter_year"), ("market", "market_year")]:
        ng = naive_gap(w, ycol); dd, dn = did(w, ycol)
        R[f"{kind}_naive"], R[f"{kind}_did"], R[f"{kind}_ntreat"] = ng, dd, dn
    print(f"\n{'='*70}\n{name}\n{'='*70}")
    print(f"  Gibrat 1300->1500 slope={gs:+.3f} R2={gr:.3f} (n={gn})")
    print(f"  Persistence r2 1300->1500={pr:.3f} (n={pn}); 800->1500={pr8:.3f} (n={pn8})")
    print(f"  Water premium 1300->1500={wp:+.3f} log ({np.exp(wp)-1:+.0%}) p={wpv:.3f} (n={wn})")
    print(f"  Variance: momentum {R['decomp_momentum']:.0%} / geography {R['decomp_geo']:.0%} "
          f"(total R2={tot:.2f})")
    for kind in ["staple", "fair", "charter", "market"]:
        print(f"  {kind:8s}: naive {R[kind+'_naive']:+.0%} -> DiD {R[kind+'_did']:+.0%} "
              f"(n_treat={R[kind+'_ntreat']})")
    return R


def agreement(bur_w, bai_w):
    m = bur_w[["cid", "pop1500"]].merge(
        bai_w[["cid", "pop1500"]], on="cid", suffixes=("_bur", "_bai")).dropna()
    m = m[(m.pop1500_bur >= TH) & (m.pop1500_bai >= TH)]
    r = np.corrcoef(np.log(m.pop1500_bur), np.log(m.pop1500_bai))[0, 1]
    m.to_csv(OUT / "source_agreement.csv", index=False)
    return r, len(m)


if __name__ == "__main__":
    import json
    bur = wide_pop(load_buringh(), years=(800, 1200, 1300, 1400, 1500))
    bai = load_bairoch_wide(years=(800, 1200, 1300, 1400, 1500))
    res = {"buringh": run("BURINGH (2021)", bur), "bairoch": run("BAIROCH (1988)", bai)}
    r, n = agreement(bur, bai)
    res["agreement_r"] = r; res["agreement_n"] = n
    print(f"\nAGREEMENT (log pop1500, common cities): r={r:.3f}, n={n}")
    json.dump(res, open(OUT / "robustness_summary.json", "w"), indent=2)
    print("saved out/robustness_summary.json, out/source_agreement.csv")
