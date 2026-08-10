"""Black Death mechanism test with actual plague-arrival data.

The paper's §7 shows a reduced-form pattern (coastal penalty in the plague
century, coastal premium in the recovery century) and — until now — flagged
the mechanism as untestable: 'showing that coastal cities suffered because
plague arrived through their harbors would require city-level plague-arrival
data this panel does not contain.' The Krauer & Schmid (2022) digitization of
Biraben's outbreak inventory supplies exactly that: geocoded, dated outbreak
records. This script matches first-wave (1347-1352) outbreak records to the
Buringh panel and tests the three steps of the mechanism:

  A. ARRIVAL: were coastal cities more likely to record a first-wave outbreak,
     and did the wave reach them earlier within 1347-1352?
  B. IMPACT: did recorded-hit cities lose more population over 1300->1400,
     and does the coastal penalty of the plague century shrink once recorded
     exposure is controlled?
  C. RECOVERY: over 1400->1500, did hit cities rebound, and was the rebound
     concentrated in water-access cities (hit x water interaction) — the
     Jedwab-Johnson-Koyama recovery-toward-fixed-factors channel?

Coverage discipline, as everywhere in this project: Biraben's inventory is a
chronicle compilation, not a census of outbreaks. Absence of a record is weak
evidence of absence, and recording probability plausibly rises with city
importance and documentation density (Roosen & Curtis 2018 document
undercoverage, especially for the Low Countries). We therefore (i) control for
initial size everywhere, (ii) report record-match rates by country so the
reader can see where the source is thin, and (iii) treat 'hit' as 'recorded
outbreak within MATCH_KM', an error-ridden proxy that biases interaction
estimates toward zero rather than away from it.

Writes out/08_plague_mechanism.md, out/plague_mechanism.json,
figures/fig_plague_mechanism.png.
"""
from __future__ import annotations
import json
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.neighbors import BallTree
from panel import load_buringh, wide_pop

ROOT = Path(__file__).resolve().parents[2]
BIRABEN = ROOT / "docs/external/plague_biraben/data/plague_biraben_v1.csv"
OUT = Path(__file__).resolve().parent / "out"
FIG = OUT / "figures"
EARTH_KM = 6371.0088
MATCH_KM = 10.0
TH = 1000.0
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25})


def load_wave1():
    b = pd.read_csv(BIRABEN)
    w1 = b[b["year"].between(1347, 1352) & b["lat"].notna() & b["lon"].notna()]
    # keep place-level records; drop whole-province entries whose coordinates
    # are region centroids (bbox diagonal > 60 km)
    w1 = w1[(w1["type"] == "Place") | (w1["bbox_diag_km"] <= 60)]
    return w1[["name", "year", "lat", "lon", "country", "type"]].reset_index(drop=True)


def attach_hits(d, w1):
    tree = BallTree(np.deg2rad(d[["lat", "lon"]].to_numpy()), metric="haversine")
    dist, idx = tree.query(np.deg2rad(w1[["lat", "lon"]].to_numpy()), k=1)
    km = dist.flatten() * EARTH_KM
    d = d.copy()
    d["hit"] = 0.0
    d["arrival"] = np.nan
    for j, (i, dk) in enumerate(zip(idx.flatten(), km)):
        if dk > MATCH_KM:
            continue
        d.iloc[i, d.columns.get_loc("hit")] = 1.0
        y = w1["year"].iloc[j]
        cur = d.iloc[i, d.columns.get_loc("arrival")]
        if np.isnan(cur) or y < cur:
            d.iloc[i, d.columns.get_loc("arrival")] = y
    return d


def ols(y, X, robust=True):
    m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HC1" if robust else "nonrobust")
    return m


