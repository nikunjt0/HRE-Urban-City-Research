"""Decadal city panel 1300-1789 for all 2,390 Städtebuch cities.

Outcome: construction activity per decade (all events; new buildings; secular
economic buildings = buildgen 3 'economic' + code 8 infrastructure + 5 town hall).
Treatments per decade: ruler type shares, extinction / conquest / purchase /
mediatization events, pledge & occupation spells, contested rule, foreign rule.
Controls: conflict incidents (destruction type) per decade.

Output: papers/politics/out/decadal_panel.csv
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
HIT = ROOT / "docs/territorial_histories/territorial_hit"
OUT = HERE / "out"

DEC0, DEC1 = 1300, 1780  # decades [1300..1309] ... [1780..1789]


def decade(y):
    return (y // 10) * 10


def build():
    p = pd.read_csv(HIT / "cities_polities.csv")
    rt = pd.read_csv(OUT / "ruler_types.csv")[["terr_id", "ruler_type"]]
    p = p.merge(rt, on="terr_id", how="left")
    p["ruler_type"] = p["ruler_type"].fillna("unknown")
    p["dec"] = decade(p.year)

    g = p.groupby(["city_id", "dec"])
    base = pd.DataFrame({
        "share_church": g["ruler_type"].apply(lambda s: s.eq("church").mean()),
        "share_self": g["ruler_type"].apply(lambda s: s.eq("self").mean()),
        "share_foreign": g["foreign_rule"].apply(lambda s: s.notna().mean()),
        "share_occupied": g["stype_reign"].apply(lambda s: s.eq(1).mean()),
        "share_pledged": g["stype_reign"].apply(lambda s: s.eq(2).mean()),
        "share_disputed": g["stype_reign"].apply(lambda s: s.isin([3, 4]).mean()),
        "share_uprising": g["stype_reign"].apply(lambda s: s.eq(7).mean()),
        "share_contested": g["sovereign_number"].apply(lambda s: (s > 1).mean()),
    }).reset_index()

    ev = pd.read_csv(OUT / "regime_events.csv")
    ev["dec"] = decade(ev.year)
    ec = ev.groupby(["city_id", "dec"]).agg(
        n_changes=("year", "size"),
        n_ext=("type_change", lambda s: s.eq(3).sum()),
        n_conq=("type_change", lambda s: s.eq(4).sum()),
        n_medi=("type_change", lambda s: s.eq(13).sum()),
    ).reset_index()

    con = pd.read_csv(ROOT / "docs/construction_data/construction.csv")
    con = con[(con.range <= 2)]  # dates good to +-25y
    con["dec"] = decade(con.time_point)
    cc = con.groupby(["city_id", "dec"]).agg(
        n_constr=("time_point", "size"),
        n_new=("newbuild", "sum"),
    ).reset_index()
    sec = con[con.building.isin([5, 6, 7, 8])]  # town hall, economic, mall, infra
    cc2 = sec.groupby(["city_id", "dec"]).size().rename("n_econ").reset_index()

    cf = pd.read_csv(ROOT / "docs/conflicts_and_war/conflict_incidents.csv")
    cf = cf[(cf.overreported == 0) & (cf.range <= 2)]
    cf["dec"] = decade(cf.time_point)
    ff = cf.groupby(["city_id", "dec"]).agg(
        n_conflict=("time_point", "size"),
        n_destroy=("type_conflict", lambda s: s.eq(2).sum()),
    ).reset_index()

    # full rectangular scaffold
    cities = sorted(p.city_id.unique())
    decs = list(range(DEC0, DEC1 + 1, 10))
    idx = pd.MultiIndex.from_product([cities, decs], names=["city_id", "dec"])
    d = pd.DataFrame(index=idx).reset_index()
    for extra in (base, ec, cc, cc2, ff):
        d = d.merge(extra, on=["city_id", "dec"], how="left")
    fill0 = ["n_changes", "n_ext", "n_conq", "n_medi", "n_constr", "n_new",
             "n_econ", "n_conflict", "n_destroy"]
    d[fill0] = d[fill0].fillna(0)
    # regime shares: forward-fill within city (cities enter at 1300; all present)
    d = d.sort_values(["city_id", "dec"])
    d.to_csv(OUT / "decadal_panel.csv", index=False)
    print("decadal panel:", d.shape, "cities:", d.city_id.nunique())
    print(d[fill0].sum())
    return d


if __name__ == "__main__":
    build()
