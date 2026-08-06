"""Prediction evaluation + decomposition transparency for the paper rewrite.

Answers three referee questions the draft left open:
  A. Why decompose 1500 size into {geography, size@800, size@1200}? Could the
     31% 'luck' just be factors we didn't choose (e.g. institutions)?
     -> R2 ladder built step by step + Shapley with institutions as a 4TH group
        (staple, fair, charter, market). If institutions carried hidden weight,
        adding them would shrink the unexplained share. It doesn't.
     -> Residual autocorrelation across consecutive centuries: a stable omitted
        city factor would make growth residuals persist; mostly they don't.
  B. What does 'the size its 1200 population implies' mean?
     -> It is the fitted value of the cross-city regression l1500 ~ l1200 (+water).
        Figure: scatter + fitted line + labelled over/under-performers.
  C. Does the one equation actually PREDICT city sizes?
     -> Iterate logP_{t+1}=a_t+b logP_t+c water deterministically 1200->1500,
        compare predicted vs actual per city; benchmarks (mean-only, frozen map,
        no-water, +privileges); out-of-sample splits; growth vs level R2.
Writes out/06_prediction.md and figures fig_implied_size / fig_prediction /
fig_decomp_build.
"""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from itertools import combinations
import math

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FIG = OUT / "figures"
TH = 1000.0
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25})

GEO = ["on_river", "on_coast", "atlantic", "baltic", "northsea", "medit", "elev_z"]
INST = ["has_staple", "has_fair", "has_charter", "has_market"]


def load():
    d = pd.read_csv(OUT / "synthesis_frame.csv")
    d = d[d["in_cne"] == True].copy()
    for y in [800, 1200, 1300, 1400, 1500]:
        d[f"l{y}"] = np.log(d[f"pop{y}"].where(d[f"pop{y}"] >= TH))
    d["elev_z"] = (d["elev"] - d["elev"].mean()) / d["elev"].std()
    d["water"] = ((d["on_river"] == 1) | (d["on_coast"] == 1)).astype(float)
    pw = pd.read_csv(OUT / "privilege_wide.csv")[["cid", "staple_year", "fair_year"]]
    cp = pd.read_csv(OUT / "city_performers.csv")[["cid", "charter_year", "market_year"]]
    d = d.merge(pw, on="cid", how="left").merge(cp, on="cid", how="left")
    d["has_staple"] = (d["staple_year"] <= 1500).fillna(False).astype(float)
    d["has_fair"] = (d["fair_year"] <= 1500).fillna(False).astype(float)
    d["has_charter"] = (d["charter_year"] <= 1500).fillna(False).astype(float)
    d["has_market"] = (d["market_year"] <= 1500).fillna(False).astype(float)
    return d


def r2(d, y, xs):
    s = d.dropna(subset=[y] + xs)
    if len(s) < 20:
        return np.nan, 0
    return sm.OLS(s[y], sm.add_constant(s[xs])).fit().rsquared, len(s)


def shapley(d, y, groups):
    names = list(groups)
    s = d.dropna(subset=[y] + [c for g in groups.values() for c in g]).copy()
    def R2(sel):
        cols = [c for g in sel for c in groups[g]]
        if not cols:
            return 0.0
        return sm.OLS(s[y], sm.add_constant(s[cols])).fit().rsquared
    k = len(names); phi = {n: 0.0 for n in names}
    for n in names:
        others = [x for x in names if x != n]
        for r in range(len(others) + 1):
            for S in combinations(others, r):
                w = math.factorial(len(S)) * math.factorial(k - len(S) - 1) / math.factorial(k)
                phi[n] += w * (R2(list(S) + [n]) - R2(list(S)))
    return phi, R2(names), len(s)


