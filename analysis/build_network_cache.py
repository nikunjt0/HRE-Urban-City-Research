"""Compute the town-to-town least-cost matrix ONCE and cache it, plus a
population-independent topological betweenness and closeness. Market access for
any year is then a cheap matrix-vector product downstream.
"""
from __future__ import annotations
import numpy as np, pandas as pd, networkx as nx
from pathlib import Path
from network import load_graph, match_towns_to_cities
from panel import load_buringh, wide_pop

OUT = Path(__file__).resolve().parent / "out"


def main(water_discount=5.0):
    G, towns = load_graph(water_discount=water_discount)
    w = wide_pop(load_buringh())
    towns = match_towns_to_cities(towns, w[["cid", "lat", "lon"]])
    towns = towns.dropna(subset=["cid"]).drop_duplicates("cid").reset_index(drop=True)
    src = towns["id"].tolist()
    idx_of = {nid: i for i, nid in enumerate(src)}
    N = len(src)
    town_set = set(src)
    print(f"towns matched & unique cid: {N}")

    C = np.full((N, N), np.inf)
    betw_topo = {t: 0.0 for t in src}       # unweighted interior-node counts
    for si, s in enumerate(src):
        dist, paths = nx.single_source_dijkstra(G, s, weight="w")
        for t in src:
            if t in dist:
                C[si, idx_of[t]] = dist[t]
        for t in src:
            if t == s or t not in paths:
                continue
            for mid in paths[t][1:-1]:
                if mid in town_set:
                    betw_topo[mid] += 1.0
    np.fill_diagonal(C, 0.0)

    # closeness (mean finite cost to others)
    closeness = np.zeros(N)
    for i in range(N):
        finite = C[i, np.isfinite(C[i])]
        finite = finite[finite > 0]
        closeness[i] = 1.0 / finite.mean() if len(finite) else np.nan

    meta = towns[["id", "cid", "lat", "lon", "match_dist_km"]].copy()
    meta = meta.merge(w[["cid", "city", "country"]], on="cid", how="left")
    meta["closeness"] = closeness
    meta["betw_topo"] = meta["id"].map(betw_topo)
    meta["node_idx"] = range(N)

    np.save(OUT / "cost_matrix.npy", C)
    meta.to_csv(OUT / "network_meta.csv", index=False)
    print("saved cost_matrix.npy and network_meta.csv")
    print(meta.sort_values("betw_topo", ascending=False)
          [["city", "betw_topo", "closeness"]].head(12).to_string(index=False))


if __name__ == "__main__":
    main()
