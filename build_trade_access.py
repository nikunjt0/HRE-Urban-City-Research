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
        d_river = float(t["distance_river_km"]) if np.isfinite(t["distance_river_km"]) else np.inf
        d_road = float(t["distance_road_km"]) if np.isfinite(t["distance_road_km"]) else np.inf
        # Continuous (pre-bucket) trade-access signal — GEOGRAPHIC connectivity
        # only. Institutional signal (own fair tier, own staple, Hanseatic
        # status, Messe presence) lives in merchant_capital_continuous; sharing
        # those terms here would reproduce the 0.89 multicollinearity that
        # made trade_access's coefficient flip negative in the fitted model.
        ta_continuous = (
            1.5 * float(int(t["on_trade_route"]))
            + 0.7 * math.log1p(int(n50[i]))
            + 0.7 * max(0.0, 1.0 - (d_river / 30.0))
            + 0.5 * max(0.0, 1.0 - (d_road / 15.0))
        )
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
            "trade_access_continuous": round(float(ta_continuous), 4),
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
             "trade_access_score", "trade_access_continuous"]
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


# -- 10. Bairoch-keyed output with south-German fallback ---------------------
# The Viabundus network does not cover southern Germany (Augsburg, Ulm,
# Würzburg, Regensburg, Bamberg, Speyer, Rothenburg). Joining the
# Viabundus-keyed `df` to Bairoch via the crosswalk drops those cities
# silently — `build_composite.py` then fills 0 and the predictive model
# learns that southern cities are always zero-trade. Fix: compute a
# fallback `trade_access_continuous` for every Bairoch city without a
# Viabundus nodesid, using haversine distances to the same fair / staple
# / river points the Viabundus path used. Output a Bairoch-keyed file so
# the predictive model can ingest it directly without going through the
# nodesid join.
print("\n=== Building Bairoch-keyed trade_access (with south-German fallback) ===")

CW_PATH = OUT / "crosswalk_nodesid_cityid.csv"
CITY_LOC_PATH = Path("/Users/nikunjtyagi/HistoryResearch/docs/city_locations_and_border_maps/dataverse_files/city_locations.csv")
MARKETS_PATH = Path("/Users/nikunjtyagi/HistoryResearch/docs/markets/markets_data/markets.csv")

if not CW_PATH.exists():
    print(f"  WARNING: {CW_PATH} missing — skipping Bairoch-keyed output. "
          f"Run build_crosswalk.py first.")
