"""Master city table + over/under-performer analysis for the paper.

Builds one row per Buringh city (Central/North Europe) with: population 1200-1500,
first-nature geography, dated privileges (charter/market from Cantoni, staple from
Viabundus), a 'fundamentals-predicted' 1500 size, and the residual (who beat / fell
short of what their geography+history predicted).
"""
from __future__ import annotations
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree
import statsmodels.api as sm
from panel import load_buringh, wide_pop

ROOT = Path(__file__).resolve().parent.parent
LOC = ROOT / "docs/city_locations_and_border_maps/dataverse_files/city_locations.csv"
TC = ROOT / "docs/town_charters_and_first_mentions/towncharter_data/towncharter.csv"
MK = ROOT / "docs/markets/markets_data/markets.csv"
LF = ROOT / "docs/town_charters_and_first_mentions/towncharter_data/legal_families.csv"
VIA = ROOT / "docs/viabundus/Viabundus-2-csv"
EARTH_KM = 6371.0088
TH = 1000.0
GRANT_MARKETS = {1, 2, 6, 7, 8, 9, 10}


def _nearest(src_latlon, tgt):
    tree = BallTree(np.deg2rad(tgt[["lat", "lon"]].to_numpy()), metric="haversine")
    d, idx = tree.query(np.deg2rad(src_latlon), k=1)
    return d.flatten() * EARTH_KM, idx.flatten()


import unicodedata
def _norm(s):
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    for a, b in [("ss", "s"), ("oe", "o"), ("ae", "a"), ("ue", "u")]:
        s = s.replace(a, b)
    return "".join(c for c in s if c.isalnum())


def match_loc(d, loc):
    """Match each Buringh row to a city_locations row: prefer a name match
    (across name/name_alt/name_foreign) within 60 km; else nearest within 5 km.
    Returns array of loc positional indices (or -1)."""
    loc = loc.reset_index(drop=True)
    name_cols = [c for c in ["name", "name_alt", "name_foreign"] if c in loc.columns]
    name_idx = {}
    for i, row in loc.iterrows():
        for c in name_cols:
            k = _norm(row[c])
            if k:
                name_idx.setdefault(k, []).append(i)
    loc_rad = np.deg2rad(loc[["lat", "lon"]].to_numpy())
    out = np.full(len(d), -1)
    for j, row in d.reset_index(drop=True).iterrows():
        cand = name_idx.get(_norm(row["city"]), [])
        pr = np.deg2rad([row["lat"], row["lon"]])
        if cand:
            # nearest among name matches, accept if < 60 km
            dd = np.arccos(np.clip(np.sin(loc_rad[cand, 0]) * np.sin(pr[0]) +
                  np.cos(loc_rad[cand, 0]) * np.cos(pr[0]) *
                  np.cos(loc_rad[cand, 1] - pr[1]), -1, 1)) * EARTH_KM
            if dd.min() < 60:
                out[j] = cand[int(dd.argmin())]
                continue
    # coordinate fallback for unmatched, within 5 km
    miss = np.where(out < 0)[0]
    if len(miss):
        dist, idx = _nearest(d.iloc[miss][["lat", "lon"]].to_numpy(), loc)
        for k, m in enumerate(miss):
            if dist[k] <= 5.0:
                out[m] = idx[k]
    return out


def build():
    w = wide_pop(load_buringh(), years=(800, 1200, 1300, 1400, 1500))
    d = w[w["in_cne"]].copy().reset_index(drop=True)

    # charter/market years via city_locations (name-aware match)
    loc = pd.read_csv(LOC).rename(columns={"latitude": "lat", "longitude": "lon"})
    loc = loc.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    tc = pd.read_csv(TC)
    # only treat medieval/early-modern formal charters (<=1600) as 'the charter';
    # ancient cities with no such event => NaN (they were cities before charters existed)
    charter = (tc[(tc["type_origin"] == 1) & (tc["time_point"].between(1000, 1600))]
               .groupby("city_id")["time_point"].min())
    firstment = tc[tc["type_origin"] == 5].groupby("city_id")["time_point"].min()
    mk = pd.read_csv(MK)
    market = (mk[mk["type_market"].isin(GRANT_MARKETS) & (mk["time_point"] <= 1600)]
              .groupby("city_id")["time_point"].min())
    lf = pd.read_csv(LF)
    loc["charter_year"] = loc["city_id"].map(charter)
    loc["market_year"] = loc["city_id"].map(market)
    loc["first_mention"] = loc["city_id"].map(firstment)
    loc = loc.merge(lf, left_on="name", right_on="city", how="left")

    idx = match_loc(d, loc)
    for c in ["charter_year", "market_year", "first_mention", "legal_family"]:
        vals = loc[c].to_numpy()
        d[c] = [vals[i] if i >= 0 else np.nan for i in idx]
    d["name_loc"] = [loc["name"].to_numpy()[i] if i >= 0 else "" for i in idx]

    # staple (Viabundus) by coordinate
    n = pd.read_csv(VIA / "nodes.csv", low_memory=False, na_values=["null", ""])
    n["lat"] = pd.to_numeric(n["latitude"], errors="coerce")
    n["lon"] = pd.to_numeric(n["longitude"], errors="coerce")
    st = n[n["Is_Staple"] == "y"].dropna(subset=["lat", "lon"]).reset_index(drop=True)
    sd, _ = _nearest(d[["lat", "lon"]].to_numpy(), st[["lat", "lon"]])
    d["staple"] = (sd <= 6.0).astype(int)

    d["water"] = ((d["on_river"] == 1) | (d["on_coast"] == 1)).astype(int)
    return d


