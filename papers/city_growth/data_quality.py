"""Data-quality robustness for the Buringh population panel.

Buringh (2021) is not a set of clean observations: the 'nature' column flags
city-year values that are 'imputed' (city/time-specific interpolation) or
'proxied', and the 'source' column shows that many values are taken from
Bairoch — so Buringh and Bairoch are overlapping compilations, not fully
independent reconstructions. This script quantifies both facts and re-runs the
core results where they could bite:

  A. Share of imputed/proxied observations in the analysis sample, by century;
     core results (persistence, Gibrat, water premium, staple naive gap + DiD)
     re-run on non-imputed observations only.
  B. Share of 1200-1500 observations whose source cites Bairoch.
  C. Population-threshold robustness at 1k / 5k / 10k: populations are rounded
     to the nearest thousand, so growth rates of the smallest towns are the
     noisiest; the core results should not depend on them.

Writes out/07_data_quality.md and out/data_quality.json.
"""
from __future__ import annotations
import json
import numpy as np, pandas as pd, statsmodels.api as sm
from pathlib import Path
from panel import load_buringh, wide_pop
from privileges import privilege_years, _nearest_grant
from coverage import viabundus_flag

OUT = Path(__file__).resolve().parent / "out"
YEARS = (1100, 1200, 1300, 1400, 1500)


def attach_staple(w):
    w = w.copy().reset_index(drop=True)
    st, _ = privilege_years()
    w["staple_year"] = _nearest_grant(w, st)
    w["in_via"] = viabundus_flag(w)
    return w


def core_results(w, th):
    """Persistence, Gibrat, water premium (1200->1500) and staple naive/DiD."""
    r = {"th": th}
    s = w[(w["pop1200"] >= th) & (w["pop1500"] >= th)].copy()
    r["n_1200_1500"] = len(s)
    if len(s) >= 30:
        l0, l1 = np.log(s["pop1200"]), np.log(s["pop1500"])
        r["persist_r2"] = float(np.corrcoef(l0, l1)[0, 1] ** 2)
        g = l1 - l0
        gb = sm.OLS(g, sm.add_constant(l0)).fit()
        r["gibrat_slope"] = float(gb.params.iloc[1]); r["gibrat_r2"] = float(gb.rsquared)
        s["water"] = ((s["on_river"] == 1) | (s["on_coast"] == 1)).astype(float)
        X = sm.add_constant(s[["water"]]); X["l0"] = l0
        wr = sm.OLS(g, X).fit(cov_type="HC1")
        r["water"] = float(wr.params["water"]); r["water_p"] = float(wr.pvalues["water"])
    # staple: inside Viabundus footprint only
    u = w[w["in_via"]].copy()
    u15 = u[u["pop1500"] >= th]
    if len(u15) >= 30 and u15["staple_year"].notna().sum() >= 3:
        ever = u15["staple_year"].notna().astype(float)
        ng = sm.OLS(np.log(u15["pop1500"]), sm.add_constant(ever)).fit()
        r["staple_naive"] = float(np.exp(ng.params.iloc[1]) - 1)
    d = u.copy()
    d["gc"] = np.floor(d["staple_year"] / 100.0) * 100
    rows = []
    for c in [1200, 1300, 1400]:
        c0, c1, c2 = f"pop{c-100}", f"pop{c}", f"pop{c+100}"
        base = d[(d[c0] >= th) & (d[c1] >= th) & (d[c2] >= th)].copy()
        if len(base) < 6:
            continue
        base["pre"] = np.log(base[c1]) - np.log(base[c0])
        base["post"] = np.log(base[c2]) - np.log(base[c1])
        tr = base[base["gc"] == c]
        ct = base[base["staple_year"].isna() | (base["staple_year"] > c)]
        if len(tr) < 3 or len(ct) < 3:
            continue
        rows.append((len(tr), (tr["post"].mean() - tr["pre"].mean()) -
                     (ct["post"].mean() - ct["pre"].mean())))
    if rows:
        r["staple_did"] = float(sum(n * v for n, v in rows) / sum(n for n, _ in rows))
        r["staple_did_ntreat"] = int(sum(n for n, _ in rows))
    return r


def fmt(r):
    out = f"    th={r['th']:>6.0f}: n={r.get('n_1200_1500', 0):4d}"
    if "persist_r2" in r:
        out += (f"  persist r2={r['persist_r2']:.3f}  gibrat R2={r['gibrat_r2']:.3f}"
                f"  water={r['water']:+.3f} (p={r['water_p']:.3f})")
    if "staple_did" in r:
        out += f"  stapleDiD={r['staple_did']:+.3f} (nT={r['staple_did_ntreat']})"
    return out


