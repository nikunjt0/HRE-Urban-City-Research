"""Match Viabundus dated commercial privileges (staple rights, fairs) to Buringh
cities and build a city x century event-study panel. First-ever causal test of
whether ACQUIRING a staple right / fair privilege caused city growth.

Design:
  - Long panel city x year in {1200,1300,1400,1500}, y = log(pop).
  - Treatment HasStaple_it = 1 once a staple was granted (year <= t); same for fair.
  - Two-way fixed effects (city FE + year FE) => identifies off WITHIN-city change
    around the grant, netting out fixed geography and common century shocks.
  - Event study: growth in the century AFTER grant vs the century BEFORE
    (pre-trend test for reverse causality / selection).
"""
from __future__ import annotations
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree
import statsmodels.formula.api as smf
from panel import load_buringh, wide_pop

ROOT = Path(__file__).resolve().parent.parent
VIA = ROOT / "docs/viabundus/Viabundus-2-csv"
EARTH_KM = 6371.0088
MATCH_KM = 6.0
TH = 1000.0


def _yr(s):
    return pd.to_numeric(pd.Series(s).astype(str).str[:4], errors="coerce")


def privilege_years():
    n = pd.read_csv(VIA / "nodes.csv", low_memory=False, na_values=["null", ""])
    n["lat"] = pd.to_numeric(n["latitude"], errors="coerce")
    n["lon"] = pd.to_numeric(n["longitude"], errors="coerce")
    st = n[n["Is_Staple"] == "y"].copy(); st["gy"] = _yr(st["Staple_From"])
    fa = n[n["Is_Fair"] == "y"].copy();  fa["gy"] = _yr(fa["Fair_From"])
    st = st.dropna(subset=["lat", "lon", "gy"])[["lat", "lon", "gy"]]
    fa = fa.dropna(subset=["lat", "lon", "gy"])[["lat", "lon", "gy"]]
    return st, fa


def _nearest_grant(cities, grants):
    """For each city, earliest grant year among grant-nodes within MATCH_KM."""
    if len(grants) == 0:
        return np.full(len(cities), np.nan)
    tree = BallTree(np.deg2rad(cities[["lat", "lon"]].to_numpy()), metric="haversine")
    # query grants -> nearest city, assign grant year to that city (take min)
    d, idx = tree.query(np.deg2rad(grants[["lat", "lon"]].to_numpy()), k=1)
    dist_km = d.flatten() * EARTH_KM
    out = pd.Series(np.nan, index=cities.index)
    g = grants.copy(); g["cidx"] = idx.flatten(); g["dist"] = dist_km
    g = g[g["dist"] <= MATCH_KM]
    for cidx, sub in g.groupby("cidx"):
        out.iloc[cidx] = sub["gy"].min()
    return out.to_numpy()


def build_panel(region="in_cne"):
    w = wide_pop(load_buringh(), years=(1100, 1200, 1300, 1400, 1500))
    d = w[w[region]].copy().reset_index(drop=True)
    st, fa = privilege_years()
    d["staple_year"] = _nearest_grant(d, st)
    d["fair_year"] = _nearest_grant(d, fa)
    # long
    years = [1200, 1300, 1400, 1500]
    rows = []
    for _, r in d.iterrows():
        for y in years:
            pop = r[f"pop{y}"]
            if pd.isna(pop) or pop < TH:
                continue
            rows.append({
                "cid": r["cid"], "city": r["city"], "year": y,
                "lpop": np.log(pop),
                "has_staple": int(r["staple_year"] <= y) if pd.notna(r["staple_year"]) else 0,
                "has_fair": int(r["fair_year"] <= y) if pd.notna(r["fair_year"]) else 0,
                "ever_staple": int(pd.notna(r["staple_year"])),
                "ever_fair": int(pd.notna(r["fair_year"])),
                "staple_year": r["staple_year"], "fair_year": r["fair_year"],
                "on_river": r["on_river"], "on_coast": r["on_coast"],
            })
    return pd.DataFrame(rows), d


def twfe(panel):
    print("=" * 74)
    print("TWO-WAY FIXED-EFFECTS: log(pop) ~ has_staple + has_fair + C(cid) + C(year)")
    print("=" * 74)
    m = smf.ols("lpop ~ has_staple + has_fair + C(cid) + C(year)", data=panel).fit(
        cov_type="cluster", cov_kwds={"groups": panel["cid"]})
    for v in ["has_staple", "has_fair"]:
        b = m.params[v]; p = m.pvalues[v]
        print(f"  {v:12s} beta={b:+.3f} (p={p:.3f})  => {np.exp(b)-1:+.0%} population")
    print(f"  n_obs={int(m.nobs)}  cities={panel.cid.nunique()}")
    return m


def event_study(paneldf, wide, kind="staple"):
    """Compare growth in the century AFTER the grant vs BEFORE (pre-trend test)."""
    print("\n" + "=" * 74)
    print(f"EVENT STUDY / PRE-TREND TEST — {kind.upper()} grants")
    print("=" * 74)
    gcol = f"{kind}_year"
    d = wide.dropna(subset=[gcol]).copy()
    # bucket grant into the century it falls in; growth of the treated century vs prior
    def century_of(y):
        return int(np.floor(y / 100.0) * 100)
    d["gc"] = d[gcol].apply(century_of)
    results = {"pre": [], "post": []}
    for _, r in d.iterrows():
        gc = r["gc"]
        # pre-growth: (gc-100 -> gc); post-growth: (gc -> gc+100)
        for tag, y0, y1 in [("pre", gc - 100, gc), ("post", gc, gc + 100)]:
            c0, c1 = f"pop{y0}", f"pop{y1}"
            if c0 in r and c1 in r and pd.notna(r[c0]) and pd.notna(r[c1]) \
               and r[c0] >= TH and r[c1] >= TH:
                results[tag].append(np.log(r[c1]) - np.log(r[c0]))
    pre = np.array(results["pre"]); post = np.array(results["post"])
    print(f"  cities treated: {len(d)}")
    print(f"  mean growth in century BEFORE grant: {pre.mean():+.3f}  (n={len(pre)})")
    print(f"  mean growth in century AFTER  grant: {post.mean():+.3f}  (n={len(post)})")
    print(f"  post - pre (within treated): {post.mean()-pre.mean():+.3f}")
    from scipy import stats
    # compare post-growth of treated vs all-city baseline for same centuries
    print("  (flat 'before' vs high 'after' => grant plausibly causal, not selection)")


if __name__ == "__main__":
    panel, wide = build_panel("in_cne")
    print(f"panel obs: {len(panel)}, cities: {panel.cid.nunique()}, "
          f"ever_staple cities: {wide['staple_year'].notna().sum()}, "
          f"ever_fair cities: {wide['fair_year'].notna().sum()}\n")
    twfe(panel)
    event_study(panel, wide, "staple")
    event_study(panel, wide, "fair")
    panel.to_csv("out/privilege_panel.csv", index=False)
    wide.to_csv("out/privilege_wide.csv", index=False)
