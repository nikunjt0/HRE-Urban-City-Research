"""Sharpened causal test using the Cantoni-Mohr-Weigand (2020) 'Princes and
Townspeople' charter & market data (2,390 Deutsches-Staedtebuch cities, dated).

Treatments (canonical HRE institutions, finer-dated than Viabundus staples):
  - TOWN CHARTER (Stadtrecht): first year type_origin==1  (formal bestowal)
  - MARKET RIGHT (Marktrecht):  first year type_market in {1,2,6,7,8,9,10} (a grant)

City_id (city_locations.csv) is matched to Buringh population by nearest
coordinate. We then repeat the three-way comparison:
  (1) naive two-way FE association,  (2) matched difference-in-differences,
  (3) pre-trend / event-study check — on a much larger sample and the
      institutions historians actually emphasise.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree
import statsmodels.formula.api as smf
from panel import load_buringh, wide_pop

ROOT = Path(__file__).resolve().parents[2]
LOC = ROOT / "docs/city_locations_and_border_maps/dataverse_files/city_locations.csv"
TC = ROOT / "docs/town_charters_and_first_mentions/towncharter_data/towncharter.csv"
MK = ROOT / "docs/markets/markets_data/markets.csv"
EARTH_KM = 6371.0088
TH = 1000.0
GRANT_MARKETS = {1, 2, 6, 7, 8, 9, 10}   # granting (not withdrawal) market types


def load_treatment_years():
    loc = pd.read_csv(LOC)[["city_id", "name", "latitude", "longitude"]].dropna()
    loc = loc.rename(columns={"latitude": "lat", "longitude": "lon"})
    tc = pd.read_csv(TC)
    charter = (tc[tc["type_origin"] == 1].groupby("city_id")["time_point"].min()
               .rename("charter_year"))
    mk = pd.read_csv(MK)
    market = (mk[mk["type_market"].isin(GRANT_MARKETS)].groupby("city_id")["time_point"].min()
              .rename("market_year"))
    loc = loc.merge(charter, on="city_id", how="left").merge(market, on="city_id", how="left")
    return loc


def attach_population(loc):
    w = wide_pop(load_buringh(), years=(1100, 1200, 1300, 1400, 1500))
    tree = BallTree(np.deg2rad(w[["lat", "lon"]].to_numpy()), metric="haversine")
    d, idx = tree.query(np.deg2rad(loc[["lat", "lon"]].to_numpy()), k=1)
    loc = loc.copy()
    loc["match_km"] = d.flatten() * EARTH_KM
    for c in ["pop1100", "pop1200", "pop1300", "pop1400", "pop1500",
              "on_river", "on_coast", "cid"]:
        loc[c] = w[c].to_numpy()[idx.flatten()]
    loc.loc[loc["match_km"] > 6.0, ["pop1100", "pop1200", "pop1300", "pop1400", "pop1500"]] = np.nan
    loc = loc.dropna(subset=["cid"]).drop_duplicates("cid")
    return loc


def to_long(loc, treat="charter"):
    ycol = f"{treat}_year"
    rows = []
    for _, r in loc.iterrows():
        for y in [1200, 1300, 1400, 1500]:
            p = r[f"pop{y}"]
            if pd.isna(p) or p < TH:
                continue
            rows.append({"cid": r["cid"], "name": r["name"], "year": y,
                         "lpop": np.log(p),
                         "treated": int(r[ycol] <= y) if pd.notna(r[ycol]) else 0,
                         "on_river": r["on_river"], "on_coast": r["on_coast"]})
    return pd.DataFrame(rows)


def naive_twfe(long, treat):
    m = smf.ols("lpop ~ treated + C(cid) + C(year)", data=long).fit(
        cov_type="cluster", cov_kwds={"groups": long["cid"]})
    b = m.params["treated"]; p = m.pvalues["treated"]
    print(f"  [naive TWFE]  {treat}: beta={b:+.3f} ({np.exp(b)-1:+.0%}), p={p:.3f}, "
          f"n={int(m.nobs)}, cities={long.cid.nunique()}")
    return np.exp(b) - 1


def matched_did(loc, treat="charter"):
    ycol = f"{treat}_year"
    d = loc.copy()
    d["gc"] = np.floor(d[ycol] / 100.0) * 100
    print(f"  [matched DiD] effect of acquiring a {treat.upper()} on next-century growth:")
    rows = []
    for c in [1200, 1300, 1400]:
        c0, c1, c2 = f"pop{int(c-100)}", f"pop{int(c)}", f"pop{int(c+100)}"
        base = d[(d[c0] >= TH) & (d[c1] >= TH) & (d[c2] >= TH)].copy()
        base["pre"] = np.log(base[c1]) - np.log(base[c0])
        base["post"] = np.log(base[c2]) - np.log(base[c1])
        treated = base[base["gc"] == c]
        ctrl = base[(d[ycol].isna()) | (d[ycol] > c)]
        if len(treated) < 5 or len(ctrl) < 5:
            continue
        did = (treated["post"].mean() - treated["pre"].mean()) - \
              (ctrl["post"].mean() - ctrl["pre"].mean())
        rows.append({"c": int(c), "nt": len(treated), "did": did,
                     "t_pre": treated["pre"].mean(), "t_post": treated["post"].mean()})
        print(f"      grant century {int(c)}: n_treat={len(treated):3d}  "
              f"treated pre={treated['pre'].mean():+.2f} post={treated['post'].mean():+.2f}  "
              f"DiD={did:+.3f}")
    if rows:
        R = pd.DataFrame(rows)
        w = np.average(R["did"], weights=R["nt"])
        print(f"      --> pooled DiD = {w:+.3f} log ({np.exp(w)-1:+.0%} population)")
        return np.exp(w) - 1
    return np.nan


def pretrend(loc, treat="charter"):
    ycol = f"{treat}_year"
    d = loc.dropna(subset=[ycol]).copy()
    d["gc"] = np.floor(d[ycol] / 100.0) * 100
    pre, post = [], []
    for _, r in d.iterrows():
        gc = r["gc"]
        for tag, y0, y1 in [("pre", gc - 100, gc), ("post", gc, gc + 100)]:
            c0, c1 = f"pop{int(y0)}", f"pop{int(y1)}"
            if c0 in r and c1 in r and pd.notna(r[c0]) and pd.notna(r[c1]) \
               and r[c0] >= TH and r[c1] >= TH:
                (pre if tag == "pre" else post).append(np.log(r[c1]) - np.log(r[c0]))
    pre, post = np.array(pre), np.array(post)
    print(f"  [pre-trend]   growth century BEFORE grant={pre.mean():+.3f} (n={len(pre)}), "
          f"AFTER={post.mean():+.3f} (n={len(post)}), diff={post.mean()-pre.mean():+.3f}")


if __name__ == "__main__":
    loc = attach_population(load_treatment_years())
    print(f"cities matched to population: {len(loc)}  "
          f"(charter-dated {loc.charter_year.notna().sum()}, "
          f"market-dated {loc.market_year.notna().sum()})\n")
    for treat in ["charter", "market"]:
        print("=" * 74)
        print(f"{treat.upper()} — Stadtrecht" if treat == "charter" else f"{treat.upper()} — Marktrecht")
        print("=" * 74)
        long = to_long(loc, treat)
        naive_twfe(long, treat)
        matched_did(loc, treat)
        pretrend(loc, treat)
        print()
    loc.to_csv("out/charter_frame.csv", index=False)
