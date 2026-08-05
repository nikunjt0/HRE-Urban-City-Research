"""Paper figures that depend on the city/charter/causal data."""
from __future__ import annotations
import numpy as np, pandas as pd, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.grid": True, "grid.alpha": 0.25})


def fig_causal():
    res = json.load(open(OUT / "causal_summary.json"))
    order = ["staple", "fair", "charter", "market"]
    names = {"staple": "Staple right\n(Viabundus)", "fair": "Trade fair\n(Viabundus)",
             "charter": "Town charter\n(Städtebuch)", "market": "Market right\n(Städtebuch)"}
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    x = np.arange(len(order)); w = 0.38
    naive = [res[k]["naive"] * 100 for k in order]
    did = [res[k]["did"] * 100 for k in order]
    lo = [(res[k]["did"] - res[k]["ci"][0]) * 100 for k in order]
    hi = [(res[k]["ci"][1] - res[k]["did"]) * 100 for k in order]
    b1 = ax.bar(x - w/2, naive, w, color="#c0392b", label="Naïve association (two-way fixed effects)")
    b2 = ax.bar(x + w/2, did, w, color="#2c7fb8", label="Causal effect (matched diff-in-diff, 95% CI)")
    ax.errorbar(x + w/2, did, yerr=[lo, hi], fmt="none", ecolor="#154360", capsize=4, lw=1.4)
    for xi, k in zip(x - w/2, order):
        p = res[k]["naive_p"]
        star = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else "n.s."
        ax.text(xi, res[k]["naive"]*100 + 1.5, f"{res[k]['naive']:+.0%}\n{star}", ha="center", fontsize=9, fontweight="bold")
    for xi, k in zip(x + w/2, order):
        ax.text(xi, res[k]["did"]*100 + (2.0 if res[k]["did"] >= 0 else -4), f"{res[k]['did']:+.0%}",
                ha="center", fontsize=9, fontweight="bold", color="#154360")
    ax.axhline(0, color="k", lw=0.9)
    ax.set_xticks(x); ax.set_xticklabels([names[k] for k in order])
    ax.set_ylabel("Effect on city population (%)")
    ax.set_title("Commercial privileges are associated with size — but did not CAUSE growth\n"
                 "Every causal estimate's confidence interval includes zero", fontsize=11.5)
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout(); fig.savefig(FIG / "fig_causal_consolidated.png"); plt.close(fig)


def _basin(r):
    if r["atlantic"] == 1 or r["northsea"] == 1:
        return "Atlantic / North Sea"
    if r["baltic"] == 1:
        return "Baltic"
    if r["medit"] == 1:
        return "Mediterranean"
    if r["on_river"] == 1:
        return "Inland river"
    return "Landlocked"


def fig_performers():
    import statsmodels.api as sm
    s = pd.read_csv(OUT / "city_performers.csv").copy()
    # residual vs PERSISTENCE ONLY, so geography is free to show up in the residual
    s["l1200"] = np.log(s["pop1200"]); s["l1500"] = np.log(s["pop1500"])
    r = sm.OLS(s["l1500"], sm.add_constant(s[["l1200"]])).fit()
    s["res_p"] = s["l1500"] - r.predict(sm.add_constant(s[["l1200"]]))
    s["basin"] = s.apply(_basin, axis=1)
    cmap = {"Atlantic / North Sea": "#1b7837", "Baltic": "#2c7fb8",
            "Mediterranean": "#c0392b", "Inland river": "#8c6d31", "Landlocked": "#7f7f7f"}
    top = s.nlargest(11, "res_p"); bot = s.nsmallest(11, "res_p")
    both = pd.concat([bot, top.iloc[::-1]])
    fig, ax = plt.subplots(figsize=(8.8, 6.6))
    y = np.arange(len(both))
    ax.barh(y, both["res_p"], color=[cmap[b] for b in both["basin"]])
    ax.set_yticks(y); ax.set_yticklabels(both["city"], fontsize=9)
    ax.axvline(0, color="k", lw=0.9)
    ax.set_xlabel("Residual: log(actual 1500 size) − log(size predicted by 1200 size alone)")
    ax.set_title("Who beat their history, 1200→1500?\n"
                 "Atlantic/North-Sea ports (green) rose; Mediterranean & landlocked river towns (red/brown) fell",
                 fontsize=11)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=k) for k, c in cmap.items()],
              loc="lower right", fontsize=8.5)
    fig.tight_layout(); fig.savefig(FIG / "fig_performers.png"); plt.close(fig)


def fig_water_timing():
    # coastal premium by sea basin & period (from water_timing.py output, hard-referenced)
    periods = ["1200–1300", "1300–1400", "1400–1500", "1500–1600"]
    atlns = [-0.02, -0.10, 0.16, 0.05]
    balt = [0.15, -0.04, 0.22, 0.15]
    med = [-0.08, -0.18, 0.25, 0.15]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    x = np.arange(len(periods)); w = 0.26
    ax.bar(x - w, atlns, w, label="Atlantic / North Sea", color="#1b7837")
    ax.bar(x, balt, w, label="Baltic", color="#2c7fb8")
    ax.bar(x + w, med, w, label="Mediterranean", color="#c0392b")
    ax.axhline(0, color="k", lw=0.9)
    ax.set_xticks(x); ax.set_xticklabels(periods)
    ax.set_ylabel("Extra log-growth vs landlocked (per century)")
    ax.set_title("The sea turned from liability to engine after 1400\n"
                 "Coastal premium by sea basin: negative during the plague, strongly positive after",
                 fontsize=11.5)
    ax.annotate("Black Death\nenters via ports", xy=(1, -0.16), xytext=(1.1, -0.05),
                fontsize=8.5, ha="left", arrowprops=dict(arrowstyle="->", color="gray"))
    ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "fig_water_timing.png"); plt.close(fig)


if __name__ == "__main__":
    fig_causal(); fig_performers(); fig_water_timing()
    print("wrote fig_causal_consolidated, fig_performers, fig_water_timing")