else:
    cw = pd.read_csv(CW_PATH)
    cw = cw.dropna(subset=["city_id", "nodesid"]).drop_duplicates("nodesid")
    cw["city_id"] = cw["city_id"].astype(int)
    cw["nodesid"] = cw["nodesid"].astype(int)
    node_to_city = cw.set_index("nodesid")["city_id"].to_dict()

    # Bairoch master gazetteer
    bcities = pd.read_csv(CITY_LOC_PATH)
    bcities = bcities[["city_id", "name", "latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"})
    bcities = bcities.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    bcities["city_id"] = bcities["city_id"].astype(int)

    # Viabundus path: for each (city_id, year) where a nodesid exists, take the
    # Viabundus-derived continuous value
    df_via = df.copy()
    df_via["bairoch_id"] = df_via["city_id"].map(node_to_city)
    df_via = df_via.dropna(subset=["bairoch_id"]).copy()
    df_via["bairoch_id"] = df_via["bairoch_id"].astype(int)
    df_via = df_via[["bairoch_id", "year", "trade_access_continuous",
                     "trade_access_score", "distance_river_km",
                     "distance_road_km", "distance_fair_km",
                     "num_fairs_50km", "has_own_staple", "on_trade_route"]] \
        .rename(columns={"bairoch_id": "city_id"})
    # Multiple Viabundus nodes (gate, harbour, fair, parent town) can map to
    # the same Bairoch city. Collapse to one row per (city_id, year) by
    # keeping the row with the strongest signal (max trade_access_continuous);
    # break ties by max trade_access_score.
    df_via = (df_via.sort_values(["trade_access_continuous", "trade_access_score"],
                                  ascending=False)
                    .drop_duplicates(["city_id", "year"], keep="first")
                    .reset_index(drop=True))
    df_via["trade_access_source"] = "viabundus"
    via_keys = set(zip(df_via["city_id"], df_via["year"]))
    print(f"  Viabundus-keyed rows for Bairoch cities: {len(df_via):,} "
          f"({df_via['city_id'].nunique():,} unique cities; "
          f"deduped to one row per (city, year))")

    # Fallback path: for Bairoch cities NOT in `via_keys` at each benchmark year
    # we compute trade_access_continuous purely from Bairoch lat/lon and the
    # Viabundus fair/staple/river point clouds.
    bcity_xy = np.deg2rad(bcities[["lat", "lon"]].to_numpy())

    # Fair locations are time-varying — re-derive per year
    fairs_by_year_xy = {}
    fairs_by_year_n50 = {}
    for y in BENCHMARKS:
        active = fairs[is_active(fairs["fromyear"], fairs["toyear"], y)].copy()
        if len(active) == 0:
            fairs_by_year_xy[y] = (None, np.zeros(len(bcities)),
                                   np.full(len(bcities), np.nan),
                                   np.full(len(bcities), 0))
            continue
        axy = np.deg2rad(active[["fair_lat", "fair_lon"]].to_numpy())
        tree = BallTree(axy, metric="haversine")
        d, _ = tree.query(bcity_xy, k=1)
        nearest = d.flatten() * EARTH_KM
        n50 = tree.query_radius(bcity_xy, r=50.0 / EARTH_KM, count_only=True)
        # interregional-only tree for own-rank fallback
        intr = active[active["category"] == "interregional"]
        own_rank_arr = np.zeros(len(bcities), dtype=float)
        if len(intr) > 0:
            ixy = np.deg2rad(intr[["fair_lat", "fair_lon"]].to_numpy())
            ix_tree = BallTree(ixy, metric="haversine")
            id_, _ = ix_tree.query(bcity_xy, k=1)
            # treat "interregional fair within 5 km" as own_rank = 3 fallback
            close = (id_.flatten() * EARTH_KM) <= 5.0
            own_rank_arr[close] = 3.0
        regional = active[active["category"] == "regional"]
        if len(regional) > 0:
            rxy = np.deg2rad(regional[["fair_lat", "fair_lon"]].to_numpy())
            rt = BallTree(rxy, metric="haversine")
            rd, _ = rt.query(bcity_xy, k=1)
            close = (rd.flatten() * EARTH_KM) <= 5.0
            own_rank_arr[(own_rank_arr == 0) & close] = 2.0
        fairs_by_year_xy[y] = (own_rank_arr, n50, nearest, None)

    # Markets / Messe presence as a south-German fair signal (Bairoch markets.csv
    # is the authoritative source for southern German Jahrmärkte not in Viabundus).
    if MARKETS_PATH.exists():
        mk = pd.read_csv(MARKETS_PATH)
        mk = mk[mk["time_point"] <= 1600].copy()
        mk_messe = mk[mk["type_market"] == 6].groupby("city_id")["time_point"].min().to_dict()
        mk_any = mk.groupby("city_id")["time_point"].min().to_dict()
        print(f"  loaded {len(mk_messe):,} cities with Messe (annual fair) for fallback")
    else:
        mk_messe = {}
        mk_any = {}

    # Distance-to-Viabundus-river-edge for Bairoch cities (a coarse proxy
    # for navigable-water access; misses the Danube/Lech/Main/Neckar but
    # we mitigate by giving south-German cities an explicit small uplift).
    river_xy_b = np.deg2rad(river_edges[["mid_lat", "mid_lon"]].to_numpy())
    river_tree_b = BallTree(river_xy_b, metric="haversine")
    rd_b, _ = river_tree_b.query(bcity_xy, k=1)
    river_dist_km_b = rd_b.flatten() * EARTH_KM

    # Hand-coded set of large south-German rivers (Danube, Lech, Main,
    # Neckar) approximated by a few coordinate samples along each. This
    # closes the systematic Viabundus gap without new data collection.
    SOUTH_GERMAN_RIVER_POINTS = [
        # Danube (Donau): Ulm, Donauwörth, Regensburg, Passau
        (48.4011, 9.9876), (48.7180, 10.7747), (49.0134, 12.1016), (48.5667, 13.4319),
        # Lech: Augsburg, Landsberg
        (48.3705, 10.8978), (48.0521, 10.8810),
        # Main: Würzburg, Bamberg, Frankfurt, Aschaffenburg
        (49.7913, 9.9534), (49.8988, 10.9028), (50.1109, 8.6821), (49.9769, 9.1437),
        # Neckar: Heilbronn, Stuttgart, Tübingen
        (49.1427, 9.2109), (48.7758, 9.1829), (48.5216, 9.0576),
    ]
    sg_xy = np.deg2rad(np.array(SOUTH_GERMAN_RIVER_POINTS))
    sg_tree = BallTree(sg_xy, metric="haversine")
    sd_b, _ = sg_tree.query(bcity_xy, k=1)
    sg_river_dist_b = sd_b.flatten() * EARTH_KM
    # combined river distance: min of Viabundus rivers and the south-German set
    river_dist_combined = np.minimum(river_dist_km_b, sg_river_dist_b)

    fallback_rows = []
    bcity_records = bcities.to_dict("records")
    for y in BENCHMARKS:
        own_rank_arr, n50_arr, nearest_arr, _ = fairs_by_year_xy[y]
        for i, c in enumerate(bcity_records):
            cid = int(c["city_id"])
            if (cid, y) in via_keys:
                continue  # Viabundus already supplies this row
            d_river = float(river_dist_combined[i])
            n50 = int(n50_arr[i])
            own_rank = float(own_rank_arr[i]) if own_rank_arr is not None else 0.0
            d_fair = float(nearest_arr[i]) if np.isfinite(nearest_arr[i]) else np.nan
            # Markets-based Messe uplift (south-German cities get this boost)
            has_messe = (
                cid in mk_messe and float(mk_messe[cid]) <= y
            )
            has_market = cid in mk_any and float(mk_any[cid]) <= y
            # Geographic-only (matches the Viabundus path; institutional signal
            # belongs to merchant_capital). Cities not in Viabundus have no
            # `on_trade_route` flag, so this term is 0 by construction.
            ta_continuous = (
                0.7 * math.log1p(n50)
                + 0.7 * max(0.0, 1.0 - (d_river / 30.0))
            )
            # Crude 0-3 score for backward compat with build_composite.py
            if own_rank >= 3 or has_messe and own_rank >= 2:
                fb_score = 3
            elif own_rank >= 2 or has_messe or n50 >= 2:
                fb_score = 2
            elif own_rank >= 1 or (np.isfinite(d_fair) and d_fair <= 25) or has_market:
                fb_score = 1
            else:
                fb_score = 0
            fallback_rows.append({
                "city_id": cid,
                "year": y,
                "trade_access_continuous": round(float(ta_continuous), 4),
                "trade_access_score": fb_score,
                "distance_river_km": round(d_river, 3),
                "distance_road_km": np.nan,
                "distance_fair_km": (round(d_fair, 3) if np.isfinite(d_fair) else np.nan),
                "num_fairs_50km": n50,
                "has_own_staple": 0,
                "on_trade_route": 0,
                "trade_access_source": "fallback",
            })

    df_fb = pd.DataFrame(fallback_rows)
    print(f"  Fallback rows for non-Viabundus Bairoch cities: {len(df_fb):,} "
          f"({df_fb['city_id'].nunique() if len(df_fb) else 0:,} unique cities)")

    # Stitch together: Viabundus rows + fallback rows
    df_bairoch = pd.concat([df_via, df_fb], ignore_index=True, sort=False)
    df_bairoch = df_bairoch.merge(
        bcities[["city_id", "name", "lat", "lon"]],
        on="city_id", how="left",
    )
    cols_order = ["city_id", "name", "lat", "lon", "year",
                  "trade_access_continuous", "trade_access_score",
                  "distance_river_km", "distance_road_km",
                  "distance_fair_km", "num_fairs_50km",
                  "has_own_staple", "on_trade_route",
                  "trade_access_source"]
    df_bairoch = df_bairoch[[c for c in cols_order if c in df_bairoch.columns]]
    out_b = OUT / "cities_trade_access_bairoch.csv"
    df_bairoch.to_csv(out_b, index=False)
    print(f"  Wrote {out_b} ({len(df_bairoch):,} rows; "
          f"sources: {df_bairoch['trade_access_source'].value_counts().to_dict()})")
    print("\n=== trade_access_continuous distribution by source ===")
    print(df_bairoch.groupby("trade_access_source")["trade_access_continuous"]
          .agg(["count", "mean", "median", "max"]).round(2))
