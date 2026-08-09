"""Consolidated causal evidence across FOUR commercial privileges, two independent
sources: staple rights & fairs (Viabundus, network-footprint universe) and town
charters & market rights (Cantoni-Mohr-Weigand, Städtebuch universe). For each:

  1. naive two-way-FE association vs matched difference-in-differences with a
     bootstrap 95% CI (as before, now on coverage-correct samples);
  2. a STACKED EVENT STUDY around grant centuries: cohort-specific datasets
     (treated + not-yet/never-treated clean controls, event window -2..+1
     centuries), stacked with cohort-x-city and cohort-x-year fixed effects,
     clustered by city — event-time coefficients expose pre-trends directly;
  3. minimum detectable effects (80% power) and 95% equivalence bounds, so
     "CI includes zero" is not over-read as "effect proven zero";
  4. exposure-timing robustness: populations are observed per century, so a
     grant in 1297 gets ~3 years of exposure before the 1300 census. We report
     the exposure distribution and re-run the DiD on early-in-century grants
     (>=50 years of exposure) only.

Saves out/causal_summary.json.
"""
from __future__ import annotations
import numpy as np, pandas as pd, json
import statsmodels.formula.api as smf
from pathlib import Path
from privileges import build_panel
from charter_did import attach_population, load_treatment_years, to_long

TH = 1000.0
OUT = Path(__file__).resolve().parent / "out"
rng = np.random.default_rng(7)


def naive(long):
    m = smf.ols("lpop ~ treated + C(cid) + C(year)", data=long).fit(
        cov_type="cluster", cov_kwds={"groups": long["cid"]})
    return float(np.exp(m.params["treated"]) - 1), float(m.pvalues["treated"])


def did_with_ci(wide, ycol, n_boot=1000, max_delay=100):
    """Pooled matched DiD across grant-centuries, with cohort-resampled bootstrap CI.
    max_delay: keep treated whose grant falls within the first `max_delay` years
    of its century (exposure-timing robustness uses max_delay=50)."""
    d = wide.copy()
    d["gc"] = np.floor(d[ycol] / 100.0) * 100
    if max_delay < 100:
        late = d[ycol].notna() & (d[ycol] - d["gc"] > max_delay)
        d = d[~late]  # drop late-granted cities entirely (neither treated nor control)
    def one(sample):
        rows = []
        for c in [1200, 1300, 1400]:
            c0, c1, c2 = f"pop{int(c-100)}", f"pop{int(c)}", f"pop{int(c+100)}"
            if c0 not in sample:
                continue
            base = sample[(sample[c0] >= TH) & (sample[c1] >= TH) & (sample[c2] >= TH)].copy()
            if len(base) < 6:
                continue
            base["pre"] = np.log(base[c1]) - np.log(base[c0])
            base["post"] = np.log(base[c2]) - np.log(base[c1])
            tr = base[base["gc"] == c]
            ct = base[base[ycol].isna() | (base[ycol] > c)]
            if len(tr) < 3 or len(ct) < 3:
                continue
            did = (tr["post"].mean() - tr["pre"].mean()) - (ct["post"].mean() - ct["pre"].mean())
            rows.append((len(tr), did))
        if not rows:
            return np.nan, []
        wsum = sum(n for n, _ in rows)
        return sum(n * v for n, v in rows) / wsum, rows
    point, cohort_rows = one(d)
    boots = []
    idx = np.arange(len(d))
    for _ in range(n_boot):
        b, _ = one(d.iloc[rng.choice(idx, len(idx), replace=True)])
        if not np.isnan(b):
            boots.append(b)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    se = float(np.std(boots))
    return (float(np.exp(point) - 1), float(np.exp(lo) - 1), float(np.exp(hi) - 1),
            se, [(int(n), float(v)) for n, v in cohort_rows])


def pretrend(wide, ycol):
    d = wide.dropna(subset=[ycol]).copy()
    d["gc"] = np.floor(d[ycol] / 100.0) * 100
    pre, post = [], []
    for _, r in d.iterrows():
        gc = r["gc"]
        for tag, y0, y1 in [("pre", gc-100, gc), ("post", gc, gc+100)]:
            c0, c1 = f"pop{int(y0)}", f"pop{int(y1)}"
            if c0 in r and c1 in r and pd.notna(r[c0]) and pd.notna(r[c1]) and r[c0] >= TH and r[c1] >= TH:
                (pre if tag == "pre" else post).append(np.log(r[c1]) - np.log(r[c0]))
    return float(np.mean(pre)), float(np.mean(post))


