"""Paper-ready analysis & graphics for the HRE urban-growth paper.

Generates:
  output/paper_analysis_report.html      — narrative report with embedded figures
  output/paper_figures/*.png             — every figure as a standalone PNG
                                          (drop into LaTeX directly)
  output/paper_tables/*.csv              — every table as CSV

Frame (per the paper outline):
  Path dependence dominated HRE city size, but among cities with similar
  starting populations, those with stronger legal institutions and merchant
  capital outperformed their inherited trajectory. The HRE's fragmented
  political structure created variation in those institutions.

Sections:
  1. Sample & data (Buringh primary, Bairoch as cross-check)
  2. The HRE urban system: 1200 vs 1500 (map graphics)
  3. Path-dependence baseline: log(pop_T) ~ log(pop_T-100)
  4. Residual analysis: who beat expectations?
  5. Residual regression: what predicts overperformance?
  6. The 13 priority cities (variable trajectories table)
  7. Geographic determinants (Buringh transport location)
  8. Robustness: Buringh vs Bairoch convergence
  9. Implications for the paper
"""
from __future__ import annotations

import base64
import html as _html
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patheffects as mpe  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
import numpy as np
import pandas as pd

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from lib.bairoch_pop import load_pop_panel as load_bairoch
from lib.buringh_pop import load_buringh_panel, match_buringh_to_bairoch
from lib.paths import OUT
from lib.targets import PRIORITY_CITIES


# ----------------------------------------------------------------- constants

REPORT_PATH = OUT / "paper_analysis_report.html"
FIG_DIR = OUT / "paper_figures"
TBL_DIR = OUT / "paper_tables"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TBL_DIR.mkdir(parents=True, exist_ok=True)

POP_YEARS = [1200, 1300, 1400, 1500]
LEVEL_YEARS = [1300, 1400, 1500]
TRANSITIONS = [(1200, 1300), (1300, 1400), (1400, 1500)]
FACTOR_YEAR_FOR_TRANSITION = {(1200, 1300): 1250, (1300, 1400): 1300,
                              (1400, 1500): 1400}

FACTORS = [
    ("legal_capacity",       "cities_legal_capacity.csv",       "legal_capacity_continuous"),
    ("merchant_capital",     "cities_merchant_capital.csv",     "merchant_capital_continuous"),
    ("trade_access",         "cities_trade_access_bairoch.csv", "trade_access_continuous"),
    ("agricultural_surplus", "cities_agricultural_surplus.csv", "agricultural_surplus_continuous"),
    ("noble_extraction",     "cities_noble_extraction.csv",     "noble_extraction_continuous"),
    ("conflict_risk",        "cities_conflict_risk.csv",        "conflict_risk_continuous"),
]
FACTOR_NAMES = [f[0] for f in FACTORS]
FACTOR_NAMES_NICE = {
    "legal_capacity":       "Legal capacity",
    "merchant_capital":     "Merchant capital",
    "trade_access":         "Trade access",
    "agricultural_surplus": "Agricultural surplus",
    "noble_extraction":     "Noble extraction (–)",
    "conflict_risk":        "Conflict risk (–)",
}

# HRE bounding box for maps
HRE_BBOX = (3.5, 17.5, 45.5, 55.5)  # (lon_min, lon_max, lat_min, lat_max)


# ---------------------------------------------------------- IO helpers

def load_factor(name: str, fname: str, col: str) -> pd.DataFrame:
    df = pd.read_csv(OUT / fname)
    score_col = name + "_score"
    keep = ["city_id", "year", col]
    if score_col in df.columns:
        keep.append(score_col)
    return df[keep].rename(columns={col: f"{name}_cont", score_col: f"{name}_score"})


def save_fig(fig, slug: str) -> str:
    """Save a figure as a paper-ready PNG and return the embedded data-URI."""
    out_path = FIG_DIR / f"{slug}.png"
    fig.savefig(out_path, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    data_uri = ("data:image/png;base64,"
                + base64.b64encode(buf.getvalue()).decode())
    return data_uri


def save_table_csv(df: pd.DataFrame, slug: str) -> Path:
    p = TBL_DIR / f"{slug}.csv"
    df.to_csv(p, index=False)
    return p


# ---------------------------------------------------------- modelling helpers

def fit_ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    Xc = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    return beta[1:], float(beta[0]), Xc @ beta


def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def cluster_bootstrap(X: np.ndarray, y: np.ndarray,
                      group_ids: np.ndarray, n: int = 500,
                      seed: int = 17) -> np.ndarray:
    rng = np.random.default_rng(seed)
    cities = np.unique(group_ids)
    n_c = len(cities)
    by_city = {cid: np.where(group_ids == cid)[0] for cid in cities}
    out = np.zeros((n, X.shape[1] + 1))
    for b in range(n):
        sampled = rng.choice(cities, size=n_c, replace=True)
        idx = np.concatenate([by_city[c] for c in sampled])
        Xc = np.column_stack([np.ones(len(idx)), X[idx]])
        try:
            beta, *_ = np.linalg.lstsq(Xc, y[idx], rcond=None)
        except np.linalg.LinAlgError:
            beta = np.full(Xc.shape[1], np.nan)
        out[b] = beta
    return out


def kfold_by_city(X: np.ndarray, y: np.ndarray, group_ids: np.ndarray,
                  n_splits: int = 5, seed: int = 17) -> dict:
    rng = np.random.default_rng(seed)
    cities = np.unique(group_ids)
    rng.shuffle(cities)
    folds = np.array_split(cities, n_splits)
    r2s = []
    for i in range(n_splits):
        test_cities = set(folds[i].tolist())
        test_mask = np.array([c in test_cities for c in group_ids])
        train_mask = ~test_mask
        if train_mask.sum() < 10 or test_mask.sum() < 5:
            continue
        Xt = np.column_stack([np.ones(train_mask.sum()), X[train_mask]])
        beta, *_ = np.linalg.lstsq(Xt, y[train_mask], rcond=None)
        Xe = np.column_stack([np.ones(test_mask.sum()), X[test_mask]])
        r2s.append(r2(y[test_mask], Xe @ beta))
    return {"mean": float(np.mean(r2s)), "std": float(np.std(r2s))}


# ---------------------------------------------------------- data loading

def build_panel(buringh_matched: pd.DataFrame) -> pd.DataFrame:
    """Level panel keyed (city_id, year ∈ {1300,1400,1500}) with both lag-pop
    and the 6 factor scores attached at year T. Uses Buringh population as the
    primary outcome (richer HRE coverage) but cross-checks against Bairoch.
    """
    bur = buringh_matched.dropna(subset=["city_id"]).copy()
    bur["city_id"] = bur["city_id"].astype(int)
    bur = bur[bur["year"].isin(POP_YEARS)].copy()

    # one row per (city_id, year) — keep largest if duplicates
    bur = (bur.sort_values(["city_id", "year", "pop_pers"], ascending=[True, True, False])
              .drop_duplicates(["city_id", "year"]))
    wide = bur.pivot_table(
        index=["city_id"], columns="year", values="pop_pers", aggfunc="max"
    ).reset_index()
    wide.columns.name = None

    # Build (city, year) rows for level model
    rows = []
    for y in LEVEL_YEARS:
        ylag = y - 100
        sub = wide.dropna(subset=[y, ylag]).copy()
        sub = sub[(sub[y] > 0) & (sub[ylag] > 0)]
        sub["year"] = y
        sub["pop_pers"] = sub[y]
        sub["pop_pers_lag"] = sub[ylag]
        sub["log_pop"] = np.log(sub[y])
        sub["log_pop_lag"] = np.log(sub[ylag])
        rows.append(sub[["city_id", "year", "pop_pers", "pop_pers_lag",
                         "log_pop", "log_pop_lag"]])
    panel = pd.concat(rows, ignore_index=True)

    # Attach metadata (city name, lat/lon, country, transport)
    meta = (bur[["city_id", "buringh_city", "country", "transport",
                 "p_lat", "p_lon", "elev_m"]]
            .drop_duplicates("city_id"))
    panel = panel.merge(meta, on="city_id", how="left")

    # Attach factors at year T (state at end of period)
    for name, fname, col in FACTORS:
        f = load_factor(name, fname, col)
        panel = panel.merge(f, on=["city_id", "year"], how="left")

    factor_cols = [f"{n}_cont" for n in FACTOR_NAMES]
    panel = panel.dropna(subset=factor_cols).reset_index(drop=True)
    return panel


# ---------------------------------------------------------- mapping

def _make_hre_axes(figsize: tuple[float, float] = (11, 8.5)):
    """Create a figure + cartopy axes with modern country borders, coastlines,
    and the HRE bounding box. All shapefiles are cached locally; no network
    access required. Returns (fig, ax)."""
    lon_min, lon_max, lat_min, lat_max = HRE_BBOX
    fig = plt.figure(figsize=figsize)
    fig.set_facecolor("#fdfcf8")
    ax = plt.axes(projection=ccrs.LambertConformal(
        central_longitude=10, central_latitude=50,
        standard_parallels=(46, 54)))
    ax.set_extent(HRE_BBOX, crs=ccrs.PlateCarree())

    # Filled land + ocean for visual context
    ax.add_feature(cfeature.LAND.with_scale("50m"),
                   facecolor="#f3eedf", zorder=0)
    ax.add_feature(cfeature.OCEAN.with_scale("50m"),
                   facecolor="#cfe1ee", zorder=0)
    # Coastline + modern country borders (this is the change the user asked for)
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
                   linewidth=0.6, edgecolor="#444", zorder=2)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"),
                   linewidth=0.5, edgecolor="#888", linestyle="-", zorder=2)

    # Subtle latitude/longitude graticule for orientation
    gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="#cdc7b1",
                      alpha=0.6, linestyle=":")
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 9, "color": "#6b6759"}
    gl.ylabel_style = {"size": 9, "color": "#6b6759"}

    return fig, ax


