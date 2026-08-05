"""Headline figures for the findings report."""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from panel import load_buringh, wide_pop

FIG = Path(__file__).resolve().parent / "out" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
TH = 1000.0
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25})


def _zeta(pops):
    p = np.sort(pops[pops >= TH * 0.999])[::-1]
    rank = np.arange(1, len(p) + 1)
    r = sm.OLS(np.log(rank - 0.5), sm.add_constant(np.log(p))).fit()
    return -r.params[1]


def fig_privileges():
    """The causal null: naive association vs matched DiD."""
    fig, ax = plt.subplots(figsize=(7, 4.4))
    labels = ["Staple right", "Fair"]
    naive = [43, 31]         # % from TWFE
    did = [-9, 0]            # % from matched DiD
    x = np.arange(len(labels)); w = 0.36
    ax.bar(x - w/2, naive, w, label="Naïve association (two-way FE)", color="#c0392b")
    ax.bar(x + w/2, did, w, label="Causal effect (matched diff-in-diff)", color="#2c7fb8")
    for xi, v in zip(x - w/2, naive):
        ax.text(xi, v + 1, f"+{v}%", ha="center", fontsize=10, fontweight="bold")
    for xi, v in zip(x + w/2, did):
        ax.text(xi, v + (1 if v >= 0 else -3), f"{v:+d}%", ha="center", fontsize=10, fontweight="bold")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("Effect on city population")
    ax.set_title("Medieval commercial privileges did NOT cause growth\n"
                 "(they were awarded to cities that had already grown)", fontsize=11)
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout(); fig.savefig(FIG / "fig_privileges_causal_null.png"); plt.close(fig)


def fig_persistence(d):
    """Persistence: r2 of log pop_Y -> log pop1500, back to 800 CE."""
    ys = [800, 1000, 1200, 1300, 1400]
    r2s = []
    for y in ys:
        s = d.dropna(subset=[f"pop{y}", "pop1500"])
        s = s[(s[f"pop{y}"] >= TH) & (s["pop1500"] >= TH)]
        rho = np.corrcoef(np.log(s[f"pop{y}"]), np.log(s["pop1500"]))[0, 1]
        r2s.append(rho ** 2)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.plot(ys, r2s, "o-", color="#2c3e50", lw=2, ms=8)
    for y, r in zip(ys, r2s):
        ax.text(y, r + 0.015, f"{r:.2f}", ha="center", fontsize=9)
    ax.set_xlabel("City size measured in year …"); ax.set_ylabel("r² predicting size in 1500")
    ax.set_ylim(0, 0.85)
    ax.set_title("The urban hierarchy was locked in centuries early\n"
                 "A city's size in 800 CE still explains 40% of its size 700 years later")
    fig.tight_layout(); fig.savefig(FIG / "fig_persistence_depth.png"); plt.close(fig)


def fig_variance():
    """Shapley decomposition of 1500 log-size."""
    # of TOTAL variance: explained 0.693, luck 0.307. Within explained: shares.
    tot = 0.693
    parts = {"Inherited size / momentum\n(path dependence)": 0.687 * tot,
             "Deep origin (size in 800 CE)": 0.275 * tot,
             "Geography (direct)": 0.038 * tot,
             "Idiosyncratic (luck + noise)": 1 - tot}
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    left = 0
    colors = ["#34495e", "#2980b9", "#16a085", "#bdc3c7"]
    for (k, v), col in zip(parts.items(), colors):
        ax.barh(0, v, left=left, color=col, edgecolor="white")
        ax.text(left + v/2, 0, f"{v*100:.0f}%", ha="center", va="center",
                color="white" if col != "#bdc3c7" else "#333", fontweight="bold", fontsize=10)
        left += v
    ax.set_xlim(0, 1); ax.set_yticks([]); ax.set_xlabel("Share of variance in log city size, 1500")
    ax.legend(list(parts.keys()), loc="upper center", bbox_to_anchor=(0.5, -0.35),
              ncol=2, fontsize=8.5, frameon=False)
    ax.set_title("What determined how big a city was in 1500?")
    fig.tight_layout(); fig.savefig(FIG / "fig_variance_decomp.png", bbox_inches="tight"); plt.close(fig)


def fig_gibrat(d):
    """Growth vs initial size — the near-flat Gibrat relationship."""
    s = d[(d["pop1200"] >= TH) & (d["pop1500"] >= TH)].copy()
    s["l0"] = np.log(s["pop1200"]); s["g"] = np.log(s["pop1500"]) - s["l0"]
    r = sm.OLS(s["g"], sm.add_constant(s["l0"])).fit()
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.scatter(s["l0"], s["g"], s=14, alpha=0.35, color="#2c7fb8")
    xs = np.linspace(s["l0"].min(), s["l0"].max(), 50)
    ax.plot(xs, r.params.iloc[0] + r.params.iloc[1]*xs, color="#c0392b", lw=2,
            label=f"slope = {r.params.iloc[1]:+.2f}  (R²={r.rsquared:.02f})")
    ax.set_xlabel("log city size in 1200"); ax.set_ylabel("log growth 1200→1500")
    ax.set_title("Growth is almost independent of size (Gibrat's law)\n"
                 "Big and small cities grew at nearly the same rate — growth is ~random",
                 fontsize=11)
    ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "fig_gibrat.png"); plt.close(fig)


def fig_zipf(d):
    """Actual Zipf exponent path vs Gibrat-null simulation band."""
    from generative_model import estimate_and_simulate  # reuse? too heavy; recompute simply
    years = [1200, 1300, 1400, 1500]
    actual = [_zeta(d[f"pop{y}"].to_numpy()) for y in years]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.plot(years, actual, "o-", color="#c0392b", lw=2, ms=8, label="Actual HRE cities")
    ax.axhline(1.0, ls="--", color="gray", lw=1, label="Zipf's law (ζ=1)")
    # null band from generative model (hard-coded simulated means/bands)
    sim_mean = [1.263, 1.291, 1.368, 1.219]
    sim_lo = [1.26, 1.26, 1.32, 1.18]; sim_hi = [1.26, 1.32, 1.42, 1.26]
    ax.plot(years, sim_mean, "s--", color="#7f8c8d", label="Random-growth null (Gibrat)")
    ax.fill_between(years, sim_lo, sim_hi, color="#bdc3c7", alpha=0.4)
    for y, a in zip(years, actual):
        ax.text(y, a - 0.03, f"{a:.2f}", ha="center", fontsize=9, color="#c0392b")
    ax.set_xlabel("Year"); ax.set_ylabel("Zipf exponent ζ")
    ax.set_title("The urban hierarchy concentrated toward Zipf's law\n"
                 "Real cities (red) concentrated more than random growth predicts",
                 fontsize=11)
    ax.legend(fontsize=8.5)
    fig.tight_layout(); fig.savefig(FIG / "fig_zipf_evolution.png"); plt.close(fig)


if __name__ == "__main__":
    w = wide_pop(load_buringh(), years=(800, 1000, 1100, 1200, 1300, 1400, 1500))
    d = w[w["in_cne"]].copy()
    fig_privileges()
    fig_persistence(d)
    fig_variance()
    fig_gibrat(d)
    fig_zipf(d)
    print("figures written to", FIG)
    for p in sorted(FIG.glob("*.png")):
        print("  ", p.name)
