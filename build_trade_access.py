"""
Build TradeAccess database from Viabundus 2 (1300-1650).

Output: long-format CSV, one row per (town, benchmark year), with:
  - identity:   city_id, name, lat, lon, country, town_from, town_to, ready
  - population: inhabitants (Bairoch/Bosker, only 1300/1400/1500/1550/1600/1650)
  - geography:  distance_river_km, distance_road_km
  - fairs:      has_own_fair, own_fair_category, distance_fair_km,
                num_fairs_50km, num_fairs_100km
  - infra:      has_own_toll, has_own_staple, has_own_bridge,
                has_own_ferry, has_own_harbour
  - routes:     on_trade_route
  - composite:  trade_access_score (0-3)

Distance is straight-line geodesic km (haversine).
Time-varying: features are filtered by their From/To year for each benchmark.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

# -- paths -------------------------------------------------------------------
ROOT = Path("/Users/nikunjtyagi/HistoryResearch/docs/viabundus/Viabundus-2-csv")
OUT = Path("/Users/nikunjtyagi/HistoryResearch/output")
OUT.mkdir(parents=True, exist_ok=True)

BENCHMARKS = [1300, 1350, 1400, 1450, 1500, 1550, 1600, 1650]
EARTH_KM = 6371.0088


def to_int_year(s: pd.Series, default: int) -> pd.Series:
    """Coerce a year column with 'null', NaN, blank to int with default."""
    return pd.to_numeric(s, errors="coerce").fillna(default).astype(int)


def is_active(from_year: pd.Series, to_year: pd.Series, year: int,
              default_from: int = 1350, default_to: int = 1650) -> pd.Series:
    """Boolean mask: feature is active in `year` given its from/to bounds."""
    fy = to_int_year(from_year, default_from)
    ty = to_int_year(to_year, default_to)
    return (fy <= year) & (year <= ty)


# -- 1. Load nodes -----------------------------------------------------------
print("Loading nodes.csv ...")
nodes = pd.read_csv(ROOT / "nodes.csv", low_memory=False, na_values=["null", ""])
print(f"  {len(nodes):,} nodes total")

# Parent attributes (Town, Settlement, Staple, Fair) cascade to child nodes.
# For each child node, fill those attributes from its parent if it has one.
parent_attrs = [
    "Is_Town", "Town_From", "Town_To", "Town_Description",
    "Is_Settlement", "Settlement_From", "Settlement_To",
    "Is_Staple", "Staple_From", "Staple_To", "Staple_Duration_Of_Stay",
    "Is_Fair", "Fair_From", "Fair_To",
]
parents = nodes.set_index("id")[parent_attrs]
for col in parent_attrs:
    if col not in nodes.columns:
        continue
    inherited = nodes["parentid"].map(parents[col])
    nodes[col] = nodes[col].fillna(inherited)

# A "city" = node where Is_Town == 'y' (after parent cascade)
towns = nodes[nodes["Is_Town"] == "y"].copy()
towns["lat"] = pd.to_numeric(towns["latitude"], errors="coerce")
towns["lon"] = pd.to_numeric(towns["longitude"], errors="coerce")
towns = towns.dropna(subset=["lat", "lon"]).reset_index(drop=True)
print(f"  {len(towns):,} towns with coordinates")


# -- 2. Population pivot -----------------------------------------------------
print("Loading population.csv ...")
pop = pd.read_csv(ROOT / "population.csv", na_values=["null", ""])
# inhabitants are recorded in steps of 1000, so multiply by 1000
pop["inhabitants"] = pd.to_numeric(pop["inhabitants"], errors="coerce") * 1000
pop_wide = pop.pivot_table(
    index="nodesid", columns="year", values="inhabitants", aggfunc="first"
)
print(f"  population data for {len(pop_wide):,} nodes, years {sorted(pop_wide.columns.tolist())}")


# -- 3. Edges: rivers and roads ---------------------------------------------
print("Loading edges.csv ...")
edges = pd.read_csv(ROOT / "edges.csv", low_memory=False, na_values=["null", ""])
print(f"  {len(edges):,} edges; types: {edges['type'].value_counts().to_dict()}")

# Get coords of fromnode/tonode for each edge to build straight segments
node_coords = nodes.set_index("id")[["latitude", "longitude"]].astype(float)
edges = edges.merge(
    node_coords.rename(columns={"latitude": "from_lat", "longitude": "from_lon"}),
    left_on="fromnode", right_index=True, how="left",
)
edges = edges.merge(
    node_coords.rename(columns={"latitude": "to_lat", "longitude": "to_lon"}),
    left_on="tonode", right_index=True, how="left",
)
edges = edges.dropna(subset=["from_lat", "from_lon", "to_lat", "to_lon"])

# We approximate each edge by its midpoint for nearest-neighbour distance.
# This is fast and good enough for a 0-3 score; medieval edge segments are short.
edges["mid_lat"] = (edges["from_lat"] + edges["to_lat"]) / 2.0
edges["mid_lon"] = (edges["from_lon"] + edges["to_lon"]) / 2.0

river_edges = edges[edges["type"].isin(["river", "canal"])].reset_index(drop=True)
road_edges = edges[edges["type"] == "land"].reset_index(drop=True)
print(f"  {len(river_edges):,} river/canal edges, {len(road_edges):,} land edges")


def haversine_nearest(town_xy_rad: np.ndarray, target_xy_rad: np.ndarray) -> np.ndarray:
    """Return nearest-neighbour distance (km) from each town to the target set."""
    if len(target_xy_rad) == 0:
        return np.full(len(town_xy_rad), np.nan)
    tree = BallTree(target_xy_rad, metric="haversine")
    dist_rad, _ = tree.query(town_xy_rad, k=1)
    return dist_rad.flatten() * EARTH_KM


town_xy = np.deg2rad(towns[["lat", "lon"]].to_numpy())

print("Computing distance to nearest river/canal edge ...")
river_xy = np.deg2rad(river_edges[["mid_lat", "mid_lon"]].to_numpy())
towns["distance_river_km"] = haversine_nearest(town_xy, river_xy)

print("Computing distance to nearest land road edge ...")
road_xy = np.deg2rad(road_edges[["mid_lat", "mid_lon"]].to_numpy())
towns["distance_road_km"] = haversine_nearest(town_xy, road_xy)


# -- 4. Trade route node membership -----------------------------------------
# A town is "on a trade route" if at least one Viabundus edge touches it
# (or any of its child nodes) and is reasonably certain (certainty<=2).
print("Flagging trade-route nodes ...")
edges["certainty_int"] = pd.to_numeric(edges["certainty"], errors="coerce")
good_edges = edges[edges["certainty_int"].fillna(3) <= 2]

# parent cascade: a child node touched by an edge counts for its parent town
node_to_parent = nodes.set_index("id")["parentid"].to_dict()


def resolve_to_parent_town(node_id):
    """Walk parentid up until we find a town node, else return the node itself."""
    seen = set()
    cur = node_id
    while cur is not None and cur not in seen:
        seen.add(cur)
        if cur in town_id_set:
            return cur
        cur = node_to_parent.get(cur)
        if pd.isna(cur):
            return None
    return None


town_id_set = set(towns["id"].tolist())
edge_node_ids = pd.unique(good_edges[["fromnode", "tonode"]].values.ravel())
edge_to_town = {nid: resolve_to_parent_town(nid) for nid in edge_node_ids}
on_route_towns = {t for t in edge_to_town.values() if t is not None}
towns["on_trade_route"] = towns["id"].isin(on_route_towns).astype(int)
print(f"  {towns['on_trade_route'].sum():,} of {len(towns):,} towns sit on a Viabundus edge")


# -- 5. Fairs ---------------------------------------------------------------
print("Loading fairs.csv ...")
fairs = pd.read_csv(ROOT / "fairs.csv", low_memory=False, na_values=["null", ""])
fairs = fairs.merge(
    node_coords.rename(columns={"latitude": "fair_lat", "longitude": "fair_lon"}),
    left_on="nodesid", right_index=True, how="left",
).dropna(subset=["fair_lat", "fair_lon"])
fairs["fair_lat"] = fairs["fair_lat"].astype(float)
fairs["fair_lon"] = fairs["fair_lon"].astype(float)
print(f"  {len(fairs):,} fair entries across {fairs['nodesid'].nunique():,} nodes")

# Map each fair to its parent town (if any) so that "has_own_fair" works at town level
fair_to_town = {nid: resolve_to_parent_town(nid) for nid in fairs["nodesid"].unique()}
fairs["town_id"] = fairs["nodesid"].map(fair_to_town)


# -- 6. Build the long-format frame -----------------------------------------
print("Building long frame across benchmark years ...")
rows = []

# Pre-build per-year fair index for fast nearest-neighbour and radius counts
for year in BENCHMARKS:
    active = fairs[is_active(fairs["fromyear"], fairs["toyear"], year)].copy()
    if len(active) == 0:
        active_xy = np.empty((0, 2))
        active_tree = None
    else:
        active_xy = np.deg2rad(active[["fair_lat", "fair_lon"]].to_numpy())
        active_tree = BallTree(active_xy, metric="haversine")

    # nearest-fair distance
    if active_tree is None:
        nearest_fair_km = np.full(len(towns), np.nan)
    else:
        d, _ = active_tree.query(town_xy, k=1)
        nearest_fair_km = d.flatten() * EARTH_KM

    # count of fairs within 50 / 100 km
    if active_tree is None:
        n50 = np.zeros(len(towns), dtype=int)
        n100 = np.zeros(len(towns), dtype=int)
    else:
        n50 = active_tree.query_radius(town_xy, r=50.0 / EARTH_KM, count_only=True)
        n100 = active_tree.query_radius(town_xy, r=100.0 / EARTH_KM, count_only=True)

    # has_own_fair: any fair in `active` whose town_id == this town id
    own_fairs_year = active.dropna(subset=["town_id"])
    own_fairs_year = own_fairs_year.assign(town_id=own_fairs_year["town_id"].astype(int))
    cat_rank = {"local": 1, "regional": 2, "interregional": 3}
    own_fairs_year["cat_rank"] = own_fairs_year["category"].map(cat_rank).fillna(1).astype(int)
    own_best = own_fairs_year.groupby("town_id")["cat_rank"].max()

    # active per-attribute towns at this year
    def yes(col, fy_col, ty_col):
        return ((nodes[col] == "y") & is_active(nodes[fy_col], nodes[ty_col], year))

    toll_active_nodes = nodes[yes("Is_Toll", "Toll_From", "Toll_To")]["id"]
    staple_active_nodes = nodes[yes("Is_Staple", "Staple_From", "Staple_To")]["id"]
    bridge_active_nodes = nodes[yes("Is_Bridge", "Bridge_From", "Bridge_To")]["id"]
    ferry_active_nodes = nodes[yes("Is_Ferry", "Ferry_From", "Ferry_To")]["id"]
    harbour_active_nodes = nodes[yes("Is_Harbour", "Harbour_From", "Harbour_To")]["id"]

    def to_town_set(node_ids):
        return {resolve_to_parent_town(nid) for nid in node_ids} - {None}

    toll_towns = to_town_set(toll_active_nodes)
    staple_towns = to_town_set(staple_active_nodes)
    bridge_towns = to_town_set(bridge_active_nodes)
    ferry_towns = to_town_set(ferry_active_nodes)
    harbour_towns = to_town_set(harbour_active_nodes)

    # whether each town itself is alive in the year (Town_From <= y <= Town_To)
    town_alive = is_active(towns["Town_From"], towns["Town_To"], year).to_numpy()

    pop_year = pop_wide[year] if year in pop_wide.columns else pd.Series(dtype=float)
    pop_lookup = pop_year.to_dict()

    for i, t in towns.reset_index(drop=True).iterrows():
        if not town_alive[i]:
            continue
        tid = int(t["id"])
        own_rank = int(own_best.get(tid, 0))
        own_cat = {0: None, 1: "local", 2: "regional", 3: "interregional"}[own_rank]
        rows.append({
            "city_id": tid,
            "name": t["name"],
            "lat": t["lat"],
            "lon": t["lon"],
            "town_from": int(to_int_year(pd.Series([t["Town_From"]]), 1350).iloc[0]),
            "town_to": int(to_int_year(pd.Series([t["Town_To"]]), 1650).iloc[0]),
            "ready": t.get("ready"),
            "year": year,
            "population": pop_lookup.get(tid, np.nan),
            "distance_river_km": round(t["distance_river_km"], 3),
            "distance_road_km": round(t["distance_road_km"], 3),
            "distance_fair_km": round(float(nearest_fair_km[i]), 3),
            "num_fairs_50km": int(n50[i]),
            "num_fairs_100km": int(n100[i]),
            "has_own_fair": int(own_rank > 0),
            "own_fair_category": own_cat,
            "has_own_toll": int(tid in toll_towns),
            "has_own_staple": int(tid in staple_towns),
            "has_own_bridge": int(tid in bridge_towns),
            "has_own_ferry": int(tid in ferry_towns),
            "has_own_harbour": int(tid in harbour_towns),
            "on_trade_route": int(t["on_trade_route"]),
        })

df = pd.DataFrame(rows)
print(f"Built {len(df):,} (town, year) rows")


# -- 7. TradeAccess composite score -----------------------------------------
def score_row(r) -> int:
    """0=isolated, 1=local market, 2=regional road/river, 3=major fair/trade-route node."""
    # 3: own interregional fair, OR own staple, OR a regional fair within 25km
    if r["own_fair_category"] == "interregional":
        return 3
    if r["has_own_staple"] == 1:
        return 3
    if r["own_fair_category"] == "regional" and r["on_trade_route"] == 1:
        return 3
    # 2: on a Viabundus trade route AND river/road within 5km, OR own regional fair,
    #    OR ≥2 fairs within 50km
    if r["on_trade_route"] == 1 and (r["distance_river_km"] <= 5 or r["distance_road_km"] <= 2):
        return 2
    if r["own_fair_category"] == "regional":
        return 2
    if r["num_fairs_50km"] >= 2:
        return 2
    # 1: own local fair, OR a fair within 25km, OR a road within 10km
    if r["own_fair_category"] == "local":
        return 1
    if r["distance_fair_km"] <= 25:
        return 1
    if r["distance_road_km"] <= 10:
        return 1
    # 0: isolated
    return 0


df["trade_access_score"] = df.apply(score_row, axis=1).astype(int)


# -- 8. Write -----------------------------------------------------------------
out_path = OUT / "cities_trade_access.csv"
df.to_csv(out_path, index=False)
print(f"Wrote {out_path} ({len(df):,} rows)")

# also write a wide town-level file with one row per city, year columns side by side
wide_cols = ["population", "distance_fair_km", "num_fairs_50km", "num_fairs_100km",
             "has_own_fair", "own_fair_category", "has_own_toll", "has_own_staple",
             "has_own_bridge", "has_own_ferry", "has_own_harbour",
             "trade_access_score"]
identity = df.drop_duplicates("city_id")[
    ["city_id", "name", "lat", "lon", "town_from", "town_to",
     "distance_river_km", "distance_road_km", "on_trade_route"]
]
wide_parts = [identity.set_index("city_id")]
for col in wide_cols:
    p = df.pivot_table(index="city_id", columns="year", values=col, aggfunc="first")
    p.columns = [f"{col}_{y}" for y in p.columns]
    wide_parts.append(p)
wide = pd.concat(wide_parts, axis=1).reset_index()
wide_path = OUT / "cities_trade_access_wide.csv"
wide.to_csv(wide_path, index=False)
print(f"Wrote {wide_path} ({len(wide):,} cities)")


# -- 9. Summary --------------------------------------------------------------
print("\n=== TradeAccess score distribution by year ===")
print(df.groupby("year")["trade_access_score"].value_counts().unstack(fill_value=0))
print("\n=== Population coverage by year ===")
print(df.groupby("year")["population"].agg(["count", "mean", "max"]).round(1))
