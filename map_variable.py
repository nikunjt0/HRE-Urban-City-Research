"""Generic small-multiples mapper for any of the seven 0-3 variables (or composite).

Usage:
    python map_variable.py legal_capacity
    python map_variable.py composite          (uses composite_0_3)
    python map_variable.py merchant_capital --label-top 15

Reuses the visual style of map_top_trade_access.py (matplotlib scatter,
no GeoPandas), parameterized by score column.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lib.paths import OUT


COLOR_TIERS = {
    0: "#dcdcdc",
    1: "#9ab8d5",
    2: "#3d6da6",
    3: "#d62728",
}
SIZE_TIERS = {0: 1.0, 1: 2.0, 2: 5.0, 3: 18.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("var", help="legal_capacity | merchant_capital | "
                    "agricultural_surplus | peasant_mobility | noble_extraction "
                    "| conflict_risk | composite")
    ap.add_argument("--label-top", type=int, default=10,
                    help="label the top-N score-3 (or composite top-N) per panel")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    var = args.var
    score_col = f"{var}_score" if var != "composite" else "composite_0_3"
    csv = OUT / f"cities_{var}.csv"
    if not csv.exists():
        raise FileNotFoundError(csv)
    df = pd.read_csv(csv)
    if score_col not in df.columns:
        raise KeyError(f"{score_col} not in {csv.name}; columns: {list(df.columns)}")

    # Normalize population column (only present in some files) for sizing labels
    if "population" in df.columns:
        df["pop_for_label"] = df["population"]
    elif "composite_raw" in df.columns:
        df["pop_for_label"] = df["composite_raw"]
    else:
        df["pop_for_label"] = df[score_col]

    years = sorted(df["year"].unique())
    n = len(years)
    ncols = 3
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(15, 4.4 * nrows),
                             constrained_layout=True)
    axes = axes.flatten() if n > 1 else [axes]

    coords = df.drop_duplicates("city_id")[["lat", "lon"]]
    xlim = (coords["lon"].min() - 0.5, coords["lon"].max() + 0.5)
    ylim = (coords["lat"].min() - 0.5, coords["lat"].max() + 0.5)

    for ax, year in zip(axes, years):
        yr = df[df["year"] == year]
        for tier in [0, 1, 2, 3]:
            sub = yr[yr[score_col] == tier]
            if len(sub) == 0:
                continue
            ax.scatter(sub["lon"], sub["lat"],
                       s=SIZE_TIERS[tier], c=COLOR_TIERS[tier],
                       alpha=0.55 if tier < 2 else 0.85,
                       edgecolors="black" if tier == 3 else "none",
                       linewidths=0.25 if tier == 3 else 0,
                       label=f"{tier} ({len(sub)})")
        # Label top-N (by pop or composite_raw or score), within score==3 only
        s3 = yr[yr[score_col] == 3]
        labelled = s3.sort_values("pop_for_label", ascending=False,
                                  na_position="last").head(args.label_top)
        for _, r in labelled.iterrows():
            ax.annotate(str(r["name"]), (r["lon"], r["lat"]),
                        fontsize=6.0, xytext=(2, 2), textcoords="offset points")

        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_title(f"{year}", fontsize=11, fontweight="bold")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.legend(fontsize=6.0, loc="lower left", framealpha=0.85)
        ax.set_aspect(1.6)

    for ax in axes[len(years):]:
        ax.axis("off")

    fig.suptitle(f"{var.replace('_', ' ').title()} (0-3) by year — HRE city panel",
                 fontsize=12, fontweight="bold")
    out_path = Path(args.out) if args.out else OUT / f"map_{var}_by_year.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
