"""Is the water-access growth premium CONSTANT, or does it switch on over time?

If geography were 'destiny', the coastal/river premium on growth would be
stable across centuries. If instead a change in TRADE REGIME activated
geography, the premium should be ~0 early and rise sharply later.

We test this three ways on the full Buringh panel (all cities, not just the
Viabundus subset), with sea-basin resolution (Atlantic/North Sea vs Baltic vs
Mediterranean) to connect to the 'rise of the Atlantic economy' hypothesis.
"""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
from panel import load_buringh, wide_pop, first_nature

TH = 1000.0
STEPS = [(1000, 1100), (1100, 1200), (1200, 1300), (1300, 1400), (1400, 1500),
         (1500, 1600), (1600, 1700)]


def growth_by_period(region_filter="in_cne"):
    w = wide_pop(load_buringh(), years=(1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700))
    d = w[w[region_filter]].copy()
    print("=" * 78)
    print(f"WATER-ACCESS GROWTH PREMIUM BY PERIOD   (sample: {region_filter}, threshold pop>={TH:.0f})")
    print("  g ~ log pop0 + on_river + on_coast, per 100-yr step. Coefs = extra log-growth.")
    print("=" * 78)
    print(f"  {'period':12s} {'n':>4s} {'meanG':>7s} {'river':>8s} {'coast':>8s} "
          f"{'p_riv':>6s} {'p_cst':>6s}")
    rows = []
    for y0, y1 in STEPS:
        c0, c1 = f"pop{y0}", f"pop{y1}"
        if c0 not in d or c1 not in d:
            continue
        s = d[(d[c0] >= TH) & (d[c1] >= TH)].copy()
        if len(s) < 30:
            continue
        s["g"] = np.log(s[c1]) - np.log(s[c0])
        X = sm.add_constant(s[["on_river", "on_coast"]].astype(float))
        X["lpop0"] = np.log(s[c0])
        r = sm.OLS(s["g"], X).fit(cov_type="HC1")
        rows.append((f"{y0}-{y1}", len(s), s["g"].mean(),
                     r.params["on_river"], r.params["on_coast"],
                     r.pvalues["on_river"], r.pvalues["on_coast"]))
        print(f"  {y0}-{y1:<7d} {len(s):>4d} {s['g'].mean():>7.3f} "
              f"{r.params['on_river']:>+8.3f} {r.params['on_coast']:>+8.3f} "
              f"{r.pvalues['on_river']:>6.3f} {r.pvalues['on_coast']:>6.3f}")
    return rows


def sea_basin_timing(region_filter="in_cne"):
    """Resolve coast premium by sea basin, per period."""
    w = wide_pop(load_buringh(), years=(1200, 1300, 1400, 1500, 1600))
    d = w[w[region_filter]].copy()
    print("\n" + "=" * 78)
    print("COASTAL PREMIUM BY SEA BASIN & PERIOD (Atlantic/NorthSea vs Baltic vs Med)")
    print("=" * 78)
    d["atl_ns"] = ((d["atlantic"] == 1) | (d["northsea"] == 1)).astype(float)
    d["balt"] = (d["baltic"] == 1).astype(float)
    d["med"] = (d["medit"] == 1).astype(float)
    for y0, y1 in [(1200, 1300), (1300, 1400), (1400, 1500), (1500, 1600)]:
        c0, c1 = f"pop{y0}", f"pop{y1}"
        s = d[(d[c0] >= TH) & (d[c1] >= TH)].copy()
        if len(s) < 30:
            continue
        s["g"] = np.log(s[c1]) - np.log(s[c0])
        X = sm.add_constant(s[["on_river", "atl_ns", "balt", "med"]])
        X["lpop0"] = np.log(s[c0])
        r = sm.OLS(s["g"], X).fit(cov_type="HC1")
        print(f"  {y0}-{y1}: river={r.params['on_river']:+.2f} "
              f"AtlNS={r.params['atl_ns']:+.2f}(p{r.pvalues['atl_ns']:.2f}) "
              f"Baltic={r.params['balt']:+.2f}(p{r.pvalues['balt']:.2f}) "
              f"Med={r.params['med']:+.2f}(p{r.pvalues['med']:.2f})  n={len(s)}")


def stacked_panel_interaction(region_filter="in_cne"):
    """Pooled panel with city & period effects and water x period interactions.
    Cleanest single test of 'does the water premium grow over time'."""
    df = load_buringh()
    df = df[df[region_filter] & (df["year"].isin([1200, 1300, 1400, 1500, 1600]))].copy()
    df = df[df["pop"] >= TH].copy()
    df["lpop"] = np.log(df["pop"])
    fn = df["transport"].apply(first_nature).apply(pd.Series)
    df = pd.concat([df.reset_index(drop=True), fn.reset_index(drop=True)], axis=1)
    df["water"] = ((df["on_river"] == 1) | (df["on_coast"] == 1)).astype(float)
    print("\n" + "=" * 78)
    print("STACKED PANEL: log(pop) ~ year FE + water*year   (period-varying water premium)")
    print("=" * 78)
    base = df["year"].min()
    for y in sorted(df["year"].unique()):
        df[f"yr{y}"] = (df["year"] == y).astype(float)
        df[f"water_x_{y}"] = df["water"] * (df["year"] == y).astype(float)
    yrcols = [f"yr{y}" for y in sorted(df["year"].unique()) if y != base]
    wxcols = [f"water_x_{y}" for y in sorted(df["year"].unique()) if y != base]
    X = sm.add_constant(df[["water"] + yrcols + wxcols])
    r = sm.OLS(df["lpop"], X).fit(cov_type="cluster", cov_kwds={"groups": df["cid"]})
    print(f"  water (baseline {base}): {r.params['water']:+.3f} (p={r.pvalues['water']:.3f})")
    print("  water premium relative to baseline, by year (cumulative interaction):")
    for c in wxcols:
        y = c.split("_")[-1]
        tot = r.params["water"] + r.params[c]
        print(f"    {y}: extra={r.params[c]:+.3f} (p={r.pvalues[c]:.3f})  "
              f"=> total water premium {tot:+.3f} log ({np.exp(tot)-1:+.0%})")


if __name__ == "__main__":
    growth_by_period("in_cne")
    sea_basin_timing("in_cne")
    stacked_panel_interaction("in_cne")
