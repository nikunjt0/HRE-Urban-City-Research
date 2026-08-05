"""Figures for the politics & policy paper. Writes to out/politics/figures/."""
from __future__ import annotations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "politics"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)

C_POS, C_NEG, C_NULL = "#2a9d8f", "#c1121f", "#8d99ae"


def jload(name):
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else {}


def fig_ledger():
    """Forest plot: the political ledger — what moved cities and what didn't."""
    eu = jload("europe_regressions.json")
    rb = jload("europe_robustness.json")
    ts = jload("timing_succession.json")
    de = jload("decadal_twfe.json")
    gr = jload("regime_regressions.json")
    # continuous regressors scaled to a 1-SD dose so magnitudes are comparable
    SD_PARL, SD_DEPO, SD_PLED = 0.5, 3.166, 0.099
    def sc(cv, f):
        return [cv[0] * f, cv[1] * f, cv[2]]
    rows = [
        ("Capital city status (0/1)", eu["E2b_city_FE_europe"]["coef"]["capital"], "pos"),
        ("Parliament activity (+1 sd)", sc(eu["E2b_city_FE_europe"]["coef"]["parl_act"], SD_PARL), "pos"),
        ("Gain of free (non-absolutist) rule (0/1)", rb["R6_gain_vs_loss"]["coef"]["gain_free"], "pos"),
        ("Ruler deposition rate (+1 sd)", sc(ts["T2a_succession_cityFE"]["coef"]["depo_rate"], SD_DEPO), "neg"),
        ("Time pledged to creditors (+1 sd, DE)", sc(gr["A2_types_plus_instability"]["coef"]["share_pledged"], SD_PLED), "neg"),
        ("Commune / self-governance (0/1)", eu["E2b_city_FE_europe"]["coef"]["commune"], "null"),
        ("Primogeniture succession law (0/1)", ts["T2a_succession_cityFE"]["coef"]["primo"], "null"),
        ("Church vs secular lord (DE)", gr["A3_city_FE"]["coef"]["share_church"], "null"),
        ("Self-rule share (DE, city FE)", gr["A3_city_FE"]["coef"]["share_self"], "null"),
        ("Ruler turnover, +1 change/century (DE)", gr["A3_city_FE"]["coef"]["turnover"], "null"),
        ("University founded (0/1)", eu["E2b_city_FE_europe"]["coef"]["university"], "null"),
    ]
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ys = np.arange(len(rows))[::-1]
    for y, (label, (b, se, p), sign) in zip(ys, rows):
        col = {"pos": C_POS, "neg": C_NEG, "null": C_NULL}[sign]
        ax.errorbar(b, y, xerr=1.96 * se, fmt="o", color=col, capsize=3, lw=2, ms=7)
        ax.text(-0.02, y, label, ha="right", va="center", fontsize=9,
                transform=ax.get_yaxis_transform())
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks([])
    ax.set_xlabel("effect on city population growth (log points per century, 95% CI)")
    ax.set_title("The political ledger: what actually moved cities, 800–1800\n"
                 "(population-growth outcomes; city & century FE where marked)")
    for spine in ["left", "top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "fig_political_ledger.png", dpi=200)
    plt.close(fig)


def fig_freeprince_es():
    rb = jload("europe_robustness.json")
    co = rb["R5_freeprince_es_long"]["coef"]
    ks = ["es_m3", "es_m2", "es_p0", "es_p1", "es_p2", "es_p3"]
    x = [-3, -2, 0, 1, 2, 3]
    b = [co[k][0] for k in ks]
    se = [co[k][1] for k in ks]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.errorbar(x, b, yerr=[1.96 * s for s in se], fmt="o-", color=C_POS,
                capsize=3, lw=1.6)
    ax.scatter([-1], [0], color="k", zorder=5)
    ax.axhline(0, color="k", lw=0.8)
    ax.axvline(-0.5, color="k", lw=0.8, ls="--")
    ax.set_xlabel("centuries relative to switch to free (non-absolutist) rule")
    ax.set_ylabel("Δ log city population per century")
    ax.set_title("Becoming 'free': growth dynamics around regime change\n(546 European cities, city & century FE)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_freeprince_eventstudy.png", dpi=200)
    plt.close(fig)


def fig_league():
    lg = pd.read_csv(OUT / "dynasty_league.csv")
    lg = lg[lg.n >= 8].sort_values("shrunk")
    show = pd.concat([lg.head(10), lg.tail(10)])
    names = [n if len(n) < 42 else n[:39] + "…" for n in show.terr_name]
    cols = [C_NEG if v < 0 else C_POS for v in show.shrunk]
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(range(len(show)), show.shrunk * 100, color=cols)
    ax.set_yticks(range(len(show)), names, fontsize=8)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("city growth vs expectation, % per century (shrunken)")
    ax.set_title("League table of rulers: whose cities beat their fundamentals?\n(German lands 1300–1800, net of size, water access, era)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_dynasty_league.png", dpi=200)
    plt.close(fig)


def fig_liberty_scale():
    """Marginal effect of commune by city size (pooled EU estimates)."""
    b0, b1 = 0.0511, 0.1051   # commune, commune x lpop_c (pooled spec)
    se0, se1, cov = 0.0272, 0.0372, 0.0  # cov approx 0 (conservative)
    lp = np.linspace(-1.6, 2.2, 60)      # lpop_c range ~ 5k to ~ 60k+
    eff = b0 + b1 * lp
    se = np.sqrt(se0**2 + (lp * se1) ** 2)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.plot(lp, eff, color=C_POS, lw=2)
    ax.fill_between(lp, eff - 1.96 * se, eff + 1.96 * se, color=C_POS, alpha=0.18)
    ax.axhline(0, color="k", lw=0.8)
    xt = np.log(np.array([5, 10, 20, 40, 80]) / 18.0)  # approx mean ~18k
    ax.set_xticks(xt, ["5k", "10k", "20k", "40k", "80k"])
    ax.set_xlabel("city population at start of century")
    ax.set_ylabel("commune effect on growth (log pts/century)")
    ax.set_title("Liberty needed scale: self-governance paid only in big cities")
    fig.tight_layout()
    fig.savefig(FIG / "fig_liberty_scale.png", dpi=200)
    plt.close(fig)


def fig_es_dynamics():
    es = jload("event_studies.json")
    if not es:
        return
    panels = [("PLG_y", "City pledged to creditors"),
              ("OCC_y", "City occupied"),
              ("EXT_y", "Ruler line dies out (quasi-random change)"),
              ("SELFGAIN_y", "City gains self-rule")]
    panels = [(k, t) for k, t in panels if k in es]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    for ax, (k, title) in zip(axes.flat, panels):
        co = es[k]["coefs"]
        xs, bs, ses = [], [], []
        for kk, v in co.items():
            sgn = -1 if kk[3] == "m" else 1
            xs.append(sgn * int(kk[4:]))
            bs.append(v[0]); ses.append(v[1])
        o = np.argsort(xs)
        xs, bs, ses = np.array(xs)[o], np.array(bs)[o], np.array(ses)[o]
        ax.errorbar(xs, bs, yerr=1.96 * ses, fmt="o-", ms=4, capsize=2,
                    color=C_NEG if "PLG" in k or "OCC" in k else C_POS)
        ax.scatter([-1], [0], color="k", zorder=5, s=14)
        ax.axhline(0, color="k", lw=0.7)
        ax.axvline(-0.5, color="k", lw=0.7, ls="--")
        ax.set_title(f"{title} (n={es[k]['n_treated']})", fontsize=10)
    for ax in axes[1]:
        ax.set_xlabel("decades relative to event")
    for ax in axes[:, 0]:
        ax.set_ylabel("asinh construction/decade")
    fig.suptitle("Political events and city construction, all 2,390 German cities")
    fig.tight_layout()
    fig.savefig(FIG / "fig_event_dynamics.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig_ledger()
    fig_freeprince_es()
    fig_league()
    fig_liberty_scale()
    fig_es_dynamics()
    print("figures written to", FIG)
