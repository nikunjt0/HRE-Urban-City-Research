"""Persistent crosswalk: Buringh cid <-> Cantoni/Wahl city_id.

Matches every Buringh city (full panel, not just CNE) to the city_locations
gazetteer via name-within-60km, falling back to nearest-within-5km, reusing
papers/city_growth/city_table.py's match_loc. Output: papers/politics/out/crosswalk_cid_cityid.csv
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "city_growth"))
from panel import load_buringh, wide_pop  # noqa: E402
from city_table import match_loc, LOC  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

ALL_YEARS = (800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1750, 1800)


def build() -> pd.DataFrame:
    w = wide_pop(load_buringh(), years=ALL_YEARS)
    loc = pd.read_csv(LOC).rename(columns={"latitude": "lat", "longitude": "lon"})
    loc = loc.reset_index(drop=True)
    pos = match_loc(w, loc)
    w = w.reset_index(drop=True)
    w["loc_pos"] = pos
    m = w[w["loc_pos"] >= 0].copy()
    m["city_id"] = loc.loc[m["loc_pos"], "city_id"].to_numpy()
    m["name_loc"] = loc.loc[m["loc_pos"], "name"].to_numpy()
    # if several cids hit the same city_id keep the closest-named / largest city
    m["pop_max"] = m[[f"pop{y}" for y in ALL_YEARS]].max(axis=1)
    m = (m.sort_values("pop_max", ascending=False)
           .drop_duplicates("city_id", keep="first"))
    keep = ["cid", "city", "country", "lat", "lon", "in_hre", "in_cne",
            "city_id", "name_loc"]
    xw = m[keep].sort_values("cid")
    xw.to_csv(OUT / "crosswalk_cid_cityid.csv", index=False)
    return xw


if __name__ == "__main__":
    xw = build()
    print(f"matched {len(xw)} Buringh cids to city_ids")
    print(xw.head(10).to_string(index=False))
