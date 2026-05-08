"""Bairoch / Bosker population panel — load + match to Bairoch city_id.

Lifts the inline matching logic from build_agricultural_surplus.py:34-116 so
both the agri-surplus builder and the predictive-model builder share one
canonical population loader. Returns a long-format DataFrame keyed on
(city_id, year) with population in persons (not thousands).

Bairoch records snapshots at 700, 800, ..., 1200, 1300, 1400, 1500, 1600, 1650.
There are no annual values in this dataset.
"""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from .geo import EARTH_KM
from .paths import CITY_LOCATIONS_CSV, EU_POP_XLSX


def _norm(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    for tok in [" am main", " am rhein", "(oder)", "/main", "(main)", " ob der tauber"]:
        s = s.replace(tok, "")
    return "".join(c for c in s if c.isalnum())


def load_pop_panel() -> pd.DataFrame:
    """Return long DataFrame: city_id, year, pop_pers, name, lat, lon."""
    cities = pd.read_csv(CITY_LOCATIONS_CSV)
    cities = cities[["city_id", "name", "latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"})
    cities = cities.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    cities["b_norm"] = cities["name"].apply(_norm)

    pop = pd.read_excel(EU_POP_XLSX, engine="openpyxl", sheet_name=0)
    pop = pop.rename(columns={
        "city": "city_name",
        "year": "year",
        "inhabitants in 000-s": "pop_000",
        "latitude in degrees": "p_lat",
        "longitude in degrees": "p_lon",
    })
    pop = pop[["city_name", "p_lat", "p_lon", "year", "pop_000"]].copy()
    for col in ["p_lat", "p_lon", "pop_000"]:
        pop[col] = pop[col].apply(
            lambda v: str(v).replace(",", ".") if isinstance(v, str) else v)
        pop[col] = pd.to_numeric(pop[col], errors="coerce")
    pop = pop[(pop["p_lat"].between(35, 72)) & (pop["p_lon"].between(-15, 45))]
    pop = pop.dropna(subset=["p_lat", "p_lon", "year"])
    pop["bosker_norm"] = pop["city_name"].apply(_norm)

    bx = np.deg2rad(cities[["lat", "lon"]].to_numpy())
    bt = BallTree(bx, metric="haversine")
    K = min(10, len(cities))
    pxy = np.deg2rad(pop[["p_lat", "p_lon"]].to_numpy())
    d_rad, idx = bt.query(pxy, k=K)
    d_km = d_rad * EARTH_KM

    matched_ids = []
    for i, n in enumerate(pop["bosker_norm"].values):
        chosen = None
        for k in range(K):
            if d_km[i, k] > 15:
                break
            cand = cities.iloc[idx[i, k]]["b_norm"]
            if cand.startswith(n) or n.startswith(cand):
                chosen = cities.iloc[idx[i, k]]["city_id"]
                break
        if chosen is None and d_km[i, 0] <= 5:
            chosen = cities.iloc[idx[i, 0]]["city_id"]
        matched_ids.append(chosen if chosen is not None else np.nan)
    pop["city_id"] = matched_ids
    pop = pop.dropna(subset=["city_id", "pop_000"])
    pop["city_id"] = pop["city_id"].astype(int)
    pop["pop_pers"] = pop["pop_000"] * 1000.0
    pop["year"] = pop["year"].astype(int)
    pop = (pop.groupby(["city_id", "year"])["pop_pers"].max().reset_index())

    out = pop.merge(
        cities[["city_id", "name", "lat", "lon"]], on="city_id", how="left")
    return out[["city_id", "name", "lat", "lon", "year", "pop_pers"]]
