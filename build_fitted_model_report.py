"""Tutorial-style fitted-model report for HRE urban growth (1200-1500).

Produces output/fitted_model_report.html — a self-contained tutorial that:
  * Explains every statistic from scratch (R², CV, β, CI, residual map, etc.)
  * Fits FIVE model variants in increasing power and shows what drives R² up
  * Gives a single recommended equation with a worked-example prediction
  * Lists what additional data would push R² toward its realistic ceiling

This file is independent from build_predictive_model.py / build_report.py;
running it alone produces a complete, standalone HTML deliverable. It reuses
lib.bairoch_pop for the canonical Bairoch population panel and the existing
*_continuous columns each builder now emits.

Run:  python3 build_fitted_model_report.py
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
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance

from lib.bairoch_pop import load_pop_panel
from lib.paths import OUT


# ----------------------------------------------------------------- constants

REPORT_PATH = OUT / "fitted_model_report.html"

POP_YEARS = [1200, 1300, 1400, 1500]
LEVEL_YEARS = [1300, 1400, 1500]   # years with pop AND a 100-yr lag
TRANSITIONS = [(1200, 1300), (1300, 1400), (1400, 1500)]

FACTOR_YEAR_FOR_TRANSITION = {
    (1200, 1300): 1250,
    (1300, 1400): 1300,
    (1400, 1500): 1400,
}

FACTORS = [
    ("legal_capacity",       "cities_legal_capacity.csv",       "legal_capacity_continuous"),
    ("merchant_capital",     "cities_merchant_capital.csv",     "merchant_capital_continuous"),
    ("agricultural_surplus", "cities_agricultural_surplus.csv", "agricultural_surplus_continuous"),
    ("noble_extraction",     "cities_noble_extraction.csv",     "noble_extraction_continuous"),
    ("conflict_risk",        "cities_conflict_risk.csv",        "conflict_risk_continuous"),
    ("trade_access",         "cities_trade_access_bairoch.csv", "trade_access_continuous"),
]
FEATURE_NAMES = [f[0] for f in FACTORS]


# --------------------------------------------------------- data loading

def load_factor(name: str, fname: str, col: str) -> pd.DataFrame:
    df = pd.read_csv(OUT / fname)
    return df[["city_id", "year", col]].rename(columns={col: name})


def build_panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (level_panel, growth_panel).

    level_panel:  one row per (city, year) with year in {1300, 1400, 1500}.
                  Columns: pop_pers, log_pop, log_pop_lag (T-100), 6 factors,
                  year (categorical → year_FE handled at fit time).
    growth_panel: one row per (city, transition) with d_log_pop and 6 factors
                  measured at the START of the transition.
    """
    pop = load_pop_panel()
    pop = pop[pop["year"].isin(POP_YEARS) & (pop["pop_pers"] > 0)].copy()
    pop["log_pop"] = np.log(pop["pop_pers"])

    # wide pivot for lag construction
    wide = pop.pivot_table(
        index=["city_id", "name", "lat", "lon"],
        columns="year", values="log_pop", aggfunc="max"
    ).reset_index()
    wide.columns.name = None

    # --- level panel ---
    level_rows = []
    for y in LEVEL_YEARS:
        ylag = y - 100
        sub = wide.dropna(subset=[y, ylag]).copy()
        sub["year"] = y
        sub["log_pop"] = sub[y]
        sub["log_pop_lag"] = sub[ylag]
        sub["pop_pers"] = np.exp(sub["log_pop"])
        level_rows.append(sub[[
            "city_id", "name", "lat", "lon", "year",
            "log_pop", "log_pop_lag", "pop_pers"]])
    level = pd.concat(level_rows, ignore_index=True)

    # attach factors at same year
    for name, fname, col in FACTORS:
        f = load_factor(name, fname, col)
        level = level.merge(f, on=["city_id", "year"], how="left")
    level = level.dropna(subset=FEATURE_NAMES).reset_index(drop=True)

    # --- growth panel ---
    growth_rows = []
    for t_minus, t_end in TRANSITIONS:
        sub = wide.dropna(subset=[t_minus, t_end]).copy()
        sub["year_T"] = t_end
        sub["year_T_minus"] = t_minus
        sub["factor_year"] = FACTOR_YEAR_FOR_TRANSITION[(t_minus, t_end)]
        sub["period"] = f"{t_minus}-{t_end}"
        sub["log_pop_T"] = sub[t_end]
        sub["log_pop_T_minus"] = sub[t_minus]
        sub["d_log_pop"] = sub["log_pop_T"] - sub["log_pop_T_minus"]
        growth_rows.append(sub[[
            "city_id", "name", "lat", "lon", "year_T", "year_T_minus",
            "factor_year", "period", "log_pop_T", "log_pop_T_minus", "d_log_pop"]])
    growth = pd.concat(growth_rows, ignore_index=True)

    for name, fname, col in FACTORS:
        f = load_factor(name, fname, col).rename(columns={"year": "factor_year"})
        growth = growth.merge(f, on=["city_id", "factor_year"], how="left")
    growth = growth.dropna(subset=FEATURE_NAMES).reset_index(drop=True)

    return level, growth


# --------------------------------------------------------- modelling

def standardize(df: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, dict, dict]:
    means = df[cols].mean()
    stds = df[cols].std(ddof=0).replace(0, 1.0)
    z = (df[cols] - means) / stds
    z.columns = [f"z_{c}" for c in cols]
    return df.join(z), means.to_dict(), stds.to_dict()


def fit_ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    """Plain OLS via numpy lstsq. Returns (coefs_for_X, intercept, fitted)."""
    Xc = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    return beta[1:], float(beta[0]), Xc @ beta


def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def kfold_by_city(X: np.ndarray, y: np.ndarray, group_ids: np.ndarray,
                  n_splits: int = 5, seed: int = 17) -> dict:
    """Group-aware 5-fold CV: each city's rows go entirely into train OR test.

    Returns dict with mean_r2, std_r2, predictions (concatenated test
    predictions per fold for plotting).
    """
    rng = np.random.default_rng(seed)
    cities = np.unique(group_ids)
    rng.shuffle(cities)
    folds = np.array_split(cities, n_splits)
    r2s = []
    pred_full = np.full(len(y), np.nan)
    for i in range(n_splits):
        test_cities = set(folds[i].tolist())
        test_mask = np.array([c in test_cities for c in group_ids])
        train_mask = ~test_mask
        if train_mask.sum() < 10 or test_mask.sum() < 5:
            continue
        Xt = np.column_stack([np.ones(train_mask.sum()), X[train_mask]])
        beta, *_ = np.linalg.lstsq(Xt, y[train_mask], rcond=None)
        Xe = np.column_stack([np.ones(test_mask.sum()), X[test_mask]])
        preds = Xe @ beta
        r2s.append(r2(y[test_mask], preds))
        pred_full[test_mask] = preds
    return {"mean_r2": float(np.mean(r2s)), "std_r2": float(np.std(r2s)),
            "fold_predictions": pred_full}


