"""Viabundus nodes loader with parent-attribute cascade.

Lifted in spirit from build_trade_access.py (lines 50-75, 144-164) and
exposed as a single function for reuse by new variable builders.
"""
import pandas as pd

from .paths import VIABUNDUS

PARENT_ATTRS = [
    "Is_Town", "Town_From", "Town_To", "Town_Description",
    "Is_Settlement", "Settlement_From", "Settlement_To",
    "Is_Staple", "Staple_From", "Staple_To", "Staple_Duration_Of_Stay",
    "Is_Fair", "Fair_From", "Fair_To",
]


def load_nodes_with_cascade() -> pd.DataFrame:
    """Load Viabundus nodes.csv and cascade parent attrs onto child nodes."""
    nodes = pd.read_csv(VIABUNDUS / "nodes.csv", low_memory=False, na_values=["null", ""])
    parents = nodes.set_index("id")[PARENT_ATTRS]
    for col in PARENT_ATTRS:
        if col not in nodes.columns:
            continue
        inherited = nodes["parentid"].map(parents[col])
        nodes[col] = nodes[col].fillna(inherited)
    return nodes


def load_towns():
    """Return (towns_df, nodes_df, resolve_to_parent_town).

    `towns_df` has lat/lon coerced to float and rows missing coords dropped.
    `resolve_to_parent_town(node_id)` walks parentid until it finds a town,
    returning that town's id (or None).
    """
    nodes = load_nodes_with_cascade()
    towns = nodes[nodes["Is_Town"] == "y"].copy()
    towns["lat"] = pd.to_numeric(towns["latitude"], errors="coerce")
    towns["lon"] = pd.to_numeric(towns["longitude"], errors="coerce")
    towns = towns.dropna(subset=["lat", "lon"]).reset_index(drop=True)

    town_id_set = set(towns["id"].tolist())
    node_to_parent = nodes.set_index("id")["parentid"].to_dict()

    def resolve_to_parent_town(node_id):
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

    return towns, nodes, resolve_to_parent_town
