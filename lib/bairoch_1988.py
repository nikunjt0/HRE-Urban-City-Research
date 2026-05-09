"""Bairoch (1988) historical urban population, original tidy CSV.

Source: docs/bairoch_pop_data/bairoch-1988-tidy.csv — 2,201 European cities
across 12 century snapshots (800, 900, 1000, 1200, 1300, 1400, 1500, 1600,
1700, 1750, 1800, 1850). Population in thousands, "NA" for missing.

Distinct from lib/bairoch_pop.py and lib/buringh_pop.py — those load the
Buringh (2021) expanded xlsx (2,262 cities × 19 snapshots). The robustness
scatter in build_paper_analysis_report.py uses THIS loader for the original
Bairoch series.

Matching to Bairoch city_id is done indirectly: Bairoch (1988) → Buringh
(name + country) → city_id, since Bairoch (1988) has no lat/lon. Cities
that don't survive both matching steps are dropped.
"""
from __future__ import annotations

import unicodedata

import pandas as pd

from .buringh_pop import match_buringh_to_bairoch
from .paths import DOCS

BAIROCH_CSV = DOCS / "bairoch_pop_data" / "bairoch-1988-tidy.csv"

# Bairoch (1988) uses pre-1990 country names. Map to modern names so we can
# join to Buringh's modern-country labels.
COUNTRY_MAP = {
    "Czechoslovakia": "Czech Republic",
    "Yugoslavia":      "Slovenia",
}


def _norm(s) -> str:
    if pd.isna(s):
        return ""
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    for tok in [" am main", " am rhein", "(oder)", "/main", "(main)",
                " ob der tauber"]:
        s = s.replace(tok, "")
    return "".join(c for c in s if c.isalnum())


def load_bairoch_panel(filter_hre: bool = True) -> pd.DataFrame:
    """Long DataFrame: city_id, year, pop_pers, country, city.

    Matches each (country, city) in Bairoch (1988) to a Bairoch city_id by
    going through Buringh's name+country mapping. Cities not matched in
    Buringh are dropped (we cannot place them on the city_id grid). When
    filter_hre is True, restrict to HRE-area countries.
    """
    raw = pd.read_csv(BAIROCH_CSV, na_values="NA")
    raw = raw.rename(columns={"population": "pop_000", "city": "city_b88",
                              "country": "country_b88"})
    raw["pop_000"] = pd.to_numeric(raw["pop_000"], errors="coerce")
    raw["pop_pers"] = raw["pop_000"] * 1000.0
    raw["year"] = pd.to_numeric(raw["year"], errors="coerce").astype("Int64")
    raw["nrm"] = raw["city_b88"].apply(_norm)
    raw["country_modern"] = raw["country_b88"].replace(COUNTRY_MAP)

    # Buringh matching: gives us {(country, normalized_name) -> city_id}
    bur = match_buringh_to_bairoch()
    bur_ids = bur.dropna(subset=["city_id"]).copy()
    bur_ids["city_id"] = bur_ids["city_id"].astype(int)
    bur_ids["nrm"] = bur_ids["buringh_city"].apply(_norm)
    lookup = (bur_ids.drop_duplicates("buringh_city")
              [["country", "nrm", "city_id"]])

    merged = raw.merge(lookup, left_on=["country_modern", "nrm"],
                       right_on=["country", "nrm"], how="inner")
    out = merged[["city_id", "year", "pop_pers", "country_b88",
                  "city_b88"]].rename(
        columns={"country_b88": "country", "city_b88": "city"})
    out = out.dropna(subset=["year"]).copy()
    out["year"] = out["year"].astype(int)
    if filter_hre:
        # already restricted by virtue of Buringh-HRE-filtered lookup,
        # but be explicit
        out = out[out["country"].isin(
            ["Germany", "Austria", "Switzerland", "Czechoslovakia",
             "Belgium", "Netherlands", "Yugoslavia"])]
    # take max population if duplicates per (city_id, year)
    out = (out.groupby(["city_id", "year"])
              .agg(pop_pers=("pop_pers", "max"),
                   country=("country", "first"),
                   city=("city", "first"))
              .reset_index())
    return out