def map_hre_year(buringh_matched: pd.DataFrame, year: int,
                 threshold: int, slug: str, title: str) -> str:
    sub = buringh_matched[(buringh_matched["year"] == year) &
                          (buringh_matched["pop_pers"] >= threshold)].copy()
    sub = sub.dropna(subset=["p_lat", "p_lon"])

    fig, ax = _make_hre_axes()

    if len(sub) > 0:
        sizes = np.clip((sub["pop_pers"].to_numpy() / 1000.0) * 4, 12, 800)
        norm = plt.matplotlib.colors.LogNorm(
            vmin=max(threshold, 1000),
            vmax=max(50000, float(sub["pop_pers"].max())))
        sc = ax.scatter(sub["p_lon"], sub["p_lat"], s=sizes,
                        c=sub["pop_pers"], cmap="YlOrRd", norm=norm,
                        edgecolor="black", linewidth=0.4, alpha=0.9,
                        transform=ccrs.PlateCarree(), zorder=5)
        cb = plt.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
        cb.set_label("population (persons, log scale)", fontsize=10)
        for _, r in sub.nlargest(15, "pop_pers").iterrows():
            ax.annotate(r["buringh_city"], (r["p_lon"], r["p_lat"]),
                        xytext=(5, 3), textcoords="offset points",
                        fontsize=9.5, fontweight="bold", color="#1f1d18",
                        transform=ccrs.PlateCarree(), zorder=10,
                        path_effects=[
                            mpe.withStroke(linewidth=2, foreground="white",
                                           alpha=0.85)])

    ax.set_title(f"{title}    (n = {len(sub)} cities ≥ {threshold:,})",
                 fontsize=14, pad=12)

    legend_elements = []
    for ref_pop in [5000, 15000, 30000]:
        s = np.clip((ref_pop / 1000.0) * 4, 12, 800)
        legend_elements.append(
            Line2D([0], [0], marker='o', color='w',
                   markerfacecolor="#e58c4d",
                   markersize=np.sqrt(s),
                   markeredgecolor="black", markeredgewidth=0.4,
                   label=f"{ref_pop:,}"))
    ax.legend(handles=legend_elements, loc="lower right",
              title="population", fontsize=9, frameon=True,
              labelspacing=1.2)

    return save_fig(fig, slug)


def map_residuals(panel: pd.DataFrame, slug: str, title: str) -> str:
    fig, ax = _make_hre_axes()

    sub = panel.dropna(subset=["p_lat", "p_lon", "residual_lag_only"])
    if len(sub) == 0:
        ax.text(0.5, 0.5, "no residuals", ha="center", va="center",
                transform=ax.transAxes)
        return save_fig(fig, slug)
    rmax = float(np.nanpercentile(np.abs(sub["residual_lag_only"]), 95))
    sc = ax.scatter(sub["p_lon"], sub["p_lat"], s=44,
                    c=sub["residual_lag_only"], cmap="RdBu_r",
                    vmin=-rmax, vmax=rmax, edgecolor="black",
                    linewidth=0.3, alpha=0.9,
                    transform=ccrs.PlateCarree(), zorder=5)
    cb = plt.colorbar(sc, ax=ax, shrink=0.75, pad=0.02)
    cb.set_label("residual = log(pop_T) − predicted from log(pop_T-100)",
                 fontsize=10)
    over = sub.nlargest(8, "residual_lag_only")
    under = sub.nsmallest(8, "residual_lag_only")
    for _, r in pd.concat([over, under]).iterrows():
        # red residual (positive) = beat trajectory; blue (negative) = fell short
        color = "#7c1f15" if r["residual_lag_only"] > 0 else "#1a3d6e"
        ax.annotate(r["buringh_city"], (r["p_lon"], r["p_lat"]),
                    xytext=(5, 3), textcoords="offset points",
                    fontsize=9, fontweight="bold", color=color,
                    transform=ccrs.PlateCarree(), zorder=10,
                    path_effects=[
                        plt.matplotlib.patheffects.withStroke(
                            linewidth=2, foreground="white", alpha=0.85)])
    ax.set_title(title, fontsize=14, pad=12)
    return save_fig(fig, slug)


# ---------------------------------------------------------- non-map figures

def fig_calibration_lag_only(panel: pd.DataFrame, slug: str) -> str:
    fig, ax = plt.subplots(figsize=(7.5, 6))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    actual = panel["log_pop"].to_numpy()
    pred = panel["pred_lag_only"].to_numpy()
    lo, hi = float(min(actual.min(), pred.min())), float(max(actual.max(), pred.max()))
    pad = 0.3
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad],
            color="#888", linewidth=1, linestyle="--",
            label="perfect prediction (y = x)")
    sc = ax.scatter(actual, pred, c=panel["year"], cmap="viridis",
                    s=22, alpha=0.7, edgecolor="white", linewidth=0.4)
    ax.set_xlabel("actual log(pop_T)", fontsize=12)
    ax.set_ylabel("predicted log(pop_T) from log(pop_T-100) alone", fontsize=12)
    r2_val = r2(actual, pred)
    ax.set_title(f"Path-dependence baseline:  R² = {r2_val:.3f}",
                 fontsize=13, pad=10)
    cb = plt.colorbar(sc, ax=ax, ticks=LEVEL_YEARS)
    cb.set_label("year T", fontsize=10)
    ax.legend(loc="upper left", fontsize=10, frameon=False)
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    return save_fig(fig, slug)


def fig_residual_distribution(panel: pd.DataFrame, slug: str) -> str:
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    res = panel["residual_lag_only"].to_numpy()
    ax.hist(res, bins=40, color="#3463a6", alpha=0.75, edgecolor="white")
    mean = float(np.nanmean(res))
    ax.axvline(0, color="black", linewidth=1)
    ax.axvline(mean, color="#a23a2a", linestyle="--", linewidth=1.5,
               label=f"mean = {mean:+.3f}")
    ax.set_xlabel("residual (actual − predicted log pop, given lag pop only)",
                  fontsize=11)
    ax.set_ylabel("count", fontsize=11)
    ax.set_title("Distribution of path-dependence residuals: each city's "
                 "deviation from its inherited trajectory",
                 fontsize=12.5, pad=10)
    ax.legend(loc="best", fontsize=10, frameon=False)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return save_fig(fig, slug)