def performers(d):
    """Fundamentals model: predict log pop1500 from log pop1200 + water; residual =
    over/under-performance relative to geography+history."""
    s = d[(d["pop1200"] >= TH) & (d["pop1500"] >= TH)].copy()
    s["l1200"] = np.log(s["pop1200"]); s["l1500"] = np.log(s["pop1500"])
    r = sm.OLS(s["l1500"], sm.add_constant(s[["l1200", "water"]])).fit()
    s["pred1500"] = np.exp(r.predict(sm.add_constant(s[["l1200", "water"]])))
    s["resid"] = s["l1500"] - np.log(s["pred1500"])
    return s, r


def fmt_year(y):
    if pd.isna(y):
        return "—"
    y = int(y)
    return f"{abs(y)} BCE" if y < 0 else str(y)


if __name__ == "__main__":
    d = build()
    s, r = performers(d)
    print(f"fundamentals model: log(pop1500) = {r.params['const']:.2f} + "
          f"{r.params['l1200']:.2f}*log(pop1200) + {r.params['water']:.2f}*water   "
          f"R2={r.rsquared:.3f}, n={int(r.nobs)}")

    famous = ["Cologne", "Köln", "Nürnberg", "Nuremberg", "Lübeck", "Hamburg",
              "Frankfurt am Main", "Augsburg", "Magdeburg", "Leipzig", "Bremen",
              "Vienna", "Wien", "Prague", "Praha", "Strasbourg", "Straßburg",
              "Basel", "Danzig", "Gdansk", "Erfurt", "Rostock", "Ulm", "Regensburg",
              "Mainz", "Nürtingen"]
    sub = s[s["city"].isin(famous)].copy()
    sub["growth"] = sub["l1500"] - sub["l1200"]
    cols = ["city", "pop1200", "pop1500", "growth", "water", "charter_year",
            "market_year", "staple", "legal_family", "resid"]
    print("\n=== FAMOUS CITIES ===")
    view = sub[cols].sort_values("pop1500", ascending=False)
    for _, row in view.iterrows():
        print(f"  {row['city']:<18s} p1200={row['pop1200']:>7.0f} p1500={row['pop1500']:>7.0f} "
              f"g={row['growth']:+.2f} water={int(row['water'])} "
              f"charter={fmt_year(row['charter_year']):>6s} staple={int(row['staple'])} "
              f"resid={row['resid']:+.2f}")

    print("\n=== TOP 12 OVER-PERFORMERS (beat their fundamentals) ===")
    for _, row in s.nlargest(12, "resid").iterrows():
        print(f"  {row['city']:<18s} p1200={row['pop1200']:>6.0f} p1500={row['pop1500']:>7.0f} "
              f"resid={row['resid']:+.2f} water={int(row['water'])} charter={fmt_year(row['charter_year'])}")
    print("\n=== TOP 12 UNDER-PERFORMERS ===")
    for _, row in s.nsmallest(12, "resid").iterrows():
        print(f"  {row['city']:<18s} p1200={row['pop1200']:>6.0f} p1500={row['pop1500']:>7.0f} "
              f"resid={row['resid']:+.2f} water={int(row['water'])} charter={fmt_year(row['charter_year'])}")

    d.to_csv("out/city_master.csv", index=False)
    s.to_csv("out/city_performers.csv", index=False)

    # curated famous-city table (persistence-only residual, for the paper)
    s2 = s.copy()
    rp = sm.OLS(s2["l1500"], sm.add_constant(s2[["l1200"]])).fit()
    s2["res_p"] = s2["l1500"] - rp.predict(sm.add_constant(s2[["l1200"]]))
    fam = ["Koeln", "Luebeck", "Hamburg", "Nuernberg", "Magdeburg", "Frankfurt am Main",
           "Augsburg", "Leipzig", "Bremen", "Gdansk", "Rostock", "Erfurt", "Ulm",
           "Regensburg", "Mainz", "Wien", "Strasbourg", "Basel", "Amsterdam",
           "Antwerpen", "Utrecht"]
    disp = {"Koeln": "Cologne", "Luebeck": "Lübeck", "Nuernberg": "Nuremberg",
            "Gdansk": "Danzig", "Wien": "Vienna", "Frankfurt am Main": "Frankfurt"}
    fam_df = s2[s2["city"].isin(fam)].copy()
    fam_df["disp"] = fam_df["city"].map(lambda c: disp.get(c, c))
    fam_df.sort_values("pop1500", ascending=False).to_csv("out/famous_cities.csv", index=False)
    print("\nsaved out/city_master.csv, out/city_performers.csv, out/famous_cities.csv")
