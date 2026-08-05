"""What actually determined the 1500 urban hierarchy?

1. R2 ladder + Shapley variance decomposition of log(pop1500):
      geography (first-nature)  vs  deep history (early size)  vs  idiosyncratic.
2. Depth of persistence: how far back does size lock in (pop800..1300 -> pop1500)?
3. Water-access growth premium with bootstrap CI (the one exogenous, causal driver).
4. Black-Death reshuffle: were the permanent post-plague WINNERS the high-water cities?
"""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
from itertools import combinations
from panel import load_buringh, wide_pop

TH = 1000.0


def r2(df, y, xs):
    d = df.dropna(subset=[y] + xs)
    if len(d) < 20:
        return np.nan, 0
    r = sm.OLS(d[y], sm.add_constant(d[xs])).fit()
    return r.rsquared, len(d)


def shapley(df, y, groups):
    """Shapley decomposition of R2 across variable GROUPS (dict name->[cols])."""
    names = list(groups)
    d = df.dropna(subset=[y] + [c for g in groups.values() for c in g]).copy()
    def R2(sel):
        cols = [c for g in sel for c in groups[g]]
        if not cols:
            return 0.0
        return sm.OLS(d[y], sm.add_constant(d[cols])).fit().rsquared
    import math
    k = len(names); phi = {n: 0.0 for n in names}
    for n in names:
        others = [x for x in names if x != n]
        for r in range(len(others) + 1):
            for S in combinations(others, r):
                w = math.factorial(len(S)) * math.factorial(k - len(S) - 1) / math.factorial(k)
                phi[n] += w * (R2(list(S) + [n]) - R2(list(S)))
    return phi, R2(names), len(d)


def main(region="in_cne"):
    w = wide_pop(load_buringh(), years=(800, 900, 1000, 1100, 1200, 1300, 1400, 1500))
    d = w[w[region]].copy()
    for y in [800, 1000, 1200, 1300, 1400, 1500]:
        d[f"l{y}"] = np.log(d[f"pop{y}"].where(d[f"pop{y}"] >= TH))
    d["elev_z"] = (d["elev"] - d["elev"].mean()) / d["elev"].std()
    geo = ["on_river", "on_coast", "atlantic", "baltic", "northsea", "medit", "elev_z"]

    print("=" * 74)
    print("1. R2 LADDER — predicting log(pop1500)")
    print("=" * 74)
    for label, xs in [
        ("geography (first-nature) only", geo),
        ("deep history: l800 only", ["l800"]),
        ("medieval start: l1200 only", ["l1200"]),
        ("geography + l1200", geo + ["l1200"]),
        ("geography + l800 + l1200", geo + ["l800", "l1200"]),
    ]:
        rr, n = r2(d, "l1500", xs)
        print(f"  {label:34s} R2={rr:5.3f}  n={n}")

    print("\n" + "=" * 74)
    print("2. SHAPLEY variance decomposition of log(pop1500)")
    print("=" * 74)
    groups = {"geography": geo, "deep_history(l800)": ["l800"],
              "medieval_momentum(l1200)": ["l1200"]}
    phi, tot, n = shapley(d, "l1500", groups)
    print(f"  total R2 = {tot:.3f}  (n={n}); idiosyncratic/unexplained = {1-tot:.3f}")
    for k, v in phi.items():
        print(f"    {k:26s} share of explained = {v/tot:5.1%}   (R2 units {v:.3f})")
    print(f"    {'IDIOSYNCRATIC (luck+error)':26s} share of TOTAL variance = {1-tot:5.1%}")

    print("\n" + "=" * 74)
    print("3. DEPTH OF PERSISTENCE — corr(log pop_Y, log pop1500)")
    print("=" * 74)
    for y in [800, 1000, 1200, 1300, 1400]:
        s = d.dropna(subset=[f"l{y}", "l1500"])
        rho = s[f"l{y}"].corr(s["l1500"])
        print(f"  log(pop{y}) -> log(pop1500): r={rho:.3f}  r2={rho**2:.3f}  n={len(s)}")

    print("\n" + "=" * 74)
    print("4. WATER-ACCESS GROWTH PREMIUM 1200->1500 (exogenous geography) + bootstrap CI")
    print("=" * 74)
    s = d.dropna(subset=["l1200", "l1500"]).copy()
    s["g"] = s["l1500"] - s["l1200"]
    s["water"] = ((s["on_river"] == 1) | (s["on_coast"] == 1)).astype(float)
    X = sm.add_constant(s[["l1200", "water"]])
    r = sm.OLS(s["g"], X).fit(cov_type="HC1")
    b = r.params["water"]
    rng = np.random.default_rng(42)
    bs = []
    idx = np.arange(len(s))
    for _ in range(2000):
        j = rng.choice(idx, len(idx), replace=True)
        sj = s.iloc[j]
        bb = sm.OLS(sj["g"], sm.add_constant(sj[["l1200", "water"]])).fit().params["water"]
        bs.append(bb)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"  water premium on 1200->1500 growth: {b:+.3f} log  ({np.exp(b)-1:+.0%} population)")
    print(f"  bootstrap 95% CI: [{lo:+.3f}, {hi:+.3f}]  ({np.exp(lo)-1:+.0%} .. {np.exp(hi)-1:+.0%})  n={len(s)}")

    print("\n" + "=" * 74)
    print("5. BLACK-DEATH RESHUFFLE: were permanent WINNERS the high-water cities?")
    print("=" * 74)
    p = d.dropna(subset=["l1300", "l1500"]).copy()
    p["g_shock_recov"] = p["l1500"] - p["l1300"]     # net change across plague+recovery
    p["water"] = ((p["on_river"] == 1) | (p["on_coast"] == 1)).astype(float)
    # winners = above-median net change; losers = below
    med = p["g_shock_recov"].median()
    p["winner"] = (p["g_shock_recov"] > med).astype(int)
    win_water = p[p.winner == 1]["water"].mean()
    los_water = p[p.winner == 0]["water"].mean()
    print(f"  share on water among post-plague WINNERS: {win_water:.2f}")
    print(f"  share on water among post-plague LOSERS:  {los_water:.2f}")
    rr = sm.OLS(p["g_shock_recov"], sm.add_constant(p[["l1300", "water"]])).fit(cov_type="HC1")
    print(f"  net 1300->1500 change ~ water: {rr.params['water']:+.3f} (p={rr.pvalues['water']:.3f}) "
          f"controlling for pre-plague size")
    d.to_csv("out/synthesis_frame.csv", index=False)


if __name__ == "__main__":
    main("in_cne")
