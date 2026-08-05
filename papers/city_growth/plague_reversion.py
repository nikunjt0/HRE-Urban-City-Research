"""Davis-Weinstein test on the Black Death (1347-51).

The plague killed ~40-50% of Europe's population in ~4 years -- an enormous,
spatially near-uniform shock to PEOPLE that left LOCATIONS untouched. This is
the ideal natural experiment for the deepest question in urban economics:

  Is a city's size determined by locational fundamentals (the place), or by
  historical accident / path dependence (the people, once there, stay)?

Predictions:
  * FUNDAMENTALS: cities revert to pre-plague relative size. The plague trough
    (1400) adds nothing beyond pre-plague size (1300) in predicting 1500.
    Growth during the crash (1300->1400) is REVERSED during recovery
    (1400->1500): whoever fell furthest bounces back furthest.
  * PATH DEPENDENCE: the shock is permanent; 1400 trough predicts 1500;
    no reversal.

Snapshots: 1300 (pre), 1400 (post-plague trough), 1500 (recovered).
"""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy import stats
from panel import load_buringh, wide_pop

TH = 1000.0


def main(region="in_cne"):
    w = wide_pop(load_buringh(), years=(1200, 1300, 1400, 1500, 1600))
    d = w[w[region]].copy()
    s = d[(d["pop1300"] >= TH) & (d["pop1400"] >= TH) & (d["pop1500"] >= TH)].copy()
    for y in [1200, 1300, 1400, 1500, 1600]:
        s[f"l{y}"] = np.log(s[f"pop{y}"])
    s["g_crash"] = s["l1400"] - s["l1300"]      # 1300->1400 (plague)
    s["g_recov"] = s["l1500"] - s["l1400"]      # 1400->1500 (recovery)
    n = len(s)
    print("=" * 76)
    print(f"BLACK DEATH REVERSION TEST   (n={n} {region} cities present 1300/1400/1500)")
    print("=" * 76)

    # 1. Rank preservation across the shock
    for a, b in [("pop1300", "pop1500"), ("pop1300", "pop1400"), ("pop1400", "pop1500")]:
        rho = stats.spearmanr(s[a], s[b]).statistic
        print(f"  Spearman rank corr {a} vs {b}: {rho:.3f}")

    # 2. Does the plague TROUGH add anything beyond pre-plague size for 1500?
    print("\n  Predicting log(pop1500):")
    r1 = sm.OLS(s["l1500"], sm.add_constant(s[["l1300"]])).fit(cov_type="HC1")
    print(f"    ~ l1300 only:          R2={r1.rsquared:.3f}  b_l1300={r1.params['l1300']:.3f}")
    r2 = sm.OLS(s["l1500"], sm.add_constant(s[["l1300", "l1400"]])).fit(cov_type="HC1")
    print(f"    ~ l1300 + l1400:       R2={r2.rsquared:.3f}  "
          f"b_l1300={r2.params['l1300']:+.3f}(p{r2.pvalues['l1300']:.3f})  "
          f"b_l1400={r2.params['l1400']:+.3f}(p{r2.pvalues['l1400']:.3f})")
    print("    (fundamentals => l1300 keeps a large coef, l1400 adds little)")

    # 3. THE reversal test: does the recovery undo the crash?
    print("\n  RECOVERY-REVERSES-CRASH test:  g_recov ~ g_crash")
    rr = sm.OLS(s["g_recov"], sm.add_constant(s[["g_crash"]])).fit(cov_type="HC1")
    print(f"    slope={rr.params['g_crash']:+.3f} (p={rr.pvalues['g_crash']:.4f})  R2={rr.rsquared:.3f}")
    print(f"    corr(g_crash, g_recov) = {s['g_crash'].corr(s['g_recov']):+.3f}")
    print("    slope<0 => cities that crashed hardest rebounded hardest (reversion to fundamentals)")

    # 4. Half-life of reversion: how fast does the deviation from pre-plague trend close?
    #    deviation at 1400 = l1400 - l1300 ; residual deviation at 1500 = l1500 - l1300
    dev1400 = s["l1400"] - s["l1300"]
    dev1500 = s["l1500"] - s["l1300"]
    beta = sm.OLS(dev1500, sm.add_constant(dev1400)).fit().params.iloc[1]
    print(f"\n  Persistence of the plague deviation 1400->1500: beta={beta:.3f}")
    frac_undone = 1 - beta
    print(f"    => {frac_undone:.0%} of the plague-era deviation from pre-plague size was "
          f"undone within a century")

    s.to_csv("out/plague_frame.csv", index=False)
    return s


if __name__ == "__main__":
    main("in_cne")
    print()
    main("in_hre")
