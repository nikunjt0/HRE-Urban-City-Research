"""Buringh expanded urban population panel (2,262 cities, 700-2000).

This is the dataset Buringh (2021) "The population of European cities from
700 to 2000" — used for paper robustness against Bairoch and as a richer
covariate source (transport location / water catchment area, country code).

Distinct from lib/bairoch_pop.py: same matching logic to Bairoch city_id,
but the Buringh panel is rectangular (every city × every century snapshot,
even before the city existed → pop = 0) and includes a `transport` column.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from .geo import EARTH_KM
from .paths import CITY_LOCATIONS_CSV, DOCS

BURINGH_DIR = DOCS / "European_Population_data_Buringh"
BURINGH_XLSX = BURINGH_DIR / "European urban population, 700 - 2000.xlsx"

# HRE-relevant countries (modern names) for filtering. The HRE was bigger
# than modern Germany; this captures the main territory.
HRE_COUNTRIES = {
    "Germany", "Austria", "Czech Republic", "Switzerland", "Belgium",
    "Netherlands", "Luxembourg", "Slovenia",
}


def _norm(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    for tok in [" am main", " am rhein", "(oder)", "/main", "(main)",
                " ob der tauber"]:
        s = s.replace(tok, "")
    return "".join(c for c in s if c.isalnum())


def load_buringh_panel(filter_hre: bool = False) -> pd.DataFrame:
    """Long DataFrame: city, country, transport, lat, lon, elev_m, year, pop_pers.

    `filter_hre=True` restricts to modern-day HRE-area countries.
    Pop is multiplied by 1000 to get persons. Zeros are kept (they encode
    "city did not exist yet at this snapshot").
    """
    df = pd.read_excel(BURINGH_XLSX, engine="openpyxl")
    df = df.rename(columns={
        "city": "buringh_city",
        "synonyms and historical names": "synonyms",
        "ISO-3166 country code": "iso",
        "country": "country",
        "transportlocation/water catchment area": "transport",
        "latitude in degrees": "p_lat",
        "longitude in degrees": "p_lon",
        "elevation in m": "elev_m",
        "year": "year",
        "inhabitants in 000-s": "pop_000",
        "source": "source",
        "nature of estimate": "nature_estimate",
    })
    for col in ["p_lat", "p_lon", "elev_m", "pop_000"]:
        df[col] = df[col].apply(
            lambda v: str(v).replace(",", ".") if isinstance(v, str) else v)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["p_lat", "p_lon", "year"])
    df["pop_pers"] = df["pop_000"].fillna(0) * 1000.0
    if filter_hre:
        df = df[df["country"].isin(HRE_COUNTRIES)].reset_index(drop=True)
    return df[[
        "buringh_city", "synonyms", "country", "transport",
        "p_lat", "p_lon", "elev_m", "year", "pop_pers"]].copy()


def match_buringh_to_bairoch() -> pd.DataFrame:
    """Match Buringh rows to Bairoch city_id via name + spatial.

    Returns the Buringh long panel (HRE-filtered) augmented with `city_id`
    where a match was found within 15 km. Rows without a match keep
    `city_id = NaN`.
    """
    bcities = pd.read_csv(CITY_LOCATIONS_CSV)
    bcities = bcities[["city_id", "name", "latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"})
    bcities = bcities.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    bcities["b_norm"] = bcities["name"].apply(_norm)

    bur = load_buringh_panel(filter_hre=True)
    # Match unique (city, lat, lon) once; broadcast to all years
    keys = bur.drop_duplicates("buringh_city")[
        ["buringh_city", "p_lat", "p_lon"]].copy()
    keys["b_norm"] = keys["buringh_city"].apply(_norm)

    bx = np.deg2rad(bcities[["lat", "lon"]].to_numpy())
    bt = BallTree(bx, metric="haversine")
    K = min(10, len(bcities))
    pxy = np.deg2rad(keys[["p_lat", "p_lon"]].to_numpy())
    d_rad, idx = bt.query(pxy, k=K)
    d_km = d_rad * EARTH_KM

    matches = []
    for i, n in enumerate(keys["b_norm"].values):
        chosen = None
        for k in range(K):
            if d_km[i, k] > 15:
                break
            cand = bcities.iloc[idx[i, k]]["b_norm"]
            if cand.startswith(n) or n.startswith(cand):
                chosen = bcities.iloc[idx[i, k]]["city_id"]
                break
        if chosen is None and d_km[i, 0] <= 5:
            chosen = bcities.iloc[idx[i, 0]]["city_id"]
        matches.append(chosen)
    keys["city_id"] = matches
    bur = bur.merge(keys[["buringh_city", "city_id"]], on="buringh_city",
                    how="left")
    return bur