def main():
    md = ["# Data quality: imputation, source overlap, thresholds\n"]
    res = {}
    df = load_buringh()
    df["observed"] = df["nature"].isna()
    df["from_bairoch"] = df["source"].astype(str).str.lower().str.startswith("bai")

    # ---- A. imputation shares in the analysis sample
    sub = df[df["in_cne"] & df["year"].isin([1200, 1300, 1400, 1500]) & (df["pop"] >= 1000)]
    share_by_year = (1 - sub.groupby("year")["observed"].mean()).round(3)
    res["share_imputed_by_year"] = {int(k): float(v) for k, v in share_by_year.items()}
    res["share_imputed_total"] = float(1 - sub["observed"].mean())
    res["share_bairoch_sourced"] = float(sub["from_bairoch"].mean())
    print("A. IMPUTATION (CNE sample, pop>=1000, 1200-1500)")
    print(f"   imputed/proxied share: {res['share_imputed_total']:.1%}  "
          f"by year: {dict(share_by_year)}")
    print(f"   observations citing Bairoch as source: {res['share_bairoch_sourced']:.1%}")
    md.append(f"Imputed/proxied share of city-year observations (CNE, pop>=1k, "
              f"1200-1500): **{res['share_imputed_total']:.1%}** "
              f"(by year: {dict(share_by_year)}). Observations whose source field cites "
              f"Bairoch: {res['share_bairoch_sourced']:.1%} — the two reconstructions "
              f"overlap and are not fully independent.\n")

    # ---- core results: all obs vs non-imputed only (th=1000)
    w_all = attach_staple(wide_pop(df[df["in_cne"]], years=YEARS))
    w_obs = attach_staple(wide_pop(df[df["in_cne"] & df["observed"]], years=YEARS))
    r_all = core_results(w_all, 1000.0)
    r_obs = core_results(w_obs, 1000.0)
    res["all_obs"] = r_all; res["non_imputed"] = r_obs
    print("\nB. CORE RESULTS: all observations vs non-imputed only (th=1000)")
    print("  all:        " + fmt(r_all))
    print("  non-imputed:" + fmt(r_obs))
    md.append("## Core results, all vs non-imputed observations (threshold 1,000)\n")
    md.append("| sample | n(1200&1500) | persistence r2 | Gibrat R2 | water premium | staple DiD |\n|---|---|---|---|---|---|")
    for lab, r in [("all observations", r_all), ("non-imputed only", r_obs)]:
        md.append(f"| {lab} | {r.get('n_1200_1500','—')} | {r.get('persist_r2', float('nan')):.3f} | "
                  f"{r.get('gibrat_r2', float('nan')):.3f} | {r.get('water', float('nan')):+.3f} "
                  f"(p={r.get('water_p', float('nan')):.3f}) | "
                  f"{r.get('staple_did', float('nan')):+.3f} (nT={r.get('staple_did_ntreat', 0)}) |")

    # ---- C. threshold robustness on the full panel
    print("\nC. THRESHOLD ROBUSTNESS (all observations)")
    md.append("\n## Population-threshold robustness (all observations)\n")
    md.append("| threshold | n(1200&1500) | persistence r2 | Gibrat R2 | water premium | staple DiD |\n|---|---|---|---|---|---|")
    res["thresholds"] = []
    for th in [1000.0, 5000.0, 10000.0]:
        r = core_results(w_all, th)
        res["thresholds"].append(r)
        print(fmt(r))
        md.append(f"| {th:,.0f} | {r.get('n_1200_1500','—')} | "
                  f"{r.get('persist_r2', float('nan')):.3f} | "
                  f"{r.get('gibrat_r2', float('nan')):.3f} | "
                  f"{r.get('water', float('nan')):+.3f} (p={r.get('water_p', float('nan')):.3f}) | "
                  f"{r.get('staple_did', float('nan')):+.3f} (nT={r.get('staple_did_ntreat', 0)}) |")

    (OUT / "07_data_quality.md").write_text("\n".join(md))
    json.dump(res, open(OUT / "data_quality.json", "w"), indent=2)
    print("\nwrote out/07_data_quality.md, out/data_quality.json")


if __name__ == "__main__":
    main()
