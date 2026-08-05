"""Build the real medieval transport network (Viabundus) and compute, for each
town, its position in that network:

  - MARKET ACCESS (Harris potential): MA_i = sum_j pop_j * exp(-theta * cost_ij)
  - TRADE BETWEENNESS: pop-weighted share of town-to-town least-cost paths
    that pass through town i (its role as an intermediary/entrepot).
  - CLOSENESS: 1 / mean least-cost travel time to all other towns.

Economic distance: land edges cost length_km * slopemultiplier; water edges
(river/canal/coast/ferry) are discounted by WATER_DISCOUNT (medieval water
freight was ~1/5-1/10 the cost of land per ton-km). We report sensitivity.

Towns are matched to Buringh cities by nearest neighbour within MATCH_KM.
"""
from __future__ import annotations
import numpy as np, pandas as pd, networkx as nx
from pathlib import Path
from sklearn.neighbors import BallTree

ROOT = Path(__file__).resolve().parents[2]
VIA = ROOT / "docs/viabundus/Viabundus-2-csv"
EARTH_KM = 6371.0088

WATER_TYPES = {"river", "canal", "coast", "ferry"}
WATER_DISCOUNT = 5.0     # water cost per km = land / 5
MATCH_KM = 6.0


def load_graph(water_discount=WATER_DISCOUNT):
    e = pd.read_csv(VIA / "edges.csv", na_values=["null", ""])
    n = pd.read_csv(VIA / "nodes.csv", low_memory=False, na_values=["null", ""])
    e = e.dropna(subset=["fromnode", "tonode", "length"]).copy()
    e["length_km"] = e["length"] / 1000.0
    e["slope"] = pd.to_numeric(e["slopemultiplier"], errors="coerce").fillna(1.0)
    is_water = e["type"].isin(WATER_TYPES)
    # effective economic travel cost (km-equivalent of land)
    e["cost"] = np.where(is_water,
                         e["length_km"] / water_discount,
                         e["length_km"] * e["slope"])
    G = nx.Graph()
    for fr, to, c in zip(e["fromnode"].astype(int), e["tonode"].astype(int), e["cost"]):
        if G.has_edge(fr, to):
            if c < G[fr][to]["w"]:
                G[fr][to]["w"] = c
        else:
            G.add_edge(fr, to, w=float(c))
    # town nodes with coords
    n["lat"] = pd.to_numeric(n["latitude"], errors="coerce")
    n["lon"] = pd.to_numeric(n["longitude"], errors="coerce")
    towns = n[(n["Is_Town"] == "y")].dropna(subset=["lat", "lon"]).copy()
    towns = towns[towns["id"].isin(G.nodes)].copy()
    # keep largest connected component
    comp = max(nx.connected_components(G), key=len)
    G = G.subgraph(comp).copy()
    towns = towns[towns["id"].isin(G.nodes)].reset_index(drop=True)
    return G, towns


def match_towns_to_cities(towns, cities):
    """cities: DataFrame with cid, lat, lon, pop columns. Return towns with
    attached cid/pop via nearest-neighbour within MATCH_KM."""
    ct = cities.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    tree = BallTree(np.deg2rad(ct[["lat", "lon"]].to_numpy()), metric="haversine")
    d, idx = tree.query(np.deg2rad(towns[["lat", "lon"]].to_numpy()), k=1)
    dist_km = d.flatten() * EARTH_KM
    towns = towns.copy()
    towns["match_dist_km"] = dist_km
    towns["cid"] = ct["cid"].to_numpy()[idx.flatten()]
    towns.loc[towns["match_dist_km"] > MATCH_KM, "cid"] = np.nan
    return towns


def compute_network_features(G, towns, popcol_by_cid, theta_km=150.0):
    """popcol_by_cid: dict cid -> population (weights for MA & betweenness).
    theta_km: decay scale in km-equivalent (MA weight = exp(-cost/theta)).
    Returns DataFrame indexed by town node id with MA, betweenness, closeness.
    """
    towns = towns.copy()
    towns["pop"] = towns["cid"].map(popcol_by_cid).fillna(0.0)
    src_nodes = towns["id"].tolist()
    node_pop = dict(zip(towns["id"], towns["pop"]))
    node_cid = dict(zip(towns["id"], towns["cid"]))
    town_set = set(src_nodes)

    MA = {t: 0.0 for t in src_nodes}
    betw = {t: 0.0 for t in src_nodes}
    closeness_num = {t: 0.0 for t in src_nodes}
    closeness_cnt = {t: 0 for t in src_nodes}

    for s in src_nodes:
        dist, paths = nx.single_source_dijkstra(G, s, weight="w")
        ps = node_pop[s]
        for t in src_nodes:
            if t == s or t not in dist:
                continue
            c = dist[t]
            # market access (exclude self); pop of destination
            MA[s] += node_pop[t] * np.exp(-c / theta_km)
            closeness_num[s] += c
            closeness_cnt[s] += 1
        # trade betweenness: for paths from s to other towns, credit intermediaries
        # weight by pop_s * pop_t (gravity of the flow using that path)
        for t in src_nodes:
            if t == s or t not in paths:
                continue
            flow = ps * node_pop[t]
            if flow <= 0:
                continue
            for mid in paths[t][1:-1]:      # interior nodes
                if mid in town_set:
                    betw[mid] += flow

    rows = []
    for t in src_nodes:
        cl = (closeness_cnt[t] / closeness_num[t]) if closeness_num[t] > 0 else np.nan
        rows.append({"node": t, "cid": node_cid[t], "MA": MA[t],
                     "betweenness": betw[t], "closeness": cl,
                     "match_dist_km": None})
    out = pd.DataFrame(rows)
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from panel import load_buringh, wide_pop
    G, towns = load_graph()
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges (largest component)")
    print(f"Town nodes in component: {len(towns)}")
    w = wide_pop(load_buringh())
    cities = w[["cid", "lat", "lon"]].copy()
    towns = match_towns_to_cities(towns, cities)
    matched = towns["cid"].notna().sum()
    print(f"Town nodes matched to Buringh cities (<= {MATCH_KM}km): {matched}")
    # sanity: population weights at 1200
    pop1200 = w.set_index("cid")["pop1200"].fillna(0.0).to_dict()
    feats = compute_network_features(G, towns, pop1200, theta_km=150.0)
    feats = feats.merge(w[["cid", "city", "pop1200", "pop1500"]], on="cid", how="left")
    print("\nTop 15 towns by trade-betweenness (pop1200-weighted):")
    print(feats.dropna(subset=["city"]).sort_values("betweenness", ascending=False)
          [["city", "MA", "betweenness", "closeness", "pop1200", "pop1500"]].head(15).to_string(index=False))
