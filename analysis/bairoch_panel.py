"""Parallel population panel from Bairoch, Batou & Chevre (1988), matched onto the
SAME geographic scaffold (coordinates + first-nature transport class) as the
Buringh panel, so that the ONLY thing that changes between the two panels is the
population source. This isolates whether our findings depend on which historian's
reconstruction we trust.

Match: normalized (country, city) between Bairoch and Buringh. Bairoch's pre-1990
country labels are mapped to modern names first.
"""
from __future__ import annotations
import unicodedata
import numpy as np, pandas as pd
from pathlib import Path
from panel import load_buringh, first_nature

ROOT = Path(__file__).resolve().parent.parent
BAIROCH = ROOT / "docs/bairoch_pop_data/bairoch-1988-tidy.csv"

COUNTRY_MAP = {
    "Czechoslovakia": "Czech Republic", "Yugoslavia": "Slovenia",
    "Luxemburg": "Luxembourg", "Great Britain": "United Kingdom",
    "Rumania": "Romania",
}


def _norm(s):
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    for tok in [" am main", " am rhein", "(oder)", "/main", "(main)", " ob der tauber",
                " a.m.", ".", "'"]:
        s = s.replace(tok, "")
    for a, b in [("ss", "s"), ("oe", "o"), ("ae", "a"), ("ue", "u")]:
        s = s.replace(a, b)
    return "".join(c for c in s if c.isalnum())


def load_bairoch_wide(years=(800, 1200, 1300, 1400, 1500)):
    """Return one row per matched city with Bairoch pop columns + Buringh geography."""
    b = pd.read_csv(BAIROCH, na_values="NA")
    b["population"] = pd.to_numeric(b["population"], errors="coerce")
    b["pop"] = b["population"] * 1000.0
    b["year"] = pd.to_numeric(b["year"], errors="coerce")
    b["country_m"] = b["country"].replace(COUNTRY_MAP)
    b["nrm"] = b["city"].apply(_norm)

    # Buringh scaffold: cid, country, city, lat, lon, transport, first-nature
    bur = load_buringh()
    scaf = (bur.sort_values("year").groupby("cid")
            .agg(country=("country", "first"), city=("city", "first"),
                 lat=("lat", "first"), lon=("lon", "first"),
                 elev=("elev", "first"), transport=("transport", "first"),
                 in_hre=("in_hre", "first"), in_cne=("in_cne", "first")).reset_index())
    scaf["nrm"] = scaf["city"].apply(_norm)

    # match on (country, normalized name)
    lookup = scaf.drop_duplicates(["country", "nrm"])[["country", "nrm", "cid", "lat", "lon",
                                                        "elev", "transport", "in_hre", "in_cne"]]
    lookup = lookup.rename(columns={"country": "country_bur"})
    merged = b.drop(columns=["country"]).merge(
        lookup, left_on=["country_m", "nrm"], right_on=["country_bur", "nrm"], how="inner")
    merged = merged.rename(columns={"country_bur": "country", "city": "city"})

    # pivot to wide by year, one row per cid (max pop if dup)
    w = (merged[merged["year"].isin(years)]
         .pivot_table(index="cid", columns="year", values="pop", aggfunc="max"))
    w.columns = [f"pop{int(c)}" for c in w.columns]
    meta = (merged.groupby("cid").agg(city=("city", "first"), country=("country", "first"),
            lat=("lat", "first"), lon=("lon", "first"), elev=("elev", "first"),
            transport=("transport", "first"), in_hre=("in_hre", "first"),
            in_cne=("in_cne", "first")))
    out = meta.join(w, how="left").reset_index()
    fn = out["transport"].apply(first_nature).apply(pd.Series)
    return pd.concat([out, fn], axis=1)


if __name__ == "__main__":
    w = load_bairoch_wide()
    print("Bairoch cities matched to Buringh scaffold:", len(w))
    print("  ...in HRE core:", int(w.in_hre.sum()), "| in CNE:", int(w.in_cne.sum()))
    for y in [800, 1200, 1300, 1400, 1500]:
        c = f"pop{y}"
        if c in w:
            print(f"  {c}: {w[c].notna().sum()} cities with data (CNE: "
                  f"{w[w.in_cne][c].notna().sum()})")
    # quick agreement check vs Buringh on overlapping cities in 1500
    from panel import wide_pop
    bur = wide_pop(load_buringh())
    m = w[["cid", "pop1500"]].merge(bur[["cid", "pop1500"]], on="cid", suffixes=("_bai", "_bur"))
    m = m.dropna()
    m = m[(m.pop1500_bai > 0) & (m.pop1500_bur > 0)]
    r = np.corrcoef(np.log(m.pop1500_bai), np.log(m.pop1500_bur))[0, 1]
    print(f"\nAgreement Bairoch vs Buringh, log pop1500: r={r:.3f} (n={len(m)})")
