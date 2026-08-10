"""Southern/Europe-wide institution treatments: Bosker communes & Wahl PPI.

Both sources are century-resolution STATUS panels (0/1 observed at years 800,
900, ..., 1800), unlike the exactly-dated Cantoni/Viabundus grants. Convention:
if an institution is first observed at century year c, adoption happened in
(c-100, c]; we date the treatment at the midpoint c-50. Under the existing
machinery (grant century gc = floor(year/100)*100) this makes the "post"
century the century DURING which the institution emerged — mirroring a
mid-century grant with ~50 years of exposure before the first treated census.

Coverage discipline (same as coverage.py): a status is an observed zero only
for cities the source actually codes. Buringh cities are matched to a source
city by nearest coordinates within MATCH_KM; unmatched cities are outside the
universe (flag False) and their institution status is missing, never zero.

  - Bosker, Buringh & van Zanden (2013): `commune` (communal self-government),
    792 cities, all Europe + MENA. This is the Europe-wide analogue of a town
    charter: it covers Italy, France, Austria, Switzerland, Hungary — exactly
    the region where charter status is otherwise unobservable.
  - Wahl (2015, extended database): participative political institutions
    (council elections, guild participation, burgher representation) for 325
    cities incl. Austria and Switzerland. Treatment = first century with ANY
    participative institution. NOTE: the extended file has no year-1100
    observation, so a first observation at 1200 may reflect adoption anywhere
    in (1000, 1200]; the midpoint convention dates it 1150.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree

ROOT = Path(__file__).resolve().parents[2]
BOSKER = ROOT / "docs/external/bosker_baghdad_london/bagdad_london_final_restat.dta"
PPI = ROOT / "docs/external/wahl_ppi/extended_ppi_database.xlsx"
EARTH_KM = 6371.0088
MATCH_KM = 8.0


def _nearest_attach(w: pd.DataFrame, src: pd.DataFrame, ycol: str):
    """Nearest-neighbour match src (lat, lon, first_year) onto w. Returns
    (in_universe flag, treatment year) arrays aligned to w. If several source
    cities map to the same Buringh city, the earliest year wins."""
    tree = BallTree(np.deg2rad(w[["lat", "lon"]].to_numpy()), metric="haversine")
    d, idx = tree.query(np.deg2rad(src[["lat", "lon"]].to_numpy()), k=1)
    km = d.flatten() * EARTH_KM
    in_uni = np.zeros(len(w), bool)
    year = np.full(len(w), np.nan)
    for j, (i, dist) in enumerate(zip(idx.flatten(), km)):
        if dist > MATCH_KM:
            continue
        in_uni[i] = True
        fy = src[ycol].iloc[j]
        if pd.notna(fy) and (np.isnan(year[i]) or fy < year[i]):
            year[i] = fy
    return in_uni, year


def attach_commune(w: pd.DataFrame) -> pd.DataFrame:
    """Add in_bosker + commune_year (midpoint-dated) to a wide Buringh frame."""
    b = pd.read_stata(BOSKER)
    b = b[b["year"].between(800, 1600)]
    meta = b.groupby("city").agg(lat=("latitude", "first"), lon=("longitude", "first"))
    first = b[b["commune"] == 1].groupby("city")["year"].min() - 50  # midpoint
    src = meta.join(first.rename("first_year")).dropna(subset=["lat", "lon"]).reset_index()
    in_uni, year = _nearest_attach(w, src, "first_year")
    w = w.copy()
    w["in_bosker"] = in_uni
    w["commune_year"] = year
    return w


def attach_ppi(w: pd.DataFrame) -> pd.DataFrame:
    """Add in_ppi + ppi_year (first century with ANY participative institution,
    midpoint-dated) to a wide Buringh frame."""
    p = pd.read_excel(PPI)
    p.columns = ["city", "year", "country", "lat", "lon", "election", "guild", "burgherrep"]
    p = p[p["year"].between(800, 1600)]
    p["any_ppi"] = ((p["election"] >= 1) | (p["guild"] >= 1) | (p["burgherrep"] >= 1)).astype(int)
    meta = p.groupby("city").agg(lat=("lat", "first"), lon=("lon", "first"))
    first = p[p["any_ppi"] == 1].groupby("city")["year"].min() - 50  # midpoint
    src = meta.join(first.rename("first_year")).dropna(subset=["lat", "lon"]).reset_index()
    in_uni, year = _nearest_attach(w, src, "first_year")
    w = w.copy()
    w["in_ppi"] = in_uni
    w["ppi_year"] = year
    return w


if __name__ == "__main__":
    from panel import load_buringh, wide_pop
    w = wide_pop(load_buringh(), years=(1100, 1200, 1300, 1400, 1500))
    w = w[w["in_cne"]].reset_index(drop=True)
    w = attach_commune(w)
    w = attach_ppi(w)
    for tag, uni, ycol in [("commune", "in_bosker", "commune_year"),
                           ("ppi", "in_ppi", "ppi_year")]:
        u = w[w[uni]]
        dated = u[ycol].notna()
        print(f"{tag}: universe {len(u)} cities; dated treatments {int(dated.sum())}; "
              f"treatment-century distribution "
              f"{u.loc[dated, ycol].apply(lambda y: int(y//100*100)).value_counts().sort_index().to_dict()}")
        print(f"   by country (dated): "
              f"{u.loc[dated, 'country'].value_counts().head(8).to_dict()}")