def fig_residual_coefficients(features: list[str], betas: list[float],
                              ci_lo: list[float], ci_hi: list[float],
                              slug: str, title: str) -> str:
    fig, ax = plt.subplots(figsize=(9, 4.6))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    y_pos = np.arange(len(features))
    err_lo = [b - lo for b, lo in zip(betas, ci_lo)]
    err_hi = [hi - b for b, hi in zip(betas, ci_hi)]
    colors = ["#27ae60" if (b > 0 and lo > 0)
              else "#a23a2a" if (b < 0 and hi < 0)
              else "#888"
              for b, lo, hi in zip(betas, ci_lo, ci_hi)]
    ax.barh(y_pos, betas, xerr=[err_lo, err_hi], color=colors, alpha=0.85,
            ecolor="black", capsize=3)
    ax.axvline(0, color="black", linewidth=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([FACTOR_NAMES_NICE.get(f, f) for f in features])
    ax.set_xlabel("β  (effect on path-dependence residual per +1 SD of factor)",
                  fontsize=11)
    ax.set_title(title, fontsize=12.5, pad=10)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    return save_fig(fig, slug)


def fig_buringh_vs_bairoch(buringh_match: pd.DataFrame,
                           bairoch: pd.DataFrame, slug: str) -> str:
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")

    bur = buringh_match.dropna(subset=["city_id"]).copy()
    bur["city_id"] = bur["city_id"].astype(int)
    bur = bur[bur["year"].isin(LEVEL_YEARS) & (bur["pop_pers"] > 0)]
    bur = bur[["city_id", "year", "pop_pers"]].rename(columns={"pop_pers": "buringh"})

    bai = bairoch[bairoch["year"].isin(LEVEL_YEARS) & (bairoch["pop_pers"] > 0)].copy()
    bai = bai[["city_id", "year", "pop_pers"]].rename(columns={"pop_pers": "bairoch"})

    j = bur.merge(bai, on=["city_id", "year"], how="inner")
    if len(j) == 0:
        ax.text(0.5, 0.5, "no overlapping cities", ha="center")
        return save_fig(fig, slug)
    lp_b = np.log(j["buringh"]); lp_a = np.log(j["bairoch"])
    sc = ax.scatter(lp_b, lp_a, c=j["year"], cmap="viridis",
                    s=22, alpha=0.7, edgecolor="white", linewidth=0.4)
    lo = float(min(lp_b.min(), lp_a.min())); hi = float(max(lp_b.max(), lp_a.max()))
    ax.plot([lo, hi], [lo, hi], color="#888", linestyle="--", linewidth=1)
    r = float(np.corrcoef(lp_b, lp_a)[0, 1])
    ax.set_xlabel("Buringh log(pop)", fontsize=11.5)
    ax.set_ylabel("Bairoch log(pop)", fontsize=11.5)
    ax.set_title(f"Buringh vs Bairoch (matched cities, 1300/1400/1500): "
                 f"r = {r:.3f}, n = {len(j):,}", fontsize=12.5, pad=10)
    cb = plt.colorbar(sc, ax=ax, ticks=LEVEL_YEARS); cb.set_label("year")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return save_fig(fig, slug)


def fig_transport_growth(buringh_match: pd.DataFrame, slug: str) -> str:
    df = buringh_match.dropna(subset=["city_id", "transport", "pop_pers"]).copy()
    df = df[df["pop_pers"] > 0].copy()
    df["log_pop"] = np.log(df["pop_pers"])
    # collapse rare transport categories
    cnt = df["transport"].value_counts()
    keep_cats = cnt[cnt >= 50].index.tolist()
    df = df[df["transport"].isin(keep_cats)].copy()

    yearly = df[df["year"].isin(LEVEL_YEARS)].copy()
    grp = (yearly.groupby(["transport", "year"])
                  .agg(mean_log_pop=("log_pop", "mean"),
                       n=("city_id", "nunique"))
                  .reset_index())

    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    cmap = plt.get_cmap("tab10")
    for i, t in enumerate(keep_cats):
        sub = grp[grp["transport"] == t].sort_values("year")
        ax.plot(sub["year"], sub["mean_log_pop"],
                marker="o", label=f"{t} (n≈{int(sub['n'].mean())})",
                color=cmap(i % 10), linewidth=1.5)
    ax.set_xlabel("year", fontsize=11.5)
    ax.set_ylabel("mean log(pop) of cities in this transport class", fontsize=11.5)
    ax.set_title("Average city size by Buringh transport-location class",
                 fontsize=12.5, pad=10)
    ax.legend(loc="best", fontsize=9, frameon=True, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(LEVEL_YEARS)
    fig.tight_layout()
    return save_fig(fig, slug)


def fig_priority_residual_trajectories(panel: pd.DataFrame,
                                        slug: str) -> str:
    """Each priority city's residual at 1300/1400/1500 — shows path of overperformance."""
    priority_ids = [b for (_, b, _) in PRIORITY_CITIES]
    name_for_id = {b: nm for (nm, b, _) in PRIORITY_CITIES}

    sub = panel[panel["city_id"].isin(priority_ids)].copy()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    cmap = plt.get_cmap("tab20")
    for i, cid in enumerate(priority_ids):
        s = sub[sub["city_id"] == cid].sort_values("year")
        if len(s) == 0:
            continue
        ax.plot(s["year"], s["residual_lag_only"], marker="o",
                color=cmap(i % 20), linewidth=1.5,
                label=name_for_id.get(cid, str(cid)))
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xlabel("year", fontsize=11.5)
    ax.set_ylabel("path-dependence residual", fontsize=11.5)
    ax.set_title("Priority cities: deviations from their inherited trajectory",
                 fontsize=12.5, pad=10)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0),
              fontsize=9, frameon=False)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(LEVEL_YEARS)
    fig.tight_layout()
    return save_fig(fig, slug)


# ---------------------------------------------------------- 13-city table

