"""
Map the top-tier (score=3) trade-access cities for each benchmark year.

Outputs:
  output/top_score3_by_year.csv      one row per (city, year) for every
                                     city that scored 3, ranked within year.
  output/top3_per_year.txt           plain-text top-list per year.
  output/map_score3_by_year.png      8-panel small-multiples map of all
                                     score-3 cities, one panel per year.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path("/Users/nikunjtyagi/HistoryResearch/output")
df = pd.read_csv(OUT / "cities_trade_access.csv")

# --- 1. Per-year ranked top list -------------------------------------------
# Within score=3, rank by population (where known) desc, then num_fairs_100km desc.
top = df[df["trade_access_score"] == 3].copy()
top["pop_rank_key"] = top["population"].fillna(-1)
top["sort_key"] = list(zip(-top["pop_rank_key"], -top["num_fairs_100km"]))
top = top.sort_values(["year", "pop_rank_key", "num_fairs_100km"],
                      ascending=[True, False, False])
top.to_csv(OUT / "top_score3_by_year.csv", index=False)
print(f"Wrote {OUT / 'top_score3_by_year.csv'} ({len(top):,} city-year rows)")

# Per-year top-15 plain-text list (population-ranked)
lines = []
for year, grp in top.groupby("year"):
    lines.append(f"\n=== {year}  ({len(grp)} cities scoring 3) ===")
    head = grp.head(15)[["name", "population", "num_fairs_100km",
                         "own_fair_category", "has_own_staple",
                         "has_own_toll", "has_own_harbour"]]
    head = head.rename(columns={
        "num_fairs_100km": "fairs_100km",
        "own_fair_category": "own_fair",
        "has_own_staple": "staple",
        "has_own_toll": "toll",
        "has_own_harbour": "harbour",
    })
    lines.append(head.to_string(index=False, na_rep="-"))

(OUT / "top3_per_year.txt").write_text("\n".join(lines))
print(f"Wrote {OUT / 'top3_per_year.txt'}")
print("\n" + "\n".join(lines[:3]))  # show first year as preview


# --- 2. Map: small-multiples, one panel per year ---------------------------
years = sorted(df["year"].unique())
n = len(years)
ncols = 4
nrows = int(np.ceil(n / ncols))
fig, axes = plt.subplots(nrows, ncols, figsize=(16, 4.2 * nrows),
                         constrained_layout=True)
axes = axes.flatten()

# all towns as faint background
all_lat = df.drop_duplicates("city_id")["lat"]
all_lon = df.drop_duplicates("city_id")["lon"]

xlim = (all_lon.min() - 0.5, all_lon.max() + 0.5)
ylim = (all_lat.min() - 0.5, all_lat.max() + 0.5)

for ax, year in zip(axes, years):
    yr_df = df[df["year"] == year]
    score_3 = yr_df[yr_df["trade_access_score"] == 3]
    score_2 = yr_df[yr_df["trade_access_score"] == 2]
    score_01 = yr_df[yr_df["trade_access_score"] <= 1]

    ax.scatter(score_01["lon"], score_01["lat"], s=1.2, c="#cfcfcf",
               alpha=0.6, label=f"0–1 ({len(score_01)})")
    ax.scatter(score_2["lon"], score_2["lat"], s=2.5, c="#7faedc",
               alpha=0.6, label=f"2 ({len(score_2)})")
    # size score-3 cities by population (fall back to flat size)
    s3 = score_3.copy()
    pop = s3["population"].fillna(s3["population"].median() if s3["population"].notna().any() else 5000)
    sizes = np.clip(np.sqrt(pop) / 6.0, 8, 80)
    ax.scatter(s3["lon"], s3["lat"], s=sizes, c="#d62728",
               edgecolors="black", linewidths=0.3, alpha=0.85,
               label=f"3 ({len(s3)})")

    # label the top-8 by population
    labelled = s3.sort_values("population", ascending=False, na_position="last").head(8)
    for _, r in labelled.iterrows():
        if pd.notna(r["population"]):
            ax.annotate(r["name"], (r["lon"], r["lat"]),
                        fontsize=6.5, xytext=(2, 2), textcoords="offset points")

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_title(f"{year}", fontsize=11, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(fontsize=6.5, loc="lower left", framealpha=0.85)
    ax.set_aspect(1.6)

# hide unused panels
for ax in axes[len(years):]:
    ax.axis("off")

fig.suptitle("Top-tier TradeAccess (score 3) cities by benchmark year — Viabundus 2",
             fontsize=13, fontweight="bold")

map_path = OUT / "map_score3_by_year.png"
fig.savefig(map_path, dpi=180, bbox_inches="tight")
print(f"\nWrote {map_path}")


# --- 3. A second map showing churn: cities that newly hit 3 vs lost 3 ------
years = sorted(df["year"].unique())
fig2, axes2 = plt.subplots(1, len(years) - 1, figsize=(4.5 * (len(years) - 1), 4.5),
                           constrained_layout=True)
if len(years) - 1 == 1:
    axes2 = [axes2]

for ax, (y_prev, y_now) in zip(axes2, zip(years[:-1], years[1:])):
    prev3 = set(df[(df["year"] == y_prev) & (df["trade_access_score"] == 3)]["city_id"])
    now3 = set(df[(df["year"] == y_now) & (df["trade_access_score"] == 3)]["city_id"])
    new = now3 - prev3
    lost = prev3 - now3
    kept = prev3 & now3

    coords = df.drop_duplicates("city_id").set_index("city_id")[["lat", "lon"]]

    def plot_set(s, color, label, size=18):
        pts = coords.loc[list(s)]
        ax.scatter(pts["lon"], pts["lat"], s=size, c=color,
                   edgecolors="black", linewidths=0.2, alpha=0.85, label=label)

    ax.scatter(all_lon, all_lat, s=0.6, c="#dcdcdc", alpha=0.5)
    plot_set(kept, "#a0a0a0", f"kept ({len(kept)})", size=10)
    plot_set(new, "#2ca02c", f"new in {y_now} ({len(new)})", size=22)
    plot_set(lost, "#d62728", f"lost in {y_now} ({len(lost)})", size=22)

    ax.set_title(f"{y_prev} → {y_now}", fontsize=10, fontweight="bold")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(fontsize=6.5, loc="lower left", framealpha=0.85)
    ax.set_aspect(1.6)

fig2.suptitle("Churn in score=3 cities between benchmarks",
              fontsize=12, fontweight="bold")
churn_path = OUT / "map_score3_churn.png"
fig2.savefig(churn_path, dpi=170, bbox_inches="tight")
print(f"Wrote {churn_path}")