def stacked_event_study(wide, ycol):
    """Stacked event study on the century panel.

    For each grant-century cohort c in {1200,1300,1400}: treated = grant in
    [c, c+100); clean controls = never treated or treated after c+100.
    Event time e = (year - c)/100 - 1, so e=-1 is the last pre-grant census
    (reference), e=0 the first census after the grant. Stack cohorts with
    cohort-specific city and year FE; cluster by city."""
    d = wide.copy()
    d["gc"] = np.floor(d[ycol] / 100.0) * 100
    rows = []
    for c in [1200, 1300, 1400]:
        treated = d[d["gc"] == c]
        ctrl = d[d[ycol].isna() | (d[ycol] > c + 100)]
        for role, sub in [("t", treated), ("c", ctrl)]:
            for _, r in sub.iterrows():
                for y in [c - 100, c, c + 100, c + 200]:
                    col = f"pop{int(y)}"
                    if col not in d.columns or y > 1500 or y < 1100:
                        continue
                    p = r[col]
                    if pd.isna(p) or p < TH:
                        continue
                    e = int((y - c) / 100) - 1
                    rows.append({"cid": r["cid"], "stack": c, "year": y,
                                 "lpop": np.log(p), "treatgrp": int(role == "t"),
                                 "e": e})
    S = pd.DataFrame(rows)
    if S.empty or S[S.treatgrp == 1].cid.nunique() < 5:
        return None
    S["sc"] = S["stack"].astype(str) + "_" + S["cid"].astype(str)
    S["sy"] = S["stack"].astype(str) + "_" + S["year"].astype(str)
    dcols = []
    for e in [-2, 0, 1]:
        c = f"D{e}".replace("-", "m")
        S[c] = ((S["treatgrp"] == 1) & (S["e"] == e)).astype(float)
        dcols.append(c)
    # absorb cohort-x-city and cohort-x-year FE by iterative two-way demeaning
    # (explicit dummies are numerically singular at this size)
    import statsmodels.api as sm_api
    Z = S[["lpop"] + dcols].astype(float).copy()
    for _ in range(50):
        Z = Z - Z.groupby(S["sc"]).transform("mean")
        Z = Z - Z.groupby(S["sy"]).transform("mean")
    keep = [c for c in dcols if Z[c].std() > 1e-8]
    m = sm_api.OLS(Z["lpop"], Z[keep]).fit(
        cov_type="cluster", cov_kwds={"groups": S["cid"]})
    out = {}
    for e, v in [(-2, "Dm2"), (0, "D0"), (1, "D1")]:
        if v in keep:
            out[str(e)] = {"coef": float(m.params[v]), "se": float(m.bse[v]),
                           "lo": float(m.conf_int().loc[v, 0]),
                           "hi": float(m.conf_int().loc[v, 1])}
        else:
            out[str(e)] = {"coef": float("nan"), "se": float("nan"),
                           "lo": float("nan"), "hi": float("nan")}
    out["n_treated_cities"] = int(S[S.treatgrp == 1].cid.nunique())
    out["n_control_cities"] = int(S[S.treatgrp == 0].cid.nunique())
    out["n_obs"] = int(m.nobs)
    return out


def exposure_stats(wide, ycol):
    g = wide[ycol].dropna()
    gc = np.floor(g / 100.0) * 100
    expo = (gc + 100 - g) / 100.0
    return float(expo.mean()), float((expo >= 0.5).mean())


def main():
    res = {}
    # Viabundus staples & fairs (footprint-restricted inside build_panel)
    panel, wide = build_panel("in_cne")
    frames = {}
    for kind in ["staple", "fair"]:
        frames[kind] = (panel.rename(columns={f"has_{kind}": "treated"})[
            ["cid", "year", "lpop", "treated"]], wide, f"{kind}_year", "Viabundus")
    # Cantoni charters & markets (Städtebuch universe by construction)
    loc = attach_population(load_treatment_years())
    for kind, ycol in [("charter", "charter_year"), ("market", "market_year")]:
        frames[kind] = (to_long(loc, kind)[["cid", "year", "lpop", "treated"]],
                        loc, ycol, "Cantoni/Städtebuch")

    for kind, (lp, w, ycol, src) in frames.items():
        nv, p = naive(lp)
        dd, lo, hi, se, cohorts = did_with_ci(w, ycol)
        dd50, lo50, hi50, _, coh50 = did_with_ci(w, ycol, max_delay=50)
        pr, po = pretrend(w, ycol)
        es = stacked_event_study(w, ycol)
        exp_mean, exp_early = exposure_stats(w, ycol)
        # 80%-power minimum detectable effect and 95% equivalence bound, in %:
        mde = float(np.exp(2.8 * se) - 1)
        equiv = float(max(abs(np.exp(lo) - 1), abs(np.exp(hi) - 1)))
        res[kind] = dict(source=src, naive=nv, naive_p=p, did=dd, ci=[lo, hi],
                         did_se=se, mde80=mde, equiv95=equiv,
                         did_early=dd50, ci_early=[lo50, hi50],
                         cohorts=cohorts, cohorts_early=coh50,
                         pre=pr, post=po,
                         exposure_mean=exp_mean, exposure_early_share=exp_early,
                         n_treat=int(w[ycol].notna().sum()),
                         event_study=es)
    json.dump(res, open(OUT / "causal_summary.json", "w"), indent=2)

    print(f"\n{'privilege':9s} {'source':18s} {'naive':>7s} {'DiD':>7s} {'95% CI':>15s} "
          f"{'MDE80':>7s} {'DiD(early)':>10s} {'nT':>4s}")
    for k, v in res.items():
        print(f"{k:9s} {v['source']:18s} {v['naive']:+7.0%} {v['did']:+7.0%} "
              f"[{v['ci'][0]:+.0%},{v['ci'][1]:+.0%}]".ljust(62) +
              f" {v['mde80']:+.0%}  {v['did_early']:+8.0%} {v['n_treat']:4d}")
        if v["event_study"]:
            es = v["event_study"]
            print(f"          event study (nT={es['n_treated_cities']}, "
                  f"nC={es['n_control_cities']}): " +
                  "  ".join(f"e={e}: {es[e]['coef']:+.3f}±{es[e]['se']:.3f}"
                            for e in ["-2", "0", "1"]))
    print("\nsaved out/causal_summary.json")


if __name__ == "__main__":
    main()