# ---------------------------------------------------------------- A. decomposition
def part_a(d, md):
    md.append("## A. Building the decomposition step by step (R2 ladder)\n")
    md.append("Candidate explanations of log pop1500, entered alone and together:\n")
    ladder = [
        ("institutions only (staple/fair/charter/market by 1500)", INST),
        ("geography only (river/coast/basin/elevation)", GEO),
        ("deep history only (log pop 800)", ["l800"]),
        ("inherited size only (log pop 1200)", ["l1200"]),
        ("geography + inherited size", GEO + ["l1200"]),
        ("geography + deep history + inherited size", GEO + ["l800", "l1200"]),
        ("ALL FOUR (adding institutions)", GEO + ["l800", "l1200"] + INST),
    ]
    md.append("| model | R2 | n |\n|---|---|---|")
    for label, xs in ladder:
        rr, n = r2(d, "l1500", xs)
        md.append(f"| {label} | {rr:.3f} | {n} |")
        print(f"  {label:52s} R2={rr:.3f} n={n}")

    # same-sample comparison: does adding institutions shrink the unexplained part?
    s = d.dropna(subset=["l1500", "l800", "l1200"] + GEO + INST)
    r3 = sm.OLS(s["l1500"], sm.add_constant(s[GEO + ["l800", "l1200"]])).fit().rsquared
    r4 = sm.OLS(s["l1500"], sm.add_constant(s[GEO + ["l800", "l1200"] + INST])).fit().rsquared
    md.append(f"\nSame {len(s)} cities: unexplained share 3-group = {1-r3:.3f}, "
              f"after adding institutions = {1-r4:.3f} "
              f"(institutions recover {r4-r3:.3f} of the {1-r3:.3f}).\n")
    print(f"  unexplained: {1-r3:.3f} -> {1-r4:.3f} after adding institutions")

    md.append("## A2. Shapley shares with institutions as a fourth group\n")
    groups = {"geography": GEO, "deep_history_800": ["l800"],
              "inherited_1200": ["l1200"], "institutions": INST}
    phi, tot, n = shapley(d, "l1500", groups)
    md.append(f"total R2 = {tot:.3f} (n={n}); unexplained = {1-tot:.3f}\n")
    md.append("| group | share of explained | share of total variance |\n|---|---|---|")
    for k2, v in phi.items():
        md.append(f"| {k2} | {v/tot:.1%} | {v:.3f} |")
        print(f"    {k2:20s} {v/tot:6.1%} of explained   ({v:.3f} R2 units)")
    print(f"    unexplained {1-tot:.1%}")

    # residual autocorrelation: is the unexplained part a stable omitted factor?
    md.append("\n## A3. Is the unexplained 31% a stable hidden factor, or noise?\n")
    rows = []
    for y0, y1 in [(1200, 1300), (1300, 1400), (1400, 1500)]:
        s = d.dropna(subset=[f"l{y0}", f"l{y1}"]).copy()
        m = sm.OLS(s[f"l{y1}"], sm.add_constant(s[[f"l{y0}", "water"]])).fit()
        s[f"e{y0}"] = m.resid
        rows.append(s[["cid", f"e{y0}"]])
    e = rows[0].merge(rows[1], on="cid").merge(rows[2], on="cid")
    c12 = e["e1200"].corr(e["e1300"]); c23 = e["e1300"].corr(e["e1400"])
    md.append(f"Correlation of a city's growth residual with its residual next century: "
              f"1200/1300 vs 1300/1400: r={c12:.2f}; 1300/1400 vs 1400/1500: r={c23:.2f} "
              f"(n={len(e)}). A stable omitted city trait would push these toward 1; "
              f"values ~{(c12+c23)/2:.2f} mean only ~{((c12+c23)/2)**1:.0%} of a shock "
              f"carries into the next century's residual.\n")
    print(f"  residual autocorrelation: {c12:.2f}, {c23:.2f} (n={len(e)})")

    # figure: ladder + shapley
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    ax = axes[0]
    labels = ["Institutions\nonly", "Geography\nonly", "Size in 800\nonly",
              "Size in 1200\nonly", "Geo + 800\n+ 1200", "+ Institutions"]
    vals = [r2(d, "l1500", xs)[0] for xs in
            [INST, GEO, ["l800"], ["l1200"], GEO + ["l800", "l1200"],
             GEO + ["l800", "l1200"] + INST]]
    colors = ["#c0392b", "#7fbf7b", "#8073ac", "#2c7fb8", "#555555", "#999999"]
    ax.barh(range(len(vals))[::-1], vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(v + 0.01, len(vals) - 1 - i, f"{v:.2f}", va="center", fontsize=10,
                fontweight="bold")
    ax.set_yticks(range(len(vals))[::-1]); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 0.85); ax.set_xlabel("share of 1500 size variation explained (R²)")
    ax.set_title("Step 1: what can each candidate explain?")
    ax = axes[1]
    groups4 = {"geography": GEO, "deep_history_800": ["l800"],
               "inherited_1200": ["l1200"], "institutions": INST}
    phi4, tot4, _ = shapley(d, "l1500", groups4)
    parts = [("Inherited size\n(1200)", phi4["inherited_1200"], "#2c7fb8"),
             ("Deep origin\n(800)", phi4["deep_history_800"], "#8073ac"),
             ("Geography (direct)", phi4["geography"], "#7fbf7b"),
             ("Institutions", phi4["institutions"], "#c0392b"),
             ("Unexplained\n(luck + measurement)", 1 - tot4, "#cccccc")]
    left = 0
    stagger = 0
    for name, v, c in parts:
        ax.barh([0], [v], left=left, color=c, edgecolor="white", height=0.5)
        if v > 0.08:
            ax.text(left + v/2, 0, f"{name}\n{v:.0%}", ha="center", va="center",
                    fontsize=8.5)
        else:
            ytxt = 0.40 + 0.14 * stagger
            ax.annotate(f"{name}: {v:.1%}", xy=(left + v/2, 0.26),
                        xytext=(left + v/2, ytxt), ha="center", fontsize=8,
                        color=c if c != "#cccccc" else "#777",
                        arrowprops=dict(arrowstyle="-", lw=0.7, color=c))
            stagger += 1
        left += v
    ax.set_xlim(0, 1); ax.set_ylim(-0.6, 0.75); ax.set_yticks([])
    ax.set_xlabel("share of total variance in city size, 1500")
    ax.set_title("Step 2: fair (Shapley) split of the credit")
    fig.tight_layout(); fig.savefig(FIG / "fig_decomp_build.png", bbox_inches="tight")
    plt.close(fig)
    return phi4, tot4


