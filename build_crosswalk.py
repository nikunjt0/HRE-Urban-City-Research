"""Build a nodesid <-> city_id crosswalk between Viabundus and Bairoch.

Outputs output/crosswalk_nodesid_cityid.csv with columns:
    nodesid, city_id, viabundus_name, bairoch_name,
    lat_v, lon_v, lat_b, lon_b, dist_km, match_method, confidence

Match stages (in priority order):
  manual : hand-verified for the 13 priority cities (lib/targets.py)
  exact  : normalized name match + within 25 km
  alt    : Viabundus alternative-name match + within 25 km
  spatial: nearest Bairoch within 10 km AND name similarity >= 0.6

Cities with no Bairoch match get city_id = NaN; downstream variable builders
treat these with imputed=True and score 0.
"""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from lib.geo import EARTH_KM
from lib.nodes_loader import load_towns
from lib.paths import CITY_LOCATIONS_CSV, CROSSWALK_CSV, VIABUNDUS
from lib.targets import PRIORITY_CITIES


def normalize_name(s: object) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # strip common HRE suffixes that vary by source
    for suf in [
        " am main", " am rhein", " ob der tauber", " an der saale",
        " an der oder", " (oder)", " (saale)", "/main", "/rhein",
        "/oder", "/saale", "(oder)", "(saale)", "(main)", "(rhein)",
    ]:
        s = s.replace(suf, "")
    # drop punctuation
    keep = "abcdefghijklmnopqrstuvwxyz0123456789 "
    s = "".join(c if c in keep else " " for c in s)
    return " ".join(s.split())


