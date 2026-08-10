"""Source-coverage universes for the privilege datasets.

A blank in a privilege source can mean two different things: "this city did not
have the privilege" (a true, observable zero) or "this city lies outside the
area the source documents" (missing data). Conflating the two contaminates
every privilege analysis with false zeros — e.g. Vienna is absent from the
Deutsches Städtebuch (1937 German borders), and every Italian city lies beyond
the southern edge of the Viabundus map, yet both were previously coded as
"never privileged". This module tags each city with whether absence is actually
observable in each source:

  - Viabundus (staples, fairs): the mapped road/river/sea network of northern
    and central Europe. Rule: within VIA_KM (25 km) of any network node.
    Cities in covered countries sit a median of ~1 km from a node (NL/BE/DK/PL
    97-100% within 25 km); cities beyond the map edge (Italy, Austria,
    Switzerland, Hungary, southern France, southern Germany) are hundreds of
    km away, so the threshold choice is not sensitive.

  - Deutsches Städtebuch via Cantoni-Mohr-Weigand (town charters, market
    rights): Germany in its 1937 borders, 2,390 cities. Rule: the city matches
    a Städtebuch city (name match within 60 km, else coordinates within 5 km).
    A matched city with no charter record is a true zero; an unmatched city is
    outside the universe and its charter status is unknown.
"""
from __future__ import annotations
import unicodedata
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree

ROOT = Path(__file__).resolve().parents[2]
VIA_NODES = ROOT / "docs/viabundus/Viabundus-2-csv/nodes.csv"
LOC = ROOT / "docs/city_locations_and_border_maps/dataverse_files/city_locations.csv"
EARTH_KM = 6371.0088
VIA_KM = 25.0


def _norm(s):
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    for a, b in [("ss", "s"), ("oe", "o"), ("ae", "a"), ("ue", "u")]:
        s = s.replace(a, b)
    return "".join(c for c in s if c.isalnum())


def viabundus_flag(d: pd.DataFrame, km: float = VIA_KM) -> np.ndarray:
    """True if the city lies inside the Viabundus network footprint
    (within `km` of any network node) — i.e. staple/fair absence is observable."""
    n = pd.read_csv(VIA_NODES, low_memory=False, na_values=["null", ""])
    n["lat"] = pd.to_numeric(n["latitude"], errors="coerce")
    n["lon"] = pd.to_numeric(n["longitude"], errors="coerce")
    n = n.dropna(subset=["lat", "lon"])
    tree = BallTree(np.deg2rad(n[["lat", "lon"]].to_numpy()), metric="haversine")
    dist, _ = tree.query(np.deg2rad(d[["lat", "lon"]].to_numpy()), k=1)
    return (dist.flatten() * EARTH_KM <= km)


def match_stadtebuch(d: pd.DataFrame, loc: pd.DataFrame | None = None) -> np.ndarray:
    """Match each row of `d` (needs city, lat, lon) to a Städtebuch city.
    Prefer a name match (name/name_alt/name_foreign) within 60 km; else nearest
    coordinates within 5 km. Returns positional indices into `loc` (or -1)."""
    if loc is None:
        loc = load_stadtebuch_locations()
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
            dd = np.arccos(np.clip(np.sin(loc_rad[cand, 0]) * np.sin(pr[0]) +
                  np.cos(loc_rad[cand, 0]) * np.cos(pr[0]) *
                  np.cos(loc_rad[cand, 1] - pr[1]), -1, 1)) * EARTH_KM
            if dd.min() < 60:
                out[j] = cand[int(dd.argmin())]
                continue
    miss = np.where(out < 0)[0]
    if len(miss):
        tree = BallTree(loc_rad, metric="haversine")
        dist, idx = tree.query(np.deg2rad(d.iloc[miss][["lat", "lon"]].to_numpy()), k=1)
        for k, m in enumerate(miss):
            if dist[k][0] * EARTH_KM <= 5.0:
                out[m] = idx[k][0]
    return out


def load_stadtebuch_locations() -> pd.DataFrame:
    loc = pd.read_csv(LOC).rename(columns={"latitude": "lat", "longitude": "lon"})
    return loc.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def stadtebuch_flag(d: pd.DataFrame) -> np.ndarray:
    """True if the city matches a Städtebuch city — i.e. charter/market absence
    is observable (an in-universe city with no grant record is a true zero)."""
    return match_stadtebuch(d) >= 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from panel import load_buringh, wide_pop
    w = wide_pop(load_buringh(), years=(1200, 1500))
    w["in_via"] = viabundus_flag(w)
    w["in_stb"] = stadtebuch_flag(w)
    print("Coverage of Buringh cities by privilege source universe:")
    for ctry, g in w.groupby("country"):
        if len(g) >= 3:
            print(f"  {ctry:16s} n={len(g):4d}  Viabundus {g.in_via.mean():5.0%}  "
                  f"Städtebuch {g.in_stb.mean():5.0%}")
    print(f"  {'TOTAL':16s} n={len(w):4d}  Viabundus {w.in_via.mean():5.0%}  "
          f"Städtebuch {w.in_stb.mean():5.0%}")