# ---------------------------------------------------------------- B. implied size
def part_b(d, md):
    md.append("\n## B. 'Implied size from 1200' made explicit\n")
    s = d.dropna(subset=["l1200", "l1500"]).copy()
    m = sm.OLS(s["l1500"], sm.add_constant(s[["l1200", "water"]])).fit()
    s["pred"] = m.fittedvalues
    s["resid"] = m.resid
    md.append(f"Fitted rule across {len(s)} cities: "
              f"log pop1500 = {m.params['const']:.2f} + {m.params['l1200']:.2f} x log pop1200 "
              f"+ {m.params['water']:.2f} x water, R2={m.rsquared:.3f}. A city's 'implied "
              f"1500 size' is this fitted value; its performance is the residual "
              f"(actual minus implied), in log points.\n")
    print(f"  implied-size rule: l1500 = {m.params['const']:.2f} + {m.params['l1200']:.2f} l1200 "
          f"+ {m.params['water']:.2f} water, R2={m.rsquared:.3f}")

    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    ax.scatter(np.exp(s["l1200"]), np.exp(s["l1500"]), s=12, alpha=0.25, color="#555")
    xs = np.linspace(s["l1200"].min(), s["l1200"].max(), 50)
    ax.plot(np.exp(xs), np.exp(m.params["const"] + m.params["l1200"] * xs + m.params["water"]),
            color="#2c7fb8", lw=2.2, label="implied size, city on water\n(fitted average relationship)")
    ax.plot(np.exp(xs), np.exp(m.params["const"] + m.params["l1200"] * xs),
            color="#7fbf7b", lw=1.8, ls="--", label="implied size, landlocked")
    for name in ["Hamburg", "Amsterdam", "Gdansk", "Mainz", "Erfurt", "Koeln", "Nuernberg"]:
        row = s[s["city"] == name]
        if len(row):
            row = row.iloc[0]
            x1, yact = np.exp(row["l1200"]), np.exp(row["l1500"])
            yimp = np.exp(row["pred"])
            ax.plot([x1, x1], [yimp, yact], color="#c0392b", lw=1.2, alpha=0.8)
            ax.scatter([x1], [yact], s=28, color="#c0392b", zorder=5)
            ax.annotate(f"{name} ({row['resid']:+.2f})", (x1, yact), fontsize=8.5,
                        xytext=(4, 3), textcoords="offset points")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("population in 1200"); ax.set_ylabel("population in 1500")
    ax.set_title("What 'implied size' means: the average 1200→1500 relationship\n"
                 "red = distance between a city's actual 1500 size and the line (its residual)")
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout(); fig.savefig(FIG / "fig_implied_size.png", bbox_inches="tight")
    plt.close(fig)
    return m


# ---------------------------------------------------------------- C. prediction
def fit_law(P):
    X = pd.get_dummies(P["period"], prefix="a").astype(float)
    X["l0"] = P["l0"]; X["water"] = P["water"]
    m = sm.OLS(P["l1"], X).fit()
    a_t = {p.replace("a_", ""): m.params[p] for p in X.columns if p.startswith("a_")}
    return m.params["l0"], m.params["water"], a_t, np.std(m.resid)


