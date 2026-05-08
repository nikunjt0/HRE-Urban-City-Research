"""Build the AgriculturalSurplus 0-3 variable per (city, benchmark year).

This is a **proxy** score. /docs has no soil-quality, grain-price, or tithe
dataset, so the score combines:
  - population presence/growth as outcome proxy (Bairoch/Bosker xlsx)
  - latitude band as crude climate/soil proxy (south Germany > north)
  - distance to nearest river edge for grain-import capacity (Viabundus edges)
  - elevation when available (mountain cities have weaker hinterland)

Score:
  3: river<=10 AND south-band AND population growing 50yr
  2: (river<=15 AND not north-band) OR population growing 50yr OR pop>=5000
  1: river<=30 OR pop>=2000
  0: cold-and-landlocked-and-small
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lib.crosswalk import attach_nodesid
from lib.geo import EARTH_KM, haversine_nearest
from lib.paths import (BENCHMARKS, CITY_LOCATIONS_CSV, EU_POP_XLSX, TOWNCHARTER_CSV,
                       VIABUNDUS)
from lib.scoring import write_long_and_wide


def main():
    print("Loading city_locations ...")
    cities = pd.read_csv(CITY_LOCATIONS_CSV)
    cities = cities[["city_id", "name", "latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"})
    print(f"  {len(cities):,} cities")

    print("Loading Bosker/Bairoch population xlsx ...")
    pop = pd.read_excel(EU_POP_XLSX, engine="openpyxl", sheet_name=0)
    pop = pop.rename(columns={
        "city": "city_name",
        "year": "year",
        "inhabitants in 000-s": "pop_000",
        "latitude in degrees": "p_lat",
        "longitude in degrees": "p_lon",
        "elevation in m": "elev_m",
        "country": "country",
    })
    pop = pop[["city_name", "country", "p_lat", "p_lon", "elev_m", "year", "pop_000"]].copy()
    # Bosker xlsx uses European decimal separator (comma). Convert before coercion.
    for col in ["p_lat", "p_lon", "pop_000", "elev_m"]:
        pop[col] = pop[col].apply(
            lambda v: str(v).replace(",", ".") if isinstance(v, str) else v)
        pop[col] = pd.to_numeric(pop[col], errors="coerce")
    # Drop coords that are obviously bad (e.g. lat > 90 from typos)
    pop = pop[(pop["p_lat"].between(35, 72)) & (pop["p_lon"].between(-15, 45))]
    pop = pop.dropna(subset=["p_lat", "p_lon", "year"])
    print(f"  {len(pop):,} (city, year) pop rows; "
          f"years available: {sorted(pop['year'].dropna().unique().tolist())[:8]} ...")

    # Match Bosker rows to Bairoch city_ids using name + spatial (<=15 km).
    # Pure nearest-neighbor matches the wrong city when suburbs share Bosker's
    # round-rounded coords (e.g. Augsburg → Goeggingen). Pull k=10 candidates,
    # then pick the closest one whose name fuzzy-matches.
    print("Joining Bosker pop -> Bairoch city_id (name + spatial) ...")
    import unicodedata
    def norm(s):
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return ""
        s = str(s).lower()
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        for tok in [" am main", " am rhein", "(oder)", "/main", "(main)", " ob der tauber"]:
            s = s.replace(tok, "")
        return "".join(c for c in s if c.isalnum())

    cities_b = cities.copy()
    cities_b["b_norm"] = cities_b["name"].apply(norm)
    pop["bosker_norm"] = pop["city_name"].apply(norm)

    from sklearn.neighbors import BallTree
    bx = np.deg2rad(cities_b[["lat", "lon"]].to_numpy())
    bt = BallTree(bx, metric="haversine")
    K = min(10, len(cities_b))
    p_xy = np.deg2rad(pop[["p_lat", "p_lon"]].to_numpy())
    d_rad, idx = bt.query(p_xy, k=K)
    d_km = d_rad * EARTH_KM

    matched_ids = []
    matched_dist = []
    for i, n in enumerate(pop["bosker_norm"].values):
        chosen, chosen_d = None, None
        # 1st pass: name match within 15 km
        for k in range(K):
            if d_km[i, k] > 15:
                break
            if cities_b.iloc[idx[i, k]]["b_norm"].startswith(n) or n.startswith(cities_b.iloc[idx[i, k]]["b_norm"]):
                chosen = cities_b.iloc[idx[i, k]]["city_id"]
                chosen_d = d_km[i, k]
                break
        # 2nd pass: nearest within 5 km (no name check; rural matches)
        if chosen is None and d_km[i, 0] <= 5:
            chosen = cities_b.iloc[idx[i, 0]]["city_id"]
            chosen_d = d_km[i, 0]
        matched_ids.append(chosen if chosen is not None else np.nan)
        matched_dist.append(chosen_d if chosen_d is not None else np.nan)
    pop["matched_city_id"] = matched_ids
    pop["dist_km"] = matched_dist
    pop_match = pop.dropna(subset=["matched_city_id"]).copy()
    pop_match["matched_city_id"] = pop_match["matched_city_id"].astype(int)
    print(f"  {len(pop_match):,} pop rows matched "
          f"({pop_match['matched_city_id'].nunique():,} unique cities)")
    pop_match["pop_pers"] = pop_match["pop_000"] * 1000

    # Build a (city_id, year) -> pop dict, picking max pop value per pair
    pop_lookup = pop_match.groupby(["matched_city_id", "year"])["pop_pers"].max().to_dict()

    # Elevation per Bairoch city (best-effort from Bosker, take min dist match)
    elev_lookup = pop_match.dropna(subset=["elev_m"]).sort_values("dist_km") \
        .drop_duplicates("matched_city_id").set_index("matched_city_id")["elev_m"].to_dict()

    print("Loading Viabundus edges (rivers/canals) ...")
    edges = pd.read_csv(VIABUNDUS / "edges.csv", low_memory=False, na_values=["null", ""])
    nodes = pd.read_csv(VIABUNDUS / "nodes.csv", low_memory=False, na_values=["null", ""])
    nc = nodes.set_index("id")[["latitude", "longitude"]].astype(float)
    edges = edges.merge(nc.rename(columns={"latitude": "fl", "longitude": "fn"}),
                        left_on="fromnode", right_index=True, how="left")
    edges = edges.merge(nc.rename(columns={"latitude": "tl", "longitude": "tn"}),
                        left_on="tonode", right_index=True, how="left").dropna(
        subset=["fl", "fn", "tl", "tn"])
    edges["mid_lat"] = (edges["fl"] + edges["tl"]) / 2.0
    edges["mid_lon"] = (edges["fn"] + edges["tn"]) / 2.0
    river = edges[edges["type"].isin(["river", "canal"])].reset_index(drop=True)
    print(f"  {len(river):,} river/canal edges")

    print("Computing distance from each city to nearest river ...")
    city_xy = np.deg2rad(cities[["lat", "lon"]].to_numpy())
    river_xy = np.deg2rad(river[["mid_lat", "mid_lon"]].to_numpy())
    cities["dist_river_km"] = haversine_nearest(city_xy, river_xy)

    # Voronoi cell area (km^2) — proxy for agricultural hinterland independent
    # of own population. Cells unbounded at the convex hull of the city set
    # get the within-region mean. Clipped to a generous HRE bounding box.
    print("Computing Voronoi hinterland area for each city ...")
    from scipy.spatial import Voronoi  # type: ignore
    BBOX = (45.0, 55.0, 5.0, 20.0)  # (lat_min, lat_max, lon_min, lon_max)
    # Use lat/lon directly for area computation, then convert with a coarse
    # cos(lat)-corrected scaling. Good enough for a rank-preserving feature.
    pts = cities[["lon", "lat"]].to_numpy()
    vor = Voronoi(pts)
    voronoi_area = np.full(len(cities), np.nan)
    for i, region_idx in enumerate(vor.point_region):
        region = vor.regions[region_idx]
        if len(region) == 0 or -1 in region:
            continue  # unbounded cell at convex hull
        verts = vor.vertices[region]
        # Reject cells with vertices well outside the bounding box
        if (verts[:, 1].min() < BBOX[0] - 5 or verts[:, 1].max() > BBOX[1] + 5 or
                verts[:, 0].min() < BBOX[2] - 5 or verts[:, 0].max() > BBOX[3] + 5):
            continue
        # Shoelace area in degrees^2, then convert (1° lat ≈ 111 km)
        x = verts[:, 0]
        y = verts[:, 1]
        area_deg2 = 0.5 * abs(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
        lat_mean = float(verts[:, 1].mean())
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * np.cos(np.deg2rad(lat_mean))
        area_km2 = area_deg2 * km_per_deg_lat * km_per_deg_lon
        voronoi_area[i] = area_km2
    # Cap at 99th percentile to neutralize huge boundary cells; impute mean.
    finite = np.isfinite(voronoi_area)
    if finite.any():
        cap = np.nanquantile(voronoi_area[finite], 0.99)
        voronoi_area[finite & (voronoi_area > cap)] = cap
        mean_area = float(np.nanmean(voronoi_area[finite]))
        voronoi_area[~finite] = mean_area
    cities["voronoi_area_km2"] = voronoi_area
    print(f"  Voronoi area: median={np.nanmedian(voronoi_area):.0f} km², "
          f"max={np.nanmax(voronoi_area):.0f} km²")

    # Earliest-mention year per city — the substrate for "centuries since
    # first mention", a proxy for established cleared/cultivated hinterland.
    print("Loading earliest-mention year per city from towncharter ...")
    ch = pd.read_csv(TOWNCHARTER_CSV)
    ch["time_point"] = pd.to_numeric(ch["time_point"], errors="coerce")
    ch["type_origin"] = pd.to_numeric(ch["type_origin"], errors="coerce")
    ch = ch.dropna(subset=["time_point", "city_id"])
    fm = ch[ch["type_origin"] == 5].groupby("city_id")["time_point"].min().to_dict()
    # Fall back to any earliest charter event when type_origin==5 missing
    any_earliest = ch.groupby("city_id")["time_point"].min().to_dict()
    print(f"  {len(fm):,} cities with type_origin==5 first mention; "
          f"{len(any_earliest):,} with any charter event")

    print("Building per-(city, year) frame ...")
    # Pre-compute the closest available pop for each city across benchmark years
    # so we can interpolate (Bosker years are 700,800,900,...,1200,1300,1400,1500
    # - so 1250/1350/1450 fall between two known points).
    bosker_years = sorted({y for (_, y) in pop_lookup.keys()})

    def pop_at(cid: int, y: int) -> float:
        """Linear interpolation between Bosker benchmark years (max gap 100 yr)."""
        if (cid, y) in pop_lookup:
            return pop_lookup[(cid, y)]
        # find nearest below and nearest above
        below = [yy for yy in bosker_years if yy <= y and (cid, yy) in pop_lookup]
        above = [yy for yy in bosker_years if yy >= y and (cid, yy) in pop_lookup]
        if not below or not above:
            return np.nan
        b, a = below[-1], above[0]
        if b == a:
            return pop_lookup[(cid, b)]
        if a - b > 100:
            return np.nan
        # linear
        pb, pa = pop_lookup[(cid, b)], pop_lookup[(cid, a)]
        frac = (y - b) / (a - b)
        return pb + frac * (pa - pb)

    rows = []
    for y in BENCHMARKS:
        prev_y = y - 50
        for _, c in cities.iterrows():
            cid = int(c["city_id"])
            lat = c["lat"]
            lat_band = "south" if lat < 49.0 else ("middle" if lat < 51.5 else "north")
            d_river = c["dist_river_km"]
            elev = elev_lookup.get(cid, np.nan)
            varea = float(c["voronoi_area_km2"]) if np.isfinite(c["voronoi_area_km2"]) else np.nan

            pop_y = pop_at(cid, y)
            pop_prev = pop_at(cid, prev_y)
            growth = ((pop_y / pop_prev) if (np.isfinite(pop_y) and np.isfinite(pop_prev)
                                             and pop_prev > 0) else np.nan)
            growing = bool(np.isfinite(growth) and growth > 1.05)

            # Population thresholds: 20k+ means a city was clearly being fed
            # well; 10k+ is a serious city; 3k+ a working town.
            very_big = bool(np.isfinite(pop_y) and pop_y >= 20000)
            big = bool(np.isfinite(pop_y) and pop_y >= 10000)
            mid = bool(np.isfinite(pop_y) and pop_y >= 3000)
            high_elev_penalty = bool(np.isfinite(elev) and elev > 600)

            # Note: Viabundus river edges only cover northern/western Europe.
            # Southern German cities (Augsburg, Ulm) often show "no river" but
            # actually sit on the Lech / Danube. Use river distance only as a
            # POSITIVE bonus, never as a penalty.
            river_bonus = bool(np.isfinite(d_river) and d_river <= 15)

            # Legacy 0-3 score (kept for the report's tier maps and the
            # heuristic composite). Uses population thresholds — DO NOT feed
            # this into the predictive model: it leaks the outcome.
            if very_big or (big and growing):
                score = 3
            elif big or (mid and (river_bonus or growing)) or (river_bonus and lat_band != "north"):
                score = 2
            elif mid or river_bonus:
                score = 1
            else:
                score = 0
            if high_elev_penalty and score > 0:
                score = max(0, score - 1)

            # Continuous (population-free) score for the predictive model.
            # All inputs are pre-determined relative to outcome:
            #   * voronoi_area_km2: agricultural catchment, structural
            #   * centuries_since_first_mention: cleared/cultivated land age
            #   * river distance, elevation, lat band: geography
            fm_y = fm.get(cid, any_earliest.get(cid, np.nan))
            if np.isfinite(fm_y):
                cent_since = max(0.0, min(8.0, (y - float(fm_y)) / 100.0))
            else:
                cent_since = 0.0
            varea_term = math.log1p(varea) if (varea is not None and np.isfinite(varea)) else 0.0
            river_term = (max(0.0, 1.0 - (float(d_river) / 40.0))
                          if np.isfinite(d_river) else 0.0)
            elev_term = (max(0.0, (float(elev) - 400.0) / 600.0)
                         if np.isfinite(elev) else 0.0)
            lat_south = 1.0 if lat_band == "south" else 0.0
            lat_north = 1.0 if lat_band == "north" else 0.0
            agri_continuous = (
                0.4 * varea_term
                + 0.3 * cent_since
                + 0.5 * river_term
                - 0.4 * elev_term
                + 0.2 * lat_south
                - 0.2 * lat_north
            )

            rows.append({
                "city_id": cid,
                "name": c["name"],
                "lat": c["lat"],
                "lon": c["lon"],
                "year": y,
                "lat_band": lat_band,
                "dist_river_km": (round(float(d_river), 1) if np.isfinite(d_river) else np.nan),
                "elev_m": (round(float(elev), 0) if np.isfinite(elev) else np.nan),
                "voronoi_area_km2": (round(float(varea), 1) if np.isfinite(varea) else np.nan),
                "centuries_since_first_mention": round(cent_since, 2),
                "population": (int(pop_y) if np.isfinite(pop_y) else np.nan),
                "pop_growth_50yr": (round(float(growth), 3) if np.isfinite(growth) else np.nan),
                "agricultural_surplus_score": score,
                "agricultural_surplus_continuous": round(float(agri_continuous), 4),
            })

    df = pd.DataFrame(rows)
    df = attach_nodesid(df)
    print(f"Built {len(df):,} (city, year) rows")

    feat = ["lat_band", "dist_river_km", "elev_m", "voronoi_area_km2",
            "centuries_since_first_mention", "population", "pop_growth_50yr",
            "agricultural_surplus_continuous"]
    long_path, wide_path = write_long_and_wide(
        df, "agricultural_surplus", feat, "agricultural_surplus_score")
    print(f"Wrote {long_path}")
    print(f"Wrote {wide_path}")
    print("\n=== agricultural_surplus_score by year ===")
    print(df.groupby("year")["agricultural_surplus_score"].value_counts().unstack(fill_value=0))


if __name__ == "__main__":
    main()
