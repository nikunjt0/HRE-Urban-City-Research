"""Build the city x window political-regime panel, 1300-1789.

Inputs
  cities_polities.csv   annual city x year: ruler lineage, change type, secondary rule
  territories_all.csv   rule episodes incl. city_status (free/imperial city spells)
  ruler_types.csv       terr_id -> church / self / noble / unknown
  crosswalk_cid_cityid  Buringh cid <-> city_id (populations)
  construction.csv      dated construction events (all 2,390 cities)
  markets.csv           dated market grants

Outputs (analysis/out/politics/)
  regime_events.csv   every primary-ruler change: year, old/new lineage+type, how
  regime_windows.csv  city_id x window: regime shares, instability, events
  growth_panel.csv    regime_windows joined with dlog pop and construction counts
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
from panel import load_buringh  # noqa: E402

HIT = ROOT / "docs/territorial_histories/territorial_hit"
OUT = HERE.parent / "out" / "politics"
OUT.mkdir(parents=True, exist_ok=True)

# pop years available in Buringh within the political panel's 1300-1789 span
WINDOWS = [(1300, 1400), (1400, 1500), (1500, 1550), (1550, 1600),
           (1600, 1650), (1650, 1700), (1700, 1750), (1750, 1800)]

UNSTABLE_STYPES = {1, 2, 3, 4, 7}  # occupation, pledge, inh. dispute, comp. claims, uprising


def load_polities() -> pd.DataFrame:
    p = pd.read_csv(HIT / "cities_polities.csv")
    rt = pd.read_csv(OUT / "ruler_types.csv")[["terr_id", "ruler_type", "subtype"]]
    p = p.merge(rt, on="terr_id", how="left")
    p["ruler_type"] = p["ruler_type"].fillna("unknown")
    return p


def self_rule_years(p: pd.DataFrame) -> pd.DataFrame:
    """Self-rule = lineage classified 'self' OR a dated free/imperial city_status
    episode in territories_all (primary timeline)."""
    t = pd.read_csv(HIT / "territories_all.csv", low_memory=False)
    ep = t[(t["city_status"].isin([1, 2, 3])) & t["beginning_reign"].notna()].copy()
    ep["end"] = ep["end_reign"].fillna(1789).clip(upper=1789)
    ep["beg"] = ep["beginning_reign"].clip(lower=1300)
    rows = []
    for _, r in ep.iterrows():
        if r["end"] >= r["beg"]:
            rows.append((r["city_id"], int(r["beg"]), int(r["end"]), int(r["city_status"])))
    spans = pd.DataFrame(rows, columns=["city_id", "beg", "end", "status"])
    # expand to city-years (small enough)
    yrs = []
    for _, r in spans.iterrows():
        for y in range(r["beg"], r["end"] + 1):
            yrs.append((r["city_id"], y, r["status"]))
    sr = (pd.DataFrame(yrs, columns=["city_id", "year", "status"])
            .groupby(["city_id", "year"], as_index=False)["status"].max())
    p = p.merge(sr, on=["city_id", "year"], how="left")
    p["is_self"] = (p["ruler_type"].eq("self")) | (p["status"].notna())
    return p


def extract_events(p: pd.DataFrame) -> pd.DataFrame:
    p = p.sort_values(["city_id", "year"])
    g = p.groupby("city_id")
    prev_terr = g["terr_id"].shift()
    prev_type = g["ruler_type"].shift()
    chg = p["terr_id"].ne(prev_terr) & prev_terr.notna()
    ev = p[chg].copy()
    ev["old_terr"] = prev_terr[chg]
    ev["old_type"] = prev_type[chg]
    keep = ["city_id", "year", "old_terr", "terr_id", "old_type", "ruler_type",
            "type_change", "foreign_rule"]
    ev = ev[keep].rename(columns={"terr_id": "new_terr", "ruler_type": "new_type"})
    ev.to_csv(OUT / "regime_events.csv", index=False)
    return ev


def window_features(p: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    p = p.copy()
    p["win"] = None
    feats = []
    for (a, b) in WINDOWS:
        sub = p[(p.year >= a) & (p.year < min(b, 1790))]
        g = sub.groupby("city_id")
        f = pd.DataFrame({
            "share_church": g.apply(lambda d: d.ruler_type.eq("church").mean(), include_groups=False),
            "share_self": g["is_self"].mean(),
            "share_noble": g.apply(lambda d: (d.ruler_type.eq("noble") & ~d.is_self).mean(), include_groups=False),
            "share_unknown": g.apply(lambda d: d.ruler_type.eq("unknown").mean(), include_groups=False),
            "share_foreign": g.apply(lambda d: d.foreign_rule.notna().mean(), include_groups=False),
            "share_unstable": g.apply(lambda d: d.stype_reign.isin(UNSTABLE_STYPES).mean(), include_groups=False),
            "share_occupied": g.apply(lambda d: d.stype_reign.eq(1).mean(), include_groups=False),
            "share_pledged": g.apply(lambda d: d.stype_reign.eq(2).mean(), include_groups=False),
            "share_contested": g.apply(lambda d: (d.sovereign_number > 1).mean(), include_groups=False),
            "hanse": g["hanse"].max(),
        }).reset_index()
        e = ev[(ev.year >= a) & (ev.year < min(b, 1790))]
        ec = e.groupby("city_id").agg(
            n_ruler_changes=("year", "size"),
            n_extinction=("type_change", lambda s: s.eq(3).sum()),
            n_conquest=("type_change", lambda s: s.eq(4).sum()),
            n_purchase=("type_change", lambda s: s.eq(5).sum()),
            n_mediatized=("type_change", lambda s: s.eq(13).sum()),
        ).reset_index()
        f = f.merge(ec, on="city_id", how="left").fillna(
            {c: 0 for c in ["n_ruler_changes", "n_extinction", "n_conquest",
                            "n_purchase", "n_mediatized"]})
        f["y0"], f["y1"] = a, b
        feats.append(f)
    w = pd.concat(feats, ignore_index=True)
    w.to_csv(OUT / "regime_windows.csv", index=False)
    return w


def outcomes(w: pd.DataFrame) -> pd.DataFrame:
    xw = pd.read_csv(OUT / "crosswalk_cid_cityid.csv")
    b = load_buringh()
    pop = b[b.cid.isin(xw.cid)][["cid", "year", "pop"]]
    pop = pop.merge(xw[["cid", "city_id"]], on="cid")
    piv = pop.pivot_table(index="city_id", columns="year", values="pop", aggfunc="max")
    con = pd.read_csv(ROOT / "docs/construction_data/construction.csv")
    mk = pd.read_csv(ROOT / "docs/markets/markets_data/markets.csv")
    new_mk = mk[mk.type_market.isin(range(1, 11)) & (mk.unused == 0)]
    rows = []
    for _, r in w.iterrows():
        a, bb = int(r.y0), int(r.y1)
        d = dict(r)
        p0 = piv[a].get(r.city_id, np.nan) if a in piv.columns else np.nan
        p1 = piv[bb].get(r.city_id, np.nan) if bb in piv.columns else np.nan
        d["pop0"], d["pop1"] = p0, p1
        d["dlog_pop"] = (np.log(p1) - np.log(p0)) if (p0 and p1 and p0 > 0 and p1 > 0) else np.nan
        d["n_constr"] = ((con.city_id == r.city_id) & (con.time_point >= a) & (con.time_point < bb)).sum()
        d["n_markets_new"] = ((new_mk.city_id == r.city_id) & (new_mk.time_point >= a) & (new_mk.time_point < bb)).sum()
        rows.append(d)
    gp = pd.DataFrame(rows)
    gp.to_csv(OUT / "growth_panel.csv", index=False)
    return gp


if __name__ == "__main__":
    p = load_polities()
    p = self_rule_years(p)
    ev = extract_events(p)
    print(f"events: {len(ev)}  by type_change:\n", ev.type_change.value_counts().head(10))
    print("transitions old->new type:\n", ev.groupby(["old_type", "new_type"]).size())
    w = window_features(p, ev)
    print("windows:", w.shape)
    gp = outcomes(w)
    print("growth panel:", gp.shape, "with dlog_pop:", gp.dlog_pop.notna().sum())