def main():
    md = ["# Black Death mechanism: plague arrival, impact, recovery\n",
          "Source: Krauer & Schmid (2022) digitization of Biraben's outbreak inventory; "
          "first wave = recorded outbreak 1347–1352 within 10 km of the city. Biraben is a "
          "chronicle compilation, not a census: absence of a record is weak evidence, and "
          "recording probability plausibly rises with documentation density, which is why "
          "initial size is controlled throughout and match rates are reported by country.\n"]
    res = {}
    w = wide_pop(load_buringh(), years=(1200, 1300, 1400, 1500))
    d = w[w["in_cne"]].copy().reset_index(drop=True)
    w1 = load_wave1()
    d = attach_hits(d, w1)
    d["water"] = ((d["on_river"] == 1) | (d["on_coast"] == 1)).astype(float)
    s = d[(d["pop1300"] >= TH)].copy()
    s["l1300"] = np.log(s["pop1300"])
    res["n_wave1_records"] = int(len(w1))
    res["n_cities_pop1300"] = int(len(s))
    res["n_hit"] = int(s["hit"].sum())
    print(f"wave-1 records (place-level): {len(w1)}; sample cities (pop1300>=1k): {len(s)}; "
          f"with recorded outbreak: {int(s['hit'].sum())}")
    md.append(f"Wave-1 place-level records: {len(w1)}. Sample: {len(s)} cities with "
              f"pop(1300) ≥ 1,000; {int(s['hit'].sum())} have a recorded outbreak within "
              f"10 km.\n")
    # match rate by country (coverage honesty)
    byc = s.groupby("country").agg(n=("hit", "size"), hit_share=("hit", "mean"))
    byc = byc[byc["n"] >= 10].sort_values("hit_share", ascending=False)
    md.append("Recorded-outbreak share by country (n≥10 cities): " +
              ", ".join(f"{c} {r.hit_share:.0%} (n={int(r.n)})" for c, r in byc.iterrows()) +
              ". Low shares in the Low Countries and eastern Europe reflect Biraben's "
              "documented undercoverage there, not plague-free regions.\n")
    print(byc.to_string())
    res["hit_share_by_country"] = {c: float(r.hit_share) for c, r in byc.iterrows()}

    # ---- A. arrival: geography of recorded exposure
    md.append("## A. Arrival: recorded exposure concentrates on water; arrival year does not discriminate\n")
    mA = ols(s["hit"], s[["on_coast", "on_river", "l1300"]])
    res["arrival_lpm"] = {k: [float(mA.params[k]), float(mA.pvalues[k])]
                          for k in ["on_coast", "on_river", "l1300"]}
    md.append(f"Linear probability of a recorded 1347–52 outbreak: coast "
              f"{mA.params['on_coast']:+.3f} (p={mA.pvalues['on_coast']:.3f}), river "
              f"{mA.params['on_river']:+.3f} (p={mA.pvalues['on_river']:.3f}), log size "
              f"{mA.params['l1300']:+.3f} (p={mA.pvalues['l1300']:.3f}); n={int(mA.nobs)}. "
              f"The size coefficient partly reflects recording bias — bigger cities are "
              f"better documented — which is exactly why it must be in the regression.\n")
    print(f"A. P(hit): coast {mA.params['on_coast']:+.3f} (p={mA.pvalues['on_coast']:.3f}), "
          f"river {mA.params['on_river']:+.3f} (p={mA.pvalues['on_river']:.3f}), "
          f"l1300 {mA.params['l1300']:+.3f}")
    hit = s[s["hit"] == 1].copy()
    arr_coast = hit[hit["on_coast"] == 1]["arrival"].mean()
    arr_river = hit[(hit["on_coast"] == 0) & (hit["on_river"] == 1)]["arrival"].mean()
    arr_inl = hit[(hit["on_coast"] == 0) & (hit["on_river"] == 0)]["arrival"].mean()
    mAy = ols(hit["arrival"], hit[["on_coast", "on_river", "l1300"]])
    res["arrival_year"] = {"coast": float(arr_coast), "river": float(arr_river),
                           "inland": float(arr_inl),
                           "coast_coef": [float(mAy.params["on_coast"]), float(mAy.pvalues["on_coast"])]}
    md.append(f"Mean recorded arrival year among hit cities: coastal {arr_coast:.1f}, "
              f"river (non-coastal) {arr_river:.1f}, landlocked {arr_inl:.1f}. In a "
              f"regression on geography and size, coastal cities are reached "
              f"{mAy.params['on_coast']:+.2f} years earlier (p={mAy.pvalues['on_coast']:.3f}, "
              f"n={int(mAy.nobs)}).\n")
    print(f"   arrival year: coast {arr_coast:.1f} river {arr_river:.1f} inland {arr_inl:.1f} "
          f"(coast coef {mAy.params['on_coast']:+.2f}, p={mAy.pvalues['on_coast']:.3f})")

    # ---- B. impact 1300->1400
    md.append("## B. Impact: not identifiable at century resolution\n"
              "A recorded hit does NOT predict century-scale decline — the century grid "
              "averages the 1347-52 crash with fifty years of rebound, and recording is "
              "positively selected on the documentation density of thriving towns. The "
              "positive 'hit' coefficient below should be read as that selection, not as "
              "plague helping cities.\n")
    sb = s[(s["pop1400"] >= TH)].copy()
    sb["g34"] = np.log(sb["pop1400"]) - sb["l1300"]
    m0 = ols(sb["g34"], sb[["water", "l1300"]])
    m1 = ols(sb["g34"], sb[["water", "hit", "l1300"]])
    res["impact"] = {"water_alone": [float(m0.params["water"]), float(m0.pvalues["water"])],
                     "water_with_hit": [float(m1.params["water"]), float(m1.pvalues["water"])],
                     "hit": [float(m1.params["hit"]), float(m1.pvalues["hit"])],
                     "n": int(m1.nobs)}
    md.append(f"Growth 1300→1400 on water + size: water {m0.params['water']:+.3f} "
              f"(p={m0.pvalues['water']:.3f}). Adding recorded exposure: hit "
              f"{m1.params['hit']:+.3f} (p={m1.pvalues['hit']:.3f}), water "
              f"{m1.params['water']:+.3f} (p={m1.pvalues['water']:.3f}); n={int(m1.nobs)}.\n")
    print(f"B. g(1300-1400): water alone {m0.params['water']:+.3f} (p={m0.pvalues['water']:.3f}); "
          f"with hit: hit {m1.params['hit']:+.3f} (p={m1.pvalues['hit']:.3f}) "
          f"water {m1.params['water']:+.3f} (p={m1.pvalues['water']:.3f})")

    # ---- C. recovery 1400->1500
    md.append("## C. Recovery: did water cities rebound harder after being hit?\n")
    sc = d[(d["pop1400"] >= TH) & (d["pop1500"] >= TH)].copy()
    sc["l1400"] = np.log(sc["pop1400"])
    sc["g45"] = np.log(sc["pop1500"]) - sc["l1400"]
    sc["hitxwater"] = sc["hit"] * sc["water"]
    m2 = ols(sc["g45"], sc[["water", "hit", "hitxwater", "l1400"]])
    res["recovery"] = {k: [float(m2.params[k]), float(m2.pvalues[k])]
                       for k in ["water", "hit", "hitxwater", "l1400"]}
    res["recovery_n"] = int(m2.nobs)
    md.append(f"Growth 1400→1500 on water, hit, hit×water, log size: water "
              f"{m2.params['water']:+.3f} (p={m2.pvalues['water']:.3f}), hit "
              f"{m2.params['hit']:+.3f} (p={m2.pvalues['hit']:.3f}), hit×water "
              f"{m2.params['hitxwater']:+.3f} (p={m2.pvalues['hitxwater']:.3f}); "
              f"n={int(m2.nobs)}.\n")
    print(f"C. g(1400-1500): water {m2.params['water']:+.3f} (p={m2.pvalues['water']:.3f}) "
          f"hit {m2.params['hit']:+.3f} (p={m2.pvalues['hit']:.3f}) "
          f"hitxwater {m2.params['hitxwater']:+.3f} (p={m2.pvalues['hitxwater']:.3f})")

    # ---- figure
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4))
    ax = axes[0]
    groups = [("Coastal", (s["on_coast"] == 1)),
              ("River\n(non-coastal)", (s["on_coast"] == 0) & (s["on_river"] == 1)),
              ("Landlocked", (s["on_coast"] == 0) & (s["on_river"] == 0))]
    shares = [s.loc[m, "hit"].mean() for _, m in groups]
    years = [s.loc[m & (s["hit"] == 1), "arrival"].mean() for _, m in groups]
    x = np.arange(3)
    ax.bar(x, shares, 0.55, color=["#c0392b", "#2c7fb8", "#7f7f7f"])
    for xi, sh, yr in zip(x, shares, years):
        ax.text(xi, sh + 0.012, f"{sh:.0%}\n(mean arrival {yr:.1f})", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([g for g, _ in groups])
    ax.set_ylabel("share with recorded outbreak 1347–52")
    ax.set_ylim(0, max(shares) + 0.12)
    ax.set_title("A. Water cities more often record a first-wave outbreak\n"
                 "(arrival years are indistinguishable at this resolution)", fontsize=10.5)
    ax = axes[1]
    labels = ["hit\n(1300→1400)", "water\n(1300→1400)", "hit\n(1400→1500)",
              "hit × water\n(1400→1500)"]
    coefs = [m1.params["hit"], m1.params["water"], m2.params["hit"], m2.params["hitxwater"]]
    errs = [1.96 * m1.bse["hit"], 1.96 * m1.bse["water"], 1.96 * m2.bse["hit"],
            1.96 * m2.bse["hitxwater"]]
    cols = ["#c0392b", "#2c7fb8", "#c0392b", "#1b7837"]
    ax.bar(range(4), coefs, 0.55, yerr=errs, capsize=4, color=cols)
    ax.axhline(0, color="k", lw=0.9)
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("effect on log century growth (95% CI)")
    ax.set_title("B/C. Impact and recovery, controlling for size\n"
                 "(hit = recorded first-wave outbreak within 10 km)", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(FIG / "fig_plague_mechanism.png", bbox_inches="tight")
    plt.close(fig)

    (OUT / "08_plague_mechanism.md").write_text("\n".join(md))
    json.dump(res, open(OUT / "plague_mechanism.json", "w"), indent=2)
    print("\nwrote out/08_plague_mechanism.md, out/plague_mechanism.json, "
          "figures/fig_plague_mechanism.png")


if __name__ == "__main__":
    main()
