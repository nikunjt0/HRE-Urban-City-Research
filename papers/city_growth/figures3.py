"""Robustness figures: Bairoch vs Buringh."""
from __future__ import annotations
import numpy as np, pandas as pd, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"; FIG = OUT / "figures"
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.grid": True, "grid.alpha": 0.25})


def fig_agreement():
    m = pd.read_csv(OUT / "source_agreement.csv")
    r = json.load(open(OUT / "robustness_summary.json"))["agreement_r"]
    fig, ax = plt.subplots(figsize=(6.6, 6.4))
    x = np.log10(m["pop1500_bur"]); y = np.log10(m["pop1500_bai"])
    ax.scatter(x, y, s=16, alpha=0.4, color="#2c7fb8")
    lim = [np.log10(1000), np.log10(200000)]
    ax.plot(lim, lim, "--", color="#c0392b", lw=1.5, label="perfect agreement (45°)")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ticks = [1000, 3000, 10000, 30000, 100000]
    ax.set_xticks(np.log10(ticks)); ax.set_xticklabels([f"{t//1000}k" for t in ticks])
    ax.set_yticks(np.log10(ticks)); ax.set_yticklabels([f"{t//1000}k" for t in ticks])
    ax.set_xlabel("Buringh (2021) population, 1500")
    ax.set_ylabel("Bairoch (1988) population, 1500")
    ax.set_title(f"The two reconstructions agree closely\n"
                 f"correlation of log-populations r = {r:.2f}  (n = {len(m)} common cities)",
                 fontsize=11.5)
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout(); fig.savefig(FIG / "fig_source_agreement.png"); plt.close(fig)


def fig_robustness_bars():
    R = json.load(open(OUT / "robustness_summary.json"))
    metrics = [
        ("Persistence r²\n(1300→1500)", R["buringh"]["persist_1300"], R["bairoch"]["persist_1300"], 1),
        ("Momentum share of\nvariance in 1500 size", R["buringh"]["decomp_momentum"], R["bairoch"]["decomp_momentum"], 1),
        ("Water premium\n(per century)", R["buringh"]["water"], R["bairoch"]["water"], 1),
        ("Staple: naïve\nsize gap", R["buringh"]["staple_naive"], R["bairoch"]["staple_naive"], 1),
        ("Staple: causal\neffect (DiD)", R["buringh"]["staple_did"], R["bairoch"]["staple_did"], 1),
    ]
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    x = np.arange(len(metrics)); w = 0.38
    bur = [m[1] for m in metrics]; bai = [m[2] for m in metrics]
    ax.bar(x - w/2, bur, w, color="#34495e", label="Buringh (2021)")
    ax.bar(x + w/2, bai, w, color="#d99f2b", label="Bairoch (1988)")
    for xi, v in zip(x - w/2, bur):
        ax.text(xi, v + (0.02 if v >= 0 else -0.06), f"{v:+.2f}" if abs(v) < 1.2 else f"{v:.2f}",
                ha="center", fontsize=8.5, fontweight="bold")
    for xi, v in zip(x + w/2, bai):
        ax.text(xi, v + (0.02 if v >= 0 else -0.06), f"{v:+.2f}" if abs(v) < 1.2 else f"{v:.2f}",
                ha="center", fontsize=8.5, fontweight="bold")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([m[0] for m in metrics], fontsize=9)
    ax.set_ylabel("value")
    ax.set_title("Every core result holds across both population reconstructions\n"
                 "(persistence dominates; the staple's big raw size-gap collapses to ~zero causally)",
                 fontsize=11)
    ax.legend(fontsize=9.5)
    fig.tight_layout(); fig.savefig(FIG / "fig_robustness_bars.png"); plt.close(fig)


if __name__ == "__main__":
    fig_agreement(); fig_robustness_bars()
    print("wrote fig_source_agreement, fig_robustness_bars")