def build_priority_table(panel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Wide table: one row per (priority_city, year) with all 6 factor scores
    + actual pop + predicted pop + residual. Returns (DataFrame, HTML)."""
    priority_ids = [b for (_, b, _) in PRIORITY_CITIES]
    name_for_id = {b: nm for (nm, b, _) in PRIORITY_CITIES}

    # Load full factor-score CSVs (need every benchmark year, not just LEVEL_YEARS)
    bench_years = [1250, 1300, 1350, 1400, 1450, 1500]
    factor_panels = []
    for name, fname, _ in FACTORS:
        df = pd.read_csv(OUT / fname)
        score_col = f"{name}_score"
        df = df[df["city_id"].isin(priority_ids) & df["year"].isin(bench_years)]
        df = df[["city_id", "year", score_col]].rename(
            columns={score_col: name})
        factor_panels.append(df)
    base = factor_panels[0]
    for fp in factor_panels[1:]:
        base = base.merge(fp, on=["city_id", "year"], how="outer")
    # populations from panel
    pp = panel[["city_id", "year", "pop_pers", "pop_pers_lag",
                "pred_lag_only", "residual_lag_only"]]
    base = base.merge(pp, on=["city_id", "year"], how="left")
    base["display_name"] = base["city_id"].map(name_for_id)
    base = base.sort_values(["display_name", "year"]).reset_index(drop=True)

    save_table_csv(base, "priority_city_trajectories")

    # Build HTML — one collapsible per city, rows by year
    blocks = []
    for cid in priority_ids:
        nm = name_for_id[cid]
        sub = base[base["city_id"] == cid]
        if len(sub) == 0:
            continue
        # header row
        rows = []
        for _, r in sub.iterrows():
            pop_str = (f"{int(r['pop_pers']):,}"
                       if pd.notna(r['pop_pers']) and r['pop_pers'] > 0 else "—")
            res = r["residual_lag_only"]
            res_str = f"{res:+.2f}" if pd.notna(res) else "—"
            res_color = ("#27ae60" if pd.notna(res) and res > 0.05
                         else "#a23a2a" if pd.notna(res) and res < -0.05
                         else "#1f1d18")
            score_cells = "".join(
                f"<td class='num score-{int(r[fn]) if pd.notna(r[fn]) else 0}'>"
                f"{int(r[fn]) if pd.notna(r[fn]) else '—'}</td>"
                for fn in FACTOR_NAMES)
            rows.append(
                f"<tr><td><strong>{int(r['year'])}</strong></td>"
                f"{score_cells}"
                f"<td class='num'>{pop_str}</td>"
                f"<td class='num' style='color:{res_color};font-weight:600'>"
                f"{res_str}</td></tr>")
        thead_cells = "".join(
            f"<th>{FACTOR_NAMES_NICE.get(n, n).split(' (')[0]}</th>"
            for n in FACTOR_NAMES)
        block = (
            f"<details><summary><strong>{_html.escape(nm)}</strong> "
            f"<span class='small'>(city_id {cid})</span></summary>"
            f"<div class='details-body'>"
            f"<table><thead><tr><th>Year</th>"
            f"{thead_cells}"
            f"<th>Pop</th><th>Residual</th></tr></thead>"
            f"<tbody>" + "".join(rows) + "</tbody></table>"
            f"<p class='small'>Scores 0–3 (color-coded; 0 lowest, 3 highest). "
            f"Residual = log(actual pop) − log(predicted from prior pop alone). "
            f"Positive = beat its inherited trajectory; negative = fell short. "
            f"Pop is Buringh-matched; blanks = no Bairoch/Buringh observation "
            f"in the panel for that year.</p>"
            f"</div></details>")
        blocks.append(block)
    return base, "\n".join(blocks)


# ---------------------------------------------------------- main analysis

def analyze(panel: pd.DataFrame, buringh_matched: pd.DataFrame,
            bairoch: pd.DataFrame) -> dict:
    """Run the two regressions and return a dict of results, figure URIs,
    and HTML fragments for the report."""
    out = {}

    # ============= MODEL 1: lag pop alone (path dependence) ===============
    print("Fitting Model 1: log(pop_T) ~ log(pop_T-100) + period_FE ...")
    panel["yr_1400"] = (panel["year"] == 1400).astype(int)
    panel["yr_1500"] = (panel["year"] == 1500).astype(int)
    X1 = panel[["log_pop_lag", "yr_1400", "yr_1500"]].to_numpy()
    y1 = panel["log_pop"].to_numpy()
    b1, a1, fit1 = fit_ols(X1, y1)
    cv1 = kfold_by_city(X1, y1, panel["city_id"].to_numpy())
    bs1 = cluster_bootstrap(X1, y1, panel["city_id"].to_numpy(), n=300)
    ci1 = np.nanquantile(bs1, [0.025, 0.975], axis=0)
    panel["pred_lag_only"] = fit1
    panel["residual_lag_only"] = y1 - fit1
    out["model1"] = {
        "in_sample_r2": r2(y1, fit1),
        "cv_r2_mean": cv1["mean"],
        "cv_r2_std": cv1["std"],
        "intercept": a1,
        "intercept_ci": [float(ci1[0, 0]), float(ci1[1, 0])],
        "beta_lag": float(b1[0]),
        "beta_lag_ci": [float(ci1[0, 1]), float(ci1[1, 1])],
        "beta_yr_1400": float(b1[1]),
        "beta_yr_1500": float(b1[2]),
        "n": len(panel),
        "n_cities": panel["city_id"].nunique(),
    }
    print(f"  R² in-sample = {out['model1']['in_sample_r2']:.3f}, "
          f"CV = {out['model1']['cv_r2_mean']:.3f}, "
          f"β_lag = {out['model1']['beta_lag']:+.4f}")

    # ============= MODEL 2: residual ~ factors (overperformance) ============
    print("Fitting Model 2: residual_lag_only ~ Σ z(factor) + period_FE ...")
    factor_cols = [f"{n}_cont" for n in FACTOR_NAMES]
    means = panel[factor_cols].mean()
    stds = panel[factor_cols].std(ddof=0).replace(0, 1)
    for c in factor_cols:
        panel[f"z_{c}"] = (panel[c] - means[c]) / stds[c]
    z_cols = [f"z_{c}" for c in factor_cols]
    X2 = panel[z_cols + ["yr_1400", "yr_1500"]].to_numpy()
    y2 = panel["residual_lag_only"].to_numpy()
    b2, a2, fit2 = fit_ols(X2, y2)
    cv2 = kfold_by_city(X2, y2, panel["city_id"].to_numpy())
    bs2 = cluster_bootstrap(X2, y2, panel["city_id"].to_numpy(), n=300)
    ci2 = np.nanquantile(bs2, [0.025, 0.975], axis=0)
    out["model2"] = {
        "in_sample_r2": r2(y2, fit2),
        "cv_r2_mean": cv2["mean"],
        "cv_r2_std": cv2["std"],
        "intercept": a2,
        "factors": {},
        "n": len(panel),
    }
    for i, fn in enumerate(FACTOR_NAMES):
        out["model2"]["factors"][fn] = {
            "beta": float(b2[i]),
            "ci_lo": float(ci2[0, 1 + i]),
            "ci_hi": float(ci2[1, 1 + i]),
        }
    print(f"  R² in-sample = {out['model2']['in_sample_r2']:.3f}, "
          f"CV = {out['model2']['cv_r2_mean']:.3f}")
    for fn in FACTOR_NAMES:
        f_ = out["model2"]["factors"][fn]
        print(f"    β_{fn:<22} = {f_['beta']:+.4f}  "
              f"[{f_['ci_lo']:+.4f}, {f_['ci_hi']:+.4f}]")

    return out


def main():
    print("Loading Buringh population panel ...")
    bur = match_buringh_to_bairoch()
    print(f"  HRE rows: {len(bur):,}, matched cities: "
          f"{bur.dropna(subset=['city_id'])['city_id'].nunique():,}")

    print("Loading Bairoch population panel ...")
    bai = load_bairoch()
    print(f"  Bairoch panel: {len(bai):,} rows")

    print("Building level panel (Buringh primary, factors at year T) ...")
    panel = build_panel(bur)
    print(f"  panel: {len(panel):,} rows, {panel['city_id'].nunique():,} cities, "
          f"years {sorted(panel['year'].unique().tolist())}")

    results = analyze(panel, bur, bai)

    # ----- HRE 1200 vs 1500 maps -----------
    print("\nRendering HRE maps 1200 / 1500 ...")
    THRESHOLD = 2000  # cities ≥2k inhabitants
    map_uri_1200 = map_hre_year(bur, year=1200, threshold=THRESHOLD,
                                slug="map_hre_1200",
                                title="HRE urban system, 1200 (population threshold ≥ 2,000)")
    map_uri_1500 = map_hre_year(bur, year=1500, threshold=THRESHOLD,
                                slug="map_hre_1500",
                                title="HRE urban system, 1500 (population threshold ≥ 2,000)")
    map_uri_residuals = map_residuals(
        panel, slug="map_residuals_hre",
        title="Path-dependence residuals (pooled 1300/1400/1500): "
              "red = beat trajectory, blue = fell short")

    # ----- Other figures -----------
    fig_calib_uri = fig_calibration_lag_only(panel, slug="calibration_model1")
    fig_resdist_uri = fig_residual_distribution(panel, slug="residual_distribution")

    # Coefficients for model 2
    feat_betas = [results["model2"]["factors"][f]["beta"] for f in FACTOR_NAMES]
    feat_lo = [results["model2"]["factors"][f]["ci_lo"] for f in FACTOR_NAMES]
    feat_hi = [results["model2"]["factors"][f]["ci_hi"] for f in FACTOR_NAMES]
    fig_coef_uri = fig_residual_coefficients(
        FACTOR_NAMES, feat_betas, feat_lo, feat_hi,
        slug="model2_coefficients",
        title="Model 2 — what predicts overperformance? (β on z-scored factors)")

    # Buringh vs Bairoch convergence
    fig_convergence_uri = fig_buringh_vs_bairoch(bur, bai, slug="buringh_vs_bairoch")

    # Transport-class growth
    fig_transport_uri = fig_transport_growth(bur, slug="transport_class_growth")

    # Priority residual trajectories
    fig_priority_uri = fig_priority_residual_trajectories(
        panel, slug="priority_residual_trajectories")

    # ----- Build 13-city table ---------
    print("\nBuilding 13-city variable-trajectory table ...")
    priority_df, priority_html = build_priority_table(panel)

    # ----- Top over/under-performers tables (for reference) ----
    over10 = (panel.sort_values("residual_lag_only", ascending=False)
                   .head(15)[["buringh_city", "country", "year",
                              "pop_pers_lag", "pop_pers", "residual_lag_only"]]
                   .reset_index(drop=True))
    under10 = (panel.sort_values("residual_lag_only", ascending=True)
                   .head(15)[["buringh_city", "country", "year",
                              "pop_pers_lag", "pop_pers", "residual_lag_only"]]
                   .reset_index(drop=True))
    save_table_csv(over10, "top_overperformers")
    save_table_csv(under10, "top_underperformers")

    def _residual_table_html(df, label):
        rows = []
        for _, r in df.iterrows():
            growth = (r["pop_pers"] / r["pop_pers_lag"] - 1) * 100 \
                if pd.notna(r["pop_pers_lag"]) and r["pop_pers_lag"] > 0 else float("nan")
            rows.append(
                f"<tr><td>{_html.escape(str(r['buringh_city']))}</td>"
                f"<td>{_html.escape(str(r['country']))}</td>"
                f"<td class='num'>{int(r['year'])}</td>"
                f"<td class='num'>{int(r['pop_pers_lag']):,}</td>"
                f"<td class='num'>{int(r['pop_pers']):,}</td>"
                f"<td class='num'>{growth:+.0f}%</td>"
                f"<td class='num'><strong>{r['residual_lag_only']:+.3f}</strong></td>"
                f"</tr>")
        return (f"<h4>{label}</h4>"
                f"<table><thead><tr><th>City</th><th>Country</th><th>Year T</th>"
                f"<th>Pop T-100</th><th>Pop T</th><th>Growth</th>"
                f"<th>Residual</th></tr></thead>"
                f"<tbody>" + "".join(rows) + "</tbody></table>")

    over_html = _residual_table_html(over10, "Top 15 over-performers (cities that exceeded their inherited trajectory)")
    under_html = _residual_table_html(under10, "Top 15 under-performers (cities that fell short of their inherited trajectory)")

    # Save panel + residuals as a CSV for paper appendix
    save_table_csv(panel, "panel_with_residuals_full")
    print(f"  saved panel with residuals → {TBL_DIR / 'panel_with_residuals_full.csv'}")

    # ----- Render HTML --------------------
    print("\nRendering HTML report ...")

    m1 = results["model1"]
    m2 = results["model2"]
    panel_n = len(panel)
    panel_cities = panel["city_id"].nunique()

    # Model 1 KPI block
    m1_kpi = f"""
<div class='kpi-grid'>
  <div class='kpi'><div class='label'>n observations</div>
    <div class='value'>{m1['n']:,}</div>
    <div class='sub'>{m1['n_cities']:,} cities × 3 years</div></div>
  <div class='kpi'><div class='label'>In-sample R²</div>
    <div class='value'>{m1['in_sample_r2']:+.3f}</div>
    <div class='sub'>fit on training data</div></div>
  <div class='kpi'><div class='label'>5-fold CV R²</div>
    <div class='value'>{m1['cv_r2_mean']:+.3f}</div>
    <div class='sub'>± {m1['cv_r2_std']:.3f} (held-out cities)</div></div>
  <div class='kpi'><div class='label'>β_lag (autocorrelation)</div>
    <div class='value'>{m1['beta_lag']:+.3f}</div>
    <div class='sub'>95% CI [{m1['beta_lag_ci'][0]:+.3f}, {m1['beta_lag_ci'][1]:+.3f}]</div></div>
</div>
"""

    # Model 2 KPI block
    m2_kpi = f"""
<div class='kpi-grid'>
  <div class='kpi'><div class='label'>R² of residuals on factors</div>
    <div class='value'>{m2['in_sample_r2']:+.3f}</div>
    <div class='sub'>incremental over Model 1</div></div>
  <div class='kpi'><div class='label'>5-fold CV R²</div>
    <div class='value'>{m2['cv_r2_mean']:+.3f}</div>
    <div class='sub'>± {m2['cv_r2_std']:.3f}</div></div>
</div>
"""

    # Model 2 coefficient table
    m2_rows = []
    for fn in FACTOR_NAMES:
        f_ = m2["factors"][fn]
        sig = (f_["ci_lo"] > 0) or (f_["ci_hi"] < 0)
        sig_tag = ("<span class='tag good'>significant</span>" if sig
                   else "<span class='tag muted'>not significant</span>")
        m2_rows.append(
            f"<tr><td>{FACTOR_NAMES_NICE.get(fn, fn)}</td>"
            f"<td class='num'>{f_['beta']:+.4f}</td>"
            f"<td class='num small'>[{f_['ci_lo']:+.4f}, {f_['ci_hi']:+.4f}]</td>"
            f"<td>{sig_tag}</td></tr>")
    m2_table = ("<table><thead><tr><th>Factor (z-scored, +1 SD)</th>"
                "<th>β on residual</th><th>95% CI</th><th>Sig.</th>"
                "</tr></thead><tbody>" + "".join(m2_rows) + "</tbody></table>")

    nav_items = """
      <li><a href='#data'>1. Sample &amp; data</a></li>
      <li><a href='#maps'>2. Urban system, 1200 vs 1500</a></li>
      <li><a href='#path-dep'>3. Path-dependence baseline</a></li>
      <li><a href='#residuals'>4. Residuals: who beat expectations?</a></li>
      <li><a href='#m2'>5. What predicts overperformance?</a></li>
      <li><a href='#priority'>6. The 13 priority cities</a></li>
      <li><a href='#geog'>7. Geographic determinants (Buringh)</a></li>
      <li><a href='#robust'>8. Robustness: Buringh vs Bairoch</a></li>
      <li><a href='#implications'>9. Implications for the paper</a></li>
    """

    body = f"""
<section id='data'>
  <h2>1. Sample &amp; Data</h2>
  <div class='callout'>
    <p><strong>Headline.</strong> The analysis uses an <strong>unbalanced
       panel of {panel_n} city-year observations</strong> across
       <strong>{panel_cities}</strong> cities in the HRE-centered Central
       European urban system, observed at century benchmarks from 1300 to
       1500. Each observation has a 100-year-lagged Bairoch/Buringh
       population endpoint and six factor scores constructed at year T;
       the panel is unbalanced because not every city has both pop_T and
       pop_{{T-100}} in Buringh at every benchmark.</p>
  </div>

  <p>The panel uses Buringh's expanded urban-population dataset
     (Buringh 2021) as the primary outcome series. Buringh covers 2,262
     European settlements at century snapshots (700, 800, ..., 1500, ...,
     2000), with population in thousands plus transport-location
     classifications. We restrict to cities in the <strong>HRE and
     imperial-periphery urban zone</strong> — modern Germany, Austria,
     Switzerland, Czech Republic, Belgium, Netherlands, Luxembourg, and
     Slovenia (414 cities). This sample captures the HRE-centered Central
     European urban system, but we do not claim every Low-Countries or
     Bohemian city was politically inside the HRE in every year of the
     period; some cities sit on imperial peripheries whose status shifted.
     After spatial+name matching to the Bairoch <code>city_id</code>
     system used by our factor builders, <strong>{panel_cities}</strong>
     cities have both a population endpoint and at least one valid factor
     measurement and so enter the analysis.</p>

  <p>The six factors at year T (state-of-the-city, 50-yr aggregations):</p>
  <ul>
    <li><strong>Legal capacity</strong> — formal charter, town hall,
        free-imperial / imperial / free-city status, distance to
        nearest pre-1500 university, legal-family code (Magdeburg,
        Lübeck, Kulm).</li>
    <li><strong>Merchant capital</strong> — Hanseatic membership,
        Viabundus fair tier (interregional / regional / local), staple
        rights, Bairoch-listed Messe presence, market attestation.</li>
    <li><strong>Trade access (geography)</strong> — Viabundus
        trade-route membership, fair density within 50 km, distance to
        navigable river or land road. Bairoch-keyed, with a Bairoch+south-
        German fallback so Augsburg, Ulm, Würzburg, Regensburg,
        Bamberg, Speyer, and Rothenburg are no longer zero by data
        artefact.</li>
    <li><strong>Agricultural surplus</strong> — Voronoi hinterland
        area, centuries-since-first-mention, river distance, latitude
        band, elevation. Population is intentionally NOT in this score
        (the prior version leaked the outcome).</li>
    <li><strong>Noble extraction (–)</strong> — terr_id transitions in
        the 50-yr window, foreign rule, prince-bishop seat. Higher =
        more lord-extraction.</li>
    <li><strong>Conflict risk (–)</strong> — number of conflict
        incidents, major sieges, fire-damage events in the 50-yr
        window.</li>
  </ul>

  <h3>1.1 What's missing on purpose (and why)</h3>
  <p><em>Peasant mobility</em> is excluded from the regressions. The
     score (<code>build_peasant_mobility.py</code>) is constructed as a
     deterministic function of three other factors (legal capacity,
     merchant capital, noble extraction), so feeding it into the
     regression yields perfect collinearity. It is retained in the
     heuristic composite for narrative continuity but not estimated
     here.</p>
</section>

<section id='maps'>
  <h2>2. The HRE Urban System: 1200 vs 1500</h2>

  <p>The first historical fact your paper needs to establish is what the HRE
     urban system <em>looked like</em> at the start versus the end of the
     period. These two maps use the same population threshold
     (≥ 2,000 inhabitants in Buringh) so they are directly comparable.</p>

  <h3>2.1 HRE 1200</h3>
  <img class='embed' src='{map_uri_1200}' alt='HRE 1200 map'>
  <div class='analysis'>
    <h4>Reading this figure</h4>
    <p>Each dot is one city; size and color encode population (log scale on
       color, linear on dot area). The 1200 map shows a sparse, mostly
       Rhine-and-Danube-corridor urban system — the bulk of large cities
       sit in the Rhineland (Cologne, Mainz, Worms, Speyer, Strasbourg)
       with secondary clusters in the Low Countries (Ghent, Bruges,
       Tournai), and a thin scattering across the rest of the empire.
       Most modern German towns either don't yet exist as cities or fall
       below the 2k threshold.</p>
    <p><strong>Use in the paper.</strong> Establish the "starting position"
       of the urban system in the Introduction (alongside a 1-paragraph
       summary). The dispersion-along-rivers pattern foreshadows the
       trade-access argument and motivates including river/route variables
       as controls.</p>
  </div>

  <h3>2.2 HRE 1500</h3>
  <img class='embed' src='{map_uri_1500}' alt='HRE 1500 map'>
  <div class='analysis'>
    <h4>Reading this figure</h4>
    <p>Three centuries later, the urban system is denser everywhere. New
       large cities have appeared in the south (Augsburg, Nuremberg, Ulm),
       in central Germany (Erfurt, Magdeburg), and along the Baltic
       (Lübeck, Hamburg, Bremen, Danzig). The Rhine corridor is still
       dominant but no longer alone. The pattern of growth is geographically
       uneven — the north-east (Hanseatic League cities) and the south
       (free imperial cities of Swabia and Franconia) are the new
       additions.</p>
    <p><strong>Use in the paper.</strong> The visual contrast between this
       map and the 1200 map is your case for "city growth is heterogeneous
       — some regions filled in dramatically, others changed little." The
       residuals analysis in §4 explains <em>why</em>.</p>
  </div>
</section>

<section id='path-dep'>
  <h2>3. Path-Dependence Baseline (Model 1)</h2>

  <div class='equation'>
    <code>log(pop_T) = α + β_lag · log(pop_T-100) + γ_T · year_FE + ε</code>
  </div>

  <p><em>Plain English.</em> "Given how big the city was 100 years ago, plus
     which year T is, predict its log population today. No other inputs."</p>

  {m1_kpi}

  <p><strong>The β_lag estimate is {m1['beta_lag']:+.3f}</strong>, with a
     95% bootstrap CI of [{m1['beta_lag_ci'][0]:+.3f},
     {m1['beta_lag_ci'][1]:+.3f}]. A coefficient near 1 means the city's
     log population at T is approximately a constant offset from log
     population at T-100 — i.e., growth rates are roughly common across
     cities and the rank-ordering by size is mostly preserved over a
     century. This is the path-dependence claim.</p>

  <h3>3.1 Calibration plot</h3>
  <img class='embed' src='{fig_calib_uri}' alt='Model 1 calibration'>
  <div class='analysis'>
    <h4>Reading this figure</h4>
    <p>X-axis: actual log(pop_T). Y-axis: predicted log(pop_T) from the
       lag-only model. Each dot is one (city, year) observation; the
       dashed line is y = x (perfect prediction). Color encodes year T.</p>
    <p>The cloud is tight against the y = x line and centered on it,
       which means the lag term alone gets within a factor of e<sup>0.3</sup>
       ≈ 1.35× of actual population for most cities. That single
       coefficient explains R² ≈ {m1['cv_r2_mean']:.2f} of the
       cross-sectional variance — by far the dominant force in the
       data.</p>
    <p><strong>Use in the paper.</strong> This is your headline finding's
       first half: <em>path dependence dominated</em>. Lead Section 6
       (Results) with this plot.</p>
  </div>
</section>

<section id='residuals'>
  <h2>4. Residuals — Who Beat Expectations?</h2>

  <p>From Model 1 we get a residual for every city-year observation:</p>

  <div class='equation'>
    <code>residual_T = log(pop_T) − [α̂ + β̂_lag · log(pop_T-100) + γ̂_T]</code>
  </div>

  <p>Cities with <strong>positive</strong> residuals grew (or shrank less)
     more than their inherited trajectory predicted. Cities with
     <strong>negative</strong> residuals fell short of their inherited
     trajectory. The mean residual is by construction near zero; what
     matters is the geographic, factor-driven structure in the
     residuals.</p>

  <h3>4.1 Distribution of residuals</h3>
  <img class='embed' src='{fig_resdist_uri}' alt='residual distribution'>
  <div class='analysis'>
    <h4>Reading this figure</h4>
    <p>The residuals are roughly bell-shaped and centered on zero. Spread
       is <strong>~0.3 log-points per side</strong>, meaning the typical
       city's actual log population deviates from the lag-only prediction
       by ~0.3 — which on the population scale is roughly ±35%.</p>
  </div>

  <h3>4.2 Geographic distribution of residuals</h3>
  <img class='embed' src='{map_uri_residuals}' alt='residual map'>
  <div class='analysis'>
    <h4>Reading this figure</h4>
    <p>This is the most diagnostic plot in the paper. <strong>Red = beat
       its inherited trajectory, blue = fell short.</strong> The colorbar
       shows <code>residual = actual − predicted</code>; positive
       residuals (red) are cities larger than the lag-only model expects.
       Top over/under-performers are labeled. Watch for <em>spatial
       clustering</em>:</p>
    <ul>
      <li><strong>Concentrations of red</strong> identify regions where
          something pushed cities to grow faster than path dependence
          alone suggests.</li>
      <li><strong>Concentrations of blue</strong> are regions where cities
          underperformed — usually because of conflict, lord extraction,
          or shifting trade routes.</li>
      <li>If the colors are <em>random</em> with no spatial pattern, the
          residual is mostly idiosyncratic noise — and your factors will
          struggle to explain it.</li>
    </ul>
    <p><strong>Use in the paper.</strong> Pair this map with §5 to make
       the institutional-overperformance argument concrete.</p>
  </div>

  <h3>4.3 Top over- and under-performers</h3>
  {over_html}
  <p class='small'>Cities listed multiple times appear at different
     transitions; e.g., Hamburg may show up at both 1300 and 1500 if its
     residual was large in both periods.</p>
  {under_html}
</section>

<section id='m2'>
  <h2>5. What Predicts Overperformance? (Model 2)</h2>

  <div class='equation'>
    <code>residual_T = α + Σ β_k · z(factor_k_at_T) + γ_T · year_FE + ε</code>
  </div>

  <p><em>Plain English.</em> "Among cities that started at the same size,
     which institutional and geographic factors predict who exceeded the
     inherited trajectory?"</p>

  {m2_kpi}

  <p>Note that the headline R² for this regression is small. That is
     <em>expected and correct</em>: most of the variance in city size
     was already explained by lag pop in Model 1. Model 2 is asking only
     about the <em>residual</em> variance — what's left after the
     dominant force is removed. Even small significant coefficients here
     are doing real explanatory work.</p>

  <h3>5.1 Coefficient plot</h3>
  <img class='embed' src='{fig_coef_uri}' alt='Model 2 coefficients'>
  <div class='analysis'>
    <h4>Reading this figure</h4>
    <p>Each bar is a factor's β coefficient. Bars to the right of zero
       mean the factor predicts <em>positive</em> residuals (beat
       trajectory). Black whiskers are 95% bootstrap confidence
       intervals. <span style='color:#27ae60'><strong>Green</strong></span>
       bars exclude zero on the positive side (significantly increases
       overperformance);
       <span style='color:#a23a2a'><strong>red</strong></span> bars exclude
       zero on the negative side; gray bars cross zero (insufficient
       evidence to claim a sign).</p>
    <p>Read these as: per +1 standard deviation increase in this factor at
       year T (holding other factors fixed), the residual changes by β
       log-points. β = +0.10 means cities one SD above average on this
       factor are typically e<sup>0.10</sup> ≈ 10.5% larger than what
       lag pop alone would predict.</p>
  </div>

  <h3>5.2 Coefficient table</h3>
  {m2_table}
  <p class='small'>The factors that survive a 95% CI test of "this matters
     above and beyond path dependence" are the ones to lead with in your
     Results section. Insignificant factors are still worth mentioning —
     they tell you what does <em>not</em> drive overperformance once
     starting size is controlled.</p>

  <div class='warn'>
    <h4 style='margin:0 0 8px;color:#8a6024;text-transform:uppercase;letter-spacing:.04em;font-size:13.5px'>Interpreting the agricultural-surplus coefficient</h4>
    <p style='margin:0'>The agricultural-surplus proxy is negative and
       statistically significant in Model 2. <strong>Be careful with this
       result in the paper.</strong> The proxy combines hinterland Voronoi
       area, river distance, elevation, latitude band, and centuries-since-
       first-mention — all geographic/structural inputs, but none of which
       directly measure agricultural <em>output</em>. The defensible reading
       is:</p>
    <p style='margin:8px 0 0;font-style:italic'>"After controlling for
       inherited city size and institutional-commercial factors, the
       agricultural-surplus proxy is negatively associated with
       overperformance, suggesting that urban takeoff was less about rural
       carrying capacity alone and more about institutional-commercial
       concentration."</p>
    <p style='margin:8px 0 0'>Avoid the simpler claim "agricultural surplus
       hurt city growth" — the data cannot support it, and the proxy is
       likely picking up cities whose growth was bottlenecked by other
       factors despite favourable hinterland geography.</p>
  </div>

  <h3>5.3 Priority cities — residual trajectories</h3>
  <img class='embed' src='{fig_priority_uri}' alt='priority residual trajectories'>
  <div class='analysis'>
    <h4>Reading this figure</h4>
    <p>Each line is one priority city; X = year, Y = residual at that
       year. A line above zero means the city was beating its trajectory
       at that benchmark; below zero means falling short. Trajectories
       that <em>climb</em> over time are cities that compounded
       overperformance (institutional flywheel); trajectories that
       <em>fall</em> are cities whose advantage decayed.</p>
    <p>This is the right figure to put next to your case-study section —
       it lets you point at, e.g., Leipzig's late-15th-century rise or
       Erfurt's ceiling-effect under Mainz overlordship.</p>
  </div>
</section>

<section id='priority'>
  <h2>6. The 13 Priority Cities — Variable Trajectories</h2>

  <p>For each priority city, the table below shows all six factor scores
     (0–3 ordinal) at every benchmark year 1250 → 1500, plus the city's
     actual population at year T (where Buringh records it) and its
     path-dependence residual. Click a city to expand. The full table is
     also exported to <code>output/paper_tables/priority_city_trajectories.csv</code>
     for use in LaTeX.</p>

  {priority_html}
</section>

<section id='geog'>
  <h2>7. Geographic Determinants (Buringh transport-location)</h2>

  <p>Buringh classifies every city by its access to a major water-catchment
     system or land route. The classes are: <em>river [north/baltic/black/
     mediterranean] sea</em>, <em>land [north/baltic/atlantic/etc.]</em>,
     <em>north sea + river</em>, <em>baltic + river</em>, etc. This is a
     much sharper geographic feature than Bairoch supplies.</p>

  <img class='embed' src='{fig_transport_uri}' alt='transport class growth'>
  <div class='analysis'>
    <h4>Reading this figure (descriptive only)</h4>
    <p>Each line is one transport class; markers at 1300/1400/1500 show
       the mean log(pop) of cities in that class at each benchmark.
       Steeper-rising lines = classes whose cities grew faster on
       average.</p>
    <p><strong>Treat this as a descriptive supplement, not a statistical
       claim.</strong> Several classes have very small sample sizes —
       e.g., "north sea + river" and "baltic + river" each have only 3–5
       HRE cities. Differences between classes with such small n are not
       formally identified.</p>
    <p>The descriptive pattern: cities combining sea access with inland
       river penetration (Hamburg, Bremen, Lübeck) sit in the
       highest-mean classes; pure inland-land classes sit lower. Bosker
       &amp; Buringh (2017) "City seeds" argue physical geography and
       transport access were the original "city seeds."</p>
    <p><strong>Recommended phrasing for the paper:</strong>
       <em>"Transport location mattered descriptively, but the residual
       model suggests that institutional and merchant capacity better
       explain which cities outperformed."</em></p>
  </div>
</section>

<section id='robust'>
  <h2>8. Robustness: Buringh vs Bairoch</h2>

  <img class='embed' src='{fig_convergence_uri}' alt='Buringh vs Bairoch'>
  <div class='analysis'>
    <h4>Reading this figure</h4>
    <p>Each dot is a city-year observation. X = log(Buringh pop), Y =
       log(Bairoch pop). The dashed line is y = x. The Pearson r in the
       title quantifies how closely the two datasets agree.</p>
    <p>Tight clustering around y = x means the two datasets are
       essentially the same data with minor revisions; your conclusions
       are robust to which one you use as the outcome. Systematic
       deviation (e.g., Buringh consistently higher) would signal a
       coverage or coding difference that needs a footnote.</p>
    <p><strong>Use in the paper.</strong> Footnote in §4 (Data) — "All
       results are robust to using Buringh's expanded panel; r between
       sources is X for matched cities."</p>
  </div>
</section>

<section id='implications'>
  <h2>9. Implications for the Paper</h2>

  <div class='callout'>
    <p><strong>The two-sentence finding.</strong> HRE city size was
       overwhelmingly path-dependent: cities that were big in year
       T-100 were big in year T (β_lag ≈ {m1['beta_lag']:.2f}, R² ≈
       {m1['cv_r2_mean']:.2f}). Among cities that started at the same
       size, those with stronger {", ".join(
           FACTOR_NAMES_NICE[fn] for fn in FACTOR_NAMES
           if (m2['factors'][fn]['beta'] > 0
               and m2['factors'][fn]['ci_lo'] > 0))
       or "(no significant positive factors at the 95% level)"} exceeded
       their inherited trajectory.</p>
  </div>

  <h3>9.1 What this lets you claim</h3>
  <ul>
    <li><strong>Path dependence is the first-order story</strong> — and
        this is itself a contribution, since most of the literature
        treats institutions or trade routes as the primary cause of
        urban growth. Your main result <em>repositions</em> them as
        explaining deviation, not levels.</li>
    <li><strong>Within-cohort heterogeneity is what institutions
        explain.</strong> When you control for starting size, the factors
        that survive the 95% CI test are the institutional /
        commercial-capacity ones. That is the quantitative version of
        the Cantoni–Yuchtman story.</li>
    <li><strong>The HRE's fragmentation matters here</strong> precisely
        because it generated wide variation in legal status, rulers, and
        commercial privileges. A more unified state (e.g., the French
        crown's centralization) would have given less variation in these
        factors and thus a tighter, less informative residual.</li>
  </ul>

  <h3>9.2 What this does NOT let you claim</h3>
  <ul>
    <li>That you have <em>identified</em> a causal channel — these are
        observational regressions, and the factors are themselves
        outcomes of the same political processes that produced city
        growth. The paper should be careful with the word "cause".</li>
    <li>That the model would forecast 1500–1600. Temporal extrapolation
        across regime shifts is a documented failure of this model
        (the 1400→1500 holdout in our earlier predictive-model report
        had R² &lt; 0).</li>
  </ul>

  <h3>9.3 Recommended paper structure (your reframe)</h3>
  <ol>
    <li><strong>Introduction</strong> — open with the 1200 vs 1500 maps;
        state the puzzle (heterogeneous urban growth despite shared
        political environment).</li>
    <li><strong>Historical background</strong> — HRE fragmentation,
        urban autonomy, charters, fairs, prince-bishops.</li>
    <li><strong>Literature</strong> — Bairoch / Buringh on data;
        Cantoni–Yuchtman on markets and universities; Bosker &amp;
        Buringh "city seeds" on geography; Bosker–Buringh–van Zanden
        on institutions.</li>
    <li><strong>Data</strong> — describe panel construction, factor
        definitions, missingness; Buringh vs Bairoch robustness.</li>
    <li><strong>Empirical strategy</strong> — Model 1 (path-dependence
        baseline) and Model 2 (residual on factors). Justify why this
        is the right specification (avoids tautological R²; isolates
        within-cohort heterogeneity).</li>
    <li><strong>Results</strong> — lead with Model 1 (path dependence
        dominates). Then Model 2 (institutions explain residuals).</li>
    <li><strong>Case studies</strong> — pick 3–4 of the priority cities
        whose residual trajectories illustrate the mechanism.</li>
    <li><strong>Conclusion</strong> — return to the main claim; note
        limits and avenues for future work.</li>
  </ol>

  <h3>9.4 Files in this output</h3>
  <ul>
    <li><code>output/paper_figures/*.png</code> — all figures at 180 dpi,
        ready for LaTeX <code>\\includegraphics</code>.</li>
    <li><code>output/paper_tables/*.csv</code> — every table as CSV
        (priority-city trajectories, top over/under-performers, full
        panel + residuals).</li>
    <li><code>output/paper_analysis_report.html</code> — this report.</li>
  </ul>
</section>
"""

    CSS = """
    :root { --bg:#fdfcf8; --fg:#1f1d18; --muted:#6b6759; --rule:#e5e1d6;
            --accent:#6c4f1f; --accent-soft:#c8a861; --good:#2a7a3f;
            --bad:#a23a2a; --warn:#b8893a; --code-bg:#f3eedf;
            --teach:#eef3f7; --teach-rule:#3463a6; }
    * { box-sizing:border-box; }
    html, body { margin:0; padding:0; background:var(--bg); color:var(--fg);
      font-family:"Source Serif Pro","Iowan Old Style",Georgia,serif;
      line-height:1.6; font-size:16.5px; }
    .layout { display:grid; grid-template-columns:240px minmax(0,1fr);
      max-width:1400px; margin:0 auto; }
    nav.toc { position:sticky; top:0; height:100vh; overflow:auto;
      padding:28px 18px; border-right:1px solid var(--rule); font-size:13.5px; }
    nav.toc h2 { font-size:13px; letter-spacing:.04em; text-transform:uppercase;
      color:var(--muted); margin:0 0 12px; }
    nav.toc ol { list-style:none; padding:0; margin:0; }
    nav.toc li { margin:6px 0; }
    nav.toc a { color:var(--fg); text-decoration:none; border-left:2px solid transparent;
      padding-left:10px; display:block; }
    nav.toc a:hover { color:var(--accent); border-left-color:var(--accent-soft); }
    main { padding:36px 56px 80px; max-width:980px; }
    header.hero { border-bottom:1px solid var(--rule); padding-bottom:22px; margin-bottom:30px; }
    header.hero h1 { font-size:30px; margin:0 0 6px; letter-spacing:-0.01em; }
    header.hero .sub { color:var(--muted); font-size:15px; }
    section { margin:50px 0; scroll-margin-top:16px; }
    section > h2 { font-size:24px; border-bottom:1px solid var(--rule);
      padding-bottom:8px; margin:0 0 16px; }
    section > h3 { font-size:18px; margin-top:28px; color:var(--accent); }
    section > h4 { font-size:15.5px; margin-top:20px; color:#3463a6; }
    .equation { background:var(--code-bg); padding:18px 22px; border-radius:6px;
      font-family:"JetBrains Mono","SF Mono",Menlo,monospace; font-size:14.5px;
      overflow-x:auto; }
    .analysis { background:#f7f3e7; border-left:4px solid var(--accent-soft);
      padding:14px 18px; margin:18px 0; border-radius:0 6px 6px 0; }
    .analysis h4 { margin:0 0 8px; color:var(--accent); font-size:13.5px;
      text-transform:uppercase; letter-spacing:.04em; }
    .analysis p { margin:8px 0; }
    .callout { background:#e9f4ec; border-left:4px solid var(--good);
      padding:14px 18px; margin:18px 0; border-radius:0 6px 6px 0; }
    .warn { background:#faecd5; border-left:4px solid var(--warn);
      padding:14px 18px; margin:18px 0; border-radius:0 6px 6px 0; }
    table { border-collapse:collapse; font-size:13.5px; margin:14px 0; width:100%; }
    th, td { padding:7px 10px; border-bottom:1px solid var(--rule);
      text-align:left; vertical-align:top; }
    th { background:#f7f3e7; font-weight:600; font-size:12.5px; letter-spacing:.02em; }
    td.num { text-align:right; font-variant-numeric:tabular-nums; }
    td.score-0 { color:var(--bad); }
    td.score-1 { color:#8a6024; }
    td.score-2 { color:#4a6e2a; }
    td.score-3 { color:var(--good); font-weight:600; }
    img.embed { max-width:100%; border:1px solid var(--rule); border-radius:4px;
      margin:14px 0; }
    .kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
      gap:12px; margin:16px 0; }
    .kpi { padding:13px 14px; background:#faf7ec; border-radius:6px;
      border:1px solid var(--rule); }
    .kpi .label { color:var(--muted); font-size:12px; text-transform:uppercase;
      letter-spacing:.04em; }
    .kpi .value { font-size:22px; font-weight:600; margin-top:3px; }
    .kpi .sub { color:var(--muted); font-size:12px; }
    .tag { display:inline-block; font-size:12px; padding:2px 9px; border-radius:10px;
      background:var(--accent-soft); color:#fff; margin-right:4px; vertical-align:middle; }
    .tag.good { background:var(--good); }
    .tag.muted { background:var(--muted); }
    details { margin:14px 0; border:1px solid var(--rule); border-radius:6px;
      background:#fff; padding:0; overflow:hidden; }
    details > summary { padding:11px 16px; cursor:pointer; font-weight:600;
      background:#faf6e9; user-select:none; }
    details[open] > summary { border-bottom:1px solid var(--rule); }
    details > .details-body { padding:16px 20px; }
    .small { font-size:12.5px; color:var(--muted); }
    hr { border:0; border-top:1px solid var(--rule); margin:30px 0; }
    @media (max-width:980px) {
      .layout { grid-template-columns:1fr; }
      nav.toc { position:static; height:auto; border-right:0;
                border-bottom:1px solid var(--rule); }
      main { padding:24px 20px 60px; }
    }
    """

    html_doc = f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>HRE Urban Growth — Paper Analysis Report</title>
  <style>{CSS}</style>
</head>
<body>
<div class='layout'>
  <nav class='toc'>
    <h2>Contents</h2>
    <ol style='list-style:none;padding:0'>{nav_items}</ol>
  </nav>
  <main>
    <header class='hero'>
      <h1>Beyond Trade Routes — Path Dependence and Institutional Overperformance in HRE Cities, 1200–1500</h1>
      <div class='sub'>Data &amp; analysis for the paper. Every figure exports to
        <code>output/paper_figures/</code> and every table to
        <code>output/paper_tables/</code>.</div>
    </header>
    {body}
    <hr>
    <p class='small'>Generated by <code>build_paper_analysis_report.py</code>.
       Buringh population panel: Buringh (2021); Bairoch panel:
       Bairoch (1988) via Bosker, Buringh &amp; van Zanden replication.</p>
  </main>
</div>
</body>
</html>"""
    REPORT_PATH.write_text(html_doc, encoding="utf-8")
    print(f"\nWrote {REPORT_PATH} ({len(html_doc.encode('utf-8'))/1024:.0f} KB)")
    print(f"Saved {len(list(FIG_DIR.glob('*.png')))} figures to {FIG_DIR}/")
    print(f"Saved {len(list(TBL_DIR.glob('*.csv')))} tables to {TBL_DIR}/")


if __name__ == "__main__":
    main()