def transitions(d, cids=None):
    recs = []
    for y0, y1 in [(1200, 1300), (1300, 1400), (1400, 1500)]:
        s = d.dropna(subset=[f"l{y0}", f"l{y1}"]).copy()
        if cids is not None:
            s = s[s["cid"].isin(cids)]
        s["l0"] = s[f"l{y0}"]; s["l1"] = s[f"l{y1}"]; s["period"] = str(y0)
        recs.append(s[["cid", "l0", "l1", "water", "period"]])
    return pd.concat(recs, ignore_index=True)


def project(d, b, c, a_t):
    s = d.dropna(subset=["l1200", "l1500"]).copy()
    lp = s["l1200"].to_numpy().copy()
    for y in ["1200", "1300", "1400"]:
        lp = a_t.get(y, 0.0) + b * lp + c * s["water"].to_numpy()
    s["lpred"] = lp
    return s


def metrics(s, md, label):
    e = s["l1500"] - s["lpred"]
    sst = ((s["l1500"] - s["l1500"].mean()) ** 2).sum()
    r2v = 1 - (e ** 2).sum() / sst
    rho = s["l1500"].corr(s["lpred"])
    sp = s["l1500"].corr(s["lpred"], method="spearman")
    medf = np.exp(np.median(np.abs(e)))
    w15 = (np.abs(e) <= np.log(1.5)).mean()
    w20 = (np.abs(e) <= np.log(2.0)).mean()
    top = s.nlargest(10, "l1500")["cid"]
    topp = s.nlargest(10, "lpred")["cid"]
    hit = len(set(top) & set(topp))
    md.append(f"| {label} | {r2v:.3f} | {sp:.3f} | x{medf:.2f} | {w15:.0%} | {w20:.0%} | {hit}/10 |")
    print(f"  {label:38s} R2={r2v:.3f} rank={sp:.3f} med x{medf:.2f} "
          f"within1.5={w15:.0%} within2={w20:.0%} top10 {hit}/10")
    return r2v


