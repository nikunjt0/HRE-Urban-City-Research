"""Consolidated causal evidence across FOUR commercial privileges, two independent
sources: staple rights & fairs (Viabundus) and town charters & market rights
(Cantoni-Mohr-Weigand). For each: naive two-way-FE association vs matched
difference-in-differences with a bootstrap 95% CI. Saves out/causal_summary.json.
"""
from __future__ import annotations
import numpy as np, pandas as pd, json
import statsmodels.formula.api as smf
from pathlib import Path
from privileges import build_panel
from charter_did import attach_population, load_treatment_years

TH = 1000.0
OUT = Path(__file__).resolve().parent / "out"
rng = np.random.default_rng(7)


def naive(long):
    m = smf.ols("lpop ~ treated + C(cid) + C(year)", data=long).fit(
        cov_type="cluster", cov_kwds={"groups": long["cid"]})
    return float(np.exp(m.params["treated"]) - 1), float(m.pvalues["treated"])


def did_with_ci(wide, ycol, n_boot=1000):
    """Pooled matched DiD across grant-centuries, with cohort-resampled bootstrap CI."""
    d = wide.copy()
    d["gc"] = np.floor(d[ycol] / 100.0) * 100
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
            return np.nan
        wsum = sum(n for n, _ in rows)
        return sum(n * v for n, v in rows) / wsum
    point = one(d)
    boots = []
    idx = np.arange(len(d))
    for _ in range(n_boot):
        b = one(d.iloc[rng.choice(idx, len(idx), replace=True)])
        if not np.isnan(b):
            boots.append(b)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(np.exp(point) - 1), float(np.exp(lo) - 1), float(np.exp(hi) - 1)


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


def main():
    res = {}
    # Viabundus staples & fairs
    panel, wide = build_panel("in_cne")
    for kind in ["staple", "fair"]:
        lp = panel.rename(columns={f"has_{kind}": "treated"})[["cid", "year", "lpop", "treated"]]
        nv, p = naive(lp)
        dd, lo, hi = did_with_ci(wide, f"{kind}_year")
        pr, po = pretrend(wide, f"{kind}_year")
        res[kind] = dict(source="Viabundus", naive=nv, naive_p=p, did=dd, ci=[lo, hi],
                         pre=pr, post=po, n_treat=int(wide[f"{kind}_year"].notna().sum()))
    # Cantoni charters & markets
    loc = attach_population(load_treatment_years())
    for kind, ycol in [("charter", "charter_year"), ("market", "market_year")]:
        from charter_did import to_long
        lp = to_long(loc, kind).rename(columns={"treated": "treated"})
        nv, p = naive(lp[["cid", "year", "lpop", "treated"]])
        dd, lo, hi = did_with_ci(loc, ycol)
        pr, po = pretrend(loc, ycol)
        res[kind] = dict(source="Cantoni", naive=nv, naive_p=p, did=dd, ci=[lo, hi],
                         pre=pr, post=po, n_treat=int(loc[ycol].notna().sum()))
    json.dump(res, open(OUT / "causal_summary.json", "w"), indent=2)
    print(f"{'privilege':10s} {'source':10s} {'naive':>8s} {'p':>6s} {'DiD':>8s} "
          f"{'95% CI':>18s} {'preG':>6s} {'postG':>6s}")
    for k, v in res.items():
        print(f"{k:10s} {v['source']:10s} {v['naive']:+7.0%} {v['naive_p']:6.3f} "
              f"{v['did']:+7.0%} [{v['ci'][0]:+.0%},{v['ci'][1]:+.0%}]".ljust(60) +
              f" {v['pre']:+.2f} {v['post']:+.2f}")
    print("\nsaved out/causal_summary.json")


if __name__ == "__main__":
    main()