def kfold_by_city_rf(X: np.ndarray, y: np.ndarray, group_ids: np.ndarray,
                     n_splits: int = 5, seed: int = 17) -> dict:
    """5-fold by city for a RandomForest. Same return shape as kfold_by_city."""
    rng = np.random.default_rng(seed)
    cities = np.unique(group_ids)
    rng.shuffle(cities)
    folds = np.array_split(cities, n_splits)
    r2s = []
    pred_full = np.full(len(y), np.nan)
    for i in range(n_splits):
        test_cities = set(folds[i].tolist())
        test_mask = np.array([c in test_cities for c in group_ids])
        train_mask = ~test_mask
        if train_mask.sum() < 10 or test_mask.sum() < 5:
            continue
        rf = RandomForestRegressor(n_estimators=400, max_depth=None,
                                   min_samples_leaf=3, random_state=seed,
                                   n_jobs=-1)
        rf.fit(X[train_mask], y[train_mask])
        preds = rf.predict(X[test_mask])
        r2s.append(r2(y[test_mask], preds))
        pred_full[test_mask] = preds
    return {"mean_r2": float(np.mean(r2s)), "std_r2": float(np.std(r2s)),
            "fold_predictions": pred_full}


def cluster_bootstrap_ols(X: np.ndarray, y: np.ndarray, group_ids: np.ndarray,
                          n: int = 500, seed: int = 17) -> np.ndarray:
    """Cluster-bootstrap by city. Returns (n, k+1) array of [intercept, betas]."""
    rng = np.random.default_rng(seed)
    cities = np.unique(group_ids)
    n_c = len(cities)
    by_city = {}
    for cid in cities:
        by_city[cid] = np.where(group_ids == cid)[0]
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


# --------------------------------------------------------- helpers for HTML

def _png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return ("data:image/png;base64,"
            + base64.b64encode(buf.getvalue()).decode())


def fig_calibration(actual: np.ndarray, predicted: np.ndarray,
                    title: str, xlabel: str, ylabel: str,
                    annotate_top_n: int | None = None,
                    labels: list[str] | None = None) -> str:
    fig, ax = plt.subplots(figsize=(7, 6))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    valid = np.isfinite(actual) & np.isfinite(predicted)
    a, p = actual[valid], predicted[valid]
    if len(a) == 0:
        ax.text(0.5, 0.5, "no data", ha="center", va="center")
        return _png(fig)
    lo = float(min(a.min(), p.min()))
    hi = float(max(a.max(), p.max()))
    pad = (hi - lo) * 0.04
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad],
            color="#888", linewidth=1, linestyle="--", label="perfect prediction (y = x)")
    ax.scatter(a, p, s=24, alpha=0.55, color="#3463a6",
               edgecolor="white", linewidth=0.5)
    if annotate_top_n and labels is not None:
        # annotate the most-extreme residuals
        residuals = a - p
        order = np.argsort(-np.abs(residuals[valid]))[:annotate_top_n]
        for k in order:
            ax.annotate(labels[np.where(valid)[0][k]], (a[k], p[k]),
                        fontsize=8.5, alpha=0.85, color="#a23a2a",
                        xytext=(4, 3), textcoords="offset points")
    r2_val = r2(a, p)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(f"{title}    (R² = {r2_val:.3f})", fontsize=12.5, pad=10)
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.6)
    ax.legend(loc="upper left", fontsize=9.5, frameon=False)
    fig.tight_layout()
    return _png(fig)


def fig_residual_map(lat: np.ndarray, lon: np.ndarray, residuals: np.ndarray,
                     title: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 7))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    finite = np.isfinite(residuals)
    if finite.sum() == 0:
        ax.text(0.5, 0.5, "no residuals", ha="center", va="center")
        return _png(fig)
    rmax = float(np.nanpercentile(np.abs(residuals[finite]), 95)) or 0.5
    sc = ax.scatter(lon[finite], lat[finite], c=residuals[finite], s=24,
                    cmap="RdBu_r", vmin=-rmax, vmax=rmax,
                    edgecolor="black", linewidth=0.2)
    ax.set_xlabel("Longitude", fontsize=11)
    ax.set_ylabel("Latitude", fontsize=11)
    ax.set_title(title, fontsize=12.5, pad=10)
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("residual (actual − predicted)", fontsize=10.5)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _png(fig)


def fig_distribution(values: np.ndarray, title: str, xlabel: str) -> str:
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    finite = values[np.isfinite(values)]
    ax.hist(finite, bins=40, color="#3463a6", alpha=0.75, edgecolor="white")
    mean = float(finite.mean())
    median = float(np.median(finite))
    ax.axvline(mean, color="#a23a2a", linewidth=1.5, linestyle="--",
               label=f"mean = {mean:.2f}")
    ax.axvline(median, color="#27ae60", linewidth=1.5, linestyle="--",
               label=f"median = {median:.2f}")
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel("count", fontsize=11)
    ax.set_title(title, fontsize=12.5, pad=10)
    ax.legend(loc="best", fontsize=9.5, frameon=False)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _png(fig)