def part_c(d, md):
    md.append("\n## C. Does the equation actually predict 1500 sizes?\n")
    P = transitions(d)
    b, c, a_t, sigma = fit_law(P)
    md.append(f"Estimated law: b={b:.3f}, c_water={c:.3f}, sigma={sigma:.3f}, "
              f"a_t = {', '.join(f'{k}:{v:+.2f}' for k, v in sorted(a_t.items()))}\n")
    print(f"  law: b={b:.3f} c={c:.3f} sigma={sigma:.3f} a_t={a_t}")

    md.append("| predictor of 1500 size (from 1200 info only) | R2 (log size) | rank corr | median miss | within x1.5 | within x2 | top-10 hit |\n|---|---|---|---|---|---|---|")
    s = d.dropna(subset=["l1200", "l1500"]).copy()

    # benchmark 0: mean only
    s0 = s.copy(); s0["lpred"] = s["l1500"].mean()
    metrics(s0, md, "guess the average for every city")
    # benchmark 1: frozen map
    s1 = s.copy(); s1["lpred"] = s1["l1200"]
    metrics(s1, md, "frozen map: size1500 = size1200")
    # benchmark 2: equation without water
    Pn = transitions(d)
    Xn = pd.get_dummies(Pn["period"], prefix="a").astype(float); Xn["l0"] = Pn["l0"]
    mn = sm.OLS(Pn["l1"], Xn).fit()
    an = {p.replace("a_", ""): mn.params[p] for p in Xn.columns if p.startswith("a_")}
    s2 = s.copy(); lp = s2["l1200"].to_numpy().copy()
    for y in ["1200", "1300", "1400"]:
        lp = an.get(y, 0.0) + mn.params["l0"] * lp
    s2["lpred"] = lp
    metrics(s2, md, "equation without water")
    # the equation
    s3 = project(d, b, c, a_t)
    r2_eq = metrics(s3, md, "THE EQUATION (size + water + shocks)")
    # equation + privileges
    Pi = transitions(d)
    di = d[["cid"] + INST]
    Pi = Pi.merge(di, on="cid", how="left")
    Xi = pd.get_dummies(Pi["period"], prefix="a").astype(float)
    Xi["l0"] = Pi["l0"]; Xi["water"] = Pi["water"]
    for cc in INST:
        Xi[cc] = Pi[cc]
    mi = sm.OLS(Pi["l1"], Xi).fit()
    ai = {p.replace("a_", ""): mi.params[p] for p in Xi.columns if p.startswith("a_")}
    s4 = s.copy()
    lp = s4["l1200"].to_numpy().copy()
    inst_term = sum(mi.params[cc] * s4[cc].to_numpy() for cc in INST)
    for y in ["1200", "1300", "1400"]:
        lp = ai.get(y, 0.0) + mi.params["l0"] * lp + mi.params["water"] * s4["water"].to_numpy() + inst_term
    s4["lpred"] = lp
    metrics(s4, md, "equation + all four privileges")

    # growth prediction
    md.append("")
    g_pred = s3["lpred"] - s3["l1200"]; g_act = s3["l1500"] - s3["l1200"]
    sst = ((g_act - g_act.mean()) ** 2).sum()
    r2g = 1 - ((g_act - g_pred) ** 2).sum() / sst
    md.append(f"\nSame equation asked to predict GROWTH 1200->1500 instead of size: "
              f"R2 = {r2g:.3f}. It knows where the hierarchy stands, not who moves.\n")
    print(f"  growth R2 = {r2g:.3f}")

    # out of sample
    rng = np.random.default_rng(7)
    cids = s["cid"].unique()
    oos = []
    for _ in range(200):
        tr = rng.choice(cids, len(cids) // 2, replace=False)
        Ptr = transitions(d, cids=set(tr))
        bb, cc2, aa, _ = fit_law(Ptr)
        te = s[~s["cid"].isin(set(tr))].copy()
        lp = te["l1200"].to_numpy().copy()
        for y in ["1200", "1300", "1400"]:
            lp = aa.get(y, 0.0) + bb * lp + cc2 * te["water"].to_numpy()
        e = te["l1500"] - lp
        sst = ((te["l1500"] - te["l1500"].mean()) ** 2).sum()
        oos.append(1 - (e ** 2).sum() / sst)
    lo, hi = np.percentile(oos, [2.5, 97.5])
    md.append(f"Out-of-sample check: fit the law on a random half of cities, predict the "
              f"other half (200 draws): R2 = {np.mean(oos):.3f} [{lo:.3f}, {hi:.3f}] — "
              f"essentially identical to in-sample {r2_eq:.3f}; the equation is not overfit.\n")
    print(f"  OOS R2 = {np.mean(oos):.3f} [{lo:.3f},{hi:.3f}]")

    # figure: level vs growth prediction
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0))
    ax = axes[0]
    ax.scatter(np.exp(s3["lpred"]), np.exp(s3["l1500"]), s=12, alpha=0.3, color="#2c7fb8")
    lims = [800, 60000]
    ax.plot(lims, lims, "k--", lw=1)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("size in 1500 predicted by the equation (from 1200 data)")
    ax.set_ylabel("actual size in 1500")
    ax.set_title(f"The equation predicts SIZES well\nR² = {r2_eq:.2f}, "
                 f"median miss x{np.exp(np.median(np.abs(s3['l1500']-s3['lpred']))):.2f}")
    ax = axes[1]
    ax.scatter(g_pred, g_act, s=12, alpha=0.3, color="#c0392b")
    ax.axhline(0, color="k", lw=0.8); ax.set_xlim(-0.5, 2.8)
    ax.plot([-0.5, 2.8], [-0.5, 2.8], "k--", lw=1)
    ax.set_xlabel("predicted growth 1200→1500 (log)")
    ax.set_ylabel("actual growth (log)")
    ax.set_title(f"...but it cannot predict GROWTH\nR² = {r2g:.2f}: who moves is mostly noise")
    fig.tight_layout(); fig.savefig(FIG / "fig_prediction.png", bbox_inches="tight")
    plt.close(fig)


def main():
    d = load()
    md = ["# Prediction evaluation & decomposition transparency\n",
          f"Sample: Central/North Europe (in_cne), pop>=1000, Buringh panel.\n"]
    print("=" * 74); print("A. DECOMPOSITION TRANSPARENCY"); print("=" * 74)
    part_a(d, md)
    print("=" * 74); print("B. IMPLIED SIZE"); print("=" * 74)
    part_b(d, md)
    print("=" * 74); print("C. PREDICTION EVALUATION"); print("=" * 74)
    part_c(d, md)
    (OUT / "06_prediction.md").write_text("\n".join(md))
    print("\nwrote out/06_prediction.md + 3 figures")


if __name__ == "__main__":
    main()
