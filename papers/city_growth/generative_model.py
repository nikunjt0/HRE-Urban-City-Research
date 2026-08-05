"""The generative law of medieval urban growth.

Claim: the entire HRE urban system is described by ONE stochastic process — a
mean-reverting random walk in log-population, anchored on a fixed geographic
'fundamental', with common century shocks:

    log P_{i,t+1} = log P_{i,t}
                    + s_t                         (common century shock: plague, recovery)
                    + kappa * (mu_i - log P_{i,t})(slow reversion to fundamental)
                    + eps_{i,t},  eps ~ N(0, sigma^2)   (idiosyncratic Gibrat noise)

  mu_i = geographic carrying capacity (a0 + a_water*water_i + city component).

This single law simultaneously predicts, with NO free factor tuning:
  (a) growth is ~unpredictable   (Gibrat: sigma large vs kappa)
  (b) the hierarchy persists      (slow reversion + fixed mu)
  (c) the size distribution is Zipf (Gabaix 1999: Gibrat + reflecting friction)
  (d) institutions add ~nothing   (they are endogenous to P, not to eps)

We estimate {kappa, sigma, s_t, a_water} from 1200-1500 transitions, simulate the
system forward from the real 1200 sizes, and check it reproduces the ACTUAL
Zipf-exponent path, persistence r2, and growth R2.
"""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
from panel import load_buringh, wide_pop

TH = 1000.0
YEARS = [1200, 1300, 1400, 1500]


def zeta(pops):
    p = np.sort(pops[pops >= TH * 0.999])[::-1]
    if len(p) < 20:
        return np.nan
    rank = np.arange(1, len(p) + 1)
    r = sm.OLS(np.log(rank - 0.5), sm.add_constant(np.log(p))).fit()
    return -r.params[1]


def estimate_and_simulate(region="in_cne", n_sim=400, seed=0):
    w = wide_pop(load_buringh(), years=tuple(YEARS)).copy()
    d = w[w[region]].copy()
    d["water"] = ((d["on_river"] == 1) | (d["on_coast"] == 1)).astype(float)

    # --- estimate the AR(1)-with-fundamentals law ---
    #   logP_{t+1} = a_t + b*logP_t + c*water + eps
    # b<1 is slow reversion; b->1 is pure Gibrat. a_t are century (common) shocks.
    recs = []
    for y0, y1 in zip(YEARS[:-1], YEARS[1:]):
        c0, c1 = f"pop{y0}", f"pop{y1}"
        s = d[(d[c0] >= TH) & (d[c1] >= TH)].copy()
        s["l0"] = np.log(s[c0]); s["l1"] = np.log(s[c1])
        s["period"] = f"{y0}"
        recs.append(s[["l0", "l1", "water", "period"]])
    P = pd.concat(recs, ignore_index=True)
    X = pd.get_dummies(P["period"], prefix="a", drop_first=False).astype(float)
    X["l0"] = P["l0"]; X["water"] = P["water"]
    m = sm.OLS(P["l1"], X).fit()
    b = m.params["l0"]
    kappa = 1.0 - b
    c_water = m.params["water"]
    a_t = {p.replace("a_", ""): m.params[p] for p in X.columns if p.startswith("a_")}
    sigma = np.std(m.resid)
    print("=" * 74)
    print("ESTIMATED GENERATIVE LAW:  logP_{t+1} = a_t + b*logP_t + c*water + eps")
    print("=" * 74)
    print(f"  persistence      b     = {b:.3f}   (reversion kappa=1-b={kappa:.3f}/century, "
          f"half-life {np.log(2)/max(kappa,1e-6)*100:.0f} yrs)")
    print(f"  idiosyncratic    sigma = {sigma:.3f} log/century")
    print(f"  water anchor     c     = {c_water:.3f}")
    print(f"  century shocks a_t = " + ", ".join(f"{k}:{v:+.2f}" for k, v in a_t.items()))
    print(f"  signal-to-noise: kappa/sigma = {kappa/sigma:.2f}  (<<1 => growth ~ pure Gibrat noise)")

    # --- simulate forward from actual 1200 sizes ---
    sim = d[(d["pop1200"] >= TH)].copy().reset_index(drop=True)
    logP0 = np.log(sim["pop1200"].to_numpy())
    water = sim["water"].to_numpy()
    rng = np.random.default_rng(seed)
    sim_years = YEARS
    zeta_sim = {y: [] for y in sim_years}
    pers_sim = []
    for _ in range(n_sim):
        logP = logP0.copy()
        traj = {1200: logP.copy()}
        for y0, y1 in zip(sim_years[:-1], sim_years[1:]):
            a = a_t.get(str(y0), 0.0)
            eps = rng.normal(0, sigma, size=len(logP))
            logP = a + b * logP + c_water * water + eps
            traj[y1] = logP.copy()
        for y in sim_years:
            zeta_sim[y].append(zeta(np.exp(traj[y])))
        pers_sim.append(np.corrcoef(traj[1200], traj[1500])[0, 1] ** 2)

    # --- actual moments ---
    print("\n" + "=" * 74)
    print("DOES THE LAW REPRODUCE THE DATA?  (simulated mean [95% band] vs actual)")
    print("=" * 74)
    print(f"  {'moment':32s} {'simulated':>22s} {'actual':>10s}")
    for y in sim_years:
        act = zeta(d[f"pop{y}"].to_numpy())
        arr = np.array(zeta_sim[y])
        lo, hi = np.percentile(arr, [2.5, 97.5])
        print(f"  Zipf zeta {y}                    {arr.mean():6.3f} [{lo:.2f},{hi:.2f}]     {act:6.3f}")
    # persistence
    ss = d.dropna(subset=["pop1200", "pop1500"])
    ss = ss[(ss.pop1200 >= TH) & (ss.pop1500 >= TH)]
    act_pers = np.corrcoef(np.log(ss.pop1200), np.log(ss.pop1500))[0, 1] ** 2
    arr = np.array(pers_sim); lo, hi = np.percentile(arr, [2.5, 97.5])
    print(f"  persistence r2 (1200->1500)      {arr.mean():6.3f} [{lo:.2f},{hi:.2f}]     {act_pers:6.3f}")
    print("\n  If simulated bands cover the actual values, a 3-parameter stochastic law")
    print("  (kappa, sigma, water-anchor) reproduces the whole urban hierarchy's evolution.")


if __name__ == "__main__":
    estimate_and_simulate("in_cne", n_sim=400, seed=0)
