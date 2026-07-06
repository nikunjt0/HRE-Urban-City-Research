"""Canonical city-population panel from Buringh (2021), the primary source.

Buringh's "European urban population, 700-2000" is the most complete single
source: it carries lat/lon, a transport/water-catchment class (first-nature
geography), elevation, and 19 year-snapshots per city. We use it directly
(no lossy name-matching) as the backbone panel, and attach Viabundus network
ids separately where available.

Region handling: we tag each city with whether it falls inside the Holy Roman
Empire core-country set and inside the Viabundus network footprint, but we do
NOT drop anything here -- downstream analyses choose their own sample.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "docs/European_Population_data_Buringh/European urban population, 700 - 2000.xlsx"

# HRE-area modern countries (the empire's rough footprint 1200-1500).
HRE_COUNTRIES = {
    "Germany", "Austria", "Switzerland", "Czech Republic", "Belgium",
    "Netherlands", "Luxembourg", "Slovenia", "Liechtenstein",
}
# Wider Central/North Europe used for network + Zipf work.
CNE_COUNTRIES = HRE_COUNTRIES | {
    "France", "Poland", "Italy", "Denmark", "Hungary",
}


def _num(s):
    return pd.to_numeric(pd.Series(s).astype(str).str.replace(",", ".", regex=False)
                         .replace({"nan": np.nan, "": np.nan}), errors="coerce")


def load_buringh() -> pd.DataFrame:
    df = pd.read_excel(XLSX)
    df.columns = ["city", "syn", "iso", "country", "transport", "lat", "lon",
                  "elev", "year", "pop000", "source", "nature"]
    df["lat"] = _num(df["lat"]); df["lon"] = _num(df["lon"])
    df["elev"] = _num(df["elev"])
    df["pop000"] = pd.to_numeric(df["pop000"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["pop"] = df["pop000"] * 1000.0
    df = df.dropna(subset=["lat", "lon", "year"]).copy()
    # stable per-city id
    keys = df[["city", "country", "lat", "lon"]].drop_duplicates().reset_index(drop=True)
    keys["cid"] = keys.index.astype(int)
    df = df.merge(keys, on=["city", "country", "lat", "lon"], how="left")
    df["in_hre"] = df["country"].isin(HRE_COUNTRIES)
    df["in_cne"] = df["country"].isin(CNE_COUNTRIES)
    return df


def first_nature(transport: str) -> dict:
    """Decode Buringh transport string into geography dummies."""
    t = "" if pd.isna(transport) else str(transport).lower()
    # coastal if a sea basin appears WITHOUT a leading 'land'/'river' qualifier,
    # or explicitly as a standalone/compound coast token.
    seas = ["north sea", "atlantic", "baltic", "mediterranean", "med",
            "black sea", "caspian sea", "white sea"]
    on_river = "river" in t
    # coast: token starts with a sea name, or "+ river" compounds w/ sea, or bare sea
    on_coast = False
    for s in seas:
        # bare coast: string is exactly the sea, or "sea + river", or starts with sea
        if t == s or t.startswith(s) or t.endswith(s) and "land" not in t and "river" not in t.split(s)[0]:
            on_coast = True
    # simpler robust rule: 'land' => inland; else if not river-only, coastal
    inland = t.startswith("land")
    if inland:
        on_coast = False
    return {
        "on_river": int(on_river),
        "on_coast": int(on_coast),
        "inland": int(inland),
        "atlantic": int("atlantic" in t),
        "baltic": int("baltic" in t),
        "northsea": int("north sea" in t),
        "medit": int("mediterran" in t or t == "med" or "med " in t or t.endswith("med")),
    }


def wide_pop(df: pd.DataFrame, years=(1100, 1200, 1300, 1400, 1500)) -> pd.DataFrame:
    """One row per city, pop columns per year, plus geography."""
    sub = df[df["year"].isin(years)]
    w = sub.pivot_table(index="cid", columns="year", values="pop", aggfunc="max")
    w.columns = [f"pop{int(c)}" for c in w.columns]
    meta = (df.sort_values("year").groupby("cid")
            .agg(city=("city", "first"), country=("country", "first"),
                 lat=("lat", "first"), lon=("lon", "first"),
                 elev=("elev", "first"), transport=("transport", "first"),
                 in_hre=("in_hre", "first"), in_cne=("in_cne", "first")))
    out = meta.join(w, how="left").reset_index()
    fn = out["transport"].apply(first_nature).apply(pd.Series)
    return pd.concat([out, fn], axis=1)


if __name__ == "__main__":
    df = load_buringh()
    print("rows:", len(df), "cities:", df.cid.nunique())
    w = wide_pop(df)
    print("wide shape:", w.shape)
    print(w[w.in_hre].head())