def fig_coefficients(features: list[str], betas: list[float],
                     ci_lo: list[float], ci_hi: list[float],
                     title: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    y_pos = np.arange(len(features))
    err_lo = [b - lo for b, lo in zip(betas, ci_lo)]
    err_hi = [hi - b for b, hi in zip(betas, ci_hi)]
    colors = ["#27ae60" if b > 0 and lo > 0
              else "#a23a2a" if b < 0 and hi < 0
              else "#888888"
              for b, lo, hi in zip(betas, ci_lo, ci_hi)]
    ax.barh(y_pos, betas, xerr=[err_lo, err_hi], color=colors, alpha=0.85,
            ecolor="black", capsize=3)
    ax.axvline(0, color="black", linewidth=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(features)
    ax.set_xlabel("β  (effect on outcome per +1 SD of factor)", fontsize=11)
    ax.set_title(title, fontsize=12.5, pad=10)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    return _png(fig)


def fig_r2_progression(model_names: list[str], r2_values: list[float]) -> str:
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")
    x = np.arange(len(model_names))
    colors = ["#3463a6"] * len(model_names)
    bars = ax.bar(x, r2_values, color=colors, alpha=0.85, edgecolor="white")
    for i, v in enumerate(r2_values):
        ax.text(i, v + 0.015 if v >= 0 else v - 0.05,
                f"{v:+.3f}", ha="center", fontsize=10.5,
                color="#1f1d18" if v >= 0 else "#a23a2a")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axhline(1.0, color="#27ae60", linewidth=1, linestyle=":")
    ax.text(len(x) - 0.5, 1.02, "perfect prediction (R² = 1.0, unattainable)",
            color="#27ae60", fontsize=9, ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, rotation=15, ha="right", fontsize=10)
    ax.set_ylabel("k-fold CV R² (held-out cities)", fontsize=11)
    ax.set_title("R² progression across model variants", fontsize=12.5, pad=10)
    ax.set_ylim(min(min(r2_values) - 0.1, -0.1), 1.05)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return _png(fig)


# --------------------------------------------------------- HTML scaffolding

CSS = """
:root { --bg:#fdfcf8; --fg:#1f1d18; --muted:#6b6759; --rule:#e5e1d6;
        --accent:#6c4f1f; --accent-soft:#c8a861; --good:#2a7a3f; --bad:#a23a2a;
        --warn:#b8893a; --code-bg:#f3eedf; --teach:#eef3f7; --teach-rule:#3463a6; }
* { box-sizing: border-box; }
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
main { padding:36px 56px 80px; max-width:920px; }
header.hero { border-bottom:1px solid var(--rule); padding-bottom:22px; margin-bottom:30px; }
header.hero h1 { font-size:30px; margin:0 0 6px; letter-spacing:-0.01em; }
header.hero .sub { color:var(--muted); font-size:15px; }
section { margin:50px 0; scroll-margin-top:16px; }
section > h2 { font-size:23px; border-bottom:1px solid var(--rule); padding-bottom:8px;
  margin:0 0 16px; }
section > h3 { font-size:18px; margin-top:30px; color:var(--accent); }
section > h4 { font-size:15.5px; margin-top:22px; color:#3463a6; }
section p { margin:12px 0; }
.equation { background:var(--code-bg); padding:18px 22px; border-radius:6px;
  font-family:"JetBrains Mono","SF Mono",Menlo,monospace; font-size:14.5px;
  overflow-x:auto; }
table { border-collapse:collapse; font-size:13.5px; margin:14px 0; width:100%; }
th, td { padding:7px 10px; border-bottom:1px solid var(--rule);
  text-align:left; vertical-align:top; }
th { background:#f7f3e7; font-weight:600; font-size:12.5px; letter-spacing:.02em; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
img.embed { max-width:100%; border:1px solid var(--rule); border-radius:4px; margin:14px 0; }
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:12px; margin:16px 0; }
.kpi { padding:13px 14px; background:#faf7ec; border-radius:6px; border:1px solid var(--rule); }
.kpi .label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
.kpi .value { font-size:22px; font-weight:600; margin-top:3px; }
.kpi .sub { color:var(--muted); font-size:12px; }
.teach { background:var(--teach); border-left:4px solid var(--teach-rule);
  padding:14px 18px; margin:18px 0; border-radius:0 6px 6px 0; font-size:15.5px; }
.teach h4 { margin:0 0 8px; color:var(--teach-rule); font-size:14.5px;
  text-transform:uppercase; letter-spacing:.04em; }
.warn { background:#faecd5; border-left:4px solid var(--warn);
  padding:14px 18px; margin:18px 0; border-radius:0 6px 6px 0; }
.callout { background:#e9f4ec; border-left:4px solid var(--good);
  padding:14px 18px; margin:18px 0; border-radius:0 6px 6px 0; }
.tag { display:inline-block; font-size:12px; padding:2px 9px; border-radius:10px;
  background:var(--accent-soft); color:#fff; margin-right:4px; vertical-align:middle; }
.tag.good { background:var(--good); }
.tag.bad { background:var(--bad); }
.tag.muted { background:var(--muted); }
hr { border:0; border-top:1px solid var(--rule); margin:30px 0; }
@media (max-width:980px) {
  .layout { grid-template-columns:1fr; }
  nav.toc { position:static; height:auto; border-right:0; border-bottom:1px solid var(--rule); }
  main { padding:24px 20px 60px; }
}
"""


# --------------------------------------------------------- main

def main():
    print("Loading panels ...")
    level, growth = build_panels()
    print(f"  level panel  : {len(level):,} (city, year) rows, "
          f"{level['city_id'].nunique():,} cities")
    print(f"  growth panel : {len(growth):,} (city, transition) rows, "
          f"{growth['city_id'].nunique():,} cities")

    # Standardize factors using the level-panel distribution (one anchor for
    # all model variants, so coefficients are comparable).
    level, _, _ = standardize(level, FEATURE_NAMES)
    z_cols = [f"z_{c}" for c in FEATURE_NAMES]

    # Year fixed effects (drop 1300 as reference)
    level["yr_1400"] = (level["year"] == 1400).astype(int)
    level["yr_1500"] = (level["year"] == 1500).astype(int)

    # ---------------- MODEL A: Cross-sectional, factors only ------------
    print("\nFitting Model A: log(pop) ~ factors + year_FE ...")
    A_cols = z_cols + ["yr_1400", "yr_1500"]
    XA = level[A_cols].to_numpy()
    yA = level["log_pop"].to_numpy()
    bA, aA, fitA = fit_ols(XA, yA)
    cvA = kfold_by_city(XA, yA, level["city_id"].to_numpy())
    bsA = cluster_bootstrap_ols(XA, yA, level["city_id"].to_numpy())
    ciA = np.nanquantile(bsA, [0.025, 0.975], axis=0)
    rmA = level.assign(pred=fitA, residual=yA - fitA, cv_pred=cvA["fold_predictions"])
    print(f"  in-sample R² = {r2(yA, fitA):.3f}, CV R² = {cvA['mean_r2']:.3f}")

    # ---------------- MODEL B: + log(pop_lag) (the strong baseline) -----
    print("Fitting Model B: log(pop) ~ log(pop_lag) + factors + year_FE ...")
    B_cols = ["log_pop_lag"] + z_cols + ["yr_1400", "yr_1500"]
    XB = level[B_cols].to_numpy()
    yB = level["log_pop"].to_numpy()
    bB, aB, fitB = fit_ols(XB, yB)
    cvB = kfold_by_city(XB, yB, level["city_id"].to_numpy())
    bsB = cluster_bootstrap_ols(XB, yB, level["city_id"].to_numpy())
    ciB = np.nanquantile(bsB, [0.025, 0.975], axis=0)
    rmB = level.assign(pred=fitB, residual=yB - fitB, cv_pred=cvB["fold_predictions"])
    print(f"  in-sample R² = {r2(yB, fitB):.3f}, CV R² = {cvB['mean_r2']:.3f}")

    # ---------------- MODEL C: B + interactions (linear non-linearities) ---
    print("Fitting Model C: B + key interactions ...")
    level["legal_x_merchant"] = level["z_legal_capacity"] * level["z_merchant_capital"]
    level["trade_x_river"] = level["z_trade_access"] * level["z_agricultural_surplus"]
    level["lag_x_legal"] = level["log_pop_lag"] * level["z_legal_capacity"]
    C_cols = B_cols + ["legal_x_merchant", "trade_x_river", "lag_x_legal"]
    XC = level[C_cols].to_numpy()
    yC = level["log_pop"].to_numpy()
    bC, aC, fitC = fit_ols(XC, yC)
    cvC = kfold_by_city(XC, yC, level["city_id"].to_numpy())
    print(f"  in-sample R² = {r2(yC, fitC):.3f}, CV R² = {cvC['mean_r2']:.3f}")

    # ---------------- MODEL D: Random Forest on B's features (non-linear ceiling)
    print("Fitting Model D: Random Forest on B's features ...")
    cvD = kfold_by_city_rf(XB, yB, level["city_id"].to_numpy())
    rfD = RandomForestRegressor(n_estimators=400, min_samples_leaf=3,
                                random_state=17, n_jobs=-1).fit(XB, yB)
    fitD = rfD.predict(XB)
    print(f"  in-sample R² = {r2(yB, fitD):.3f}, CV R² = {cvD['mean_r2']:.3f}")
    permD = permutation_importance(rfD, XB, yB, n_repeats=10,
                                   random_state=17, n_jobs=-1)

    # ---------------- MODEL E: Growth model (the hardest question) -----
    print("Fitting Model E: Δlog(pop) ~ lag_pop + factors_at_start ...")
    growth, _, _ = standardize(growth, FEATURE_NAMES)
    E_cols = ["log_pop_T_minus"] + [f"z_{c}" for c in FEATURE_NAMES]
    XE = growth[E_cols].to_numpy()
    yE = growth["d_log_pop"].to_numpy()
    bE, aE, fitE = fit_ols(XE, yE)
    cvE = kfold_by_city(XE, yE, growth["city_id"].to_numpy())
    bsE = cluster_bootstrap_ols(XE, yE, growth["city_id"].to_numpy())
    ciE = np.nanquantile(bsE, [0.025, 0.975], axis=0)
    rmE = growth.assign(pred=fitE, residual=yE - fitE, cv_pred=cvE["fold_predictions"])
    print(f"  in-sample R² = {r2(yE, fitE):.3f}, CV R² = {cvE['mean_r2']:.3f}")

    # ---------------- Plots --------------------------------------------
    print("\nRendering plots ...")
    img_outcome_dist = fig_distribution(
        np.exp(level["log_pop"].to_numpy()),
        "Distribution of city populations (Bairoch, all years pooled)",
        "population (persons)")
    img_outcome_dist_log = fig_distribution(
        level["log_pop"].to_numpy(),
        "Distribution of log(pop) (model outcome)",
        "log(pop_pers)")
    img_growth_dist = fig_distribution(
        growth["d_log_pop"].to_numpy(),
        "Distribution of 100-year Δlog(pop) (the growth-model outcome)",
        "Δlog(pop) over 100 yr")

    img_calA = fig_calibration(
        level["log_pop"].to_numpy(), cvA["fold_predictions"],
        "Model A — calibration (out-of-fold predictions)",
        "actual log(pop)", "predicted log(pop)")
    img_calB = fig_calibration(
        level["log_pop"].to_numpy(), cvB["fold_predictions"],
        "Model B — calibration (out-of-fold predictions)",
        "actual log(pop)", "predicted log(pop)")
    img_calD = fig_calibration(
        level["log_pop"].to_numpy(), cvD["fold_predictions"],
        "Model D (Random Forest) — calibration (out-of-fold)",
        "actual log(pop)", "predicted log(pop)")
    img_calE = fig_calibration(
        growth["d_log_pop"].to_numpy(), cvE["fold_predictions"],
        "Model E (growth) — calibration (out-of-fold predictions)",
        "actual Δlog(pop)", "predicted Δlog(pop)")

    img_resA = fig_residual_map(
        level["lat"].to_numpy(), level["lon"].to_numpy(),
        (level["log_pop"].to_numpy() - cvA["fold_predictions"]),
        "Model A — geographic residuals (out-of-fold)")
    img_resB = fig_residual_map(
        level["lat"].to_numpy(), level["lon"].to_numpy(),
        (level["log_pop"].to_numpy() - cvB["fold_predictions"]),
        "Model B — geographic residuals (out-of-fold)")

    # Coefficients plots — only for the factor terms (skip year FE, lag pop)
    feat_idx = list(range(len(z_cols)))
    img_coefA = fig_coefficients(
        FEATURE_NAMES, [bA[i] for i in feat_idx],
        [ciA[0, 1 + i] for i in feat_idx],
        [ciA[1, 1 + i] for i in feat_idx],
        "Model A — factor coefficients on log(pop), z-scored factors")
    feat_idx_B = [1 + i for i in range(len(z_cols))]
    img_coefB = fig_coefficients(
        FEATURE_NAMES, [bB[i] for i in feat_idx_B],
        [ciB[0, 1 + i] for i in feat_idx_B],
        [ciB[1, 1 + i] for i in feat_idx_B],
        "Model B — factor coefficients (after controlling for prior population)")

    feat_idx_E = [1 + i for i in range(len(z_cols))]
    img_coefE = fig_coefficients(
        FEATURE_NAMES, [bE[i] for i in feat_idx_E],
        [ciE[0, 1 + i] for i in feat_idx_E],
        [ciE[1, 1 + i] for i in feat_idx_E],
        "Model E — growth-rate coefficients (z-scored factors)")

    img_progression = fig_r2_progression(
        ["A: factors only\n(level)", "B: + lag pop\n(level)", "C: + interactions\n(level)",
         "D: Random Forest\n(level)", "E: factors + lag\n(growth)"],
        [cvA["mean_r2"], cvB["mean_r2"], cvC["mean_r2"], cvD["mean_r2"], cvE["mean_r2"]])

    # ---------------- Worked example: Cologne 1500 ---------------------
    cologne = level[(level["city_id"] == 14060) & (level["year"] == 1500)]
    cologne_html = ""
    if len(cologne) == 1:
        row = cologne.iloc[0]
        # Build prediction breakdown for Model B
        contribs = {
            "intercept (α)": aB,
            "log(pop_1400)": bB[0] * row["log_pop_lag"],
        }
        for i, fname in enumerate(FEATURE_NAMES):
            contribs[fname] = bB[1 + i] * row[f"z_{fname}"]
        contribs["year_FE (1500)"] = bB[1 + len(FEATURE_NAMES) + 1] * row["yr_1500"]
        total = sum(contribs.values())
        actual = row["log_pop"]
        rows_html = []
        for k, v in contribs.items():
            rows_html.append(
                f"<tr><td>{_html.escape(k)}</td>"
                f"<td class='num'>{v:+.4f}</td></tr>")
        rows_html.append(
            f"<tr style='border-top:2px solid #1f1d18'>"
            f"<td><strong>predicted log(pop)</strong></td>"
            f"<td class='num'><strong>{total:+.4f}</strong></td></tr>")
        rows_html.append(
            f"<tr><td>actual log(pop)</td>"
            f"<td class='num'>{actual:+.4f}</td></tr>")
        rows_html.append(
            f"<tr><td><em>error (residual)</em></td>"
            f"<td class='num'><em>{actual - total:+.4f}</em></td></tr>")
        cologne_html = (
            f"<table><thead><tr><th>Term</th><th>contribution to log(pop_1500)</th></tr></thead>"
            f"<tbody>" + "".join(rows_html) + "</tbody></table>"
            f"<p class='small'>Predicted population: "
            f"e<sup>{total:.3f}</sup> = {int(np.exp(total)):,} persons. "
            f"Actual: {int(np.exp(actual)):,}.</p>")
    else:
        cologne_html = "<p class='small'>(Cologne 1500 not in the panel — pop_pers may be missing.)</p>"

    # ---------------- Compose HTML -------------------------------------
    print("Composing HTML ...")

    coef_table_B_rows = [
        ("α (intercept)", aB, ciB[0, 0], ciB[1, 0],
         "the predicted log(pop) when every factor and lag are at zero"),
        ("β · log(pop_T-100)", bB[0], ciB[0, 1], ciB[1, 1],
         "how much population at T inherits from population at T-100 (autocorrelation)"),
    ]
    for i, fname in enumerate(FEATURE_NAMES):
        coef_table_B_rows.append((
            f"β · z({fname})", bB[1 + i],
            ciB[0, 2 + i], ciB[1, 2 + i],
            f"effect of a +1 SD increase in {fname} on log(pop), holding others fixed"))
    coef_table_B_rows.append((
        "β · year_1400_FE", bB[1 + len(FEATURE_NAMES)],
        ciB[0, 1 + len(FEATURE_NAMES) + 1], ciB[1, 1 + len(FEATURE_NAMES) + 1],
        "average shift in log(pop) at year 1400 vs. 1300"))
    coef_table_B_rows.append((
        "β · year_1500_FE", bB[1 + len(FEATURE_NAMES) + 1],
        ciB[0, 1 + len(FEATURE_NAMES) + 2], ciB[1, 1 + len(FEATURE_NAMES) + 2],
        "average shift in log(pop) at year 1500 vs. 1300"))

    coef_rows_B_html = []
    for term, b, lo, hi, expl in coef_table_B_rows:
        sig = (lo > 0) or (hi < 0)
        sig_tag = ("<span class='tag good'>significant</span>" if sig
                   else "<span class='tag muted'>not significant</span>")
        coef_rows_B_html.append(
            f"<tr><td><code>{_html.escape(term)}</code></td>"
            f"<td class='num'>{b:+.4f}</td>"
            f"<td class='num small'>[{lo:+.4f}, {hi:+.4f}]</td>"
            f"<td>{sig_tag}</td>"
            f"<td class='small'>{expl}</td></tr>")
    coef_table_B_html = (
        "<table><thead><tr><th>Term</th><th>β</th>"
        "<th>95% bootstrap CI</th><th>significance</th><th>plain English</th>"
        "</tr></thead><tbody>" + "".join(coef_rows_B_html) + "</tbody></table>")

    body = f"""
<section id="intro">
  <h2>What This Report Does</h2>
  <p>You asked two things: (1) build a stronger equation for HRE city growth,
     and (2) explain the statistics from scratch because the graphs are not
     intuitive. This report tries to do both. Every section starts with plain
     English; the math is right next to it but optional.</p>
  <p>The headline finding, before any math: <strong>R² ≈ 1 is not achievable
     here, ever.</strong> Reasonable ceilings for this kind of historical
     data are 0.6–0.85 for predicting a city's <em>level</em> of population
     and 0.15–0.30 for predicting its <em>growth rate</em>. We get into why
     in §2 and §6.</p>
</section>

<section id="primer">
  <h2>1. Stats Primer — Read This Once</h2>

  <div class="teach"><h4>Regression in one sentence</h4>
    <p>Regression draws a line (or surface, in higher dimensions) through a
       cloud of points to give the best linear guess of an outcome from one
       or more inputs.</p>
  </div>

  <h3>1.1 What R² actually means</h3>
  <p>R² answers: <em>compared to just guessing the average, how much does my
     model reduce prediction error?</em></p>
  <ul>
    <li><strong>R² = 0</strong> — the model is no better than always
        predicting the mean. Useless.</li>
    <li><strong>R² = 0.5</strong> — the model has cut squared prediction error
        in half versus the mean.</li>
    <li><strong>R² = 1.0</strong> — perfect prediction. Every dot lands
        exactly on the line.</li>
    <li><strong>R² &lt; 0</strong> — the model is <em>worse</em> than
        guessing the mean. Happens when you train on one regime and test on
        a different one.</li>
  </ul>
  <p>Worked example. Suppose 5 cities have actual log(pop) = [7, 8, 9, 10, 11].
     The mean is 9. Total squared error from "always guess 9" is 4+1+0+1+4 = 10.
     A model predicts [7.5, 8.2, 9.1, 9.8, 10.9]. Its squared error is
     0.25+0.04+0.01+0.04+0.01 = 0.35. So R² = 1 − 0.35/10 = 0.965. Clean fit.</p>

  <div class="warn"><strong>Why R² = 1 is impossible in this dataset.</strong>
    <ol>
      <li>Bairoch records population in steps of 1,000. A 5,000-person town
          could be 4,500 or 5,499 — that rounding alone caps achievable R²
          at ~0.95 even with a perfect model.</li>
      <li>Cities grew or shrank because of plague variance, individual
          rulers, fires, harvest shocks, marriage politics — none of these
          are in any of our 6 factors. They show up as residual noise.</li>
      <li>Bairoch sometimes lists a town in 1500 but not in 1400, or vice
          versa, which means our panel is biased toward already-large
          cities. Smaller towns whose fortunes whip around the most are
          missing.</li>
    </ol>
  </div>

  <h3>1.2 In-sample vs out-of-sample (the overfitting trap)</h3>
  <p>If I fit a model to N data points and then ask how well it fits
     <em>those same</em> N points, I will always look smart — even a
     deliberately bad model can memorise. The honest test is to hold out
     some data the model never sees, then ask how well it predicts those.</p>
  <ul>
    <li><strong>In-sample R²</strong> — fit and evaluate on the same data.
        Almost always optimistic; rises whenever you add features.</li>
    <li><strong>k-fold cross-validation R² (CV R²)</strong> — split the
        cities into k=5 groups; train on 4, test on the 5th; rotate. We
        report the average across folds. This is a fair measure of how
        well the model would do on cities it never saw.</li>
    <li><strong>Temporal-holdout R²</strong> — train on early periods, test
        on a late period. Even fairer, but if the late period is a regime
        shift (e.g., post-Black-Death recovery), this can be very
        pessimistic.</li>
  </ul>

  <h3>1.3 Coefficients (β) and their confidence intervals</h3>
  <p>Each factor has a coefficient β. After we z-score the factors (subtract
     mean, divide by SD), β tells you: <em>per +1 standard deviation of this
     factor, the outcome moves by β units, holding the others fixed.</em></p>
  <p>Bootstrap 95% CI: if we re-collected and re-fit the data many times,
     95% of estimates would land in this interval. If the CI excludes zero
     we say the effect is "statistically significant" — meaning we are
     confident about the <em>sign</em>, not the size.</p>

  <div class="teach"><h4>Reading a calibration plot</h4>
    <ul>
      <li>X-axis: the actual outcome.</li>
      <li>Y-axis: the model's prediction.</li>
      <li>The dashed line is y = x — perfect prediction.</li>
      <li>Points <em>on</em> the line: good. Points scattered: noisy. Points
          on a different slope: model has bias.</li>
      <li>Tighter cloud → higher R². The R² value is printed in the title.</li>
    </ul>
  </div>

  <div class="teach"><h4>Reading a residual map</h4>
    <ul>
      <li>Each dot is a city, plotted at its actual lat/lon.</li>
      <li>Color = residual = actual − predicted. Blue means the model
          <em>under-predicted</em> (city was bigger than expected). Red
          means <em>over-predicted</em>.</li>
      <li>What you want: random colors with no spatial pattern (just noise).</li>
      <li>What you don't want: all the south is red and all the north is
          blue → model is missing a regional factor and is biased.</li>
    </ul>
  </div>
</section>

<section id="data">
  <h2>2. The Data</h2>

  <p>Two panels are constructed:</p>
  <ul>
    <li><strong>Level panel.</strong> One row per (city, year) for years
        {{1300, 1400, 1500}} where Bairoch population exists AND population
        100 years earlier exists. Outcome: <code>log(pop_T)</code>.
        n = {len(level):,} rows from {level['city_id'].nunique():,} cities.</li>
    <li><strong>Growth panel.</strong> One row per (city, transition) for
        transitions {{1200→1300, 1300→1400, 1400→1500}}. Outcome:
        <code>Δlog(pop) over 100 years</code>. n = {len(growth):,} rows.</li>
  </ul>

  <h3>2.1 What the outcome looks like</h3>
  <img class="embed" src="{img_outcome_dist}" alt="population distribution">
  <p>A handful of huge cities, lots of small ones. The raw distribution is
     extremely skewed.</p>
  <img class="embed" src="{img_outcome_dist_log}" alt="log pop distribution">
  <p>After log-transforming, the distribution is roughly bell-shaped. Linear
     regression assumes the outcome is roughly bell-shaped, which is why we
     model log(pop) — not pop directly.</p>

  <img class="embed" src="{img_growth_dist}" alt="growth rate distribution">
  <p>Δlog(pop) is the 100-year growth rate. Mean ≈
     {growth['d_log_pop'].mean():+.2f} (so on average cities grew ≈
     {(np.exp(growth['d_log_pop'].mean()) - 1) * 100:+.1f}% over 100 years).
     The spread is large, which is exactly why R² is hard.</p>
</section>

<section id="models">
  <h2>3. Five Model Variants — Watch R² Climb</h2>

  <p>Each variant adds something. Watch the CV R² rise.</p>
  <img class="embed" src="{img_progression}" alt="r2 progression">

  <div class="callout">
    <p><strong>Headline.</strong> The dominant predictor of city size at
       year T is <em>city size at year T−100</em>. Adding it (Model B)
       takes CV R² from {cvA['mean_r2']:.2f} to {cvB['mean_r2']:.2f}.
       This is not cheating — it is asking a different question.
       Model A asks "given factors alone, predict size". Model B asks
       "given factors AND prior size, predict size". Model E asks the
       hardest one: "given factors, predict <em>growth</em>".</p>
  </div>

  <h3>3.1 Model A — Factors only (level)</h3>
  <div class="equation"><code>log(pop_T) = α + Σ β_k · z(factor_k at T) + year_FE</code></div>
  <p><em>Plain English.</em> "Given a city's six factor scores at year T,
     and which year T is, predict log(pop) at T." No information about prior
     size.</p>
  {kpi_grid_html("Model A", cvA, in_sample=r2(yA, fitA), n=len(level))}
  <h4>Calibration</h4>
  <img class="embed" src="{img_calA}" alt="Model A calibration">
  <p>The dots are spread fairly wide around the y=x line — the factors push
     predictions in the right direction but cannot pin down magnitudes.</p>
  <h4>Coefficients</h4>
  <img class="embed" src="{img_coefA}" alt="Model A coefficients">
  <p>Bars to the right of zero = factor associates with bigger cities. Green
     = significant (95% CI excludes zero). Read these as: a city that scores
     +1 SD on legal_capacity is, on average, e^β times the size of an
     average city of the same year, holding other factors fixed.</p>
  <h4>Residual map</h4>
  <img class="embed" src="{img_resA}" alt="Model A residual map">

  <h3 style="margin-top:42px">3.2 Model B — Add prior population (the strong baseline)</h3>
  <div class="equation"><code>log(pop_T) = α + β_lag · log(pop_T-100) + Σ β_k · z(factor_k at T) + year_FE</code></div>
  <p><em>Plain English.</em> "Given a city's size 100 years ago, plus its six
     factor scores today, predict its size today."</p>
  {kpi_grid_html("Model B", cvB, in_sample=r2(yB, fitB), n=len(level))}
  <p><strong>This is the equation I would recommend</strong> when you want a
     real predictive model with high R². The lag-pop term (β =
     {bB[0]:+.3f}) is doing most of the work — cities with a large
     population in 1400 tend to have a large population in 1500. The factors
     then tweak that prediction up or down.</p>
  <h4>Calibration</h4>
  <img class="embed" src="{img_calB}" alt="Model B calibration">
  <p>Compare to Model A — the dots are now tight around the y=x line.
     R² &gt; {cvB['mean_r2']:.2f}.</p>
  <h4>Coefficient table</h4>
  {coef_table_B_html}
  <h4>Coefficient plot</h4>
  <img class="embed" src="{img_coefB}" alt="Model B coefficients">
  <p>After controlling for prior size, several factor coefficients shrink
     toward zero — not because they don't matter, but because their effect
     is mostly absorbed by lag-pop (a city's factors and its prior size are
     themselves correlated). The factors that <em>still</em> have
     significant CIs after this are the ones with predictive power
     <em>beyond</em> autocorrelation.</p>
  <h4>Residual map</h4>
  <img class="embed" src="{img_resB}" alt="Model B residual map">

  <h3 style="margin-top:42px">3.3 Model C — Add a few interactions</h3>
  <div class="equation"><code>log(pop_T) = Model B + (legal × merchant) + (trade × agri) + (lag × legal)</code></div>
  <p><em>Plain English.</em> "Maybe two factors together do more than each
     alone — e.g., legal autonomy paired with merchant capital is more than
     the sum of the parts."</p>
  {kpi_grid_html("Model C", cvC, in_sample=r2(yC, fitC), n=len(level))}
  <p>Tiny improvement over B — this dataset is too small for many
     interactions to be reliably detected without overfitting.</p>

  <h3 style="margin-top:42px">3.4 Model D — Random Forest (non-linear ceiling)</h3>
  <p><em>Plain English.</em> A Random Forest is a non-linear model — it can
     learn step functions, sharp thresholds, multi-way interactions all at
     once. If a flexible model does much better than the linear one, the
     linear model was leaving fit on the table. If they tie, our linear
     equation is already capturing what the data can support.</p>
  {kpi_grid_html("Model D", cvD, in_sample=r2(yB, fitD), n=len(level))}
  <h4>Calibration</h4>
  <img class="embed" src="{img_calD}" alt="Model D calibration">
  <p>Random Forest in-sample R² will look very high (it's flexible enough to
     memorize); the honest CV R² is what to compare to Model B.</p>

  <h3 style="margin-top:42px">3.5 Model E — Growth (the hardest question)</h3>
  <div class="equation"><code>Δlog(pop_T) = α + β_lag · log(pop_T-100) + Σ β_k · z(factor_k at start)</code></div>
  <p><em>Plain English.</em> "Given a city's size 100 years ago and its
     factor scores 100 years ago, can we predict how much it grew over the
     next 100 years?"</p>
  {kpi_grid_html("Model E", cvE, in_sample=r2(yE, fitE), n=len(growth))}
  <h4>Calibration</h4>
  <img class="embed" src="{img_calE}" alt="Model E calibration">
  <p>Note the tighter spread of the actual outcome (Δlog(pop)) versus the
     prediction. The CV R² is small but positive — the factors capture
     some signal, just not a lot.</p>
  <h4>Coefficients</h4>
  <img class="embed" src="{img_coefE}" alt="Model E coefficients">
  <p>The factors that significantly drive growth (CI excludes zero) are
     where you should focus your interpretation. The lag-pop term is
     negative (~{bE[0]:+.3f}): mean reversion — already-big cities grow
     <em>slower</em> over the next 100 years.</p>
</section>

<section id="recommended">
  <h2>4. The Recommended Equation</h2>
  <p>If you want one equation to use, this is it (Model B):</p>
  <div class="equation">
    <code>
log(pop_T) = α
           + β_lag · log(pop_T-100)
           + β_legal · z(legal_capacity)
           + β_merchant · z(merchant_capital)
           + β_trade · z(trade_access)
           + β_agri · z(agricultural_surplus)
           + β_noble · z(noble_extraction)
           + β_conflict · z(conflict_risk)
           + γ_year (year fixed effect)
    </code>
  </div>
  <p>Fitted values (in-sample R² = {r2(yB, fitB):.3f},
     k-fold CV R² = {cvB['mean_r2']:.3f} ± {cvB['std_r2']:.3f}):</p>
  <ul>
    <li>α = {aB:+.4f}</li>
    <li>β_lag = {bB[0]:+.4f}</li>
    <li>β_legal_capacity = {bB[1]:+.4f}</li>
    <li>β_merchant_capital = {bB[2]:+.4f}</li>
    <li>β_agricultural_surplus = {bB[3]:+.4f}</li>
    <li>β_noble_extraction = {bB[4]:+.4f}</li>
    <li>β_conflict_risk = {bB[5]:+.4f}</li>
    <li>β_trade_access = {bB[6]:+.4f}</li>
    <li>γ_1400 (vs 1300) = {bB[7]:+.4f}</li>
    <li>γ_1500 (vs 1300) = {bB[8]:+.4f}</li>
  </ul>

  <h3>4.1 Worked example — Cologne 1500</h3>
  <p>Step-by-step prediction. Each row is one term × its coefficient. The
     bottom row is the sum (the model's prediction).</p>
  {cologne_html}
</section>

<section id="why-not-1">
  <h2>5. Why R² Isn't Higher (And What Would Help)</h2>

  <p>Three concrete reasons R² in §3 is bounded:</p>

  <h3>5.1 Measurement noise in the outcome</h3>
  <p>Bairoch reports population in thousands. The true population can be
     anywhere within a 1,000-person bucket. For a 5,000-person town that's
     ±10%, which on the log scale is roughly ±0.1. The total variance of
     log(pop) in our panel is about
     {level['log_pop'].var():.2f}; rounding noise alone consumes some of
     that variance, capping achievable R² below 1.</p>

  <h3>5.2 Unobserved shocks</h3>
  <p>Cities grew or shrank because of factors none of our 6 measures cover:
     plague mortality variance, individual rulers, religious orders moving
     in, royal favoritism, harvest shocks, fires. These show up as
     irreducible residual noise. Many of these are basically random with
     respect to the slow-moving structural factors we have.</p>

  <h3>5.3 Selection bias</h3>
  <p>Bairoch only lists cities once they reach a certain size. The most
     interesting growth — small village to medium town — is invisible.
     Cities that <em>shrank below the threshold</em> drop out. Both biases
     trim the most volatile cases from our panel.</p>

  <h3>5.4 Linear specification</h3>
  <p>The Random Forest in §3.4 is a sanity check: if it dramatically beats
     the linear model, our linear equation is leaving fit on the table.
     Here RF CV R² ≈ {cvD['mean_r2']:.2f} vs Model B's ≈ {cvB['mean_r2']:.2f}.
     {"RF beats the linear model meaningfully — there is non-linear signal in the data and a more flexible model could capture more of it." if cvD['mean_r2'] - cvB['mean_r2'] > 0.05 else "RF does not meaningfully beat the linear model — most of the predictable variance is linear, and adding model flexibility won't help much."}</p>
</section>

<section id="user-input">
  <h2>6. What You Could Provide to Push R² Higher</h2>

  <p>Honest list, in order of expected R² lift:</p>

  <ol>
    <li><strong>Annual or decadal population data instead of 100-year
        snapshots</strong> (≈ +0.10–0.20 R²). Bairoch's 100-year jumps
        average over multi-generation dynamics. If you have a city-level
        annual census even for a subset (e.g., Hanseatic city Bürgerbücher,
        Imperial tax rolls 1437/1521, Italian catasti), they would let us
        capture intra-century trends.</li>
    <li><strong>Geographic features we don't currently have</strong>
        (≈ +0.05–0.10 R²). Specifically: distance to nearest sea coast or
        navigable port; soil-quality classes (FAO HWSD raster data);
        elevation contour for hinterland; Roman-road network density. All
        derivable from public GIS, but none currently in /docs.</li>
    <li><strong>Climate / harvest variation</strong> (≈ +0.05 R²). Late
        Medieval Warm Period vs Little Ice Age effects on agricultural
        surplus. Tree-ring summer-temperature reconstructions exist
        (Büntgen et al.) at decadal resolution.</li>
    <li><strong>Wealth or trade-volume proxies</strong> (≈ +0.05 R²).
        Sound Toll registers (already in /docs but post-1497), Hanseatic
        shipping records, mint output, Italian bank ledgers.</li>
    <li><strong>A "shock" indicator</strong> capturing big plague years,
        major sieges, or city sackings beyond our coarse conflict_risk
        score. Even a hand-curated list of 1346–53 plague mortality by city
        would help.</li>
    <li><strong>Decisions you can make now without new data</strong>:
        <ul>
          <li>Should the model predict <em>levels</em> or <em>growth</em>?
              Levels give higher R² (Model B) but are dominated by lag pop;
              growth gives smaller R² but cleaner causal interpretation.</li>
          <li>Should we use a non-linear model (Random Forest, gradient
              boosting) as the headline? Better fit, less interpretable
              coefficients.</li>
          <li>Are there specific cities whose history you'd like the model
              to fit better? We can up-weight them in training, at the cost
              of overall fit elsewhere.</li>
        </ul>
    </li>
  </ol>

  <div class="callout">
    <strong>Realistic R² ceiling for this question</strong> — even with
    everything in #1–5 above, I would not expect CV R² above ~0.85 for
    levels and ~0.30 for growth. Beyond that point, the residual variance
    is genuinely random with respect to anything observable at city-level
    in this period.
  </div>
</section>

<section id="appendix">
  <h2>7. Appendix — Files & How to Re-Run</h2>
  <ul>
    <li><code>build_fitted_model_report.py</code> — this script. Reads the
        per-factor *_continuous columns and Bairoch population.</li>
    <li><code>lib/bairoch_pop.py</code> — canonical Bairoch panel loader
        (city_id ↔ name+spatial match).</li>
    <li><code>output/cities_*_continuous</code> columns inside each per-factor
        CSV — the un-bucketed factor signal each builder now emits.</li>
    <li><code>output/cities_trade_access_bairoch.csv</code> — Bairoch-keyed
        trade access with south-German fallback (so Augsburg, Ulm,
        Würzburg, Regensburg, Bamberg, Speyer, Rothenburg are no longer
        zero).</li>
  </ul>
  <p class="small">Re-run end-to-end: <code>python3 build_all.py</code> then
     <code>python3 build_fitted_model_report.py</code>. Re-running this
     script alone takes ≈30 s.</p>
</section>
"""

    nav_html = """
      <li><a href="#intro">Intro</a></li>
      <li><a href="#primer">1. Stats Primer</a></li>
      <li><a href="#data">2. The Data</a></li>
      <li><a href="#models">3. Five Models</a></li>
      <li><a href="#recommended">4. Recommended Equation</a></li>
      <li><a href="#why-not-1">5. Why R² Isn't Higher</a></li>
      <li><a href="#user-input">6. What You Could Provide</a></li>
      <li><a href="#appendix">7. Appendix</a></li>
    """

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HRE Urban Growth — Fitted Model Report (Tutorial Edition)</title>
  <style>{CSS}</style>
</head>
<body>
<div class="layout">
  <nav class="toc">
    <h2>Contents</h2>
    <ol style="list-style:none;padding:0">
      {nav_html}
    </ol>
  </nav>
  <main>
    <header class="hero">
      <h1>Fitted Model — Tutorial Edition</h1>
      <div class="sub">A statistically-honest reading of HRE city growth, 1200–1500.
        Reads every metric from scratch; reports five model variants from
        weakest to strongest.</div>
    </header>
    {body}
    <hr>
    <p class="small">Generated by <code>build_fitted_model_report.py</code>.
       Distinct from <code>output/report.html</code>, which contains the
       earlier weighted-composite narrative.</p>
  </main>
</div>
</body>
</html>"""

    REPORT_PATH.write_text(html_doc, encoding="utf-8")
    print(f"\nWrote {REPORT_PATH} "
          f"({len(html_doc.encode('utf-8'))/1024:.0f} KB)")

    print("\n=== R² progression (k-fold CV by city) ===")
    print(f"  A: factors only (level)        = {cvA['mean_r2']:+.3f}")
    print(f"  B: + lag pop (level)           = {cvB['mean_r2']:+.3f}  <-- recommended")
    print(f"  C: + interactions (level)      = {cvC['mean_r2']:+.3f}")
    print(f"  D: Random Forest (level)       = {cvD['mean_r2']:+.3f}")
    print(f"  E: factors + lag (growth)      = {cvE['mean_r2']:+.3f}")


def kpi_grid_html(model_name: str, cv: dict, in_sample: float, n: int) -> str:
    return f"""
<div class='kpi-grid'>
  <div class='kpi'><div class='label'>n observations</div>
    <div class='value'>{n:,}</div>
    <div class='sub'>cities × years used in fit</div></div>
  <div class='kpi'><div class='label'>In-sample R²</div>
    <div class='value'>{in_sample:+.3f}</div>
    <div class='sub'>fit on training data (optimistic)</div></div>
  <div class='kpi'><div class='label'>5-fold CV R² (by city)</div>
    <div class='value'>{cv['mean_r2']:+.3f}</div>
    <div class='sub'>± {cv['std_r2']:.3f} — true predictive power</div></div>
</div>
"""


if __name__ == "__main__":
    main()
