"""Null-model diagnostics for medieval city growth.

Establishes the baseline that any 'revolutionary' factor model must beat:
  1. PERSISTENCE     -- how much of size at 1500 is locked in by size at 1200/800?
  2. GIBRAT'S LAW    -- is growth independent of current size? (random-growth null)
  3. ZIPF'S LAW      -- rank-size exponent and its evolution 1200->1500
  4. SPATIAL         -- Moran's I on growth (do neighbours grow together?)

Sample: HRE-core cities that are 'urban' (pop >= threshold) in the relevant year.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import statsmodels.api as sm
from panel import load_buringh, wide_pop

TH = 1000.0   # urban threshold (inhabitants)


def _ols(y, X, cov="HC1"):
    Xc = sm.add_constant(X)
    return sm.OLS(y, Xc, missing="drop").fit(cov_type=cov)


def persistence(w, region="in_hre"):
    print("\n" + "=" * 70)
    print("1. PERSISTENCE  (how much of later size is locked in by earlier size)")
    print("=" * 70)
    d = w[w[region]].copy()
    pairs = [(800, 1500), (1000, 1500), (1200, 1500), (1300, 1500),
             (1200, 1400), (1200, 1300)]
    for y0, y1 in pairs:
        c0, c1 = f"pop{y0}", f"pop{y1}"
        if c0 not in d or c1 not in d:
            continue
        s = d[(d[c0] >= TH) & (d[c1] >= TH)]
        if len(s) < 15:
            print(f"  log(pop{y1}) ~ log(pop{y0}): n={len(s)} too few")
            continue
        r = _ols(np.log(s[c1]), np.log(s[c0]))
        print(f"  log(pop{y1}) ~ log(pop{y0}):  R2={r.rsquared:5.3f}  "
              f"beta={r.params.iloc[1]:.3f}  n={len(s)}")


def gibrat(w, region="in_hre"):
    print("\n" + "=" * 70)
    print("2. GIBRAT'S LAW  (growth vs initial size; beta=0 => size-independent)")
    print("=" * 70)
    d = w[w[region]].copy()
    steps = [(1200, 1300), (1300, 1400), (1400, 1500), (1200, 1500)]
    for y0, y1 in steps:
        c0, c1 = f"pop{y0}", f"pop{y1}"
        s = d[(d[c0] >= TH) & (d[c1] >= TH)].copy()
        if len(s) < 15:
            continue
        s["g"] = np.log(s[c1]) - np.log(s[c0])
        r = _ols(s["g"], np.log(s[c0]))
        b = r.params.iloc[1]; p = r.pvalues.iloc[1]
        verdict = "GIBRAT holds" if p > 0.05 else ("convergence (small grow faster)" if b < 0 else "divergence")
        print(f"  {y0}->{y1}:  slope={b:+.3f} (p={p:.3f})  R2={r.rsquared:5.3f}  "
              f"mean g={s['g'].mean():+.3f}  sd g={s['g'].std():.3f}  n={len(s)}  [{verdict}]")
    # variance-ratio style: is sd(growth) ~ constant across size bins?
    s = d[(d["pop1200"] >= TH) & (d["pop1500"] >= TH)].copy()
    s["g"] = np.log(s["pop1500"]) - np.log(s["pop1200"])
    s["szbin"] = pd.qcut(np.log(s["pop1200"]).rank(method="first"), 3, labels=["small", "mid", "large"])
    print("  growth sd by initial-size tercile (Gibrat => roughly equal):")
    print("   ", s.groupby("szbin", observed=True)["g"].agg(["mean", "std", "count"]).round(3).to_dict("index"))


def zipf(w, region="in_hre"):
    print("\n" + "=" * 70)
    print("3. ZIPF'S LAW  (ln(rank-0.5) = a - zeta*ln(size); zeta~1 => Zipf)")
    print("=" * 70)
    d = w[w[region]].copy()
    for y in [1200, 1300, 1400, 1500]:
        c = f"pop{y}"
        s = d[d[c] >= TH].copy().sort_values(c, ascending=False).reset_index(drop=True)
        if len(s) < 20:
            continue
        s["rank"] = np.arange(1, len(s) + 1)
        # Gabaix-Ibragimov: regress ln(rank-0.5) on ln(size)
        y_ = np.log(s["rank"] - 0.5); x_ = np.log(s[c])
        r = _ols(y_, x_)
        zeta = -r.params.iloc[1]
        se = r.bse.iloc[1]
        print(f"  {y}:  zeta={zeta:.3f} (se~{se:.3f})  R2={r.rsquared:5.3f}  "
              f"n={len(s)}  top={s[c].max():.0f}  median={s[c].median():.0f}")


def morans_i(w, region="in_hre", k=6):
    print("\n" + "=" * 70)
    print("4. SPATIAL AUTOCORRELATION of 1200->1500 growth (Moran's I, kNN)")
    print("=" * 70)
    from sklearn.neighbors import BallTree
    d = w[w[region] & (w["pop1200"] >= TH) & (w["pop1500"] >= TH)].copy()
    d["g"] = np.log(d["pop1500"]) - np.log(d["pop1200"])
    xy = np.deg2rad(d[["lat", "lon"]].to_numpy())
    tree = BallTree(xy, metric="haversine")
    _, idx = tree.query(xy, k=k + 1)
    z = (d["g"] - d["g"].mean()).to_numpy()
    n = len(d)
    num = 0.0; W = 0.0
    for i in range(n):
        for j in idx[i, 1:]:
            num += z[i] * z[j]; W += 1
    I = (n / W) * (num / (z @ z))
    EI = -1.0 / (n - 1)
    print(f"  Moran's I = {I:+.3f}  (expected under no structure = {EI:+.3f}), n={n}, k={k}")
    print(f"  => {'positive spatial clustering of growth' if I > EI + 0.05 else 'weak/no spatial clustering'}")


if __name__ == "__main__":
    w = wide_pop(load_buringh())
    n_hre = w[w.in_hre].shape[0]
    print(f"HRE-core cities in panel: {n_hre}")
    persistence(w)
    gibrat(w)
    zipf(w)
    morans_i(w)