def levenshtein_ratio(a: str, b: str) -> float:
    """Cheap similarity 0-1 via dynamic programming (no external lib)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j - 1], dp[j])
            prev = cur
    return 1 - dp[n] / max(m, n)


def main():
    print("Loading Viabundus towns ...")
    towns, _, _ = load_towns()
    towns = towns[["id", "name", "lat", "lon"]].rename(columns={
        "id": "nodesid", "name": "viabundus_name", "lat": "lat_v", "lon": "lon_v",
    }).copy()
    towns["viabundus_norm"] = towns["viabundus_name"].apply(normalize_name)
    print(f"  {len(towns):,} Viabundus towns")

    print("Loading Bairoch city_locations ...")
    bairoch = pd.read_csv(CITY_LOCATIONS_CSV)
    bairoch = bairoch[["city_id", "name", "name_alt", "name_foreign",
                       "latitude", "longitude"]].rename(columns={
        "name": "bairoch_name", "latitude": "lat_b", "longitude": "lon_b",
    }).copy()
    bairoch["bairoch_norm"] = bairoch["bairoch_name"].apply(normalize_name)
    bairoch["alt_norm"] = bairoch["name_alt"].apply(normalize_name)
    bairoch["foreign_norm"] = bairoch["name_foreign"].apply(normalize_name)
    print(f"  {len(bairoch):,} Bairoch cities")

    print("Loading Viabundus alternativenames ...")
    altnames = pd.read_csv(VIABUNDUS / "alternativenames.csv", na_values=["null", ""])
    altnames["alt_norm"] = altnames["name"].apply(normalize_name)
    altnames = altnames.dropna(subset=["nodesid"])
    altnames["nodesid"] = altnames["nodesid"].astype(int)
    print(f"  {len(altnames):,} Viabundus alt-name records")

    matches = {}  # nodesid -> dict(city_id, ..., match_method, confidence)

    # ------ Stage D: manual overrides (highest precedence) -----------------
    name_lookup = bairoch.set_index("city_id")
    for display_name, bairoch_id, nodesid in PRIORITY_CITIES:
        if nodesid is None or pd.isna(nodesid):
            continue
        if bairoch_id not in name_lookup.index:
            continue
        b = name_lookup.loc[bairoch_id]
        v = towns[towns["nodesid"] == nodesid]
        if v.empty:
            continue
        v = v.iloc[0]
        d_km = haversine_km(v["lat_v"], v["lon_v"], b["lat_b"], b["lon_b"])
        matches[int(nodesid)] = {
            "nodesid": int(nodesid),
            "city_id": int(bairoch_id),
            "viabundus_name": v["viabundus_name"],
            "bairoch_name": b["bairoch_name"],
            "lat_v": v["lat_v"], "lon_v": v["lon_v"],
            "lat_b": b["lat_b"], "lon_b": b["lon_b"],
            "dist_km": d_km,
            "match_method": "manual",
            "confidence": 1.00,
        }

    def remaining():
        return towns[~towns["nodesid"].isin(matches)]

    # ------ Stage A: exact normalized name + lat/lon <= 25 km --------------
    print("Stage A: exact normalized-name match + 25 km tolerance ...")
    bairoch_lookup = {}
    for _, r in bairoch.iterrows():
        for k in [r["bairoch_norm"], r["alt_norm"], r["foreign_norm"]]:
            if k:
                bairoch_lookup.setdefault(k, []).append(r)

    for _, t in remaining().iterrows():
        cands = bairoch_lookup.get(t["viabundus_norm"], [])
        best = None
        best_d = 1e9
        for c in cands:
            d = haversine_km(t["lat_v"], t["lon_v"], c["lat_b"], c["lon_b"])
            if d <= 25 and d < best_d:
                best_d, best = d, c
        if best is not None:
            matches[int(t["nodesid"])] = {
                "nodesid": int(t["nodesid"]),
                "city_id": int(best["city_id"]),
                "viabundus_name": t["viabundus_name"],
                "bairoch_name": best["bairoch_name"],
                "lat_v": t["lat_v"], "lon_v": t["lon_v"],
                "lat_b": best["lat_b"], "lon_b": best["lon_b"],
                "dist_km": best_d,
                "match_method": "exact",
                "confidence": 0.95,
            }

    # ------ Stage B: Viabundus alt-name match + 25 km ----------------------
    print("Stage B: Viabundus alt-name match + 25 km tolerance ...")
    alt_by_node = altnames.groupby("nodesid")["alt_norm"].apply(set).to_dict()
    for _, t in remaining().iterrows():
        nid = int(t["nodesid"])
        alts = alt_by_node.get(nid, set())
        best = None
        best_d = 1e9
        for a in alts:
            for c in bairoch_lookup.get(a, []):
                d = haversine_km(t["lat_v"], t["lon_v"], c["lat_b"], c["lon_b"])
                if d <= 25 and d < best_d:
                    best_d, best = d, c
        if best is not None:
            matches[nid] = {
                "nodesid": nid,
                "city_id": int(best["city_id"]),
                "viabundus_name": t["viabundus_name"],
                "bairoch_name": best["bairoch_name"],
                "lat_v": t["lat_v"], "lon_v": t["lon_v"],
                "lat_b": best["lat_b"], "lon_b": best["lon_b"],
                "dist_km": best_d,
                "match_method": "alt",
                "confidence": 0.85,
            }

    # ------ Stage C: spatial nearest within 10 km + name similarity >= 0.6 -
    print("Stage C: spatial nearest within 10 km + name similarity ...")
    bairoch_xy = np.deg2rad(bairoch[["lat_b", "lon_b"]].to_numpy())
    tree = BallTree(bairoch_xy, metric="haversine")
    rem = remaining().reset_index(drop=True)
    if len(rem) > 0:
        rem_xy = np.deg2rad(rem[["lat_v", "lon_v"]].to_numpy())
        # query nearest 5 candidates and pick the best with name sim >= 0.6
        d_rad, idx = tree.query(rem_xy, k=min(5, len(bairoch)))
        d_km = d_rad * EARTH_KM
        for i, t in rem.iterrows():
            best = None
            for k in range(d_km.shape[1]):
                if d_km[i, k] > 10:
                    break
                c = bairoch.iloc[idx[i, k]]
                sim = max(
                    levenshtein_ratio(t["viabundus_norm"], c["bairoch_norm"]),
                    levenshtein_ratio(t["viabundus_norm"], c["alt_norm"]),
                    levenshtein_ratio(t["viabundus_norm"], c["foreign_norm"]),
                )
                if sim >= 0.6:
                    best = (c, d_km[i, k], sim)
                    break
            if best is not None:
                c, dkm, sim = best
                matches[int(t["nodesid"])] = {
                    "nodesid": int(t["nodesid"]),
                    "city_id": int(c["city_id"]),
                    "viabundus_name": t["viabundus_name"],
                    "bairoch_name": c["bairoch_name"],
                    "lat_v": t["lat_v"], "lon_v": t["lon_v"],
                    "lat_b": c["lat_b"], "lon_b": c["lon_b"],
                    "dist_km": dkm,
                    "match_method": "spatial",
                    "confidence": round(sim, 2),
                }

    # ------ Output ---------------------------------------------------------
    out = pd.DataFrame(list(matches.values()))
    # also write rows for unmatched Viabundus towns (city_id NaN)
    unmatched = towns[~towns["nodesid"].isin(matches)][[
        "nodesid", "viabundus_name", "lat_v", "lon_v"
    ]].assign(city_id=np.nan, bairoch_name=np.nan, lat_b=np.nan, lon_b=np.nan,
              dist_km=np.nan, match_method="unmatched", confidence=0.0)
    out = pd.concat([out, unmatched], ignore_index=True, sort=False)
    out = out[[
        "nodesid", "city_id", "viabundus_name", "bairoch_name",
        "lat_v", "lon_v", "lat_b", "lon_b",
        "dist_km", "match_method", "confidence",
    ]]
    out.to_csv(CROSSWALK_CSV, index=False)
    print(f"\nWrote {CROSSWALK_CSV} ({len(out):,} rows)")
    print("\n=== Match-method counts ===")
    print(out["match_method"].value_counts())
    print(f"\n  matched: {(out['city_id'].notna()).sum():,}/{len(out):,}")

    # Sanity: priority cities should all be in the crosswalk with their nodesid
    print("\n=== Priority-city verification ===")
    cw_by_node = out.set_index("nodesid")
    for display_name, bairoch_id, nodesid in PRIORITY_CITIES:
        if nodesid is None:
            print(f"  {display_name}: bairoch_id={bairoch_id} (no Viabundus node)")
            continue
        row = cw_by_node.loc[int(nodesid)] if int(nodesid) in cw_by_node.index else None
        if row is None:
            print(f"  {display_name}: NOT FOUND in crosswalk!")
        else:
            print(f"  {display_name}: nodesid={int(nodesid)} -> "
                  f"city_id={row['city_id']:.0f} via {row['match_method']} "
                  f"({row['dist_km']:.1f} km)")


def haversine_km(lat1, lon1, lat2, lon2):
    if pd.isna(lat1) or pd.isna(lat2):
        return float("nan")
    lat1, lon1, lat2, lon2 = map(np.deg2rad, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(a))


if __name__ == "__main__":
    main()
