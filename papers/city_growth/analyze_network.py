"""Does position in the real medieval transport network explain city growth,
beyond initial size and first-nature geography?

Nested models on the Viabundus footprint (N~200 towns matched to Buringh):
  Cross-section:  log(pop_Y) ~ [size controls] + first-nature + network
  Growth:         dlog(pop 1200->1500) ~ log pop1200 + first-nature + network

Network features (computed on the least-cost matrix):
  logMA_Y   : log market access using pop at year Y, decay theta km-equiv
  log_betw  : log(1 + topological trade-betweenness)
  closeness : network closeness centrality
"""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
from pathlib import Path
from panel import load_buringh, wide_pop

OUT = Path(__file__).resolve().parent / "out"
TH = 1000.0


def market_access(C, pops, theta):
    """pops: array aligned to matrix rows. Returns MA_i = sum_{j!=i} pop_j*exp(-C_ij/theta)."""
    W = np.exp(-C / theta)
    np.fill_diagonal(W, 0.0)
    W[~np.isfinite(C)] = 0.0
    return W @ pops


def build_frame(theta=150.0):
    C = np.load(OUT / "cost_matrix.npy")
    meta = pd.read_csv(OUT / "network_meta.csv")
    w = wide_pop(load_buringh())
    m = meta.merge(w, on="cid", how="left", suffixes=("", "_w"))
    m = m.sort_values("node_idx").reset_index(drop=True)
    assert (m["node_idx"].to_numpy() == np.arange(len(m))).all()
    for y in [1200, 1300, 1400, 1500]:
        pops = m[f"pop{y}"].fillna(0.0).to_numpy()
        m[f"logMA{y}"] = np.log1p(market_access(C, pops, theta))
    m["log_betw"] = np.log1p(m["betw_topo"])
    m["closeness_z"] = (m["closeness"] - m["closeness"].mean()) / m["closeness"].std()
    return m


def fit(df, y, xs, label):
    d = df.dropna(subset=[y] + xs)
    X = sm.add_constant(d[xs])
    r = sm.OLS(d[y], X).fit(cov_type="HC1")
    print(f"\n[{label}]  n={int(r.nobs)}  R2={r.rsquared:.3f}  adjR2={r.rsquared_adj:.3f}")
    for name in xs:
        b = r.params[name]; p = r.pvalues[name]
        star = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
        print(f"    {name:14s} beta={b:+.3f}  p={p:.3f} {star}")
    return r


def main():
    df = build_frame(theta=150.0)
    df["lpop1200"] = np.log(df["pop1200"].where(df["pop1200"] >= TH))
    df["lpop1500"] = np.log(df["pop1500"].where(df["pop1500"] >= TH))
    df["g"] = df["lpop1500"] - df["lpop1200"]

    print("=" * 74)
    print("A. CROSS-SECTION: what predicts a city's SIZE in 1500?")
    print("=" * 74)
    fit(df, "lpop1500", ["on_river", "on_coast"], "size ~ first-nature only")
    fit(df, "lpop1500", ["on_river", "on_coast", "logMA1500"], "+ market access")
    fit(df, "lpop1500", ["on_river", "on_coast", "logMA1500", "log_betw", "closeness_z"],
        "+ betweenness + closeness")

    print("\n" + "=" * 74)
    print("B. GROWTH 1200->1500: what predicts who GREW? (network measured at 1200)")
    print("=" * 74)
    fit(df, "g", ["lpop1200"], "Gibrat baseline (size only)")
    fit(df, "g", ["lpop1200", "on_river", "on_coast"], "+ first-nature")
    fit(df, "g", ["lpop1200", "on_river", "on_coast", "logMA1200"], "+ market access @1200")
    fit(df, "g", ["lpop1200", "on_river", "on_coast", "logMA1200", "log_betw", "closeness_z"],
        "+ betweenness + closeness")

    # Does network access explain the SPATIAL CLUSTERING of growth?
    print("\n" + "=" * 74)
    print("C. Does network access absorb the spatial clustering of growth?")
    print("=" * 74)
    d = df.dropna(subset=["g", "logMA1200"]).copy()
    resid = sm.OLS(d["g"], sm.add_constant(d[["lpop1200", "on_river", "on_coast", "logMA1200"]])).fit().resid
    from sklearn.neighbors import BallTree
    xy = np.deg2rad(d[["lat", "lon"]].to_numpy())
    tree = BallTree(xy, metric="haversine"); _, idx = tree.query(xy, k=7)
    def moran(z):
        z = z - z.mean(); n = len(z); num = 0.0; W = 0.0
        for i in range(n):
            for j in idx[i, 1:]:
                num += z[i] * z[j]; W += 1
        return (n / W) * (num / (z @ z))
    print(f"  Moran's I of RAW growth:                 {moran(d['g'].to_numpy()):+.3f}")
    print(f"  Moran's I of growth residual (net of MA): {moran(resid.to_numpy()):+.3f}")
    df.to_csv(OUT / "network_frame.csv", index=False)


if __name__ == "__main__":
    main()
